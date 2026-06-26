"""Helpers for parsing session-boundary command arguments."""

from __future__ import annotations

from dataclasses import dataclass
import shlex
from typing import Iterable

_DEFAULT_TOOLSET_ALIASES = {"all", "*"}


@dataclass(frozen=True)
class NewSessionArgs:
    title: str | None
    toolsets: list[str] | None
    explicit_toolset: bool
    invalid_toolsets: list[str]
    parse_error: str | None = None


def parse_new_session_args(raw_args: str, *, valid_toolsets: Iterable[str]) -> NewSessionArgs:
    """Parse `/new` command args into an optional title and toolset override.

    The parser intentionally only treats --toolset/--toolsets as special.
    Other option-looking tokens are preserved as title text for backwards
    compatibility with existing `/new [title]` behavior.
    """

    raw_args = raw_args or ""
    try:
        tokens = shlex.split(raw_args)
    except ValueError as exc:
        return NewSessionArgs(
            title=None,
            toolsets=None,
            explicit_toolset=False,
            invalid_toolsets=[],
            parse_error=str(exc),
        )

    valid = {str(toolset) for toolset in valid_toolsets}
    title_parts: list[str] = []
    requested_toolsets: list[str] = []
    explicit_toolset = False
    parse_error: str | None = None

    index = 0
    while index < len(tokens):
        token = tokens[index]

        if token in {"--toolset", "--toolsets"}:
            explicit_toolset = True
            if index + 1 >= len(tokens):
                parse_error = f"{token} requires a value"
                break
            value = tokens[index + 1]
            parsed_values = _split_toolset_value(value)
            if not parsed_values:
                parse_error = f"{token} requires at least one toolset"
            requested_toolsets.extend(parsed_values)
            index += 2
            continue

        if token.startswith("--toolset=") or token.startswith("--toolsets="):
            explicit_toolset = True
            option, value = token.split("=", 1)
            parsed_values = _split_toolset_value(value)
            if not parsed_values:
                parse_error = f"{option} requires at least one toolset"
            requested_toolsets.extend(parsed_values)
            index += 1
            continue

        title_parts.append(token)
        index += 1

    title = " ".join(title_parts).strip() or None
    deduped_toolsets = _dedupe_preserving_order(requested_toolsets)
    default_aliases = [name for name in deduped_toolsets if name in _DEFAULT_TOOLSET_ALIASES]
    concrete_toolsets = [name for name in deduped_toolsets if name not in _DEFAULT_TOOLSET_ALIASES]

    if default_aliases and concrete_toolsets:
        parse_error = "--toolset all cannot be combined with other toolsets"

    invalid_toolsets = [name for name in concrete_toolsets if name not in valid]

    if parse_error:
        return NewSessionArgs(
            title=title,
            toolsets=None,
            explicit_toolset=explicit_toolset,
            invalid_toolsets=invalid_toolsets,
            parse_error=parse_error,
        )

    toolsets: list[str] | None
    if default_aliases or not explicit_toolset:
        toolsets = None
    else:
        toolsets = concrete_toolsets
        if not toolsets:
            return NewSessionArgs(
                title=title,
                toolsets=None,
                explicit_toolset=explicit_toolset,
                invalid_toolsets=invalid_toolsets,
                parse_error="--toolset requires at least one toolset",
            )

    return NewSessionArgs(
        title=title,
        toolsets=toolsets,
        explicit_toolset=explicit_toolset,
        invalid_toolsets=invalid_toolsets,
        parse_error=None,
    )


def _split_toolset_value(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _dedupe_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
