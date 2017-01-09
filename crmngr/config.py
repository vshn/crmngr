""" crmngr configuration module """

# stdlib
from collections import namedtuple
from configparser import ConfigParser
import logging
import logging.config
import os

LOG = logging.getLogger(__name__)


def setup_logging(debug):
    """setup logging configuration"""
    if debug:
        logging.config.dictConfig({
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': '%(asctime)s - %(levelname)s - %(message)s'
                },
            },
            'handlers': {
                'default': {
                    'formatter': 'standard',
                    'class': 'logging.StreamHandler',
                },
            },
            'loggers': {
                '': {
                    'handlers': ['default'],
                    'level': 'DEBUG',
                    'propagate': True
                },
            }
        })


class CrmngrConfig:
    """crmngr configuration and profile handling"""

    def __init__(self, profile='default'):
        """initialize crmngr configuration for the specified profile"""
        self._cache_dir = None
        self._config_dir = self._ensure_configuration_directory()

        # initialize preferences
        self._config = ConfigParser(
            defaults={
                'cache_ttl': '86400',
                'version_check': 'yes',
                'wrap': 'yes'
            }
        )
        self._config.read(os.path.join(self._config_dir, 'prefs'))
        if not self._config.has_section('crmngr'):
            self._config.add_section('crmngr')

        # initialize profiles
        self._profiles = ConfigParser()
        self._profiles.read(os.path.join(self._config_dir, 'profiles'))
        self._control_repo_url = self._profiles.get(profile, 'repository')

    @classmethod
    def create_default_configuration(cls, default_profile_url):
        """ensure a default profile is configured."""
        config_directory = cls._ensure_configuration_directory()
        config = ConfigParser()
        config.add_section('default')
        config.set('default', 'repository', default_profile_url)
        with open(os.path.join(config_directory, 'profiles'),
                  'w') as profiles_file:
            config.write(profiles_file)
        return cls()

    @property
    def cache_dir(self):
        """returns the cache directory"""
        self._cache_dir = os.path.join(self._config_dir, 'cache')
        os.makedirs(self._cache_dir, exist_ok=True)
        return self._cache_dir

    @property
    def control_repo_url(self):
        """returns control repo url"""
        return self._control_repo_url

    @property
    def profiles(self):
        """returns a list of valid profiles"""
        profiles = []
        Profile = namedtuple(  # pylint: disable=invalid-name
            'Profile', ['name', 'repository']
        )
        # make sure, we list the default profile first
        profiles.append(
            Profile(
                name='default',
                repository=self._profiles.get('default',
                                              'repository')
            )
        )
        for profile in sorted(self._profiles.sections()):
            # default profile already in result list, ignore it.
            if profile == 'default':
                continue
            profiles.append(
                Profile(
                    name=profile,
                    repository=self._profiles.get(profile,
                                                  'repository',
                                                  fallback='unconfigured'),
                )
            )
        return profiles

    @property
    def version_check(self):
        """returns version_check config setting as bool"""
        return self._config.getboolean('crmngr', 'version_check')

    @property
    def cache_ttl(self):
        """returns cache_ttl config setting as int"""
        return self._config.getint('crmngr', 'cache_ttl')

    @property
    def wrap(self):
        """returns wrap config setting as bool"""
        return self._config.getboolean('crmngr', 'wrap')

    @staticmethod
    def _ensure_configuration_directory(directory=None):
        """ensures the crmngr configuration directory exists"""
        if directory is None:
            directory = os.path.join(os.path.expanduser('~'), '.crmngr')
        os.makedirs(directory, exist_ok=True, mode=0o750)
        LOG.debug("Configuration directory is %s", directory)
        return directory
