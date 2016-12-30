""" crmngr setup module. """

from setuptools import setup, find_packages
from crmngr.version import __version__

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
