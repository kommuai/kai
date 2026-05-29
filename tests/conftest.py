import os
from pathlib import Path

import pytest

_MINIMAL = Path(__file__).resolve().parent / "fixtures" / "minimal_workspace"


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
    _apply_kai_home(_MINIMAL)


@pytest.fixture(autouse=True)
def _default_minimal_home():
    _apply_kai_home(_MINIMAL)
    yield


@pytest.fixture
def minimal_kai_home():
    _apply_kai_home(_MINIMAL)
    yield _MINIMAL


@pytest.fixture
def kommu_tenant_home():
    """Optional: point KAI_HOME at sibling kai-tenant-kommu for tenant integration runs."""
    tenant = Path(__file__).resolve().parents[2] / "kai-tenant-kommu"
    if not tenant.is_dir():
        pytest.skip("kai-tenant-kommu not present")
    _apply_kai_home(tenant)
    yield tenant
