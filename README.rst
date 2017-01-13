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
the modules spread over all these environments. Here is where crmngr comes to
the rescue.

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
Dependencies
************

crmngr supports python >=3.4 and has the following 3rd-party dependencies
 - `natsort <https://pypi.python.org/pypi/natsort>`_ (>= 4.0.0)
 - `requests <https://pypi.python.org/pypi/requests>`_ (>= 2.1)

crmngr further relies on git >=1.8


************
Installation
************

crmngr can be installed using different methods, see below.

Additionally the git binary needs to be in the invoking users PATH, and the
access to the r10k control repository needs to be password-less. (f.e. using
SSH pubkey authentication). This also applies to git repositories used in
Puppetfiles.


pip
===

.. code-block:: text

    pip3 install crmngr


ArchLinux
=========

crmngr is available in the `AUR`_


Ubuntu
======

crmngr is available in the `PPA`_, package is called `python3-crmngr`


*************
Configuration
*************

crmngr is looking for its configuration files in `~/.crmngr/` and will create
them if run for the first time.

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
    cache_ttl = 86400
    version_check = yes
    wrap = yes

Supported settings:

* *cache_ttl*: yes/no
  Whether or not to read version info from cache. This sets the default value
  of the `--cache-ttl` cli argument.

* *version_check*: yes/no
  Whether or not to check for latest version in report mode . This influences
  the default behaviour of `--version-check` / `--no-version-check` cli
  arguments

* *wrap*: yes/no
  Whether or not to wrap long lines in report mode. This influences the
  default behaviour of `--wrap` / `--no-wrap` cli arguments.


*****
Usage
*****

.. code-block:: text

    usage: crmngr [-h] [-v] [--cache-ttl TTL] [-d] [-p PROFILE]
                  {clean,create,delete,environments,profiles,report,update} ...

    manage a r10k-style control repository

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         show program's version number and exit
      --cache-ttl TTL       time-to-live in seconds for version cache entries
                            (default: 86400)
      -d, --debug           enable debug output (default: False)
      -p PROFILE,
      --profile PROFILE
                            crmngr configuration profile (default: default)

    commands:
      valid commands. Use -h/--help on command for usage details

      {clean,create,delete,environments,profiles,report,update}
        clean               clean version cache
        create              create a new environment
        delete              delete an environment
        environments        list all environments of the selected profile
        profiles            list available configuration profiles
        report              generate a report about modules and versions
        update              update puppet environment


clean
=====

The clean command clears the cache used by crmngr.

.. code-block:: text

    usage: crmngr clean [-h]

    Clean version cache.

    This will delete the cache directory (~/.crmngr/cache).

    optional arguments:
      -h, --help  show this help message and exit


create
======

.. code-block:: text

    usage: crmngr create [-h] [-t ENVIRONMENT] [--no-report]
                         [--version-check | --no-version-check]
                         [--wrap | --no-wrap]
                         environment

    Create a new environment.

    Unless --template/-t is specified, this command will create a new
    environment containing the following files (tldr. an environemnt without
    any modules):

    Puppetfile
    ---
    forge 'http://forge.puppetlabs.com'

    ---

    manifests/site.pp
    ---
    hiera_include('classes')
    ---

    If --template/-t is specified, the command will clone the existing
    ENVIRONMENT including all files and directories it contains.

    positional arguments:
      environment           name of the new environment

    optional arguments:
      -h, --help            show this help message and exit
      -t ENVIRONMENT, --template ENVIRONMENT
                            name of an existing environment to clone the new
                            environment from

    report options:
      --no-report           disable printing a report for the new
                            environment (default: False)
      --version-check       enable check for latest version (forge modules)
                            or latest git tag (git modules). (default: True)
      --no-version-check    disable check for latest version (forge modules)
                            or latest git tag (git modules). (default:
                            False)
      --wrap                enable wrapping of long lines. (default: True)
      --no-wrap             disable wrapping long lines. (default: False)


delete
======

.. code-block:: text

    usage: crmngr delete [-h] environment

    Delete an environment.

    The command will ask for confirmation.

    positional arguments:
      environment  name of the environment to delete

    optional arguments:
      -h, --help   show this help message and exit


environments
============

.. code-block:: text

    usage: crmngr environments [-h]

    List all environments in the control-repository of the currently
    selected profile.

    optional arguments:
      -h, --help  show this help message and exit


profiles
========

.. code-block:: text

    usage: crmngr profiles [-h]

    List all available configuration profiles.

    To add a new configuration profile, open ~/.crmngr/profiles and add a
    new section:

    [new_profile_name]
    repository = control-repo-url

    Ensure there is always a default section!

    optional arguments:
      -h, --help  show this help message and exit


report
======

The report command is used to generate reports about module versions used in
the various branches of a control repository.

The report is aggregated by module, listing all module version, which branch
they use and what would be the latest installable version. (Version for
forge.puppetlabs.com modules, Tag for modules installed from git)

**NOTE**:
    The report command will output colorized text. When using a pager,
    make sure the pager understands these colors. For less use option -r:

    .. code-block:: text

        crmngr report | less -r

        # or if the output shall be preserved in a file
        crmngr report > report.out
        less -r report.out

        # or if you want to strip color codes all together
        crmngr report | perl -pe 's/\e\[?.*?[\@-~]//g'


.. code-block:: text

    usage: crmngr report [-h] [-e [PATTERN [PATTERN ...]]]
                         [-m [MODULES [MODULES ...]]] [-c]
                         [--version-check | --no-version-check]
                         [--wrap | --no-wrap]

    Generate a report about modules and versions deployed in the puppet
    environments.

    optional arguments:
      -h, --help            show this help message and exit

    filter options:
      -e [PATTERN [PATTERN ...]],
      --env [PATTERN [PATTERN ...]],
      --environment [PATTERN [PATTERN ...]],
      --environments [PATTERN [PATTERN ...]]
                            only report modules in environments matching any
                            PATTERN. If the first supplied PATTERN is !, only
                            report modules in environments NOT matching any
                            PATTERN. PATTERN is a case-sensitive glob(7)-style
                            pattern.
      -m [MODULES [MODULES ...]],
      --mod [MODULES [MODULES ...]],
      --module [MODULES [MODULES ...]],
      --modules [MODULES [MODULES ...]]
                            only report modules matching any PATTERN. If the
                            first supplied PATTERN is !, only report modules NOT
                            matching any PATTERN. PATTERN is a case-sensitive
                            glob(7)-style pattern.

    display options:
      -c, --compare         compare mode will only show modules that differ
                            between environments.
      --version-check       disable check for latest version (forge modules) or
                            latest git tag (git modules). The information is
                            cached for subsequent runs. (default: True)
      --no-version-check    disable check for latest version (forge modules) or
                            latest git tag (git modules). (default: False)
      --wrap                enable wrapping of long lines. (default: True)
      --no-wrap             disable wrapping of long lines. (default: False)

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


Gather a report of modules apache, php and mysql in environments starting with
Cust:

.. code-block:: text

    crmngr report --environments "Cust*" --modules apache php mysql

Gather a report of all modules in environments CustProd, CustStage and CustDev.
Only show the differences.

.. code-block:: text

    crmngr report --environments CustProd CustStage CustDev --compare

update
======

The update command updates, adds or removes modules from environments.

The update command will display a diff for every affected environment and will
ask you to confirm the changes.

**NOTE**:
    The author part of a module name is *only* used to find the correct module
    on forge. If you run update on --module puppetlabs/stdlib, this will also
    affect all other stdlib modules that might be in a environment (i.e.
    otherauthor/stdlib or stdlib installed from git will be replaced by
    puppetlabs/stdlib).


.. code-block:: text



    usage: crmngr update [-h] [-e [PATTERN [PATTERN ...]]]
                         [-m [PATTERN [PATTERN ...]]] [--add] [--remove]
                         [-r ENVIRONMENT] [-n | --non-interactive]
                         [--forge | --git [URL]] [--version [FORGE_VERSION] |
                         --tag [GIT_TAG] | --commit GIT_COMMIT | --branch
                         GIT_BRANCH]

    Update puppet environment.

    This command allows to update module version, and addition or removal of
    puppet modules in one or more environment.

    If the update command is run without update or version options all modules
    matching the filter options will be updated to the latest available version.
    (forge version for forge module, git tag (if available) or HEAD for git
    modules).

    optional arguments:
      -h, --help            show this help message and exit

    filter options:
      -e [PATTERN [PATTERN ...]],
      --env [PATTERN [PATTERN ...]],
      --environment [PATTERN [PATTERN ...]],
      --environments [PATTERN [PATTERN ...]]
                            only update modules in environments matching any
                            PATTERN. If the first supplied PATTERN is !, only
                            update modules in environments NOT matching any
                            PATTERN. PATTERN is a case-sensitive glob(7)-style
                            pattern.
      -m [PATTERN [PATTERN ...]],
      --mod [PATTERN [PATTERN ...]],
      --module [PATTERN [PATTERN ...]],
      --modules [PATTERN [PATTERN ...]]
                            only update modules matching any PATTERN. If the
                            first supplied PATTERN is !, only update modules NOT
                            matching any PATTERN. PATTERN is a case-sensitive
                            glob(7)-style pattern unless a version option is
                            specified. If a version option is specified, PATTERN
                            needs to be a single module name. If updating a
                            forge module (--forge) this needs to be in
                            author/module format.

    update options:
      --add                 add modules (-m) if not already in environment.
                            Default behaviour is to only update modules (-m) in
                            environments they are already deployed in.
      --remove              remove module from Puppetfile. version options
                            (--version, --tag, --commit, --branch) are
                            irrelevant. All modules matching a module filter
                            pattern (-m) will be removed. This also applies if a
                            module pattern includes an author (forge module).
                            Only the module name is relevant.
      -r ENVIRONMENT, --reference ENVIRONMENT
                            use ENVIRONMENT as reference. All modules will be
                            updated to the version deployed in the reference
                            ENVIRONMENT. If combined with --add, modules not yet
                            in the environments (-e) are added. If combined with
                            --remove, modules not in reference will be removed
                            from the environments (-e).

    interactivity options:
      -n, --dry-run, --diff-only
                            display diffs of what would be changed
      --non-interactive     in non-interactive mode, crmngr will neither ask for
                            confirmation before commit or push, nor will it show
                            diffs of what will be changed. Use with care!

    version options:
      these options are only applicable if operating on a single module.

      --forge               source module from puppet forge.
      --git [URL]           source module from git URL. If specified without URL
                            the existing URL will be used. URL is mandatory if
                            invoked with --add.
      --version [FORGE_VERSION]
                            pin module to forge version. If parameter is
                            specified without VERSION, latest available version
                            from forge will be used instead
      --tag [GIT_TAG]       pin a module to a git tag. If parameter is specified
                            without TAG, latest tag available in git repository
                            is used instead
      --commit GIT_COMMIT   pin module to a git commit
      --branch GIT_BRANCH   pin module to a git branch


Examples
--------

Sanitize Puppetfiles of all branches:

.. code-block:: text

    crmngr update


Update stdlib module in all branches to latest forge version.


.. code-block:: text

    crmngr update --module puppetlabs/stdlib --forge --version


Update stdlib module in all branches to latest forge version. Additionally add
the module to branches that currently lack the stdlib module

.. code-block:: text

    crmngr update --module puppetlabs/stdlib --forge --version --add


Remove icinga modules from control repository branches that end with Vagrant.

.. code-block:: text

    crmngr update --remove --module icinga --environments "*Vagrant"


Update apache module to git branch 2.0.x in control repository branch Devel

.. code-block:: text

    crmngr update --environments Devel \
                  --module apache \
                  --git git@github.com:puppetlabs/puppetlabs-apache.git \
                  --branch 2.0.x


profiles
========

The profile command lists available configuration profiles.

.. code-block:: bash

    usage: crmngr profiles


***********
Development
***********

run development version
=======================

.. code-block:: bash

    git clone https://github.com/vshn/crmngr crmngr-project
    cd crmngr-project
    python -m venv pyvenv
    . pyvenv/bin/activate
    pip install -r requirements.txt

    python -m crmngr



.. _AUR: https://aur.archlinux.org/packages/crmngr/
.. _PPA: https://launchpad.net/~vshn/+archive/ubuntu/crmngr
.. _github-r10k: https://github.com/puppetlabs/r10k
.. _Puppetfile:
  https://github.com/puppetlabs/r10k/blob/master/doc/puppetfile.mkd
