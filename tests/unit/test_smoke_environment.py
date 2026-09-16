"""Unit tests for smoke suite environment setup helpers."""
import importlib
import sys
import types
from unittest.mock import MagicMock, patch


def _setup_stubs():
    # Stub behave
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    # Stub dogtail
    dogtail_stub = types.ModuleType("dogtail")
    tree_stub = types.ModuleType("dogtail.tree")
    tree_stub.root = MagicMock()
    sys.modules["dogtail"] = dogtail_stub
    sys.modules["dogtail.tree"] = tree_stub

    # Stub qecore
    qecore_stub = types.ModuleType("qecore")
    qecore_common_stub = types.ModuleType("qecore.common_steps")
    sys.modules["qecore"] = qecore_stub
    sys.modules["qecore.common_steps"] = qecore_common_stub

    # Stub steps and steps.app_support
    steps_stub = types.ModuleType("steps")
    steps_steps_stub = types.ModuleType("steps.steps")
    steps_steps_stub._dismiss_welcome_dialog = MagicMock()
    app_support_stub = types.ModuleType("steps.app_support")
    app_support_stub._IN_CONTAINER = False
    app_support_stub._ssh_run = MagicMock()
    sys.modules["steps"] = steps_stub
    sys.modules["steps.steps"] = steps_steps_stub
    sys.modules["steps.app_support"] = app_support_stub


def test_before_all_configures_idle_lock_suppression():
    """Verify before_all sets idle-delay 0 and lock-enabled false."""
    _setup_stubs()
    sys.modules["steps.app_support"]._IN_CONTAINER = False

    with patch("time.sleep"), \
         patch("subprocess.run") as mock_run, \
         patch("tests.shared.ssh_config.populate_ssh_context"), \
         patch("builtins.open", MagicMock()):
        mock_run.return_value = MagicMock(returncode=0, stdout="(true, 'true')")

        env = importlib.import_module("tests.smoke.features.environment")
        context = MagicMock()
        try:
            env.before_all(context)
        except Exception:  # noqa: BLE001
            pass

        calls = [c[0][0] for c in mock_run.call_args_list if len(c[0]) > 0 and isinstance(c[0][0], list)]
        assert ["gsettings", "set", "org.gnome.desktop.session", "idle-delay", "0"] in calls
        assert ["gsettings", "set", "org.gnome.desktop.screensaver", "lock-enabled", "false"] in calls


def test_before_all_forwards_idle_lock_suppression_via_ssh_in_container():
    """Verify before_all forwards idle-delay and lock-enabled gsettings via SSH when _IN_CONTAINER is True."""
    _setup_stubs()
    sys.modules["steps.app_support"]._IN_CONTAINER = True
    mock_ssh_run = MagicMock(returncode=0, stdout="(true, 'true')")
    sys.modules["steps.app_support"]._ssh_run = mock_ssh_run

    with patch("time.sleep"), \
         patch("subprocess.run") as mock_run, \
         patch("tests.shared.ssh_config.populate_ssh_context"), \
         patch("builtins.open", MagicMock()):
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        env = importlib.import_module("tests.smoke.features.environment")
        context = MagicMock()
        try:
            env.before_all(context)
        except Exception:  # noqa: BLE001
            pass

        ssh_calls = [c[0][0] for c in mock_ssh_run.call_args_list if len(c[0]) > 0 and isinstance(c[0][0], str)]
        assert any("idle-delay 0" in c and "lock-enabled false" in c for c in ssh_calls)

