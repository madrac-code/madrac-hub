"""Shared fixtures for MADRAC-SUBS v3 tests."""

import pytest
from madrac.config import get_config_manager


@pytest.fixture(autouse=True)
def reset_config():
    """Reset config manager before each test to avoid cross-test pollution."""
    from madrac.config.manager import _manager
    import madrac.config.manager as cfg_mod
    cfg_mod._manager = None
    yield
    cfg_mod._manager = None
