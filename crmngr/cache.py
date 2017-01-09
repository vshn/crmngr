""" crmngr cache module """

import json
import logging
import os
import shutil
import time

LOG = logging.getLogger(__name__)


class CacheError(Exception):
    """custom exception for cache related errors"""
    pass


class JsonCache:
    """json file based cache"""

    def __init__(self, directory, ttl=86400, fail_silently=True):
        """constructor, takes directory as argument"""
        LOG.debug("initialize JsonCache in %s", directory)
        self._directory = directory
        self._default_ttl = ttl
        self._fail_silently = fail_silently

    def clear(self):
        """delete cache directory"""
        shutil.rmtree(self._directory)
        LOG.debug("deleted cache directory %s", self._directory)

    def read(self, key, ttl=None):
        """read json dict from file"""
        if ttl is None:
            ttl = self._default_ttl
        try:
            LOG.debug("attempt to read %s from cache", key)
            with open(os.path.join(self._directory, key)) as cache_fd:
                cache = json.load(cache_fd)
                LOG.debug("received %s from cache", cache)
            if cache.get('updated', 0) + ttl >= int(time.time()):
                LOG.debug("cache entry is valid, return it")
                return cache
            LOG.debug("cache expired, returning empty response")
            return {}
        except (AttributeError, KeyError, OSError, ValueError) as exc:
            LOG.debug(
                "cache lookup for %s failed. fail silently.", key
            )
            if self._fail_silently:
                return {}
            else:
                raise CacheError('could not read from cache') from exc

    def write(self, key, jsondict):
        """write json dict to file"""
        try:
            LOG.debug(
                "attempt to write %s to cache using key %s", jsondict, key
            )
            with open(os.path.join(self._directory, key), 'w') as cache_fd:
                localdict = jsondict.copy()
                localdict.update(
                    {
                        'updated': int(time.time()),
                    }
                )
                json.dump(localdict, cache_fd)
                LOG.debug('wrote %s to cache using key %s', localdict, key)
        except (AttributeError, KeyError, OSError, ValueError) as exc:
            if not self._fail_silently:
                raise CacheError('could not write to cache') from exc
            LOG.debug('failed to write to cache. fail silently.')
