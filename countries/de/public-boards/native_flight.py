"""Read native public React Flight JSON as data; never execute website scripts."""

from __future__ import annotations

import json
import re
from typing import Any

from lxml import html


class FlightError(ValueError):
    pass


def records_from_html(body: bytes) -> dict[str, Any]:
    tree = html.fromstring(body)
    chunks = []
    decoder = json.JSONDecoder()
    for script in tree.xpath("//script"):
        text = script.text or ""
        # Each argument must be JSON. No JS evaluator, dynamic import or DOM execution.
        for match in re.finditer(r"self\.__next_f\.push\(", text):
            try:
                value, _ = decoder.raw_decode(text, match.end())
            except ValueError:
                continue
            if (
                isinstance(value, list)
                and len(value) > 1
                and value[0] == 1
                and isinstance(value[1], str)
            ):
                chunks.append(value[1])
    stream = "".join(chunks).encode("utf-8")
    records = {}
    position = 0
    while position < len(stream):
        if stream[position : position + 1] == b"\n":
            position += 1
            continue
        colon = stream.find(b":", position)
        if colon == position and stream[position + 1 : position + 2] == b"H":
            end = stream.find(b"\n", position)
            position = len(stream) if end == -1 else end + 1
            continue
        if colon == -1 or not re.fullmatch(rb"[0-9a-f]+", stream[position:colon]):
            raise FlightError("Native Flight record boundary is invalid")
        identity = stream[position:colon].decode("ascii")
        position = colon + 1
        if stream[position : position + 1] == b"T":
            comma = stream.find(b",", position)
            if comma == -1 or not re.fullmatch(rb"[0-9a-f]+", stream[position + 1 : comma]):
                raise FlightError("Native text record length is invalid")
            size = int(stream[position + 1 : comma], 16)
            position = comma + 1
            if position + size > len(stream):
                raise FlightError("Native text record is truncated")
            value = stream[position : position + size].decode("utf-8")
            position += size
        else:
            end = stream.find(b"\n", position)
            end = len(stream) if end == -1 else end
            payload = stream[position:end].decode("utf-8")
            position = end + 1
            try:
                value = json.loads(payload)
            except ValueError:
                # Module/import/debug protocol records are not executed or treated as job data.
                continue
        if identity in records and records[identity] != value:
            raise FlightError("Conflicting native Flight record identity")
        records[identity] = value
    if not records:
        raise FlightError("No native JSON Flight records")
    return records


def resolve(
    value: Any, records: dict[str, Any], seen: frozenset[str] = frozenset(), depth: int = 0
) -> Any:
    if depth > 80:
        raise FlightError("Native references exceed the depth bound")
    if isinstance(value, str):
        if value == "$undefined":
            return None
        match = re.fullmatch(r"\$([0-9a-f]+)((?::[^:]+)*)", value)
        if not match or value in seen:
            return value
        if match[1] not in records:
            return value
        current = records[match[1]]
        for key in match[2].split(":")[1:]:
            if isinstance(current, str) and current.startswith("$"):
                current = resolve(current, records, seen | {value}, depth + 1)
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif (
                isinstance(current, list)
                and key == "props"
                and len(current) == 4
                and current[0] == "$"
            ):
                current = current[3]
            elif isinstance(current, list) and key.isdecimal() and int(key) < len(current):
                current = current[int(key)]
            else:
                return value
        return resolve(current, records, seen | {value}, depth + 1)
    if isinstance(value, dict):
        return {key: resolve(item, records, seen, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, records, seen, depth + 1) for item in value]
    return value


def find_property(value: Any, key: str):
    if isinstance(value, dict):
        if key in value:
            yield value[key]
        for item in value.values():
            yield from find_property(item, key)
    elif isinstance(value, list):
        for item in value:
            yield from find_property(item, key)


def public_search_state(body: bytes) -> dict[str, Any]:
    records = records_from_html(body)
    states = []
    for record in records.values():
        for state in find_property(record, "preloadedState"):
            resolved = resolve(state, records)
            if isinstance(resolved, dict) and isinstance(resolved.get("api"), dict):
                states.append(resolved)
    unique = {json.dumps(state, sort_keys=True, ensure_ascii=False): state for state in states}
    if len(unique) != 1:
        raise FlightError("One unambiguous native public search state is required")
    state = next(iter(unique.values()))
    # Never expose userTracking, arbitrary account state or the complete bootstrap.
    return {
        key: state[key]
        for key in ["searchQuery", "currentPageParams", "searchPage", "api"]
        if key in state
    }
