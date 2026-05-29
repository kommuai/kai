import os
from pathlib import Path

import pytest

_MINIMAL = Path(__file__).resolve().parent / "fixtures" / "minimal_workspace"
_KOMMU = Path(__file__).resolve().parent / "fixtures" / "kommu_workspace"


def _apply_kai_home(path: Path) -> None:
    os.environ["KAI_HOME"] = str(path)
    os.environ.pop("AGENT_WORKSPACE", None)
    from kai.settings import reload_settings
    from kai.support_runtime.tools.catalog import reload_tool_aliases
    from kai.workspace.manifest import reload_workspace_manifest
    from kai.workspace.runtime_settings import reload_grounded_tools, reload_workspace_settings_yaml

    reload_settings()
    reload_workspace_manifest()
    reload_workspace_settings_yaml()
    reload_tool_aliases()
    reload_grounded_tools()


def pytest_configure(config):
    _apply_kai_home(_KOMMU)


@pytest.fixture(autouse=True)
def _default_kommu_home():
    _apply_kai_home(_KOMMU)
    yield


@pytest.fixture
def minimal_kai_home():
    _apply_kai_home(_MINIMAL)
    yield _MINIMAL
    _apply_kai_home(_KOMMU)


@pytest.fixture
def kommu_kai_home():
    _apply_kai_home(_KOMMU)
    yield _KOMMU
