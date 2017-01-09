""" crmngr git module """

# stdlib
from collections import namedtuple
from datetime import datetime
import logging
import os
import re
import subprocess
from tempfile import TemporaryDirectory

LOG = logging.getLogger(__name__)


class GitError(Exception):
    """exception raised when a git command fails"""


class Repository:
    """a git repository"""

    def __init__(self, clone_url):
        """clone a remote repository"""
        self._url = clone_url
        self._tmpdir = TemporaryDirectory(prefix='crmngr_repository_')
        self.git([
            'clone',
            '--depth=1',
            '--quiet',
            '--no-single-branch',
            self._url,
            'git'
        ], cwd=self._tmpdir.name)
        self._workdir = os.path.join(self._tmpdir.name, 'git')
        LOG.debug('cloned %s into %s', self._url, self._workdir)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._tmpdir.cleanup()

    def git(self, cmds, cwd=None, **kwargs):
        """execute a git command"""
        cmds = ['git'] + cmds
        if cwd is None:
            cwd = self._workdir

        try:
            rval = subprocess.check_output(
                cmds,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                universal_newlines=True,
                **kwargs
            )
            LOG.debug(
                'command "%s" completed with exit code "0" and output: "%s"',
                ' '.join(cmds),
                rval.replace('\n', '; ').strip('; '),
            )
        except subprocess.CalledProcessError as exc:
            raise GitError(
                'command "%s" failed with exit code "%s" and output: "%s"' % (
                    ' '.join(cmds),
                    exc.returncode,
                    exc.output.replace('\n', '; ').strip('; '),
                )
            ) from None
        return rval

    def validate_branch(self, branch):
        """verify if repository has a specific branch"""
        if not self.git(['branch', '--list', '--all', 'origin/%s' % branch]):
            raise GitError(
                "Branch {branch} not found for reporsitory {url}".format(
                    branch=branch,
                    url=self._url
                )
            )

    def validate_tag(self, tag):
        """verify if repository has a specific tag"""
        if not self.git(['tag', '--list', tag]):
            raise GitError(
                "Tag {tag} not found for reporsitory {url}".format(
                    tag=tag,
                    url=self._url
                )
            )

    def validate_commit(self, commit):
        """verify if repository has a specific commit"""
        output = self.git(['cat-file', '-t', commit]).strip()

        if output != 'commit':
            raise GitError(
                "Commit {commit} not found for reporsitory {url}".format(
                    commit=commit,
                    url=self._url
                )
            )

    @property
    def branches(self):
        """returns all """
        gitbranches = self.git(['branch', '--list', '--all']).split('\n')

        re_branch = re.compile(r'\s*remotes/origin/(?P<branch>[^\s]+$)')

        for gitbranch in gitbranches:
            try:
                yield re_branch.match(gitbranch).groupdict()['branch']
            except AttributeError:
                continue

    @property
    def latest_tag(self):
        """returns a namedtuple of (name, date) for the newest tag"""
        Tag = namedtuple(  # pylint: disable=invalid-name
            'GitTagDate', ['name', 'date']
        )

        try:
            self.git(['fetch', '--tags'])
            # get sha1 for latest tag
            cid = self.git(['rev-list', '--tags', '--max-count=1']).strip()
            # get tag name from sha1
            tag_name = self.git(['describe', '--tags', cid]).strip()
            # get date for tag
            date = datetime.strptime(self.git(
                ['show', '-s', '--format=%ci', '%s^{commit}' % tag_name],
            ).strip(), '%Y-%m-%d %H:%M:%S %z')
        except GitError as exc:
            LOG.debug('could not determine latest tag in repository %s: %s',
                      self._url, exc)
            raise

        return Tag(name=tag_name, date=date)

    @property
    def url(self):
        """returns repository url"""
        return self._url
