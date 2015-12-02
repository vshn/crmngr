#!/usr/bin/env python3

"""manage a r10k-style control repository"""

import configparser
import fnmatch
import logging
import os
import re
from textwrap import TextWrapper
from .git import Git
from .forge import get_forge_module_info, verify_module_version
from .utils import cprint, fnlistmatch, query_yes_no, sha256
from .puppetmodules import PuppetModule, GitModule, ForgeModule
from .puppetmodules.versions import Forge, GitBranch, GitCommit, GitRef, GitTag

__author__ = "Andre Keller <andre.keller@vshn.ch>"
__copyright__ = "Copyright (c) 2015, VSHN AG, info@vshn.ch"
__license__ = 'BSD'
__version__ = '1.0.0'

LOG = logging.getLogger(__name__)


class Report:
    """control repository report"""

    def __init__(
            self,
            config,
            tmpdir,
            cache=None,
            args=None):
        self._branches = {}
        self._modules = {}

        self._cache = cache
        self._config = config
        self._args = args
        self._tmpdir = tmpdir

        self._git = Git(self._tmpdir, self._cache)
        self._process()

    @property
    def branches(self):
        """control repository branches"""
        return tuple(self._branches.keys())

    @property
    def modules(self):
        """all modules (from all control repository branches)"""
        return tuple(self._modules.keys())

    @staticmethod
    def _parse_mod_name(full_mod_name):
        """split full module name into module name and author"""
        mod_name = full_mod_name.rsplit('/', 1)
        if len(mod_name) > 1:
            return mod_name[1], mod_name[0]
        else:
            return mod_name[0], None

    @staticmethod
    def _extract_version_info(mod_line):
        """extract version information from module line"""
        version_info = {}
        for fragment in mod_line:
            clean = fragment.strip(' \'"')
            # if part does not start with a colon, it is a plain
            # version number (i.e. a forge module)
            if clean.startswith(':'):
                if clean.startswith(':git'):
                    version_info['url'] = clean.rsplit(
                        '>', 1
                    )[1].strip(' \'"')
                    version_info['type'] = 'git'
                elif clean.startswith(':commit'):
                    version_info['commit'] = clean.rsplit(
                        '>', 1
                    )[1].strip(' \'"')
                elif clean.startswith(':ref'):
                    version_info['ref'] = clean.rsplit(
                        '>', 1
                    )[1].strip(' \'"')
                elif clean.startswith(':tag'):
                    version_info['tag'] = clean.rsplit(
                        '>', 1
                    )[1].strip(' \'"')
                elif clean.startswith(':branch'):
                    version_info['branch'] = clean.rsplit(
                        '>', 1
                    )[1].strip(' \'"')
            else:
                version_info['version'] = clean
        LOG.debug('Extracted version info %s from %s', version_info, mod_line)
        return version_info

    @staticmethod
    def _collapse_puppetfile_lines(puppetfile):
        """drop non-mod lines and collapse mod lines into a single line"""
        lines = []
        re_comment = re.compile(r'^(\s+)?#')
        re_mod = re.compile(r'^(\s+)?mod')
        line_buffer = None
        LOG.debug('Collapsing Puppetfile lines')
        for line in puppetfile:
            stripped_line = line.strip()
            # skip emtpy lines
            if not stripped_line:
                LOG.debug("Skipped empty line")
                continue
            # skip comments
            if re_comment.match(stripped_line):
                LOG.debug("Skipped comment: %s", stripped_line)
                continue
            # we are processing a multiline mod block
            if line_buffer:
                # append current line to buffer
                line_buffer = line_buffer + stripped_line
                LOG.debug('Added fragment to buffer: %s', stripped_line)
                # if line does not end with a comma,
                # means we are done processing this block
                if not stripped_line.endswith(','):
                    lines.append(line_buffer)
                    LOG.debug(
                        'Finished multiline block, added mod line: %s',
                        line_buffer
                    )
                    line_buffer = None
                    continue
            # unless we are processing a multiline block
            # only mod lines are interesting
            if re_mod.match(stripped_line):
                if stripped_line.endswith(','):
                    LOG.debug('Processing multiline block')
                    line_buffer = stripped_line
                    LOG.debug('Added fragment to buffer: %s', stripped_line)
                else:
                    lines.append(stripped_line)
                    LOG.debug('Added mod line: %s', stripped_line)
        return lines

    @staticmethod
    def _git_module_version(module_data):
        """returns git version object, based on module_data"""
        if 'branch' in module_data:
            return GitBranch(module_data['branch'])
        elif 'commit' in module_data:
            return GitCommit(module_data['commit'])
        elif 'ref' in module_data:
            return GitRef(module_data['ref'])
        elif 'tag' in module_data:
            return GitTag(module_data['tag'])
        return None


    def _module_object(self, name, module_data):
        """Returns a PuppetModule object for module_data"""
        if module_data['type'] == 'forge':
            forge_module = ForgeModule(name, module_data['author'])
            if 'version' in module_data:
                forge_module.version = Forge(module_data['version'])
            if self._args.version_check:
                forge_module.info = get_forge_module_info(
                    forge_module.forgename, self._cache
                )
            return forge_module
        else:
            git_module = GitModule(name, module_data['url'])
            if self._args.version_check:
                git_module.info = self._git.get_module_info(git_module.url)
                git_module.version = self._git_module_version(module_data)
            return git_module

    @staticmethod
    def forge_module_from_args(args):
        """Returns a ForgeModule object based on cli args"""
        module = ForgeModule(
            args.module.split('/')[1],
            args.module.split('/')[0]
        )
        if args.version:
            if args.version == 'LATEST_FORGE_VERSION':
                try:
                    forge_info = get_forge_module_info(args.module)
                    module.version = Forge(forge_info['version'])
                except (KeyError, TypeError) as exc:
                    raise RuntimeError(
                        "could not gather latest %s version" % args.module
                    ) from exc
            else:
                verify_module_version(args.module, args.version)
                module.version = Forge(args.version)
        else:
            try:
                forge_info = get_forge_module_info(args.module)
                _ = forge_info['version']
            except (KeyError, TypeError) as exc:
                raise RuntimeError(
                    "could find %s on forge" % args.module
                ) from exc
        return module

    def git_module_from_args(self, args):
        """Returns a GitModule object based on cli args"""
        module = GitModule(args.module.split("/")[-1], args.git)
        workdir = self._git.verify_git(args.git)
        if args.tag:
            if args.tag == 'LATEST_GIT_TAG':
                try:
                    git_info = self._git.get_module_info(args.git, False)
                    module.version = GitTag(git_info['version'])
                except (KeyError, TypeError) as exc:
                    raise RuntimeError(
                        "could not gather latest %s version" % args.module
                    ) from exc
            else:
                self._git.verify_git_tag(args.tag, workdir)
                module.version = GitTag(args.tag)
        elif args.commit:
            self._git.verify_git_commit(args.commit, workdir)
            module.version = GitCommit(args.commit)
        elif args.branch:
            self._git.verify_git_branch(args.branch, workdir)
            module.version = GitBranch(args.branch)
        else:
            self._git.clean_workdir(workdir)
        return module

    def module_from_args(self, args):
        """Returns a puppet module object based on cli args"""
        if not args.module:
            return None

        if args.remove:
            return PuppetModule(args.module.split("/")[-1])

        if args.git:
            return self.git_module_from_args(args)
        else:
            return self.forge_module_from_args(args)

    def _process(self):
        """process puppetfiles, extract module information"""
        puppetfiles = self._git.collect_puppetfiles(
            self._config.get('crmngr', 'repository')
        )

        for branch, puppetfile in puppetfiles.items():
            LOG.debug('Processing Puppetfile for branch: %s', branch)
            self._branches.setdefault(branch, [])

            # gather branch information (modules for each branch)
            mod_lines = self._collapse_puppetfile_lines(puppetfile)
            for mod_line in mod_lines:
                # split module line into comma-separated parts (starting after
                # 'mod ')
                line_parts = mod_line[4:].split(',')

                # if module_name contains a /, split it into
                # mod_name / mod_author
                mod_name, mod_author = self._parse_mod_name(
                    line_parts[0].strip(' \'"')
                )

                module_data = {}

                if mod_author:
                    module_data['author'] = mod_author
                    module_data['type'] = 'forge'
                # parse additional parts of mod line
                module_data.update(
                    self._extract_version_info(line_parts[1:])
                )

                # create module object
                module = self._module_object(mod_name, module_data)
                # add branch to modules used branch info
                module.add_branch(branch)

                # add module to module list, if not yet there
                self._modules.setdefault(module.name, {})

                # if current module version is in reports module list,
                # add branch to module versions used branch info
                if module in self._modules[module.name]:
                    self._modules[module.name][module].add_branch(branch)
                    LOG.debug(
                        "Added branch %s to %s's used branches",
                        branch, module
                    )
                else:
                    # add module version to reports module list.
                    self._modules[module.name].setdefault(module, module)
                    LOG.debug("Added module %s to reports module list", module)

                # also add module to reports branch list.
                self._branches[branch].append(module)
                LOG.debug(
                    "Added module %s to branch %s module list",
                    module, branch
                )

    def _get_module_categories(self):
        """Get categories from configuration file"""
        try:
            categories = [i.strip() for i in self._config.get(
                'crmngr', 'categories'
            ).split(',')]
            categories.append("uncategorized")
        except (configparser.NoOptionError, configparser.NoSectionError):
            categories = ["uncategorized"]
        LOG.debug("Categories defined in configuration file: %s", categories)
        return categories

    def _get_module_category(self, module, categories):
        """Get category for specific module (from configuration file)"""

        for category in categories:
            try:
                self._config.get(category, module)
                return category
            except (configparser.NoOptionError, configparser.NoSectionError):
                pass
        return "uncategorized"

    def prepare_puppetfiles(self, mode, branches, update_module=None):
        """return generated puppetfile for a specific branch"""
        puppetfiles = {}

        for branch in sorted(self._branches.keys()):
            LOG.debug("Prepare puppetfile for branch: %s", branch)
            if not fnlistmatch(branch, branches):
                LOG.debug(
                    "Skipped branch %s, not in requested branches list: %s",
                    branch,
                    branches
                )
                continue
            lines = [
                "forge 'http://forge.puppetlabs.com'",
                '',
            ]

            categories = self._get_module_categories()

            if mode == 'add':
                for module in self._branches[branch]:
                    if module.name == update_module.name:
                        break
                else:
                    self._branches[branch].append(update_module)
                    LOG.debug("Added module %s", update_module)

            module_lines = {}
            for module in sorted(self._branches[branch]):
                LOG.debug("Prepare module %s", module)
                if isinstance(update_module, PuppetModule):
                    if module.name == update_module.name:
                        if mode == 'remove':
                            LOG.debug("Remove module %s")
                            continue
                        module = update_module
                        LOG.debug(
                            "Ensure module version %s for module %s",
                            update_module, module.name
                        )
                module_category = self._get_module_category(
                    module.name, categories
                )
                module_lines.setdefault(module_category, [])
                module_lines[module_category] += module.puppetfile
                LOG.debug(
                    "Added module %s to puppetfile category %s",
                    module, module_category
                )

            for category in [i for i in categories if i in module_lines]:
                if len(categories) > 1:
                    lines.append("# %s modules ###" % category.upper())
                lines += module_lines[category]
                lines.append('')

            puppetfiles[branch] = lines

        return puppetfiles

    def update_puppetfiles(self, puppetfiles, commit_message):
        """update puppetfile"""
        for branch, puppetfile in sorted(puppetfiles.items()):
            LOG.debug("Write puppetfile for branch %s", branch)
            diff = self._git.write_puppetfile(branch, puppetfile)
            if diff:
                LOG.debug(
                    "Puppetfile differences for branch %s: %s", branch, diff
                )
                if not self._args.debug:
                    if not (self._args.diffonly or self._args.noninteractive):
                        if self._config.has_option('crmngr',
                                                   'console_clear_command'):
                            os.system(self._config.get('crmngr',
                                                       'console_clear_command'))
                if self._args.diffonly:
                    cprint.white_bold("Diff for branch %s" % branch)
                    cprint.diff(diff)
                    self._git.revert_puppetfile()
                elif self._args.noninteractive:
                    print('Updating Puppetfile in branch %s' % branch)
                    self._git.commit_puppetfile(branch, commit_message)
                else:
                    cprint.white_bold("Diff for branch %s" % branch)
                    cprint.diff(diff)
                    if query_yes_no("Update (commit and push) puppetfile for "
                                    "branch %s" % branch):
                        self._git.commit_puppetfile(branch, commit_message)
                    else:
                        self._git.revert_puppetfile()
            else:
                LOG.debug("Puppetfile for branch %s unchanged", branch)

    def print_module_report(self,
                            report_modules=None,
                            report_branches=None,
                            report_unused_branches=False):
        """print report aggregated by module"""

        requested_branches = []
        for module in sorted(self.modules):
            # check if we need to report this module at all...
            if not fnlistmatch(module, report_modules):
                LOG.debug(
                    'Module %s does not match requested modules pattern (%s). '
                    'Skipping',
                    module, report_modules
                )
                continue

            LOG.debug("Process module: %s", module)
            match = False
            for _, module_details in self._modules[module].items():
                if report_branches:
                    for requested_branch in report_branches:
                        for branch in module_details.branches:
                            if fnmatch.fnmatch(branch, requested_branch):
                                requested_branches.append(branch)
                                match = True
                else:
                    requested_branches = list(self.branches)
                    match = True

            LOG.debug(
                'Requested branches: %s (from pattern %s)',
                requested_branches, report_branches
            )

            if not match:
                LOG.debug(
                    'Module %s not in any of the requested branches. Skipping'
                )
                continue

            cprint.white_bold('Module: %s' % module)

            module_branches = []
            for _, module_details in sorted(
                    self._modules[module].items(), reverse=True):
                LOG.debug("Process module version %s", module_details)
                if not [i for i in module_details.branches
                        if i in set(requested_branches)]:
                    LOG.debug(
                        "Module version %s not in any of the requested "
                        "branches (%s). Skipping",
                        module_details,
                        requested_branches
                    )
                    continue
                module_branches += module_details.branches
                module_details.print_version_information()
                self._print_used_branches(
                    sorted(module_details.branches),
                    set(requested_branches)
                )
                print()
            if report_unused_branches:
                self._print_unused_branches(
                    module,
                    sorted(list(set(requested_branches) - set(module_branches)))
                )
                print()

    @staticmethod
    def _print_unused_branches(module, branches):
        """print list of branches that do not use a specific module"""
        if branches:
            cprint.white('Branches not using %s module:' % module, lpad=2)
            branch_wrapper = TextWrapper(
                initial_indent=' ' * 4,
                subsequent_indent=' ' * 4
            )
            for line in branch_wrapper.wrap(", ".join(branches)):
                cprint.yellow(line)

    @staticmethod
    def _print_used_branches(branches, requested_branches):
        """print list of branches used by a specific module"""
        if requested_branches:
            local_branches = [i for i in branches if i in requested_branches]
        else:
            local_branches = branches
        if local_branches:
            cprint.white('Used by:', lpad=4, rpad=4, end='')
            branch_wrapper = TextWrapper(
                subsequent_indent=' ' * 16
            )
            for line in branch_wrapper.wrap(", ".join(local_branches)):
                cprint.cyan(line)
