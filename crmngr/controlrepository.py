""" crmngr controlrepository module """

# stdlib
from collections import defaultdict
from collections import OrderedDict
from itertools import chain
import logging
import os
import re
import sys
from tempfile import TemporaryDirectory
from textwrap import TextWrapper

# crmgnr
from crmngr.cache import JsonCache
from crmngr.forgeapi import ForgeApi, ForgeError
from crmngr.git import Repository
from crmngr.git import GitError
from crmngr.puppetfile import Forge
from crmngr.puppetfile import ForgeModule
from crmngr.puppetfile import GitBranch
from crmngr.puppetfile import GitCommit
from crmngr.puppetfile import GitModule
from crmngr.puppetfile import GitTag
from crmngr.puppetfile import PuppetModule
from crmngr import cprint
from crmngr.utils import fnlistmatch
from crmngr.utils import query_yes_no

# 3rd-party
from natsort import natsorted

LOG = logging.getLogger(__name__)


class NoEnvironmentError(Exception):
    """exception raised when no environment is matched"""


class PuppetEnvironment:
    """r10k puppet environment"""

    def __init__(self, name, modules=None):
        """initialize puppet environment"""
        self._name = name
        self._modules = modules or OrderedDict()
        LOG.debug('initialize PuppetEnvironment(%s)', self._name)

    def __repr__(self):
        return self._name

    def __iter__(self):
        return iter(self._modules.items())

    def __delitem__(self, key):
        del self._modules[key]

    def __getitem__(self, item):
        return self._modules[item]

    def __setitem__(self, key, value):
        self._modules[key] = value
        LOG.debug('added %s(%s) for PuppetEnvironment(%s)',
                  key,
                  vars(value),
                  self.name)

    def __lt__(self, other):
        return str(other) > str(self)

    @property
    def modules(self):
        """Returns a list of modules in the puppet environment"""
        return self._modules

    @property
    def name(self):
        """Returns the name of the current puppet environment"""
        return self._name

    @property
    def puppetfile(self):
        """Returns the puppetfile reprensentation as iterator"""
        for _, module in sorted(self._modules.items()):
            yield module.puppetfile


class ControlRepository(Repository):
    """r10k-style control repository"""

    def __init__(self, clone_url, environments=None, modules=None):
        """clone control repository and parse the puppetfiles it contains."""
        super().__init__(clone_url)

        self._environments = []
        self._parse_puppetfiles(
            puppetfiles=self._collect_puppetfiles(environments),
            puppetmodules=modules,
        )

    @property
    def environments(self):
        """returns a list of all environment objects"""
        return self._environments

    @property
    def environment_names(self):
        """return a set of all environment names"""
        return set([environment.name for environment in self._environments])

    def get_environment(self, environment):
        """return a specifc environment"""
        return next(env
                    for env in self._environments if env.name == environment)

    def clone_environment(self, base_env, new_env, *, report=True):
        """creates a new environment as a clone of an existing one."""
        self.git(['checkout', base_env])
        self.git(['checkout', '--orphan', new_env])
        self.git(['commit', '-m', 'Initialize new environment.'])
        self.git(['push', 'origin', new_env])

        if report:
            # reread control repository with only new environment
            self._environments = []
            self._parse_puppetfiles(
                self._collect_puppetfiles([new_env, ])
            )

    def delete_environment(self, environment):
        """deletes an existing environment."""
        self.git(['push', 'origin', ':%s' % environment])

    def new_environment(self, new_env, *, report=True):
        """creates a new empty environment."""
        self.git(['checkout', '--orphan', new_env])
        self.git(['reset', '--hard'])

        with open(os.path.join(self._workdir, 'Puppetfile'), 'w') as puppetfile:
            puppetfile.write("forge 'http://forge.puppetlabs.com'\n\n")
        self.git(['add', 'Puppetfile'])
        os.mkdir(os.path.join(self._workdir, 'manifests'))
        with open(os.path.join(self._workdir, 'manifests', 'site.pp'),
                  'w') as site_pp:
            site_pp.write("hiera_include('classes')")
        self.git(['add', os.path.join('manifests', 'site.pp')])
        self.git(['commit', '-m', 'Initialize new environment.'])
        self.git(['push', 'origin', new_env])
        if report:
            # reread control repository with only new environment
            self._environments = []
            self._parse_puppetfiles(
                self._collect_puppetfiles([new_env, ])
            )

    def _collect_puppetfiles(self, environments=None):
        """collect Puppetfile from all control repository branches.

        This will return a dictionary with environments as keys and a list of
        every Puppetfile mod line as value.

        Mulitiline mod lines are collapsed, empty and comment lines ignored.
        """

        puppetfiles = {}

        for branch in self.branches:
            if environments is not None:
                if environments[0] == '!':
                    if fnlistmatch(branch, patterns=environments[1:]):
                        LOG.debug(
                            ('branch %s does match an exclude pattern '
                             '%s. Skipping.'),
                            branch,
                            environments[1:]
                        )
                        continue
                else:
                    if not fnlistmatch(branch, patterns=environments):
                        LOG.debug(
                            ('branch %s does not match any include pattern '
                             '%s. Skipping.'),
                            branch,
                            environments
                        )
                        continue

            self.git(['checkout', branch])
            with open(os.path.join(self._workdir, 'Puppetfile')) as puppetfile:
                puppetfiles[branch] = self._collapse_puppetfile(
                    puppetfile.readlines()
                )

        if puppetfiles:
            return puppetfiles
        else:
            raise NoEnvironmentError

    @staticmethod
    def _collapse_puppetfile(lines):
        """remove whitespace and comments from puppetfile lines"""
        puppetfile_lines = []
        re_comment = re.compile(r'^\s*#')
        re_mod = re.compile(r'^\s*mod')
        line_buffer = None
        for line in lines:
            stripped_line = line.strip()
            # skip empty line or comment
            if stripped_line == '' or re_comment.match(stripped_line):
                continue
            # processing multiline mod-block
            if line_buffer:
                # append current line to buffer
                line_buffer += stripped_line
                # if line does not end with a comma, we are done
                if not stripped_line.endswith(','):
                    puppetfile_lines.append(line_buffer)
                    line_buffer = None
                    continue
            # we are not processing a multiline block, only mod lines
            # are interesting
            if re_mod.match(stripped_line):
                # start processing of multiline mod-block
                if stripped_line.endswith(','):
                    line_buffer = stripped_line
                else:
                    puppetfile_lines.append(stripped_line)
        return puppetfile_lines

    def _parse_puppetfiles(self, puppetfiles, puppetmodules=None):
        """extract module information from puppetfiles"""
        for environment, modulelines in puppetfiles.items():
            puppetenvironment = PuppetEnvironment(
                environment
            )
            for moduleline in modulelines:
                LOG.debug('processing module %s in environment %s',
                          moduleline,
                          environment)
                module_object = PuppetModule.from_moduleline(
                    moduleline
                )
                if puppetmodules is not None:
                    if puppetmodules[0] == '!':
                        if fnlistmatch(module_object.name,
                                       patterns=puppetmodules[1:]):
                            LOG.debug(
                                ('module %s does match an exclude pattern %s. '
                                 'Skipping.'),
                                module_object.name,
                                puppetmodules[1:]
                            )
                            continue
                    else:
                        if not fnlistmatch(module_object.name,
                                           patterns=puppetmodules):
                            LOG.debug(
                                ('module %s does not match any include pattern '
                                 '%s. Skipping.'),
                                module_object.name,
                                puppetmodules
                            )
                            continue
                puppetenvironment[module_object.name] = module_object
            self._environments.append(puppetenvironment)

    @staticmethod
    def _bulk_update(environment, *, modules, cache):
        """updates modules in environment to latest version."""
        cprint.white_bold('Bulk update environment {}'.format(environment.name))
        for _, module in environment:
            if modules is not None:
                if modules[0] == '!':
                    if fnlistmatch(module.name, patterns=modules[1:]):
                        LOG.debug('module %s does match an exclude pattern %s. '
                                  'Skipping.', module.name, modules[1:])
                        continue
                else:
                    if not fnlistmatch(module.name, patterns=modules):
                        LOG.debug('module %s does not match any include '
                                  'pattern %s. Skipping.', module.name, modules)
                        continue
            try:
                cprint.white('Get latest version for module {}'.format(
                    module.name
                ))
                module.version = module.get_latest_version(cache)
            except TypeError:
                LOG.debug('Could not determine latest module version for '
                          'module %s. Setting to None.', module.name)
                cprint.yellow_bold('Could not determine latest module version '
                                   'for module {}!'.format(module.name))
                module.version = None
        return environment

    @staticmethod
    def _bulk_remove(environment, *, modules):
        """bulk remove modules from an environment."""
        cprint.white_bold(
            'Bulk remove modules from environment {}'.format(environment.name)
        )
        for _, module in environment.modules.copy().items():
            if modules is not None:
                if modules[0] == '!':
                    if fnlistmatch(module.name, patterns=modules[1:]):
                        LOG.debug('module %s does match an exclude pattern %s. '
                                  'Skipping.', module.name, modules[1:])
                        continue
                else:
                    if not fnlistmatch(module.name, patterns=modules):
                        LOG.debug('module %s does not match any include '
                                  'pattern %s. Skipping.', module.name, modules)
                        continue
            LOG.debug('remove module %s from environment %s',
                      module.name, environment.name)
            del environment[module.name]
        return environment

    @staticmethod
    def _reference_update(environment, *, reference, add=False, remove=True):
        """updates an environment based on a reference branch."""
        if add and remove:
            # if we set both add and remove, we basically replace
            # the environment with the template
            environment = PuppetEnvironment(environment.name,
                                            reference.modules)
            LOG.debug('replaced environment %s with %s',
                      environment.name,
                      reference.name)
        else:
            for _, module in environment.modules.copy().items():
                if module.name in reference.modules:
                    environment[module.name] = reference[module.name]
                    LOG.debug('module %s in environemnt %s has been replaced '
                              'with version from reference environment %s',
                              module.name, environment.name, reference.name)
                if remove and (module.name not in reference.modules):
                    del environment[module.name]
                    LOG.debug('removed module %s from environment %s as it is '
                              'not present in the reference environment %s',
                              module.name, environment.name, reference.name)
            if add:
                # add modules missing in environment branch (but present in
                # reference branch)
                for module in (set(reference.modules) -
                               set(environment.modules)):
                    environment[module] = reference[module]
        return environment

    @staticmethod
    def _update_forge_module(module_string, version):
        """return new version of a single forge module"""
        module = ForgeModule(*PuppetModule.parse_module_name(
            module_string
        ))
        forge_api = ForgeApi(name=module.name, author=module.author)
        if version is None:
            module.version = None
        elif version == 'LATEST_FORGE_VERSION':
            try:
                module.version = Forge(forge_api.current_version['version'])
            except ForgeError as exc:
                cprint.red(
                    'Could not determine latest version of forge '
                    'module {author}/{module}: {error}'.format(
                        author=module.author,
                        module=module.name,
                        error=exc,
                    )
                )
                sys.exit(1)
        else:
            try:
                if not forge_api.has_version(version):
                    cprint.red(
                        '{version} is not a valid version for module '
                        '{author}/{module}'.format(
                            version=version,
                            author=module.author,
                            module=module.name,
                        )
                    )
                    sys.exit(1)
            except ForgeError as exc:
                cprint.red(
                    'Could not verify version {version} of forge '
                    'module {author}/{module}: {error}'.format(
                        version=version,
                        author=module.author,
                        module=module.name,
                        error=exc,
                    )
                )
                sys.exit(1)
            module.version = Forge(version)
        return module

    def _update_git_module(self, module_string, *, url, branch, commit, tag):
        """return new version of a single git module"""
        # pylint: disable=too-many-branches
        module_name = PuppetModule.parse_module_name(module_string).module

        if url == 'USE_EXISTING_URL':
            git_urls = {version.url: environments
                        for version, environments in
                        self.modules[module_name].items()
                        if isinstance(version, GitModule)}
            if len(git_urls) > 1:
                cprint.red('Multiple URLs for {module} found across specified '
                           'environments:\n - {urls}'.format(
                               module=module_name,
                               urls='\n - '.join([
                                   "{url} ({environments})".format(
                                       url=url,
                                       environments=', '.join(
                                           sorted(environments)
                                       )
                                   )
                                   for url, environments in sorted(
                                       git_urls.items()
                                   )
                               ])
                           ))
                cprint.red('Specify an URL using --git option or restrict the '
                           'update to environments using the same URL for '
                           '{}'.format(module_name))
                sys.exit(1)
            elif len(git_urls) < 1:
                cprint.red('Git module {module} not in any of the specified '
                           'environments. To switch from forge to git for '
                           '{module}, pass an URL to --git.'.format(
                               module=module_name
                           ))
                sys.exit(1)
            url = list(git_urls)[0]
        try:
            module_repository = Repository(url)
        except GitError as exc:
            cprint.red(
                '{url} is not a valid git repository: {error}'.format(
                    url=url,
                    error=exc,
                )
            )
            sys.exit(1)
        module = GitModule(module_name, url=url)
        if branch is not None:
            try:
                module_repository.git(['fetch', '--unshallow'])
                module_repository.validate_branch(branch)
                module.version = GitBranch(branch)  # pylint: disable=R0204
            except GitError as exc:
                cprint.red('Could not verify branch {branch} for {module}: '
                           '{error}'.format(
                               branch=branch,
                               module=module.name,
                               error=exc
                           ))
                sys.exit(1)
        elif commit is not None:
            try:
                module_repository.git(['fetch', '--unshallow'])
                module_repository.validate_commit(commit)
                module.version = GitCommit(commit)  # pylint: disable=R0204
            except GitError as exc:
                cprint.red('Could not verify commit {commit} for {module}: '
                           '{error}'.format(
                               commit=commit,
                               module=module.name,
                               error=exc
                           ))
                sys.exit(1)
        elif tag is not None:
            if tag == 'LATEST_GIT_TAG':
                try:
                    module.version = GitTag(  # pylint: disable=R0204
                        module_repository.latest_tag.name
                    )
                except GitError as exc:
                    cprint.red('Could not determine latest tag for git module '
                               '{module}: {error}'.format(
                                   module=module.name,
                                   error=exc,
                               ))
                    sys.exit(1)
            else:
                try:
                    module_repository.git(['fetch', 'origin', '--tags'])
                    module_repository.validate_tag(tag)
                    module.version = GitTag(tag)  # pylint: disable=R0204
                except GitError as exc:
                    cprint.red('Could not verify tag {tag} for {module}: '
                               '{error}'.format(
                                   tag=tag,
                                   module=module.name,
                                   error=exc
                               ))
                    sys.exit(1)
        return module

    def update_puppetfiles(self, *, cli_args):
        """update puppetfiles"""
        with TemporaryDirectory(prefix='crmngr_update_cache') as cache_dir:
            reference = None
            module = None

            update_cache = JsonCache(cache_dir)
            if cli_args.reference:
                try:
                    reference = self.get_environment(cli_args.reference)
                except StopIteration:
                    cprint.red('%s specified as reference environment does not '
                               'exist' % cli_args.reference)
                    sys.exit(1)
            elif cli_args.git_url and not cli_args.remove:
                module = self._update_git_module(  # pylint: disable=R0204
                    module_string=cli_args.modules[0],
                    url=cli_args.git_url,
                    branch=cli_args.git_branch,
                    commit=cli_args.git_commit,
                    tag=cli_args.git_tag,
                )
            elif cli_args.forge and not cli_args.remove:
                module = self._update_forge_module(  # pylint: disable=R0204
                    module_string=cli_args.modules[0],
                    version=cli_args.forge_version,
                )
            for environment in sorted(self._environments):
                # reference update mode
                commit_message = 'Update Environment'
                if reference:
                    if environment == reference:
                        # when having a reference environment, it will be in the
                        # control repository. So we skip it.
                        continue
                    environment = self._reference_update(
                        environment,
                        reference=reference,
                        add=cli_args.add,
                        remove=cli_args.remove,
                    )
                    commit_message = 'Update {} based on {}.'.format(
                        environment.name,
                        reference.name,
                    )
                elif module is not None:
                    if cli_args.add or module.name in environment.modules:
                        environment[module.name] = module
                        commit_message = module.update_commit_message
                elif cli_args.remove:
                    environment = self._bulk_remove(
                        environment,
                        modules=cli_args.modules,
                    )
                    commit_message = 'Bulk update {}.'.format(environment.name)
                # bulk update mode (i.e. no version / update options specified)
                else:
                    environment = self._bulk_update(
                        environment,
                        modules=cli_args.modules,
                        cache=update_cache,
                    )
                    commit_message = 'Bulk update {}.'.format(environment.name)
                self.write_puppetfile(
                    commit_message=commit_message,
                    diff_only=cli_args.diffonly,
                    environment=environment,
                    non_interactive=cli_args.noninteractive,
                )

    def write_puppetfile(self, environment, *,
                         commit_message='Update Puppetfile', diff_only=False,
                         non_interactive=False):
        """write a PuppetEnvironment to a Puppetfile"""
        self.git(['checkout', environment.name])
        with open(os.path.join(self._workdir, 'Puppetfile'),
                  'w') as puppetfile:
            LOG.debug('write new version of Puppetfile in environment %s',
                      environment.name)
            # write file header
            puppetfile.write("forge 'http://forge.puppetlabs.com'\n\n")
            # write module lines
            puppetfile.writelines(
                ('{}\n'.format(line)
                 for line in chain.from_iterable(environment.puppetfile))
            )
        # ask git for a diff
        diff = self.git(['diff'])
        if diff:
            if not non_interactive:
                cprint.white_bold(
                    'Diff for environment %s:' % environment.name
                )
                cprint.diff(diff)
            if diff_only:
                # revert pending changes
                self.git(['checkout', '--', 'Puppetfile'])
            else:
                if non_interactive or query_yes_no(
                        'Update (commit and push) Puppetfile for '
                        'environment {}'.format(environment.name)):
                    # commit and push pending changes
                    self.git(
                        ['commit', '-m', commit_message, 'Puppetfile']
                    )
                    try:
                        self.git(['push', 'origin', environment.name])
                        cprint.green('Updated environment {}'.format(
                            environment.name
                        ))
                    except GitError as exc:
                        cprint.red(
                            'Could not update environment {environment}. '
                            'Maybe somebody else pushed changes to '
                            '{environment} during current crmngr run. '
                            'Full git error: {error}'.format(
                                environment=environment.name,
                                error=exc,
                            ))
                        sys.exit(1)
                else:
                    # revert pending changes
                    self.git(['checkout', '--', 'Puppetfile'])
        else:
            LOG.debug('Puppetfile for environment %s unchanged', environment.name)

    @property
    def modules(self):
        """returns modules and module versions.

        This will return a dict containing all modules with their versions and
        environments they are deployed in.
        """
        modules = defaultdict(lambda: defaultdict(set))
        for environment in self._environments:
            for module, module_object in environment:
                modules[module][module_object].add(environment.name)
        return modules

    def report(self, wrap=True, version_check=True, version_cache=None,
               compare=True):
        """print control repository report"""

        for module, versions in sorted(self.modules.items()):

            # in compare mode, skip modules that are identical in all processed
            # environments.
            if compare and len(versions) == 1 and \
                            len(list(versions.values())[0]) == len(self._environments):
                continue

            cprint.white_bold('Module: %s' % module)
            for version, environments in natsorted(
                    versions.items(),
                    reverse=True,
                    key=str
            ):
                version.print_version_information(
                    version_check,
                    version_cache
                )
                if len(self._environments) > 1:
                    cprint.white('Used by:', lpad=4, rpad=4, end='')
                    if wrap:
                        used_by = TextWrapper(
                            subsequent_indent=' ' * 16
                        )
                        for line in used_by.wrap(
                                ' '.join(sorted(environments))
                        ):
                            cprint.cyan(line)
                    else:
                        cprint.cyan(' '.join(sorted(environments)))
                print()

            if compare:
                # check for modules that are in not in all (but in at least one)
                # processed environments
                missing = set.union(*list(versions.values())) ^ set(
                    [environment.name for environment in self._environments]
                )
                if missing:
                    cprint.yellow_bold('Missing from:', lpad=2)
                    if wrap:
                        not_in = TextWrapper(
                            initial_indent=' ' * 16,
                            subsequent_indent=' ' * 16
                        )
                        for line in not_in.wrap(
                                ' '.join(sorted(missing))
                        ):
                            cprint.yellow(line)
                    else:
                        print(' ' * 16, end='')
                        cprint.yellow(' '.join(sorted(missing)))
                    print()
