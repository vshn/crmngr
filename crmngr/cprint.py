#!/usr/bin/env python3

"""function for colored terminal output"""

TERM_BLUE = '\033[0;34m'
TERM_BLUE_BOLD = '\033[1;34m'
TERM_CYAN = '\033[0;36m'
TERM_CYAN_BOLD = '\033[1;36m'
TERM_GREEN = '\033[0;32m'
TERM_GREEN_BOLD = '\033[1;32m'
TERM_MAGENTA = '\033[0;35m'
TERM_MAGENTA_BOLD = '\033[1;35m'
TERM_RED = '\033[0;31m'
TERM_RED_BOLD = '\033[1;31m'
TERM_WHITE = '\033[0;37m'
TERM_WHITE_BOLD = '\033[1;37m'
TERM_YELLOW = '\033[0;33m'
TERM_YELLOW_BOLD = '\033[1;33m'

TERM_NONE = '\033[0;m'


def _cprint(color, text, **kwargs):
    """helper function to print colored text"""
    prefix = kwargs.pop('prefix', '')
    suffix = kwargs.pop('suffix', '')
    lpad = kwargs.pop('lpad', 0)
    rpad = kwargs.pop('rpad', 0)
    sep = kwargs.pop('sep', '')

    print(
        ' '*lpad,
        prefix,
        color,
        text,
        suffix,
        ' '*rpad,
        TERM_NONE,
        sep=sep,
        **kwargs
    )


def blue(text, **kwargs):
    """print blue text"""
    _cprint(TERM_BLUE, text, **kwargs)


def blue_bold(text, **kwargs):
    """print bold blue text"""
    _cprint(TERM_BLUE_BOLD, text, **kwargs)


def cyan(text, **kwargs):
    """print cyan text"""
    _cprint(TERM_CYAN, text, **kwargs)


def cyan_bold(text, **kwargs):
    """print bold cyan text"""
    _cprint(TERM_CYAN_BOLD, text, **kwargs)


def green(text, **kwargs):
    """print green text"""
    _cprint(TERM_GREEN, text, **kwargs)


def green_bold(text, **kwargs):
    """print bold green text"""
    _cprint(TERM_GREEN_BOLD, text, **kwargs)


def magenta(text, **kwargs):
    """print magenta text"""
    _cprint(TERM_MAGENTA, text, **kwargs)


def magenta_bold(text, **kwargs):
    """print bold magenta text"""
    _cprint(TERM_MAGENTA_BOLD, text, **kwargs)


def red(text, **kwargs):
    """print red text"""
    _cprint(TERM_RED, text, **kwargs)


def red_bold(text, **kwargs):
    """print bold red text"""
    _cprint(TERM_RED_BOLD, text, **kwargs)


def white(text, **kwargs):
    """print white text"""
    _cprint(TERM_WHITE, text, **kwargs)


def white_bold(text, **kwargs):
    """print bold white text"""
    _cprint(TERM_WHITE_BOLD, text, **kwargs)


def yellow(text, **kwargs):
    """print yellow text"""
    _cprint(TERM_YELLOW, text, **kwargs)


def yellow_bold(text, **kwargs):
    """print bold yellow text"""
    _cprint(TERM_YELLOW_BOLD, text, **kwargs)


def diff(text):
    """print colorized diff"""
    for line in text.split('\n'):
        if line.startswith('-'):
            red(line)
        elif line.startswith('+'):
            green(line)
        else:
            white(line)
