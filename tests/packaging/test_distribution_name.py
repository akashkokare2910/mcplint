"""Proves the PyPI distribution name (`mcplint-cli`) and the Python import
package / CLI command name (`mcplint`) are correctly decoupled.

This is slow (builds a real wheel and creates a real venv) and duplicates
what `.github/workflows/ci.yml`'s `build-and-verify-package` and
`install-and-smoke-test` jobs already verify on every push/PR at the
workflow level. It's kept here as a local regression check and a concrete,
runnable proof of the naming property. Marked `slow` and excluded from the
default `pytest` run (see `addopts` in pyproject.toml) so it doesn't build
a wheel on every test invocation. Run explicitly with:
pytest tests/packaging -v -m slow
"""

from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.slow
def test_wheel_has_distribution_name_mcplint_cli(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist_dir)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        timeout=180,
    )

    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"
    wheel_path = wheels[0]

    assert wheel_path.name.startswith("mcplint_cli-"), (
        f"wheel filename should start with the distribution name 'mcplint_cli-' "
        f"(PyPI normalizes '-' to '_' in filenames), got: {wheel_path.name}"
    )

    metadata = subprocess.run(
        [sys.executable, "-m", "zipfile", "-e", str(wheel_path), str(tmp_path / "extracted")],
        check=True,
        capture_output=True,
        timeout=30,
    )
    assert metadata.returncode == 0

    dist_info_dirs = list((tmp_path / "extracted").glob("*.dist-info"))
    assert len(dist_info_dirs) == 1
    metadata_text = (dist_info_dirs[0] / "METADATA").read_text()
    assert "Name: mcplint-cli" in metadata_text

    _install_and_verify_runtime_identity(wheel_path, tmp_path / "smoke-venv")


def _install_and_verify_runtime_identity(wheel_path: Path, venv_dir: Path) -> None:
    venv.create(venv_dir, with_pip=True)
    venv_python = venv_dir / "bin" / "python"

    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--quiet", str(wheel_path)],
        check=True,
        capture_output=True,
        timeout=120,
    )

    # The import package is `mcplint`, not `mcplint_cli`: the distribution
    # name never needs to be importable.
    import_result = subprocess.run(
        [str(venv_python), "-c", "import mcplint; print(mcplint.__version__)"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert import_result.returncode == 0, import_result.stderr
    assert import_result.stdout.strip()

    no_such_module = subprocess.run(
        [str(venv_python), "-c", "import mcplint_cli"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert no_such_module.returncode != 0
    assert "ModuleNotFoundError" in no_such_module.stderr

    venv_mcplint = venv_dir / "bin" / "mcplint"
    assert venv_mcplint.exists(), "the installed CLI command must be named 'mcplint'"

    version_result = subprocess.run(
        [str(venv_mcplint), "--version"], capture_output=True, text=True, timeout=30
    )
    assert version_result.returncode == 0
    assert "mcplint" in version_result.stdout

    rules_result = subprocess.run(
        [str(venv_mcplint), "rules"], capture_output=True, text=True, timeout=30
    )
    assert rules_result.returncode == 0
    assert "missing-tool-description" in rules_result.stdout


def test_source_package_directory_is_still_src_mcplint() -> None:
    assert (REPO_ROOT / "src" / "mcplint").is_dir()
    assert (REPO_ROOT / "src" / "mcplint" / "__about__.py").is_file()
    assert not (REPO_ROOT / "src" / "mcplint_cli").exists()
