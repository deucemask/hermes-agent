"""Gateway /new --toolset tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gateway.config import Platform
from gateway.session import build_session_key
from tests.gateway.test_session_model_reset import _make_event, _make_runner, _make_source


@pytest.mark.asyncio
async def test_new_command_stores_toolset_override_and_uses_parsed_title():
    runner = _make_runner()
    session_key = build_session_key(_make_source())
    runner._session_db = MagicMock()

    reply = await runner._handle_reset_command(
        _make_event("/new --toolset terminal,file Focus")
    )

    runner.session_store.reset_session.assert_called_once_with(session_key)
    assert runner._session_toolset_overrides[session_key] == ["terminal", "file"]
    runner._session_db.set_session_title.assert_called_once()
    assert runner._session_db.set_session_title.call_args.args[1] == "Focus"
    assert "Toolsets: terminal, file" in str(reply)


@pytest.mark.asyncio
async def test_new_command_without_toolset_clears_existing_override():
    runner = _make_runner()
    session_key = build_session_key(_make_source())
    runner._session_toolset_overrides[session_key] = ["file"]

    reply = await runner._handle_reset_command(_make_event("/new Normal"))

    assert session_key not in runner._session_toolset_overrides
    assert "Toolsets: default" in str(reply)


@pytest.mark.asyncio
async def test_invalid_toolset_does_not_reset_or_mutate_override():
    runner = _make_runner()
    session_key = build_session_key(_make_source())
    runner._session_toolset_overrides[session_key] = ["file"]
    runner._invalidate_session_run_generation = MagicMock()
    runner._release_running_agent_state = MagicMock()
    runner._evict_cached_agent = MagicMock()

    reply = await runner._handle_reset_command(_make_event("/new --toolset nope Focus"))

    runner.session_store.reset_session.assert_not_called()
    runner._invalidate_session_run_generation.assert_not_called()
    runner._release_running_agent_state.assert_not_called()
    runner._evict_cached_agent.assert_not_called()
    assert runner._session_toolset_overrides[session_key] == ["file"]
    assert "Unknown toolset(s): nope" in str(reply)


@pytest.mark.asyncio
async def test_parse_error_does_not_reset_or_mutate_override():
    runner = _make_runner()
    session_key = build_session_key(_make_source())
    runner._session_toolset_overrides[session_key] = ["file"]
    runner._invalidate_session_run_generation = MagicMock()

    reply = await runner._handle_reset_command(_make_event("/new --toolset"))

    runner.session_store.reset_session.assert_not_called()
    runner._invalidate_session_run_generation.assert_not_called()
    assert runner._session_toolset_overrides[session_key] == ["file"]
    assert "Invalid /new arguments" in str(reply)


def test_resolve_enabled_toolsets_prefers_session_override():
    runner = _make_runner()
    session_key = build_session_key(_make_source())
    runner._session_toolset_overrides[session_key] = ["terminal", "file"]
    user_config = {
        "platforms": {Platform.TELEGRAM.value: {"tools": ["web"]}},
        "tools": ["web"],
    }

    result = runner._resolve_enabled_toolsets_for_session(
        user_config,
        Platform.TELEGRAM.value,
        session_key,
    )

    assert result == ["file", "terminal"]


def test_clear_session_boundary_overrides_clears_toolset_with_model_state():
    runner = _make_runner()
    session_key = build_session_key(_make_source())
    runner._session_model_overrides[session_key] = {"model": "gpt-4o"}
    runner._session_reasoning_overrides[session_key] = {"enabled": True}
    runner._session_toolset_overrides[session_key] = ["file"]
    runner._pending_model_notes[session_key] = "note"

    runner._clear_session_boundary_overrides(session_key)

    assert session_key not in runner._session_model_overrides
    assert session_key not in runner._session_reasoning_overrides
    assert session_key not in runner._session_toolset_overrides
    assert session_key not in runner._pending_model_notes


@pytest.mark.asyncio
async def test_resume_clears_session_toolset_override():
    runner = _make_runner()
    session_key = build_session_key(_make_source())
    runner._session_toolset_overrides[session_key] = ["file"]
    runner._session_db = MagicMock()
    runner._session_db.find_session_by_name.return_value = "target-session"
    runner._session_db.resolve_resume_session_id.return_value = "target-session"
    runner._session_db.get_session_title.return_value = "Target"
    runner.session_store.switch_session.return_value = runner.session_store.reset_session.return_value
    runner.session_store.load_transcript.return_value = []

    await runner._handle_resume_command(_make_event("/resume Target"))

    assert session_key not in runner._session_toolset_overrides
