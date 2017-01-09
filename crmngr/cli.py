""" crmngr cli module """

# stdlib
import argparse
import sys
import textwrap

# crmngr
from crmngr.version import __version__


def parse_cli_args(configuration):
    """parse CLI args"""

    # global cli options
    parser = argparse.ArgumentParser(
        description='manage a r10k-style control repository',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog='crmngr',
    )
    parser.add_argument(
        '-v', '--version',
        action='version', version='%(prog)s ' + __version__
    )
    parser.add_argument(
        '--cache-ttl',
        dest='cache_ttl', type=int, metavar='TTL',
        help='time-to-live in seconds for version cache entries',
    )
    parser.add_argument(
        '-d', '--debug',
        dest='debug', action='store_true', default=False,
        help='enable debug output'
    )
    parser.add_argument(
        '-p', '--profile',
        dest='profile', default='default',
        help='crmngr configuration profile'
    )

    # set defaults for global options
    parser.set_defaults(
        cache_ttl=configuration.cache_ttl,
    )

    # define command parsers
    command_parser = parser.add_subparsers(
        title='commands',
        dest='command',
        description=('valid commands. Use -h/--help on command for usage '
                     'details'),
    )
    command_parser.required = True
    command_parser_defaults = {
        'parent_parser': command_parser,
        'configuration': configuration,
    }
    clean_command_parser(**command_parser_defaults)
    create_command_parser(**command_parser_defaults)
    delete_command_parser(**command_parser_defaults)
    environments_command_parser(**command_parser_defaults)
    profiles_command_parser(**command_parser_defaults)
    report_command_parser(**command_parser_defaults)
    update_parser = update_command_parser(**command_parser_defaults)

    args = parser.parse_args()
    try:
        verify_update_args(args)
    except CliError as exc:
        update_parser.print_help()
        sys.exit("error: %s" % exc)
    return args


def _ensure_single_module(args):
    """ensure that we only operate on a single module."""
    if args.modules is None or len(args.modules) < 1:
        raise CliError('it is not supported to specify --git/--forge '
                       'without specifying a module (-m).')
    if args.modules is not None and len(args.modules) > 1:
        raise CliError('cannot operate on multiple modules when version '
                       'options are set.')
    if args.reference is not None:
        raise CliError('it is not supported to specify -r/--reference '
                       'in combination with version options.')
    if args.add and args.remove:
        raise CliError('it is not supported to specify both --add/--remove '
                       'when working on a single module.')


def _reject_git_version_parameters(args):
    """reject git version parameters."""
    if args.git_branch or args.git_commit or args.git_tag:
        raise CliError('it is not supported to specify --branch/--commit/'
                       '--tag without --git.')


def _reject_forge_version_parameter(args):
    """reject forge version parameter."""
    if args.forge_version:
        raise CliError('it is not supported to specifiy --version without '
                       '--forge.')


def verify_update_args(args):
    """perform some extended validation of update parser cli arguments"""
    if args.command != 'update':
        return

    if args.git_url:
        _ensure_single_module(args)
        _reject_forge_version_parameter(args)
        if args.forge_version:
            raise CliError('--version is not supported for git modules.')
    elif args.forge:
        _ensure_single_module(args)
        _reject_git_version_parameters(args)
        if not args.remove:
            if '/' not in args.modules[0]:
                raise CliError('when adding or updating forge modules, -m '
                               'has to be in author/module format')
    else:
        _reject_forge_version_parameter(args)
        _reject_git_version_parameters(args)
        if args.add:
            raise CliError('--add is not supported for bulk updates. Combine '
                           '--add with version options.')
        if args.remove:
            if args.modules is None or len(args.modules) < 1:
                raise CliError('it is not supported to specify --remove '
                               'without specifying a module filter (-m).')


def clean_command_parser(parent_parser,
                         **kwargs):  # pylint: disable=unused-argument
    """sets up the argument parser for the clean command"""
    parser = parent_parser.add_parser(
        'clean',
        description=(
            'Clean version cache.\n'
            '\n'
            'This will delete the cache directory (~/.crmngr/cache).'
        ),
        formatter_class=KeepNewlineDescriptionHelpFormatter,
        help='clean version cache',
    )
    return parser


def create_command_parser(parent_parser, configuration,
                          **kwargs):  # pylint: disable=unused-argument
    """sets up the argument parser for the create command"""
    parser = parent_parser.add_parser(
        'create',
        description=(
            'Create a new environment.\n'
            '\n'
            'Unless --template/-t is specified, this command will create a new '
            'environment containing the following files (tldr. an environemnt '
            'without any modules):\n'
            '\n'
            'Puppetfile\n'
            '---\n'
            "forge 'http://forge.puppetlabs.com'\n"
            '\n'
            '---\n'
            '\n'
            'manifests/site.pp\n'
            '---\n'
            "hiera_include('classes')\n"
            '---\n'
            '\n'
            'If --template/-t is specified, the command will clone the '
            'existing ENVIRONMENT including all files and directories it '
            'contains.'
        ),
        formatter_class=KeepNewlineDescriptionHelpFormatter,
        help='create a new environment',
    )
    parser.add_argument(
        dest='environment', type=str,
        help='name of the new environment'
    )
    parser.add_argument(
        '-t', '--template',
        type=str, dest='template', metavar='ENVIRONMENT',
        help='name of an existing environment to clone the new environment from'
    )
    report_group = parser.add_argument_group('report options')
    report_group.add_argument(
        '--no-report',
        dest='report',
        action='store_false',
        help=('disable printing a report for the new environment '
              '(default: False)'),
    )

    version_check_group = report_group.add_mutually_exclusive_group()
    version_check_group.add_argument(
        '--version-check',
        dest='version_check',
        action='store_true',
        help=('enable check for latest version (forge modules) or latest git '
              'tag (git modules). '
              '(default: %s)' % str(configuration.version_check))
    )
    version_check_group.add_argument(
        '--no-version-check',
        dest='version_check',
        action='store_false',
        help=('disable check for latest version (forge modules) or latest '
              'git tag (git modules). '
              '(default: %s)' % str(not configuration.version_check))
    )
    wrap_group = report_group.add_mutually_exclusive_group()
    wrap_group.add_argument(
        '--wrap',
        dest='wrap',
        action='store_true',
        help=('enable wrapping of long lines. '
              '(default: %s)' % str(configuration.wrap)),
    )
    wrap_group.add_argument(
        '--no-wrap',
        dest='wrap',
        action='store_false',
        help=('disable wrapping long lines. '
              '(default: %s)' % str(not configuration.wrap)),
    )
    parser.set_defaults(
        version_check=configuration.version_check,
        wrap=configuration.wrap,
    )
    return parser


def delete_command_parser(parent_parser,
                          **kwargs):  # pylint: disable=unused-argument
    """sets up the argument parser for the delete command"""
    parser = parent_parser.add_parser(
        'delete',
        description=(
            'Delete an environment.\n'
            '\n'
            'The command will ask for confirmation.'
        ),
        formatter_class=KeepNewlineDescriptionHelpFormatter,
        help='delete an environment',
    )
    parser.add_argument(
        dest='environment', type=str,
        help='name of the environment to delete'
    )
    return parser


def environments_command_parser(parent_parser,
                                **kwargs):  # pylint: disable=unused-argument
    """sets up the argument parser for the environments command"""
    parser = parent_parser.add_parser(
        'environments',
        description=('List all environments in the control-repository of the '
                     'currently selected profile.'),
        help='list all environments of the selected profile',
    )
    return parser


def profiles_command_parser(parent_parser,
                            **kwargs):  # pylint: disable=unused-argument
    """sets up the argument parser for the profiles command"""
    parser = parent_parser.add_parser(
        'profiles',
        description=(
            'List all available configuration profiles.\n'
            '\n'
            'To add a new configuration profile, open ~/.crmngr/profiles and '
            'add a new section:\n'
            '\n'
            '[new_profile_name]\n'
            'repository = control-repo-url\n'
            '\n'
            'Ensure there is always a default section!'
        ),
        formatter_class=KeepNewlineDescriptionHelpFormatter,
        help='list available configuration profiles',
    )
    return parser


def report_command_parser(parent_parser, configuration,
                          **kwargs):  # pylint: disable=unused-argument
    """sets up the argument parser for the report command"""
    parser = parent_parser.add_parser(
        'report',
        description=(
            'Generate a report about modules and versions deployed in the '
            'puppet environments.'
        ),
        help='generate a report about modules and versions',
    )
    filter_group = parser.add_argument_group('filter options')
    filter_group.add_argument(
        '-e', '--env', '--environment', '--environments',
        nargs='*', type=str, dest='environments', metavar='PATTERN',
        help=('only report modules in environments matching any PATTERN. '
              'If the first supplied PATTERN is !, only report modules '
              'in environments NOT matching any PATTERN. '
              'PATTERN is a case-sensitive glob(7)-style pattern.')
    )
    filter_group.add_argument(
        '-m', '--mod', '--module', '--modules',
        nargs='*', type=str, dest='modules',
        help=('only report modules matching any PATTERN. If the first '
              'supplied PATTERN is !, only report modules NOT matching any '
              'PATTERN. PATTERN is a case-sensitive glob(7)-style pattern.')
    )
    display_group = parser.add_argument_group('display options')
    display_group.add_argument(
        '-c', '--compare',
        dest='compare', action='store_true',
        help=('compare mode will only show modules that differ between '
              'environments.'),
    )
    version_check_group = display_group.add_mutually_exclusive_group()
    version_check_group.add_argument(
        '--version-check',
        dest='version_check',
        action='store_true',
        help=('disable check for latest version (forge modules) or latest git '
              'tag (git modules). The information is cached for subsequent'
              ' runs. (default: %s)' % str(configuration.version_check)
             )
    )
    version_check_group.add_argument(
        '--no-version-check',
        dest='version_check',
        action='store_false',
        help=('disable check for latest version (forge modules) or latest '
              'git tag (git modules). '
              '(default: %s)' % str(not configuration.version_check))
    )
    wrap_group = display_group.add_mutually_exclusive_group()
    wrap_group.add_argument(
        '--wrap',
        dest='wrap',
        action='store_true',
        help=('enable wrapping of long lines. '
              '(default: %s)' % str(configuration.wrap)),
    )
    wrap_group.add_argument(
        '--no-wrap',
        dest='wrap',
        action='store_false',
        help=('disable wrapping of long lines. '
              '(default: %s)' % str(not configuration.wrap)),
    )
    parser.set_defaults(
        version_check=configuration.version_check,
        wrap=configuration.wrap,
    )
    return parser


def update_command_parser(parent_parser,
                          **kwargs):  # pylint: disable=unused-argument
    """sets up the argument parser for the report command"""
    parser = parent_parser.add_parser(
        'update',
        description=(
            'Update puppet environment.\n'
            '\n'
            'This command allows to update module version, and addition or '
            'removal of puppet modules in one or more environment.\n'
            '\n'
            'If the update command is run without update or version options '
            'all modules matching the filter options will be updated to the '
            'latest available version. (forge version for forge module, git '
            'tag (if available) or HEAD for git modules).'
        ),
        formatter_class=KeepNewlineDescriptionHelpFormatter,
        help='update puppet environment'
    )
    filter_group = parser.add_argument_group('filter options')
    filter_group.add_argument(
        '-e', '--env', '--environment', '--environments',
        nargs='*', type=str, dest='environments', metavar='PATTERN',
        help=('only update modules in environments matching any PATTERN. '
              'If the first supplied PATTERN is !, only update modules '
              'in environments NOT matching any PATTERN. '
              'PATTERN is a case-sensitive glob(7)-style pattern.')
    )
    filter_group.add_argument(
        '-m', '--mod', '--module', '--modules',
        nargs='*', type=str, dest='modules', metavar='PATTERN',
        help=('only update modules matching any PATTERN. If the first '
              'supplied PATTERN is !, only update modules NOT matching any '
              'PATTERN. PATTERN is a case-sensitive glob(7)-style pattern '
              'unless a version option is specified. If a version option is '
              'specified, PATTERN needs to be a single module name. If '
              'updating a forge module (--forge) this needs to be in '
              'author/module format.')
    )
    update_options = parser.add_argument_group('update options')
    update_options.add_argument(
        '--add',
        default=False, action='store_true',
        help=('add modules (-m) if not already in environment. Default '
              'behaviour is to only update modules (-m) in environments they '
              'are already deployed in.')
    )
    update_options.add_argument(
        '--remove',
        default=False, action='store_true',
        help=('remove module from Puppetfile. version options (--version, '
              '--tag, --commit, --branch) are irrelevant. All modules matching '
              'a module filter pattern (-m) will be removed. This also applies '
              'if a module pattern includes an author (forge module). Only the '
              'module name is relevant.')
    )
    update_options.add_argument(
        '-r', '--reference', metavar='ENVIRONMENT', type=str,
        help=('use ENVIRONMENT as reference. All modules will be updated to '
              'the version deployed in the reference ENVIRONMENT. If combined '
              'with --add, modules not yet in the environments (-e) are added. '
              'If combined with --remove, modules not in reference will be '
              'removed from the environments (-e).')
    )
    interactivity_group = parser.add_argument_group('interactivity options')
    interactivity_mutex = interactivity_group.add_mutually_exclusive_group()
    interactivity_mutex.add_argument(
        '-n', '--dry-run', '--diff-only',
        default=False, action='store_true', dest='diffonly',
        help='display diffs of what would be changed',
    )
    interactivity_mutex.add_argument(
        '--non-interactive',
        default=False, action='store_true', dest='noninteractive',
        help=('in non-interactive mode, crmngr will neither ask for '
              'confirmation before commit or push, nor will it show diffs '
              'of what will be changed. Use with care!')
    )
    version_group = parser.add_argument_group(
        'version options',
        description=('these options are only applicable if operating on a '
                     'single module.'),
    )
    source_mutex = version_group.add_mutually_exclusive_group()
    source_mutex.add_argument(
        '--forge',
        action='store_true', dest='forge',
        help='source module from puppet forge.',
    )
    source_mutex.add_argument(
        '--git',
        nargs='?', type=str, metavar="URL", dest='git_url',
        const='USE_EXISTING_URL',
        help=('source module from git URL. If specified without URL the '
              'existing URL will be used. URL is mandatory if invoked with '
              '--add.'),
    )
    version_mutex = version_group.add_mutually_exclusive_group()
    version_mutex.add_argument(
        '--version',
        nargs='?', const="LATEST_FORGE_VERSION", type=str, dest='forge_version',
        help=('pin module to forge version. If parameter is specified without '
              'VERSION, latest available version from forge will be used '
              'instead')
    )
    version_mutex.add_argument(
        '--tag',
        nargs='?', const="LATEST_GIT_TAG", type=str, dest='git_tag',
        help=('pin a module to a git tag. If parameter is specified without '
              'TAG, latest tag available in git repository is used instead')
    )
    version_mutex.add_argument(
        '--commit',
        type=str, dest='git_commit',
        help='pin module to a git commit'
    )
    version_mutex.add_argument(
        '--branch',
        type=str, dest='git_branch',
        help='pin module to a git branch'
    )
    return parser


class CliError(Exception):
    """exception raised when invalid cli arguments are supplied"""


class KeepNewlineDescriptionHelpFormatter(argparse.HelpFormatter):
    """argparse helpformatter that keeps newlines in the description"""

    def _fill_text(self, text, width, indent):
        return '\n'.join(
            ['\n'.join(textwrap.wrap(
                line,
                width,
                initial_indent=indent,
                subsequent_indent=indent,
                break_long_words=False,
                replace_whitespace=False
            )) for line in text.splitlines()])
