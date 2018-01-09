Change Log
==========

All notable changes to this project will be documented in this file.

`Unreleased`_
-------------

Fixed
~~~~~

- Title in environments command did not reflect the active profile correctly,
  it would always report the environment list would be for the default
  profile.


`2.0.1`_ - 2017-02-13
---------------------

Fixed
~~~~~

- Fix handling of forge modules without a current_release. (`#13`_)


`2.0.0`_ - 2017-01-13
---------------------

Changed
~~~~~~~

- Clarify install procedures in README.


`2.0.0rc1`_ - 2017-01-05
------------------------

Added
~~~~~

- Added `--reference`/`-r` option to the update command. This allows updating
  modules to the same versions as in the reference environment. Can be combined
  with `--add`/`--update`.
- Added `--compare`/`-c` option to the report command. This mode will show only
  the differences between two or more environments. I.e. modules that are
  deployed in different versions, or modules missing from some environments.
- The match algorithm used for environments (-e) and modules (-m) does now.
  support negation. When the first pattern to match is `!`, environments and
  modules that do **NOT** match any of the following patterns will be
  processed.
- Added `--wrap`/`--no-wrap` options to report mode. This allows to disable
  automatic wrapping of long-lines. Default is to wrap, unless overriden by
  the new `wrap` option in the `prefs` file.
- crmngr will emit a warning and exit with an exit code 1, if the requested
  operation does not affect any environment.
- Added command `environments` to list environments.
- Added command `create` to create a new environment. This supports creating
  either empty environments or environments as clones of existing ones.
- Added command `delete` to delete an environment.

Changed
~~~~~~~

- When updating existing git modules, it is no longer necessary to specify the
  URL.
- In update mode, when not specifying update or version updates, all modules
  matched by the filter options will be updated to the latest available version.
  For forge modules this will be the latest forge version, for git modules it
  will be the latest tag (if any) or HEAD of the default branch.
- In update mode, when working on forge module you have to explicitly specify
  the new paramter `--forge`. This makes the CLI more consistent between forge
  and git modules.
- `--version-check`/`--no-version-check` are new options of the report
  command rather than global crmngr options.
- `--cache`/`--no-cache` options have been replaced by a `--cache-ttl` option.
  This allows more granuality. Setting `--cache-ttl 0` will yield the same
  behaviour than `--no-cache` would have in previous versions. In the `prefs`
  file a new option `cache_ttl` has been introduced to set the default value
  for the `--cache_ttl` cli option. The `cache` `prefs` option has been removed.
- crmngr no longer updates the local clone of the control repository before
  updating Puppetfiles. This means if someone else pushes changes to the
  control repository during your crmngr run, crmngr might fail to update the
  control repository and exit. Previously changes would silently be reverted.
- In report mode, environments are now displayed space-separated rather
  than comma-separated. This now matches how environments need to be
  specified on the CLI.
- In the report, versions are now sorted with a natural sorting algorithm.
  This means that f.e. 1.10.x will correctly show as newer than 1.2.x which was
  not the case before.
- Cache handling and internal data structures have been vastly improved.
  update operations do not need a populated cache anymore and only
  information for modules and environments currently working on are being
  processed. This is a major performance improvement over the previous
  release.
- Wherever possible crmngr now uses git shallow clones to save bandwidth and
  increase performance.
- crmngr now depends on the 3rd-party libraries `natsort`_ and `requests`_

Removed
~~~~~~~

- support for console_clear_command has been removed.
- support for Puppetfile module categorization has been removed.
- option `--report-unused` has been removed from the report command. A similar
  functionality is provided by the new `--compare`/`-c` option.



1.0.0 - 2015-12-04
------------------

Added
~~~~~

- initial public release

.. _Unreleased: https://github.com/vshn/crmngr/compare/v2.0.1...HEAD
.. _2.0.1: https://github.com/vshn/crmngr/compare/v2.0.0...v2.0.1
.. _2.0.0: https://github.com/vshn/crmngr/compare/v2.0.0rc1...v2.0.0
.. _2.0.0rc1: https://github.com/vshn/crmngr/compare/v1.0.0...v2.0.0rc1
.. _#13: https://github.com/vshn/crmngr/issues/13
.. _natsort: https://pypi.python.org/pypi/natsort
.. _requests: https://pypi.python.org/pypi/requests
