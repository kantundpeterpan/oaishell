"""Tests for integrated bearer token management in the Textual TUI.

Covers:
- _mask_token helper
- _sync_token_from_state / startup token init from state
- _update_auth_status subtitle update
- /auth set / status / clear commands
- State-set of a token key triggers engine sync
- after_call token sync
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import MagicMock, patch
from textual.widgets import Input, RichLog

from oai_shell.config.manager import ConfigManager
from oai_shell.engine.client import OpenAIEngine, ClientState
from oai_shell.shell.textual_app import OAIShellApp, TOKEN_KEYS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(token: str | None = None, state_data: dict | None = None):
    """Build a minimal OAIShellApp with an optional pre-seeded state."""
    engine = OpenAIEngine("http://localhost:9999", token=token)
    engine.load_spec(
        {
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "list_items",
                        "summary": "List items",
                        "parameters": [],
                        "responses": {"200": {}},
                    }
                }
            }
        }
    )

    mgr = ConfigManager(None)
    cfg = mgr.config
    cfg.name = "TestShell"

    app = OAIShellApp(cfg, engine)

    if state_data:
        app.state.data.update(state_data)

    return app


# ---------------------------------------------------------------------------
# Unit tests (no Textual pilot needed)
# ---------------------------------------------------------------------------

class TestMaskToken:
    def test_short_token(self):
        assert OAIShellApp._mask_token("abc") == "***"

    def test_exactly_8_chars(self):
        assert OAIShellApp._mask_token("abcdefgh") == "***"

    def test_long_token(self):
        assert OAIShellApp._mask_token("sk-abcdefghijklmnopqrstuvwxyz1234") == "sk-a...1234"

    def test_empty_token(self):
        assert OAIShellApp._mask_token("") == ""


class TestSyncTokenFromState:
    def test_syncs_access_token(self):
        app = _make_app()
        app.state.data["access_token"] = "my-secret-token"
        app._sync_token_from_state()
        assert app.engine.token == "my-secret-token"

    def test_syncs_token_key(self):
        app = _make_app()
        app.state.data["token"] = "another-token"
        app._sync_token_from_state()
        assert app.engine.token == "another-token"

    def test_no_token_in_state(self):
        app = _make_app()
        app._sync_token_from_state()
        assert app.engine.token is None

    def test_precedence_access_token_over_token(self):
        """access_token appears first in TOKEN_KEYS, so it wins."""
        app = _make_app()
        app.state.data["access_token"] = "first"
        app.state.data["token"] = "second"
        app._sync_token_from_state()
        assert app.engine.token == "first"

    def test_startup_init_from_state(self):
        """Engine should be seeded from state at __init__ time when no CLI token."""
        import tempfile, json, os

        # Write state to a temp file so ClientState loads it before sync runs
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"access_token": "state-token"}, f)
            tmp_path = f.name

        try:
            engine = OpenAIEngine("http://localhost:9999")
            engine.load_spec(
                {
                    "paths": {
                        "/items": {
                            "get": {
                                "operationId": "list_items",
                                "parameters": [],
                                "responses": {"200": {}},
                            }
                        }
                    }
                }
            )
            mgr = ConfigManager(None)
            cfg = mgr.config
            cfg.name = "TestShell"
            cfg.state.storage = tmp_path  # point to pre-seeded file

            app = OAIShellApp(cfg, engine)
            assert app.engine.token == "state-token"
        finally:
            os.unlink(tmp_path)

    def test_cli_token_not_overridden(self):
        """When a CLI token is provided, state should NOT override it."""
        app = _make_app(token="cli-token", state_data={"access_token": "state-token"})
        # __init__ does NOT call _sync when engine.token is already set
        assert app.engine.token == "cli-token"


class TestUpdateAuthStatus:
    def test_subtitle_with_token(self):
        app = _make_app()
        app.engine.set_token("sk-abcdefghijklmnopqrstuvwxyz")
        app._update_auth_status()
        assert "🔑" in app.sub_title
        assert "sk-a" in app.sub_title

    def test_subtitle_without_token(self):
        app = _make_app()
        app._update_auth_status()
        assert "🔑" not in app.sub_title
        assert "Connected to" in app.sub_title


# ---------------------------------------------------------------------------
# Integration tests (Textual pilot)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_auth_set_command():
    """/auth set stores token in engine and state, updates subtitle."""
    app = _make_app()

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        input_widget = app.query_one("#command_input", Input)
        input_widget.value = "/auth set supersecrettoken123"
        await pilot.press("enter")
        await pilot.pause(0.2)

        assert app.engine.token == "supersecrettoken123"
        assert app.state.get("access_token") == "supersecrettoken123"
        assert "🔑" in app.sub_title


@pytest.mark.anyio
async def test_auth_clear_command():
    """/auth clear removes token from engine, state, and subtitle."""
    app = _make_app()

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        # Set a token first
        input_widget = app.query_one("#command_input", Input)
        input_widget.value = "/auth set mytoken"
        await pilot.press("enter")
        await pilot.pause(0.2)

        assert app.engine.token == "mytoken"

        # Now clear it
        input_widget.value = "/auth clear"
        await pilot.press("enter")
        await pilot.pause(0.2)

        assert app.engine.token is None
        for key in TOKEN_KEYS:
            assert key not in app.state.data
        assert "🔑" not in app.sub_title


@pytest.mark.anyio
async def test_auth_status_unauthenticated():
    """/auth status reports unauthenticated when no token is set."""
    app = _make_app()
    written = []

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        output_log = app.query_one("#output_log", RichLog)
        original_write = output_log.write
        output_log.write = lambda *a, **kw: written.append(str(a[0])) or original_write(*a, **kw)

        input_widget = app.query_one("#command_input", Input)
        input_widget.value = "/auth status"
        await pilot.press("enter")
        await pilot.pause(0.2)

    assert any("Not authenticated" in w for w in written)


@pytest.mark.anyio
async def test_auth_status_authenticated():
    """/auth status reports masked token when authenticated."""
    app = _make_app()
    written = []

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        # Set token
        app.engine.set_token("abcdefghijklmnop")

        output_log = app.query_one("#output_log", RichLog)
        original_write = output_log.write
        output_log.write = lambda *a, **kw: written.append(str(a[0])) or original_write(*a, **kw)

        input_widget = app.query_one("#command_input", Input)
        input_widget.value = "/auth status"
        await pilot.press("enter")
        await pilot.pause(0.2)

    assert any("Authenticated" in w for w in written)
    assert any("abcd...mnop" in w for w in written)


@pytest.mark.anyio
async def test_state_set_token_key_syncs_engine():
    """/state set access_token <val> must sync the token to the engine."""
    app = _make_app()

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        input_widget = app.query_one("#command_input", Input)
        input_widget.value = "/state set access_token mytoken99"
        await pilot.press("enter")
        await pilot.pause(0.2)

        assert app.engine.token == "mytoken99"
        assert "🔑" in app.sub_title


@pytest.mark.anyio
async def test_after_call_token_sync():
    """After an API call that saves a token key to state, engine is synced."""
    app = _make_app()

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "response-token"}

    from oai_shell.config.models import CommandConfig
    cmd_conf = CommandConfig(
        operationId="list_items",
        after_call={"save_to_state": {"access_token": "json:access_token"}},
    )

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        with patch.object(app.engine, "call", return_value=mock_resp):
            await app._execute_call(
                "list_items", {}, stream=False, debug=False, cmd_conf=cmd_conf
            )

    assert app.state.get("access_token") == "response-token"
    assert app.engine.token == "response-token"
    assert "🔑" in app.sub_title


@pytest.mark.anyio
async def test_autocomplete_includes_auth():
    """Autocomplete must suggest /auth when typing /a."""
    app = _make_app()

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        from textual_autocomplete import TargetState
        state = TargetState("/a", 2)
        items = app._get_autocomplete_items(state)
        mains = [i.main.plain for i in items]
        assert "/auth" in mains


@pytest.mark.anyio
async def test_autocomplete_auth_subcommands():
    """Autocomplete must suggest set/status/clear after '/auth '."""
    app = _make_app()

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        from textual_autocomplete import TargetState
        state = TargetState("/auth ", 6)
        items = app._get_autocomplete_items(state)
        mains = [i.main.plain for i in items]
        assert "set" in mains
        assert "status" in mains
        assert "clear" in mains
