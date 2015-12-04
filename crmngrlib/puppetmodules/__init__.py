#!/usr/bin/env python3

"""collection of PuppetModule objects used by crmngrlib"""

from .versions import Version, Forge, GitCommit, GitBranch, GitTag, GitRef
from ..utils import cprint


class PuppetModule:
    """Base class for puppet modules"""

    def __init__(self, name):
        """Initialize puppet module
        :argument name Name of module
        """
        self._name = name
        self._info = {}
        self._branches = []
        self._version = None

    @property
    def info(self):
        """Get external module info"""
        return self._info

    @info.setter
    def info(self, value):
        """Set external module info"""
        self._info = value

    @property
    def name(self):
        """Name of this module"""
        return self._name

    @property
    def branches(self):
        """Branches that use this module"""
        return self._branches

    @property
    def version(self):
        """Return this modules version"""
        return self._version

    @version.setter
    def version(self, value):
        """Set version of this puppet module
        :argument value version (needs to be a subclass of Version)
        """
        if isinstance(value, Version):
            self._version = value
        else:
            if value is None:
                self._version = None
            else:
                raise AttributeError('Unsupported type %s for value' % type(value))

    def __hash__(self):
        return hash(self.__repr__())

    def __repr__(self):
        return "%s" % self.name

    def __eq__(self, other):
        return str(self) >= str(other) >= str(self)

    def __ne__(self, other):
        return str(self) < str(other) or str(other) < str(self)

    def __gt__(self, other):
        return str(other) < str(self)

    def __ge__(self, other):
        return str(self) >= str(other)

    def __le__(self, other):
        return str(other) >= str(self)

    def add_branch(self, branch):
        """Add a branch to this modules internal branch list
        :argument branch Name of branch to add
        """
        if branch not in self._branches:
            self._branches.append(branch)


class GitModule(PuppetModule):
    """Puppet mdoule hosted on git"""

    def __init__(self, name, url):
        """Initialize git module
        :argument name Name of module
        :argument url Repository URL of module
        """
        super().__init__(name)
        self._url = url

    @property
    def url(self):
        """URL to git repository for this puppet module"""
        return self._url

    def __repr__(self):
        """Return unique string representation"""
        representation = "%s:git:%s" % (self.name, self.url)
        if self.version:
            representation += ":%s" % self.version
        return representation

    @property
    def puppetfile(self):
        """Return puppetfile representation of module"""
        lines = [
            "mod '%s'," % self.name,
        ]
        git_line = "  :git => '%s'" % self.url
        if self.version:
            git_line += ","
        lines.append(git_line)

        if isinstance(self.version, Version):
            lines.append(self.version.puppetfile)
        return lines

    def print_version_information(self):
        """Print out version information"""
        cprint.magenta_bold('Version:', lpad=2)
        cprint.white('Git:', lpad=4, rpad=8, end='')
        cprint.white(self.url)
        if isinstance(self.version, GitBranch):
            cprint.blue_bold('Branch: ', lpad=16, end='')
            cprint.yellow_bold(self.version.version, end='')
        elif isinstance(self.version, GitCommit):
            cprint.red('Commit: ', lpad=16, end='')
            cprint.red_bold(self.version.version[:7], end='')
        elif isinstance(self.version, GitRef):
            cprint.red('Ref: ', lpad=16, end='')
            cprint.red_bold(self.version.version, end='')
        elif isinstance(self.version, GitTag):
            cprint.blue_bold('Tag: ', lpad=16, end='')
            if self.info.get('version', None) == self.version.version:
                cprint.green_bold(self.version.version, end='')
            else:
                cprint.yellow_bold(self.version.version, end='')
        else:
            cprint.red_bold('UNSPECIFIED', lpad=16, end='')
        cprint.white('[Latest: %s (%s)]' % (
            self.info.get('version', 'unknown'),
            self.info.get('date', 'unknown')
        ), lpad=1)


class ForgeModule(PuppetModule):
    """Puppet module hosted on forge"""

    def __init__(self, name, author):
        """Initialize forge module
        :argument name Name of module
        :argument author Author/Namespace of the module
        """
        super().__init__(name)
        self._author = author

    @property
    def author(self):
        """Puppet module author / namespace"""
        return self._author

    @property
    def forgename(self):
        """Return module name as used on forge"""
        return "%s/%s" % (self._author, self._name)

    def __repr__(self):
        """Return unique string representation"""
        representation = "%s:forge:%s" % (self.name, self.author)
        if self.version:
            representation += ":%s" % self.version
        return representation

    def print_version_information(self):
        """Print out version information"""
        cprint.magenta_bold('Version:', lpad=2)
        cprint.white('Forge:', lpad=4, rpad=6, end='')
        cprint.white(self.forgename, suffix=':')
        if not self.version:
            cprint.red_bold('UNSPECIFIED', lpad=16, end='')
        else:
            if self.info.get('version', None) == self.version.version:
                cprint.green_bold(self.version.version, lpad=16, end='')
            else:
                cprint.yellow_bold(self.version.version, lpad=16, end='')
        cprint.white(' [Latest: %s (%s)]' % (
            self.info.get('version', 'unknown'),
            self.info.get('date', 'unknown')
        ))

    @property
    def puppetfile(self):
        """Return puppetfile representation of module"""
        line = "mod '%s/%s'" % (self.author, self.name)
        if self.version:
            line += ", %s" % self.version.puppetfile
        return [line, ]
