######
crmngr
######

.. contents:: Table of Contents

********
Overview
********

crmngr (Control Repository Manager) is a tool to aid with the management of a
r10k-style control repository for puppet

about r10k
==========

from `r10k's github page <https://github.com/puppetlabs/r10k>`_:
    R10k provides a general purpose toolset for deploying Puppet environments
    and modules. It implements the `Puppetfile`_ format and provides a native
    implementation of Puppet dynamic environments.

r10k is a tool that creates a puppet environment for each branch in a git
repository (the "control repository") on the puppetmaster. Each branch contains
a `Puppetfile` that declares which puppet modules in which versions from which
source (puppetforge or a git URL) should be installed in the corresponding
environment.
When working with more than a handful environments it is hard to keep track of
the modules spread over all these environments. Here is where crmngr comes to the rescue.

crmngr
======

crmngr (Control Repository Manager) can generate reports and help with adding,
updating or removing modules in Puppetfiles spread over multiple branches.

See usage section of this document for details.

CAVEATS:
    crmngr will not parse/validate metadata.json and thus will not check if all
    dependencies are satisfied between the modules in a certain environment !

It is similar to https://github.com/camptocamp/puppetfile-updater and was
developed independently during the same timeframe.

************
Installation
************

crmngr can be installed using different methods, see below.

Additionally the git binary needs to be in the invoking users PATH, and the
access to the r10k control repository needs to be password-less. (f.e. using
SSH pubkey authentication). This also applies to git repositories used in
Puppetfiles.


pip (recommanded)
=================

.. code-block:: text

    pip install crmngr


setuptools
==========

.. code-block:: text

    python setup.py install


ArchLinux
=========

crmngr is available in the `AUR <https://aur.archlinux.org/packages/crmngr/>`_


*************
Configuration
*************

crmngr is looking for its configuration files in `~/.crmngr/` and will create
them if run for the first time

profiles
========

crmngr supports multiple profiles. Each profile represents an r10k-style control
repository.

Profiles are read from `~/.crmngr/profiles`

The only mandatory setting is `repository` in the `default` section defining the
git url of the r10k-style control repository of the default profile.

.. code-block:: ini

    [default]
    repository = git@git.example.org:user/control.git

If started without configuration file, crmngr will offer to create one.

Additional sections can be added to support multiple profiles

.. code-block:: ini

    [profile2]
    repository = git@git2.example.org:anotheruser/control.git

Run crmngr with option `--profile` to use a profile other than `default`.


prefs
=====

the default behaviour of crmngr can be adjusted in the `~/.crmngr/prefs` file.

Defaults (i.e. behaviour if no prefs file is present):

.. code-block:: ini

    [crmngr]
    cache = yes
    version_check = yes

Supported settings:

* *cache*: yes/no
  Whether or not to read version info from cache. This influences the default
  behaviour of --cache / --no-cache cli arguments

* *version_check*: yes/no
  Whether or not to check for latest version. This influences the default
  behaviour of --version-check / --no-version-check cli arguments

* *console_clear_command*:
  Command to sent to terminal before displaying a diff.
  Examples: tput reset / tput clear. Default: No command.



*****
Usage
*****

.. code-block:: text

    usage: crmngr [-h] [--version] [--debug]
                  [--no-version-check | --version-check] [--no-cache | --cache]
                  [--profile PROFILE]
                  {report,update,clean,profiles} ...

    manage a r10k-style control repository

    optional arguments:
      -h, --help            show this help message and exit
      --version, -v         show program's version number and exit
      --debug, -d           enable debug output
      --no-version-check    do not check for latest versions. default behaviour,
                            unless overridden in the prefs file, is to fetch
                            current version information for every module found
                            in every Puppetfile. this may take a considerable
                            amount of time, especially if the data is not cached
                            yet/anymore.
      --version-check       check for latest versions. this is the default
                            behaviour, unless overridden in the prefs file.
      --no-cache            ignore cached information about latest versions.
                            default behaviour, unless overridden in the prefs
                            file, is to read version info from a cache (default
                            ttl 24h) if available.
      --cache               read version info from cache (default ttl 24h) if
                            available. this is the default behaviour unless
                            overridden in the prefs file.
      --profile PROFILE, -p PROFILE
                            crmngr configuration profile

    commands:
      valid commands

      {report,update,clean,profiles}
        report              puppetfile reporting (-h for usage details)
        update              puppetfile manipulation (-h for usage details)
        clean               Clean cache
        profiles            list available configuration profiles


report
======

The report command is used to generate reports about module versions used in
the various branches of a control repository.

The report is aggregated by module, listing all module version, which branch
they use and what would be the latest installable version. (Version for
forge.puppetlabs.com modules, Tag for modules installed from git)

**NOTE**:
    The report command will output colorized text. When using a pager,
    make sure the pager understands this colors. For less use option -r:

    .. code-block:: text

        crmngr report | less -r

        # or if the output shall be preserved in a file
        crmngr report > report.out
        less -r report.out

        # or if you want to strip color codes all together
        crmngr report | perl -pe 's/\e\[?.*?[\@-~]//g'


.. code-block:: text

    usage: crmngr report [-h] [--report-unused]
                         [--environments [ENVIRONMENT [ENVIRONMENT ...]]]
                         [--module [MODULES [MODULES ...]]]

    optional arguments:
      -h, --help            show this help message and exit
      --report-unused       additionally list branches that are not using a
                            certain module
      --environment [ENVIRONMENT [ENVIRONMENT ...]],
      --environments [ENVIRONMENT [ENVIRONMENT ...]],
      --env [ENVIRONMENT [ENVIRONMENT ...]],
      -e [ENVIRONMENT [ENVIRONMENT ...]]
                            restrict output to specific environment(s) /
                            branch(es). Supports glob(7)-style wildcard patterns
      --module [MODULES [MODULES ...]],
      --modules [MODULES [MODULES ...]],
      --mod [MODULES [MODULES ...]],
      -m [MODULES [MODULES ...]]
                            restrict output to specific module(s). Supports
                            glob(7)-style wildcard patterns


Examples
--------

Gather a report of all module versions, in all branches:

.. code-block:: text

    crmngr report


Gather a report of all modules in branches ending with Production:

.. code-block:: text

    crmngr report --environments "*Production"


Gather a report of all modules that contain profile in their name:

.. code-block:: text

    crmngr report --modules "*profile*"


Gather a report of modules apache, php and mysql in branches starting with Cust:

.. code-block:: text

    crmngr report --environments "Cust*" --modules apache php mysql

Gather a report of all modules in branches CustProd, CustStage and CustDev.
Additionally list which branches do not use a specific module.

.. code-block:: text

    crmngr report --environments CustProd CustStage CustDev --report-unused

update
======

The update command updates, adds or removes modules from Puppetfiles.

If you execute crmngr update with neither --git nor --module, it will write
a sanitized version of the Puppetfile, using the current module versions.

The update command will display a diff for every affected branch and will
ask you to confirm the changes.

**NOTE**:
    The author part of a module name is *only* used to find the correct module
    on forge. If you run update on --module puppetlabs/stdlib, this will also
    affect all other stdlib modules that might be in a Puppetfile (i.e.
    otherauthor/stdlib or stdlib installed from git will be replaced by
    puppetlabs/stdlib).


.. code-block:: text

    usage: crmngr update [-h] [--diff-only | --non-interactive] [--add |
                     --remove] [--environment [ENVIRONMENT [ENVIRONMENT ...]]]
                     [--module MODULE] [--git URL | --version [VERSION]]
                     [--tag [TAG] | --commit COMMIT | --branch BRANCH]

    optional arguments:
      -h, --help            show this help message and exit
      --diff-only, --dry-run, -n
                            only show changes
      --non-interactive     In non-interactive mode, crmngr will neither ask for
                            confirmation before commit or push, nor will it show
                            diffs of what will be changed. Use with care!
      --add                 add module if not already in Puppetfile. Default
                            behaviour is to only update module in branches it is
                            already defined.
      --remove              remove module from Puppetfile. Version identifying
                            parameters (--version, --tag, --commit, --branch) are
                            NOT taken into account. All module versions are
                            removed!
      --environment [ENVIRONMENT [ENVIRONMENT ...]],
      --environments [ENVIRONMENT [ENVIRONMENT ...]],
      --env [ENVIRONMENT [ENVIRONMENT ...]],
      -e [ENVIRONMENT [ENVIRONMENT ...]]
                            update only specific environment(s) / branch(es).
                            Default: All.
      --module MODULE,
      --mod MODULE,
      -m MODULE             module to update/add/remove, for modules fetched from
                            forge.puppetlabs.com the format needs to be
                            author/modulename
      --git URL             git URL of module's repository. If not specified, the
                            module is fetched from forge.puppetlabs.com
      --version [VERSION]   version of forge.puppetlabs.com module. If parameter
                            is specified without VERSION, latest available version
                            from forge.puppetlabs.com will be used instead
      --tag [TAG]           tag of git module. If parameter is specified without
                            TAG, latest tag from repository is used instead
      --commit COMMIT       commit of git module
      --branch BRANCH       branch of git module


Examples
--------

Sanitize Puppetfiles of all branches:

.. code-block:: text

    crmngr update


Update stdlib module in all branches to latest forge version.


.. code-block:: text

    crmngr update --module puppetlabs/stdlib --version


Update stdlib module in all branches to latest forge version. Additionally add
the module to branches that currently lack the stdlib module

.. code-block:: text

    crmngr update --add --module puppetlabs/stdlib --version


Remove icinga modules from control repository branches that end with Vagrant.

.. code-block:: text

    crmngr update --remove --module icinga --environments "*Vagrant"


Update apache module to git branch 2.0.x in control repository branch Devel

.. code-block:: text

    crmngr update --environments Devel \
                  --module apache \
                  --git git@github.com:puppetlabs/puppetlabs-apache.git \
                  --branch 2.0.x


clean
=====

The clean command clears the cache used by crmngr.

.. code-block:: bash

    usage: crmngr clean


profiles
========

The profile command lists available configuration profiles.

.. code-block:: bash

    usage: crmngr profiles



.. _github-r10k: https://github.com/puppetlabs/r10k

.. _Puppetfile:
  https://github.com/puppetlabs/r10k/blob/master/doc/puppetfile.mkd
