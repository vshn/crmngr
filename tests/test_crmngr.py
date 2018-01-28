import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from crmngr import ControlRepository
from crmngr.puppetfile import GitTag


class FakeCliArgs:

    def __init__(self):
        """"""
        """self.noninteractive = True"""

    def __getattr__(self, item):
        return None


@pytest.fixture()
def control_repo():
    git_dir = TemporaryDirectory(prefix='crmngr_test_')
    bare_dir = Path(git_dir.name, 'bare')
    work_dir = Path(git_dir.name, 'work')
    subprocess.run(['git', 'init', '--bare', str(bare_dir)])
    subprocess.run(['git', 'clone', bare_dir, str(work_dir)])
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
    subprocess.run(['git', 'push', 'origin', 'master'], cwd=str(work_dir))
    yield bare_dir
    git_dir.cleanup()


class TestCrmnger:
    def test_sanitize_puppetfile(self, control_repo):
        control = ControlRepository(clone_url=str(control_repo))
        assert list(control.branches) == ['master']
        assert len(control.modules) == 2
