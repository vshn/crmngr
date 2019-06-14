"""
This file should handle output

It takes the various controlrepositories and merges their output
"""

# stdlib
from textwrap import TextWrapper

# crmngr
from crmngr import cprint

# 3rd-party
from natsort import natsorted

from collections import defaultdict


# From controlrepository.report
def report(repositories, wrap=True, version_check=True, version_cache=None, compare=True):
    """print control repository report"""

    self = repositories[0]

    all_modules = defaultdict(lambda: defaultdict(lambda: set))
    # modules is a dict[dict[set]]
    for modules in [repository.modules for repository in repositories]:
        for module_name in modules.keys():
            for tag in modules[module_name]:
                all_modules[module_name][tag] = all_modules[module_name][tag].union(modules[module_name][tag])

    for module, versions in sorted(all_modules.items()):

        # in compare mode, skip modules that are identical in all processed
        # environments.
        if compare and len(versions) == 1 and \
                len(list(versions.values())[0]) == len(self._environments):
            continue

        cprint.white_bold('Module: %s' % module)
        for version, environments in natsorted(
                versions.items(),
                reverse=True,
                key=str
        ):
            version.print_version_information(
                version_check,
                version_cache
            )
            if len(self._environments) > 1:
                cprint.white('Used by:', lpad=4, rpad=4, end='')
                if wrap:
                    used_by = TextWrapper(
                        subsequent_indent=' ' * 16
                    )
                    for line in used_by.wrap(
                            ' '.join(sorted(environments))
                    ):
                        cprint.cyan(line)
                else:
                    cprint.cyan(' '.join(sorted(environments)))
            print()

        if compare:
            # check for modules that are in not in all (but in at least one)
            # processed environments
            missing = set.union(*list(versions.values())) ^ set(
                [environment.name for environment in self._environments]
            )
            if missing:
                cprint.yellow_bold('Missing from:', lpad=2)
                if wrap:
                    not_in = TextWrapper(
                        initial_indent=' ' * 16,
                        subsequent_indent=' ' * 16
                    )
                    for line in not_in.wrap(
                            ' '.join(sorted(missing))
                    ):
                        cprint.yellow(line)
                else:
                    print(' ' * 16, end='')
                    cprint.yellow(' '.join(sorted(missing)))
                print()
