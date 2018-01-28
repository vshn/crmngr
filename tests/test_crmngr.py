import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from crmngr import ControlRepository
from crmngr.puppetfile import GitTag


@pytest.fixture()
def control_repo():
    git_dir = TemporaryDirectory(prefix='crmngr_test_')
    bare_dir = Path(git_dir.name, 'bare')
    work_dir = Path(git_dir.name, 'work')
    subprocess.run(['git', 'init', '--bare', str(bare_dir)])
    subprocess.run(['git', 'clone', bare_dir, str(work_dir)])
    subprocess.run(['git', 'checkout', '-b', 'production'], cwd=str(work_dir))
    with open(str(Path(work_dir, 'Puppetfile')), 'w') as puppetfile:
        puppetfile.write("\n".join([
            "forge 'http://forge.puppetlabs.com'",
            "",
            "mod 'firewall',",
            "  :git => 'https://github.com/puppetlabs/puppetlabs-firewall.git',",
            "  :tag => '1.11.0'",
            "mod 'puppetlabs/stdlib', '4.20.0'"
            ""
        ]))
    subprocess.run(['git', 'add', str(Path(work_dir, 'Puppetfile'))], cwd=str(work_dir))
    subprocess.run(['git', 'commit', '-m', 'Initial commit', 'Puppetfile'], cwd=str(work_dir))
    subprocess.run(['git', 'push', 'origin', 'production'], cwd=str(work_dir))
    subprocess.run(['git', 'checkout', '--orphan', 'staging'], cwd=str(work_dir))
    with open(str(Path(work_dir, 'Puppetfile')), 'w') as puppetfile:
        puppetfile.write("\n".join([
            "forge 'http://forge.puppetlabs.com'",
            "",
            "mod 'puppetlabs/firewall', '1.10.0",
            "mod 'puppetlabs/stdlib', '4.23.0'"
            ""
        ]))
    subprocess.run(['git', 'add', str(Path(work_dir, 'Puppetfile'))], cwd=str(work_dir))
    subprocess.run(['git', 'commit', '-m', 'Initial commit', 'Puppetfile'], cwd=str(work_dir))
    subprocess.run(['git', 'push', 'origin', 'staging'], cwd=str(work_dir))
    yield ControlRepository(clone_url="file://{}".format(bare_dir))
    git_dir.cleanup()


class TestCrmngr:

    def test_environments(self, control_repo):
        assert sorted(control_repo.branches) == ['production', 'staging']

    def test_stdlib_staging(self, control_repo):
        staging = control_repo.get_environment('staging')
        assert str(staging['firewall']) == 'firewall:forge:puppetlabs:Forge(1.10.0)'

    def test_stdlib_production(self, control_repo):
        production = control_repo.get_environment('production')
        assert str(production['firewall']) == 'firewall:git:https://github.com/puppetlabs/puppetlabs-firewall.git:GitTag(1.11.0)'
