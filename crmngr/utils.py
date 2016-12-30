""" crmngr utility module """

# stdlib
from fnmatch import fnmatchcase
import sys


def truncate(string, max_len=1000):
    """returns a truncated to max_len version of a string (or str(string))"""
    string = str(string)
    if len(string) > max_len - 12:
        return string[:max_len] + '...TRUNCATED'
    return string


def fnlistmatch(value, patterns):
    """match a value against a list of fnmatch patterns.

    returns True if any pattern matches.
    """
    for pattern in patterns:
        if fnmatchcase(value, pattern):
            return True
    return False


def query_yes_no(question, default="yes"):
    """Asks a yes/no question via and returns the answer as bool."""
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
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').")
