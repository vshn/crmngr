#!/usr/bin/env python3

"""collection of Version objects used by crmngrlib"""


class Version:
    """Base class for version objects"""

    def __init__(self, version):
        """Initialize Version
        :argument version Version(-string) for this module.
        """
        self._version = version

    def __hash__(self):
        hash(self._version)

    @property
    def version(self):
        """Return Version(-string)"""
        return self._version

    @property
    def version_type(self):
        """String representation of version type"""
        return type(self).__name__


class Forge(Version):
    """Puppet Forge Version"""

    def __repr__(self):
        return "%s" % self._version

    @property
    def puppetfile(self):
        """Return version in suitable format for puppetfile"""
        return "'%s'" % self.version


class GitBranch(Version):
    """Git Branch"""

    def __repr__(self):
        return "branch:%s" % self._version

    @property
    def puppetfile(self):
        """Return version in suitable format for puppetfile"""
        return "  :branch => '%s'" % self.version


class GitCommit(Version):
    """Git Commit"""

    def __repr__(self):
        return "commit:%s" % self._version

    @property
    def puppetfile(self):
        """Return version in suitable format for puppetfile"""
        return "  :commit => '%s'" % self.version


class GitRef(Version):
    """Git Ref"""

    def __repr__(self):
        return "ref:%s" % self._version

    @property
    def puppetfile(self):
        """Return version in suitable format for puppetfile"""
        return "  :ref => '%s'" % self.version


class GitTag(Version):
    """ Git Tag"""

    def __repr__(self):
        return "tag:%s" % self._version

    @property
    def puppetfile(self):
        """Return version in suitable format for puppetfile"""
        return "  :tag => '%s'" % self.version

