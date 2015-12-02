"""
crmngr setup module.
"""

from setuptools import setup, find_packages

import crmngrlib

setup(
    name='crmngr',
    version=crmngrlib.__version__,
    description='manage a r10k-style control repository',
    url='https://github.com/vshn/crmngr',
    author='Andre Keller',
    author_email='andre.keller@vshn.ch',
    # BSD 3-Clause License:
    # - http://opensource.org/licenses/BSD-3-Clause
    license='BSD',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: System :: Systems Administration',
    ],

    packages=[
        'crmngrlib',
        'crmngrlib.puppetmodules',
        'crmngrlib.puppetmodules.versions',
        'crmngrlib.utils',
    ],

    scripts=['crmngr',],

)
