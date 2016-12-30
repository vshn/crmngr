"""manage a r10k-style control repository"""

# stdlib
from configparser import NoSectionError
import logging
import sys

# 3rd-party
from crmngr import cprint
from crmngr.cache import JsonCache
from crmngr.cli import parse_cli_args
from crmngr.config import CrmngrConfig
from crmngr.config import setup_logging
from crmngr.controlrepository import ControlRepository
from crmngr.controlrepository import NoEnvironmentError
from crmngr.utils import query_yes_no

LOG = logging.getLogger(__name__)


def main():
    """main entrypoint"""
    try:
        configuration = CrmngrConfig()
    except NoSectionError:
        print("No valid profile file found!")
        print("Enter git url of control repositoriy to create one.")
        print("Leave empty to abort")
        print()
        print("Control repository url: ", end="")
        default_profile_url = input().strip()
        if default_profile_url:
            configuration = CrmngrConfig.create_default_configuration(
                default_profile_url
            )
        else:
            sys.exit()

    cli_args = parse_cli_args(configuration)
    # now that the profile is known, reload the configuration using the
    # correct profile
    try:
        configuration = CrmngrConfig(profile=cli_args.profile)
    except NoSectionError:
        cprint.red('No configuration for profile {profile}'.format(
            profile=cli_args.profile
        ))
        sys.exit(1)

    setup_logging(cli_args.debug)

    version_cache = JsonCache(configuration.cache_dir, ttl=cli_args.cache_ttl)

    commands = {
        'clean': command_clean,
        'create': command_create,
        'delete': command_delete,
        'environments': command_environments,
        'profiles': command_profiles,
        'report': command_report,
        'update': command_update,
    }
    try:
        commands[cli_args.command](
            configuration=configuration,
            cli_args=cli_args,
            version_cache=version_cache)
    except NoEnvironmentError:
        cprint.yellow_bold('no environment is affected by your command. typo?')
    except KeyboardInterrupt:
        cprint.red_bold('crmngr has been aborted.')


def command_create(*, configuration, cli_args, version_cache,
                   **kwargs):  # pylint: disable=unused-argument
    """run create command"""
    control_repo = ControlRepository(
        clone_url=configuration.control_repo_url,
    )
    environments = [environment.name
                    for environment in control_repo.environments]

    if cli_args.environment in environments:
        cprint.red(
            'Template environment {environment} already exists in '
            'control repository {profile} ({url})'.format(
                environment=cli_args.environment,
                profile=cli_args.profile,
                url=control_repo.url,
            ))
        sys.exit(1)
    if cli_args.template:
        if cli_args.template.strip() not in environments:
            cprint.red(
                'Template environment {template} does not exist in '
                'control repository {profile} ({url})'.format(
                    template=cli_args.template,
                    profile=cli_args.profile,
                    url=control_repo.url,
                ))
            sys.exit(1)
        control_repo.clone_environment(
            cli_args.template,
            cli_args.environment,
            report=cli_args.report,
        )
        if cli_args.report:
            control_repo.report(
                version_cache=version_cache,
                version_check=cli_args.version_check,
                wrap=cli_args.wrap,
            )
    else:
        control_repo.new_environment(
            cli_args.environment,
            report=cli_args.report
        )
        cprint.green('Created new empty environment %s' % cli_args.environment)


def command_delete(*, configuration, cli_args,
                   **kwargs):  # pylint: disable=unused-argument
    """run delete command"""
    control_repo = ControlRepository(
        clone_url=configuration.control_repo_url,
        environments=[cli_args.environment, ]
    )
    environment = sorted(control_repo.environments)[0]
    if query_yes_no("Really delete environment {}? This is a irreversible "
                    "operation!".format(environment), default='no'):
        control_repo.delete_environment(environment)
        cprint.green('Deleted environment {}'.format(environment))


def command_report(*, configuration, cli_args, version_cache,
                   **kwargs):  # pylint: disable=unused-argument
    """run report command"""
    control_repo = ControlRepository(
        clone_url=configuration.control_repo_url,
        environments=cli_args.environments,
        modules=cli_args.modules,
    )

    if cli_args.compare and not len(control_repo.environments) >= 2:
        cprint.yellow_bold(
            'At least two environments required in compare mode. Only matched '
            'environment: {}'.format(
                ', '.join([environment.name
                           for environment in control_repo.environments])
            )
        )
        sys.exit(1)

    control_repo.report(
        compare=cli_args.compare,
        version_cache=version_cache,
        version_check=cli_args.version_check,
        wrap=cli_args.wrap,
    )


def command_environments(*, configuration,
                         **kwargs):  # pylint: disable=unused-argument
    """run environments command"""
    control_repo = ControlRepository(
        clone_url=configuration.control_repo_url,
    )
    cprint.white_bold('Environments in profile %s' % 'default')
    for environment in sorted(control_repo.environments):
        cprint.white(' - {}'.format(environment.name))


def command_update(*, configuration, cli_args,
                   **kwargs):  # pylint: disable=unused-argument
    """run report command"""

    if cli_args.reference:
        environments = cli_args.environments + [cli_args.reference]
    else:
        environments = cli_args.environments

    control_repo = ControlRepository(
        clone_url=configuration.control_repo_url,
        environments=environments,
    )
    control_repo.update_puppetfiles(
        cli_args=cli_args,
    )


def command_clean(*, version_cache,
                  **kwargs):  # pylint: disable=unused-argument
    """run clean command"""
    if query_yes_no("Really clear cache directory?"):
        return version_cache.clear()


def command_profiles(*, configuration,
                     **kwargs):  # pylint: disable=unused-argument
    """run profiles command"""
    cprint.white_bold('Available profiles:')
    for profile in configuration.profiles:
        cprint.white(" - %s: %s" % (profile.name, profile.repository))
