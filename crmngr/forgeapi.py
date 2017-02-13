""" crmngr forgeapi module """

# stdlib
from datetime import datetime
import logging

# 3rd-party
import requests
from requests.exceptions import RequestException

# crmngr
from crmngr.utils import truncate

LOG = logging.getLogger(__name__)


class ForgeError(Exception):
    """exception raised when a forge connection/parse error occurs."""


class ForgeApi:
    """puppetforge module api"""

    def __init__(self, *, name, author):
        """initialize module api"""
        self._name = name
        self._author = author
        self._url = '{forgeapi}/{author}-{module}'.format(
            forgeapi='https://forgeapi.puppetlabs.com/v3/modules',
            author=self._author,
            module=self._name
        )

    @property
    def current_version(self):
        """get version for current release"""
        try:
            LOG.debug('request info from %s', self._url)
            api = requests.get(self._url)
            api_info = api.json()['current_release']
            LOG.debug('received module info from API: %s', truncate(api_info))
        except (RequestException, KeyError) as exc:
            LOG.debug('could not read from api: %s', exc)
            raise ForgeError('could not read from api: %s' % exc) from None

        try:
            return {
                'version': api_info['version'],
                'date': datetime.strptime(
                    api_info['updated_at'], '%Y-%m-%d %H:%M:%S %z'
                ).strftime('%Y-%m-%d'),
            }
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            LOG.debug('could not parse api response: %s', exc)
            raise ForgeError('could not parse api response: %s' % exc) from None

    def has_version(self, version):
        """verify wheter a release with requested version exists."""
        try:
            LOG.debug('request info from %s', self._url)
            api = requests.get(self._url)
            api_info = api.json()['releases']
            LOG.debug(
                'received module info from API: %s',
                truncate(api_info),
            )
        except (RequestException, KeyError) as exc:
            LOG.debug('could not read from api: %s', exc)
            raise ForgeError('could not read from api: %s' % exc) from None

        return bool([release['version']
                     for release in api_info if release['version'] == version])
