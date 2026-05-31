import os
from pathlib import Path

import pytest

_MINIMAL = Path(__file__).resolve().parent / "fixtures" / "minimal_workspace"


def _apply_shadou_home(path: Path) -> None:
    os.environ["SHADOU_HOME"] = str(path)
    os.environ.pop("AGENT_WORKSPACE", None)
    from shadou.settings import reload_settings
    from shadou.support_runtime.tools.catalog import reload_tool_aliases
    from shadou.workspace.manifest import reload_workspace_manifest
    from shadou.workspace.runtime_settings import reload_grounded_tools, reload_workspace_settings_yaml

    reload_settings()
    reload_workspace_manifest()
    reload_workspace_settings_yaml()
    reload_tool_aliases()
    reload_grounded_tools()


def pytest_configure(config):
    _apply_shadou_home(_MINIMAL)


@pytest.fixture(autouse=True)
def _default_minimal_home():
    _apply_shadou_home(_MINIMAL)
    yield


@pytest.fixture
def minimal_shadou_home():
    _apply_shadou_home(_MINIMAL)
    yield _MINIMAL


@pytest.fixture
def kommu_tenant_home():
    """Optional: point SHADOU_HOME at sibling tenant dir for integration runs."""
    ws = Path(__file__).resolve().parents[2]
    tenant = ws / "shadou-tenant-kommu"
    if not tenant.is_dir():
        pytest.skip("shadou-tenant-kommu not present")
    _apply_shadou_home(tenant)
    yield tenant
