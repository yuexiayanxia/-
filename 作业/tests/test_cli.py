import subprocess
import sys
from pathlib import Path

PKG_DIR = str(Path(__file__).parent.parent)


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "codereflex.cli", "--help"],
        capture_output=True, text=True, cwd=PKG_DIR,
    )
    assert result.returncode == 0
    assert "setup" in result.stdout
    assert "run" in result.stdout
