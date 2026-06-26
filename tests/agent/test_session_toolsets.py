from agent.session_toolsets import parse_new_session_args


def test_parse_title_only():
    result = parse_new_session_args("Debug auth", valid_toolsets={"terminal", "file"})

    assert result.title == "Debug auth"
    assert result.toolsets is None
    assert result.explicit_toolset is False
    assert result.invalid_toolsets == []
    assert result.parse_error is None


def test_parse_comma_toolsets_and_title():
    result = parse_new_session_args(
        "--toolset terminal,file Debug auth",
        valid_toolsets={"terminal", "file"},
    )

    assert result.toolsets == ["terminal", "file"]
    assert result.title == "Debug auth"
    assert result.explicit_toolset is True


def test_parse_repeated_toolset_flags():
    result = parse_new_session_args(
        "--toolset terminal --toolset file",
        valid_toolsets={"terminal", "file"},
    )

    assert result.toolsets == ["terminal", "file"]


def test_parse_equals_form():
    result = parse_new_session_args(
        "--toolsets=terminal,file Focus",
        valid_toolsets={"terminal", "file"},
    )

    assert result.toolsets == ["terminal", "file"]
    assert result.title == "Focus"


def test_parse_all_normalizes_to_default():
    result = parse_new_session_args(
        "--toolset all General",
        valid_toolsets={"terminal", "file"},
    )

    assert result.toolsets is None
    assert result.explicit_toolset is True
    assert result.title == "General"


def test_parse_star_normalizes_to_default():
    result = parse_new_session_args(
        "--toolset '*' General",
        valid_toolsets={"terminal", "file"},
    )

    assert result.toolsets is None
    assert result.explicit_toolset is True
    assert result.title == "General"


def test_invalid_toolset_reported_without_losing_title():
    result = parse_new_session_args("--toolset nope Debug", valid_toolsets={"terminal"})

    assert result.invalid_toolsets == ["nope"]
    assert result.title == "Debug"


def test_missing_toolset_value_returns_parse_error():
    result = parse_new_session_args("--toolset", valid_toolsets={"terminal"})

    assert result.parse_error
    assert result.toolsets is None


def test_empty_toolset_value_returns_parse_error():
    result = parse_new_session_args("--toolset ,,, Focus", valid_toolsets={"terminal"})

    assert result.parse_error
    assert result.title == "Focus"
    assert result.toolsets is None


def test_all_cannot_be_combined_with_specific_toolsets():
    result = parse_new_session_args("--toolset all,file Focus", valid_toolsets={"file"})

    assert result.parse_error
    assert result.toolsets is None


def test_configured_mcp_name_is_accepted_when_caller_supplies_it():
    result = parse_new_session_args(
        "--toolset local-mcp Focus",
        valid_toolsets={"terminal", "local-mcp"},
    )

    assert result.toolsets == ["local-mcp"]
    assert result.title == "Focus"


def test_parse_quoted_title_with_toolsets():
    result = parse_new_session_args('--toolset file "Bug bash"', valid_toolsets={"file"})

    assert result.toolsets == ["file"]
    assert result.title == "Bug bash"


def test_unknown_flags_stay_in_title_text():
    result = parse_new_session_args("--weird flag Title", valid_toolsets={"terminal"})

    assert result.toolsets is None
    assert result.title == "--weird flag Title"


def test_deduplicates_toolsets_preserving_order():
    result = parse_new_session_args(
        "--toolset terminal,file --toolset terminal Focus",
        valid_toolsets={"terminal", "file"},
    )

    assert result.toolsets == ["terminal", "file"]
    assert result.title == "Focus"


def test_shlex_error_returns_parse_error():
    result = parse_new_session_args('--toolset file "Bug bash', valid_toolsets={"file"})

    assert result.parse_error
    assert result.toolsets is None
