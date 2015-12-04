#!/usr/bin/env python3

"""git related functions for crmngrlib"""

import logging
import os
import shutil
import subprocess

from datetime import datetime

from .cache import JsonCache
from .utils import sha256

LOG = logging.getLogger(__name__)


class Git:
    """git object, holding cache and tmpdir information"""

    def __init__(self, tmpdir, cache=None, git_binary='git'):
        self._cache = cache
        self._controlbranches = []
        self._git_binary = git_binary
        self._tmpdir = tmpdir
        self._workdir = ""

    @property
    def controlbranches(self):
        """controlbranches in this git repository"""
        return self._controlbranches

    @controlbranches.setter
    def controlbranches(self, value):
        """controlbranches in this git repository (setter)"""
        self._controlbranches = value

    def cmd(self, cmds, output=False, **kwargs):
        """run git command"""
        cmds = [self._git_binary] + cmds  # prepend with git
        # output shall be captured
        LOG.debug('running git command: %s', ' '.join(cmds))
        if output:
            rval = subprocess.check_output(
                cmds,
                stderr=subprocess.STDOUT,
                **kwargs
            ).decode()
        # output does not matter, send it to /dev/null
        else:
            with open(os.devnull, 'w') as devnull:
                rval = subprocess.call(
                    cmds,
                    stdout=devnull,
                    stderr=devnull,
                    **kwargs
                )
        LOG.debug('git command return value: %s', rval)
        return rval

    @staticmethod
    def clean_workdir(workdir):
        """Remove workdir"""
        LOG.debug("Trying to remove workdir: %s", workdir)
        try:
            shutil.rmtree(workdir)
        except OSError:
            pass

    def verify_git(self, clone_url):
        """verify if git repository exists"""
        LOG.debug("Verifying if git repository %s is valid", clone_url)
        clone_url_hash = sha256(clone_url)
        workdir = os.path.join(
            self._tmpdir,
            'verify-git-%s' % clone_url_hash
        )
        if self.cmd(
                [
                    'clone',
                    clone_url,
                    'verify-git-%s' % clone_url_hash
                ],
                cwd=self._tmpdir
        ):
            LOG.debug('Could not verify git repository. Clone failed.')
            self.clean_workdir(workdir)
            raise RuntimeError('Could not verify git repository. Clone failed.')
        LOG.debug("%s is a valid git repository", clone_url)
        return workdir

    def verify_git_tag(self, tag, workdir):
        """verify if git tag exists in repository"""
        LOG.debug("Verifying if git tag %s is valid in %s", tag, workdir)
        try:
            gitout = self.cmd(['tag', '--list', tag], cwd=workdir, output=True)
        except subprocess.CalledProcessError:
            gitout = None

        if not gitout:
            LOG.debug('Could not verify git tag. Tag %s not found', tag)
            self.clean_workdir(workdir)
            raise RuntimeError(
                'Could not verify git tag. Tag %s not found' % tag
            )
        self.clean_workdir(workdir)
        LOG.debug("Git tag %s is valid", tag)

    def verify_git_branch(self, branch, workdir):
        """verify if git branch exists in repository"""
        LOG.debug("Verifying if git branch %s is valid in %s", branch, workdir)
        try:
            gitout = self.cmd(
                ['branch', '--list', '--all', "origin/%s" % branch],
                cwd=workdir, output=True
            )
        except subprocess.CalledProcessError:
            gitout = None

        if not gitout:
            LOG.debug(
                'Could not verify git branch. Branch %s not found', branch
            )
            self.clean_workdir(workdir)
            raise RuntimeError(
                'Could not verify git branch. Branch %s not found' % branch
            )
        self.clean_workdir(workdir)
        LOG.debug("Git branch %s is valid", branch)

    def verify_git_commit(self, commit, workdir):
        """verify if git commit exists in repository"""
        LOG.debug("Verifying if git commit %s is valid in %s", commit, workdir)
        try:
            gitout = self.cmd(
                ['cat-file', '-t', commit],
                cwd=workdir,
                output=True
            ).strip()
        except subprocess.CalledProcessError:
            gitout = None

        if gitout != "commit":
            LOG.debug(
                'Could not verify git commit. Commit %s not found', commit
            )
            self.clean_workdir(workdir)
            raise RuntimeError(
                'Could not verify git commit. Commit %s not found' % commit
            )
        self.clean_workdir(workdir)
        LOG.debug("Git commit %s is valid", commit)

    def get_module_info(self, clone_url, cache=True):
        """get latest tag from a git repository"""
        clone_url_hash = sha256(clone_url)
        version = 'unknown'
        date = None
        workdir = os.path.join(
            self._tmpdir,
            'get-module-info-%s' % clone_url_hash
        )

        local_info = {}
        if self._cache and cache:
            local_info = JsonCache(self._cache).read(clone_url_hash, 86400)
            LOG.debug('Get %s info from cache: %s', clone_url, local_info)

        if not local_info:
            try:
                if self.cmd(
                        [
                            'clone',
                            clone_url,
                            'get-module-info-%s' % clone_url_hash
                        ],
                        cwd=self._tmpdir
                ):
                    raise RuntimeError('clone failed')
                if self.cmd(
                        ['rev-list', '--tags', '--max-count=1'],
                        cwd=workdir
                ):
                    raise RuntimeError('rev-list failed')
                else:
                    # get sha1 for latest tag
                    cid = self.cmd(
                        ['rev-list', '--tags', '--max-count=1'],
                        output=True,
                        cwd=workdir
                    ).strip()
                    # get tag name from sha1
                    version = self.cmd(
                        ['describe', '--tags', cid],
                        output=True,
                        cwd=workdir
                    ).strip()
                    date = self.cmd(
                        ['show', '-s', '--format=%ci',
                         '%s^{commit}' % version],
                        output=True,
                        cwd=workdir
                    ).strip()
            except RuntimeError:
                pass
            finally:
                try:
                    shutil.rmtree(workdir)
                except OSError:
                    pass

            local_info = {
                'version': version,
            }
            if date:
                local_info['date'] = datetime.strptime(
                    date,
                    '%Y-%m-%d %H:%M:%S %z',
                ).strftime('%Y-%m-%d')

            if self._cache and cache:
                JsonCache(self._cache).write(clone_url_hash, local_info)
                LOG.debug('Written %s info to cache: %s', clone_url, local_info)

        return local_info

    def write_puppetfile(self, branch, puppetfile):
        """write Puppetfile and return diff"""
        LOG.debug("Update local control repository branch %s", branch)
        self.cmd(['checkout', branch], cwd=self._workdir)
        self.cmd(['pull', 'origin', branch], cwd=self._workdir)

        LOG.debug(
            "Trying to write puppetfile to %s",
            os.path.join(self._workdir, 'Puppetfile')
        )
        with open(os.path.join(self._workdir, 'Puppetfile'), 'w') as pfile:
            pfile.write('\n'.join(puppetfile))

        return self.cmd(['diff'], cwd=self._workdir, output=True)

    def commit_puppetfile(self, branch, message):
        """commit & push current version of Puppetfile"""
        self.cmd(['commit', '-m', message, 'Puppetfile'],
                 cwd=self._workdir)
        self.cmd(['push', 'origin', branch],
                 cwd=self._workdir)

    def revert_puppetfile(self):
        """revert uncommitted changes to Puppetfile"""
        self.cmd(['checkout', '--', 'Puppetfile'], cwd=self._workdir)

    def collect_puppetfiles(self, clone_url):
        """get Puppetfile from every branch of a r10k control repository"""
        puppetfiles = {}

        # clone git r10k control repository into a temporary directory
        self.cmd(['clone', clone_url, 'control'], cwd=self._tmpdir)
        self._workdir = '%s/control' % self._tmpdir

        # gather a list of local and remote branches
        branch_list = self.cmd(
            ['branch', '-a'],
            output=True,
            cwd=self._workdir
        ).split('\n')
        localbranches = []
        self.controlbranches = []
        for line in branch_list:
            stripped_line = line.strip(' *')
            if not stripped_line:
                continue
            if ' -> ' in stripped_line:
                continue
            if '/' in stripped_line:
                self.controlbranches.append(stripped_line.rsplit('/', 1)[1])
            else:
                localbranches.append(stripped_line)

        LOG.debug("Found controlbranches: %s", self.controlbranches)
        # go through list of branches, check them out and read Puppetfile into
        # memory
        for branch in self.controlbranches:
            LOG.debug("Process controlbranch: %s", branch)
            # if its a local branch, we can just check it out
            # and pull from origin to have it uptodate.
            if branch in localbranches:
                self.cmd(['checkout', branch], cwd=self._workdir)
                self.cmd(['pull', 'origin', branch], cwd=self._workdir)
            # if it is a remote branch, we first need to create a local branch
            # and can then pull from origin to have it uptodate.
            else:
                self.cmd(
                    ['checkout', '-b', branch, 'origin/%s' % branch],
                    cwd=self._workdir
                )

            # read puppetfile and store it memory
            LOG.debug(
                "Trying to read %s into memory",
                '%s/Puppetfile' % self._workdir
            )
            with open('%s/Puppetfile' % self._workdir, 'r') as puppetfile:
                puppetfiles[branch] = puppetfile.readlines()

        return puppetfiles
