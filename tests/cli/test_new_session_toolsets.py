"""Tests for CLI /new --toolset session overrides."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from hermes_state import SessionDB
from tests.cli.test_cli_new_session import _FakeAgent, _make_cli


def test_new_command_parses_toolsets_and_title():
    cli = _make_cli()
    cli._confirm_destructive_slash = lambda *_a, **_kw: "once"
    cli.new_session = MagicMock()

    cli.process_command("/new --toolset terminal,file Focus")

    cli.new_session.assert_called_once_with(
        title="Focus",
        enabled_toolsets_override=["terminal", "file"],
    )


def test_new_command_parse_error_does_not_reset():
    cli = _make_cli()
    cli._confirm_destructive_slash = MagicMock(return_value="once")
    cli.new_session = MagicMock()
    warnings: list[str] = []
    method_globals = cli.process_command.__globals__
    original = method_globals["_cprint"]
    method_globals["_cprint"] = lambda msg: warnings.append(msg)
    try:
        cli.process_command("/new --toolset")
    finally:
        method_globals["_cprint"] = original

    cli._confirm_destructive_slash.assert_not_called()
    cli.new_session.assert_not_called()
    assert any("Invalid /new arguments" in warning for warning in warnings)


def test_new_command_invalid_toolset_does_not_reset():
    cli = _make_cli()
    cli._confirm_destructive_slash = MagicMock(return_value="once")
    cli.new_session = MagicMock()
    warnings: list[str] = []
    method_globals = cli.process_command.__globals__
    original = method_globals["_cprint"]
    method_globals["_cprint"] = lambda msg: warnings.append(msg)
    try:
        cli.process_command("/new --toolset nope Focus")
    finally:
        method_globals["_cprint"] = original

    cli._confirm_destructive_slash.assert_not_called()
    cli.new_session.assert_not_called()
    assert any("Unknown toolset(s): nope" in warning for warning in warnings)


def test_new_session_toolset_override_rebuilds_live_agent_and_keeps_title(tmp_path):
    cli = _make_cli(toolsets=["terminal"])
    cli._session_db = SessionDB(db_path=tmp_path / "state.db")
    cli._session_db.create_session(session_id=cli.session_id, source="cli", model=cli.model)
    old_agent = _FakeAgent(cli.session_id, cli.session_start)
    cli.agent = old_agent
    cli.conversation_history = []
    old_session_id = cli.session_id

    cli.new_session(title="Focused", enabled_toolsets_override=["file"])

    old_agent.close.assert_called_once()
    assert cli.agent is None
    assert cli.enabled_toolsets == ["file"]
    assert cli._session_toolset_override == ["file"]
    assert cli.session_id != old_session_id
    new_session = cli._session_db.get_session(cli.session_id)
    assert new_session is not None
    assert new_session["title"] == "Focused"


def test_new_session_same_toolset_uses_existing_agent_reset_path(tmp_path):
    cli = _make_cli(toolsets=["file"])
    cli._session_db = SessionDB(db_path=tmp_path / "state.db")
    cli._session_db.create_session(session_id=cli.session_id, source="cli", model=cli.model)
    agent = _FakeAgent(cli.session_id, cli.session_start)
    cli.agent = agent
    cli.conversation_history = []

    cli.new_session(enabled_toolsets_override=["file"])

    agent.close.assert_not_called()
    assert cli.agent is agent
    assert agent.session_id == cli.session_id
    assert agent._last_flushed_db_idx == 0


def test_new_session_default_override_restores_constructor_toolsets():
    cli = _make_cli(toolsets=["terminal", "file"])
    cli.agent = _FakeAgent("old_session_id", datetime.now())
    cli.enabled_toolsets = ["web"]
    cli._session_toolset_override = ["web"]

    cli.new_session(enabled_toolsets_override=None)

    assert cli.enabled_toolsets == ["terminal", "file"]
    assert cli._session_toolset_override is None


def test_new_command_without_toolset_clears_previous_override():
    cli = _make_cli(toolsets=["terminal", "file"])
    cli._confirm_destructive_slash = lambda *_a, **_kw: "once"
    cli.new_session = MagicMock()

    cli.process_command("/new Normal")

    cli.new_session.assert_called_once_with(
        title="Normal",
        enabled_toolsets_override=None,
    )


def test_clear_command_restores_default_toolsets(tmp_path):
    cli = _make_cli(toolsets=["terminal", "file"])
    cli._session_db = SessionDB(db_path=tmp_path / "state.db")
    cli._session_db.create_session(session_id=cli.session_id, source="cli", model=cli.model)
    cli.agent = _FakeAgent(cli.session_id, cli.session_start)
    cli.conversation_history = []
    cli.enabled_toolsets = ["web"]
    cli._session_toolset_override = ["web"]
    cli._confirm_destructive_slash = lambda *_a, **_kw: "once"
    cli.console = MagicMock()
    cli.show_banner = MagicMock()

    cli.process_command("/clear")

    assert cli.enabled_toolsets == ["terminal", "file"]
    assert cli._session_toolset_override is None


@patch("hermes_cli.plugins.invoke_hook")
def test_new_session_toolset_rebuild_still_emits_reset_hook(mock_invoke_hook, tmp_path):
    cli = _make_cli(toolsets=["terminal"])
    cli._session_db = SessionDB(db_path=tmp_path / "state.db")
    cli._session_db.create_session(session_id=cli.session_id, source="cli", model=cli.model)
    cli.agent = _FakeAgent(cli.session_id, cli.session_start)
    cli.conversation_history = []

    cli.new_session(silent=True, enabled_toolsets_override=["file"])

    assert cli.agent is None
    assert any(
        call.args == ("on_session_reset",)
        and call.kwargs["session_id"] == cli.session_id
        for call in mock_invoke_hook.call_args_list
    )
