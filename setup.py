""" crmngr setup module. """

from pathlib import Path
import re
from setuptools import setup, find_packages

# Read version from crmngr/version.py
# we do not import, as this fails if dependencies from install_depends are not
# available
with open(Path('./crmngr/version.py')) as version_file:
    VERSION_REGEX = re.compile(
        r'^\s*__version__\s*=\s*["\'](?P<version>.*)["\']\s*$'
    )
    for line in version_file.readlines():
        version_match = VERSION_REGEX.match(line)
        if version_match:
            __version__ = version_match.groupdict()['version']
            break
    else:
        __version__ = 'unknown'
        raise Exception('Could not get current version of nacli from '
                        './nacli/version.py')

setup(
    name='crmngr',
    author='Andre Keller',
    author_email='andre.keller@vshn.ch',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: System :: Systems Administration',
    ],
    description='manage a r10k-style control repository',
    entry_points={
        'console_scripts': [
            'crmngr = crmngr:main'
        ]
    },
    install_requires=[
        'natsort>=4.0.0',
        'requests>=2.1.0',
    ],
    # BSD 3-Clause License:
    # - http://opensource.org/licenses/BSD-3-Clause
    license='BSD',
    packages=find_packages(),
    url='https://github.com/vshn/crmngr',
    version=__version__,
)
