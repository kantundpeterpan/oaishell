"""Tests for async response behaviour in the Textual TUI.

Verifies that:
- The input widget is disabled while a request is in flight.
- The elapsed time is shown in the response panel title.
- The input widget is re-enabled after a successful response.
- The input widget is re-enabled even when the API call raises an error.
"""
import asyncio
import sys
import os
import threading

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import MagicMock, patch
from textual.widgets import Input, RichLog

from oai_shell.config.manager import ConfigManager
from oai_shell.engine.client import OpenAIEngine, EngineError
from oai_shell.shell.textual_app import OAIShellApp


def _make_app():
    """Build a minimal OAIShellApp wired to a stub engine."""
    engine = OpenAIEngine("http://localhost:9999")
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

    return OAIShellApp(cfg, engine)


@pytest.mark.anyio
async def test_input_disabled_during_request_and_reenabled():
    """Input must be disabled while the request runs and re-enabled after."""
    app = _make_app()

    # Gate that lets us pause the background thread mid-request
    proceed = threading.Event()
    disabled_states: list[bool] = []

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": []}

    def blocking_call(*args, **kwargs):
        """A slow synchronous call that signals when it has started."""
        disabled_states.append(True)  # mark: we're inside the thread
        proceed.wait(timeout=5)       # wait until the test tells us to finish
        return mock_resp

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        input_widget = app.query_one("#command_input", Input)

        with patch.object(app.engine, "call", side_effect=blocking_call):
            task = asyncio.create_task(
                app._execute_call("list_items", {}, stream=False, debug=False)
            )

            # Wait until the background thread is actually running
            await asyncio.to_thread(lambda: None)  # flush the thread pool queue
            await pilot.pause(0.1)

            assert input_widget.disabled, "Input should be disabled while waiting"

            # Unblock the background thread so the task can complete
            proceed.set()
            await task

        assert not input_widget.disabled, "Input should be re-enabled after response"


@pytest.mark.anyio
async def test_input_reenabled_after_error():
    """Input must be re-enabled even when the API call raises an EngineError."""
    app = _make_app()

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        input_widget = app.query_one("#command_input", Input)

        with patch.object(app.engine, "call", side_effect=EngineError("timeout")):
            await app._execute_call("list_items", {}, stream=False, debug=False)

        assert not input_widget.disabled, "Input should be re-enabled after error"


@pytest.mark.anyio
async def test_elapsed_time_shown_in_response():
    """Response panel title must include the elapsed time."""
    app = _make_app()

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"hello": "world"}

    written: list = []

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        output_log = app.query_one("#output_log", RichLog)
        original_write = output_log.write
        output_log.write = lambda *a, **kw: written.append(a[0]) or original_write(*a, **kw)

        with patch.object(app.engine, "call", return_value=mock_resp):
            await app._execute_call("list_items", {}, stream=False, debug=False)

    # The Panel title should contain elapsed time like "0.01s)"
    # The Panel is a Rich renderable – inspect its title attribute
    from rich.panel import Panel
    panels = [item for item in written if isinstance(item, Panel)]
    assert panels, "At least one Panel should have been written to the log"
    panel_titles = " ".join(str(p.title) for p in panels)
    assert "s)" in panel_titles, (
        f"Elapsed time (e.g. '0.01s)') should appear in Panel titles. Got: {panel_titles!r}"
    )

