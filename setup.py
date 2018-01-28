""" crmngr setup module. """

from pathlib import Path
import re
from setuptools import setup, find_packages


def find_version(source_file):
    """read __version__ from source file"""
    with open(source_file) as version_file:
        version_match = re.search(r"^__version__\s*=\s* ['\"]([^'\"]*)['\"]",
                                  version_file.read(), re.M)
        if version_match:
            return version_match.group(1)
        raise RuntimeError('Unable to find package version')


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
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
    python_requires='>=3.4',
    # BSD 3-Clause License:
    # - http://opensource.org/licenses/BSD-3-Clause
    license='BSD',
    packages=find_packages(),
    url='https://github.com/vshn/crmngr',
    version=find_version(str(Path('./crmngr/version.py'))),
)
