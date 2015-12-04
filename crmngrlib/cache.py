#!/usr/bin/env python3

"""cache related functions for crmngrlib"""

import json
import logging
import os
import time

LOG = logging.getLogger(__name__)


class CacheError(Exception):
    """custom exception for cache related errors"""
    pass


class JsonCache:
    """json file based cache"""

    def __init__(self, directory, fail_silently=True):
        """constructor, takes directory as argument"""
        LOG.debug("Initialize JsonCache in %s", directory)
        self.directory = directory
        self.fail_silently = fail_silently

    def read(self, key, ttl=86400):
        """read json dict from file"""
        try:
            LOG.debug("Try to read %s from cache", key)
            with open(os.path.join(self.directory, key)) as cache_fd:
                cache = json.load(cache_fd)
                LOG.debug("Got %s from cache", cache)
            if cache.get('updated', 0) + ttl >= int(time.time()):
                LOG.debug("Cache entry is valid, return it")
                return cache
            LOG.debug("Cache expired, returning empty response")
            return dict()
        except (AttributeError, KeyError, OSError, ValueError) as exc:
            if not self.fail_silently:
                raise CacheError('could not read from cache') from exc
            LOG.debug(
                "Cache lookup for %s failed. Fail silently.", key
            )

    def write(self, key, jsondict):
        """write json dict to file"""
        try:
            LOG.debug("Try to write %s to cache using key %s", jsondict, key)
            with open(os.path.join(self.directory, key), 'w') as cache_fd:
                localdict = jsondict.copy()
                localdict.update(
                    {
                        'updated': int(time.time()),
                    }
                )
                LOG.debug('Set updated to current time')
                json.dump(localdict, cache_fd)
                LOG.debug('Wrote %s to cache using key %s', localdict, key)
        except (AttributeError, KeyError, OSError, ValueError) as exc:
            if not self.fail_silently:
                raise CacheError('could not write to cache') from exc
            LOG.debug('Failed to write to cache. Fail silently.')
