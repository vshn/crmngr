""" crmngr puppetmodule module """

# stdlib
from collections import namedtuple
import hashlib
import logging
from datetime import datetime

# crmngr
from crmngr import cprint
from crmngr.forgeapi import ForgeApi
from crmngr.forgeapi import ForgeError
from crmngr.git import GitError
from crmngr.git import Repository

LOG = logging.getLogger(__name__)


class PuppetModule:
    """Base class for puppet modules"""

    def __init__(self, name):
        """Initialize puppet module"""
        self._name = name
        self._version = None

    @staticmethod
    def parse_module_name(string):
        """parse module file name into author/name"""
        ModuleName = namedtuple(  # pylint: disable=invalid-name
            'ModuleName', ['module', 'author']
        )
        module_name = string.strip(' \'"').rsplit('/', 1)
        try:
            module = ModuleName(module=module_name[1], author=module_name[0])
        except IndexError:
            module = ModuleName(module=module_name[0], author=None)
        LOG.debug("%s parsed into %s", string, module)
        return module

    @classmethod
    def from_moduleline(cls, moduleline):
        """returns a crmngr module object based on a puppetfile module line"""
        # split module line into comma-separated parts (starting after
        # 'mod ')
        line_parts = moduleline[4:].split(',')

        module_name = cls.parse_module_name(line_parts[0])

        # parse additional parts of mod line
        module_info = {}
        for fragment in line_parts[1:]:
            clean = fragment.strip(' \'"')
            # if part not start with a colon, it is git module
            if clean.startswith(':'):
                if clean.startswith(':git'):
                    module_info['url'] = clean.rsplit('>', 1)[1].strip(' \'"')
                elif clean.startswith(':commit'):
                    module_info['version'] = GitCommit(
                        clean.rsplit('>', 1)[1].strip(' \'"')
                    )
                elif clean.startswith(':ref'):
                    module_info['version'] = GitRef(
                        clean.rsplit('>', 1)[1].strip(' \'"')
                    )
                elif clean.startswith(':tag'):
                    module_info['version'] = GitTag(
                        clean.rsplit('>', 1)[1].strip(' \'"')
                    )
                elif clean.startswith(':branch'):
                    module_info['version'] = GitBranch(
                        clean.rsplit('>', 1)[1].strip(' \'"')
                    )
            # forge module
            else:
                module_info['version'] = Forge(clean)
        LOG.debug("%s parsed into %s", ','.join(line_parts[1:]), module_info)

        # forge module
        if module_name.author is not None and 'url' not in module_info:
            return ForgeModule(
                author=module_name.author,
                name=module_name.module,
                version=module_info.get('version'),
            )
        # git module
        else:
            return GitModule(
                name=module_name.module,
                url=module_info['url'],
                version=module_info.get('version'),
            )

    @property
    def name(self):
        """Name of this module"""
        return self._name

    @property
    def version(self):
        """Return this modules version"""
        raise NotImplementedError

    @version.setter
    def version(self, value):
        """Set this modules version"""
        raise NotImplementedError

    @property
    def update_commit_message(self):
        """returns commit message for updating module"""
        try:
            commit_message = 'Update {} module ({})'.format(
                self.name,
                self.version.commit_message,
            )
        except AttributeError:
            commit_message = 'Update {} module'.format(self.name)
        return commit_message

    def __hash__(self):
        return hash(self.__repr__())

    def __repr__(self):
        return "%s" % self.name

    def __eq__(self, other):
        return str(self) >= str(other) >= str(self)

    def __lt__(self, other):
        return str(other) > str(self)


class GitModule(PuppetModule):
    """Puppet mdoule hosted on git"""

    def __init__(self, name, url, version=None):
        """Initialize git module
        :argument name Name of module
        :argument url Repository URL of module
        """
        super().__init__(name)
        self._url = url
        self.version = version

    @property
    def version(self):
        """Return this modules version"""
        return self._version

    @version.setter
    def version(self, value):
        """Set version of this puppet module"""
        if isinstance(value, (GitBranch, GitCommit, GitRef, GitTag)):
            self._version = value
        else:
            if value is None:
                self._version = None
            else:
                raise TypeError('Unsupported type %s for value' % type(value))

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

        if isinstance(self.version, BaseVersion):
            lines.append(self.version.puppetfile)
        return lines

    def print_version_information(self, version_check=True, version_cache=None):
        """Print out version information"""
        if version_check:
            latest_version = self.get_latest_version(version_cache)
        else:
            latest_version = Unknown()

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
            if latest_version.version == self.version.version:
                cprint.green_bold(self.version.version, end='')
            else:
                cprint.yellow_bold(self.version.version, end='')
        else:
            cprint.red_bold('UNSPECIFIED', lpad=16, end='')

        if version_check:
            cprint.white('[Latest: %s]' % (
                latest_version.report
            ), lpad=1)
        else:
            cprint.white('')

    def get_latest_version(self, version_cache=None):
        """return a dict with version, date of newest tag in repository"""
        if version_cache is not None:
            local_info = version_cache.read(self.cachename)
        else:
            local_info = {}

        if not local_info:
            with Repository(self.url) as repository:
                try:
                    latest_tag = repository.latest_tag
                except GitError:
                    local_info = {}
                else:
                    local_info = {
                        'version': latest_tag.name,
                        'date': latest_tag.date.strftime('%Y-%m-%d'),
                    }
            if version_cache is not None:
                version_cache.write(self.cachename, local_info)

        try:
            version = GitTag(
                version=local_info['version'],
                date=datetime.strptime(
                    local_info['date'], '%Y-%m-%d'
                ).date()
            )
        except KeyError:
            version = Unknown()  # pylint: disable=redefined-variable-type
        LOG.debug("latest version for %s is %s", self.name, version)
        return version

    @property
    def cachename(self):
        """returns cache lookup key"""
        return hashlib.sha256(self.url.encode('utf-8')).hexdigest()


class ForgeModule(PuppetModule):
    """Puppet module hosted on forge"""

    def __init__(self, name, author, version=None):
        """Initialize forge module
        :argument name Name of module
        :argument author Author/Namespace of the module
        """
        super().__init__(name)
        self._author = author
        self.version = version

    @property
    def version(self):
        """Return this modules version"""
        return self._version

    @version.setter
    def version(self, value):
        """Set version of this puppet module"""
        if isinstance(value, Forge):
            self._version = value
        else:
            if value is None:
                self._version = None
            else:
                raise TypeError('Unsupported type %s for value' % type(value))

    @property
    def author(self):
        """Puppet module author / namespace"""
        return self._author

    @property
    def forgename(self):
        """Return module name as used on forge"""
        return "%s/%s" % (self._author, self._name)

    @property
    def cachename(self):
        """returns cache lookup key"""
        return hashlib.sha256(self.forgename.encode('utf-8')).hexdigest()

    def __repr__(self):
        """Return unique string representation"""
        representation = "%s:forge:%s" % (self.name, self.author)
        if self.version:
            representation += ":%s" % self.version
        return representation

    def print_version_information(self, version_check=True, version_cache=None):
        """Print out version information"""
        if version_check:
            latest_version = self.get_latest_version(version_cache)
        else:
            latest_version = Unknown()

        cprint.magenta_bold('Version:', lpad=2)
        cprint.white('Forge:', lpad=4, rpad=6, end='')
        cprint.white(self.forgename, suffix=':')
        if not self.version:
            cprint.red_bold('UNSPECIFIED', lpad=16, end='')
        else:
            if latest_version.version == self.version.version:
                cprint.green_bold(self.version.version, lpad=16, end='')
            else:
                cprint.yellow_bold(self.version.version, lpad=16, end='')

        if version_check:
            cprint.white(' [Latest: %s]' % latest_version.report)
        else:
            cprint.white('')

    def get_latest_version(self, version_cache=None):
        """returns dict with version and date of the newest version on forge"""
        if version_cache is not None:
            local_info = version_cache.read(self.cachename)
        else:
            local_info = {}

        if not local_info:
            try:
                local_info = ForgeApi(
                    name=self.name,
                    author=self.author
                ).current_version
            except ForgeError:
                return Unknown()

            if version_cache is not None:
                version_cache.write(self.cachename, local_info)

        try:
            return Forge(
                version=local_info['version'],
                date=datetime.strptime(
                    local_info['date'], '%Y-%m-%d'
                ).date()
            )
        except KeyError:
            return Unknown()

    @property
    def puppetfile(self):
        """Return puppetfile representation of module"""
        line = "mod '%s/%s'" % (self.author, self.name)
        if self.version:
            line += ", %s" % self.version.puppetfile
        return [line, ]


class BaseVersion:
    """Base class for version objects"""

    def __init__(self, version, date=None):
        """Initialize Version
        :argument version Version(-string) for this module.
        """
        self._date = date
        self._version = version

    def __hash__(self):
        return hash(self._version)

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, str(self._version))

    @property
    def version(self):
        """Return Version(-string)"""
        return self._version

    @property
    def date(self):
        """Return Date of Version"""
        return self._date

    @property
    def report(self):
        """Return version in suitable format for crmngr report"""
        if self._date is None:
            return "%s" % self._version
        else:
            return "%s (%s)" % (self._version, self._date)

    @property
    def commit_message(self):
        """Return version in suitable format for commit message"""
        return "%s" % self.version


class Unknown(BaseVersion):
    """Object to represent and unknown Version"""
    def __init__(self, version=None, date=None):
        super().__init__(version, date)

    def __repr__(self):
        return "%s()" % type(self).__name__

    @property
    def report(self):
        """Return version in suitable format for crmngr report"""
        return 'unknown'


class Forge(BaseVersion):
    """Puppet Forge Version"""

    @property
    def puppetfile(self):
        """Return version in suitable format for puppetfile"""
        return "'%s'" % self.version


class GitBranch(BaseVersion):
    """Git Branch"""

    @property
    def puppetfile(self):
        """Return version in suitable format for puppetfile"""
        return "  :branch => '%s'" % self.version

    @property
    def commit_message(self):
        """Return version in suitable format for commit message"""
        return "branch [%s]" % self.version


class GitCommit(BaseVersion):
    """Git Commit"""

    @property
    def puppetfile(self):
        """Return version in suitable format for puppetfile"""
        return "  :commit => '%s'" % self.version

    @property
    def commit_message(self):
        """Return version in suitable format for commit message"""
        return "commit [%s]" % self.version


class GitRef(BaseVersion):
    """Git Ref"""

    @property
    def puppetfile(self):
        """Return version in suitable format for puppetfile"""
        return "  :ref => '%s'" % self.version


class GitTag(BaseVersion):
    """ Git Tag"""

    @property
    def puppetfile(self):
        """Return version in suitable format for puppetfile"""
        return "  :tag => '%s'" % self.version

    @property
    def commit_message(self):
        """Return version in suitable format for commit message"""
        return "tag [%s]" % self.version
