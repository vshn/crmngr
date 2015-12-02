#!/usr/bin/env python3

"""puppet forge related functions for crmngrlib"""

import logging
import json

import urllib.request
from urllib.error import URLError

from datetime import datetime

from .cache import JsonCache
from .utils import sha256

LOG = logging.getLogger(__name__)


def get_forge_module_info(module, cache=None):
    """get current release from forge api"""

    normalized_module = '%s-%s' % (
        module.split('/', 1)[0], module.split('/', 1)[1]
    )

    module_url = '%s/%s' % (
        'https://forgeapi.puppetlabs.com:443/v3/modules',
        normalized_module
    )

    local_info = {}
    if cache:
        local_info = JsonCache(cache).read(sha256(normalized_module), 86400)
        LOG.debug('Get %s info from cache: %s', normalized_module, local_info)

    if not local_info:
        try:
            api_request = urllib.request.Request(module_url)
            api_response = urllib.request.urlopen(
                api_request
            ).read().decode('utf-8')

            api_info = json.loads(api_response)
            LOG.debug('Retrieved module info from %s', module_url)

            local_info = {
                'version': api_info['current_release']['version'],
                'date': datetime.strptime(
                    api_info['current_release']['updated_at'],
                    '%Y-%m-%d %H:%M:%S %z',
                ).strftime('%Y-%m-%d')
            }
        except (AttributeError, KeyError, URLError, ValueError):
            return dict()

        if cache:
            JsonCache(cache).write(sha256(normalized_module), local_info)
            LOG.debug(
                'Written %s info to cache: %s',
                normalized_module,
                local_info
            )

    return local_info


def verify_module_version(module, version):
    """get current release from forge api"""

    normalized_module = '%s-%s' % (
        module.split('/', 1)[0], module.split('/', 1)[1]
    )

    module_url = '%s/%s' % (
        'https://forgeapi.puppetlabs.com:443/v3/modules',
        normalized_module
    )

    try:
        api_request = urllib.request.Request(module_url)
        api_response = urllib.request.urlopen(
            api_request
        ).read().decode('utf-8')

        api_info = json.loads(api_response)
        LOG.debug('Retrieved module info from %s', module_url)

        for release in api_info['releases']:
            if version == release['version']:
                LOG.debug('Found version %s in release versions', version)
                break
        else:
            raise RuntimeError('Version %s not found' % version)

    except (AttributeError, KeyError, URLError, ValueError) as exc:
        raise RuntimeError('Failed to determine module version') from exc
