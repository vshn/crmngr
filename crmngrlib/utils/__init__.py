#!/usr/bin/env python3

"""collection of functions used by crmngrlib"""

import fnmatch
import hashlib
import sys


def sha256(string):
    """generate sha256 sum"""
    return hashlib.sha256(string.encode('utf-8')).hexdigest()


def fnlistmatch(name, patterns, noneistrue=True):
    """fnmatch a list of patterns"""
    if not patterns:
        if noneistrue:
            return True
        return False

    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer."""
    valid = {"yes": True, "y": True, "ye": True, "j": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")
