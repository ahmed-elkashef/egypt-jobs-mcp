"""Read the qualified SAP site's inline and cached Flight data without execution.

Record lengths and stream boundaries follow the public React 19.2 protocol.
The SAP cache's observed single '#' frame prefix is accepted only here.
No website code, module, HTML callback or binary value is executed.
"""
from __future__ import annotations

import json
import re

from lxml import html

MAX_BYTES = 8 * 1024 * 1024
BINARY_TAGS = set(b"AOoUSsLlGgMmV")


class SapFlightError(ValueError):
    pass


def strict_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise SapFlightError("duplicate_native_json_key")
            result[key] = item
        return result

    def nonfinite(_):
        raise SapFlightError("nonfinite_native_json")

    return json.loads(value, object_pairs_hook=pairs, parse_constant=nonfinite)


def inline_stream(body):
    if not isinstance(body, bytes) or len(body) > MAX_BYTES:
        raise SapFlightError("incomplete_native_html")
    tree = html.fromstring(body)
    parts = []
    decoder = json.JSONDecoder()
    for script in tree.xpath("//script[not(@src)]"):
        text = (script.text or "").strip()
        # Only a complete native push statement is data. Quoted strings in
        # arbitrary website code are never searched or evaluated.
        prefix = "self.__next_f.push("
        if not text.startswith(prefix):
            continue
        try:
            value, end = decoder.raw_decode(text, len(prefix))
        except ValueError:
            raise SapFlightError("invalid_native_inline_push") from None
        if text[end:] not in {")", ");"} or not isinstance(value, list) or not value:
            raise SapFlightError("invalid_native_push_boundary")
        if value[0] == 1:
            if len(value) != 2 or not isinstance(value[1], str):
                raise SapFlightError("invalid_native_text_chunk")
            parts.append(value[1])
        elif value[0] not in {0, 2}:
            raise SapFlightError("unsupported_native_inline_channel")
    try:
        stream = "".join(parts).encode("utf-8")
    except UnicodeError:
        raise SapFlightError("invalid_native_stream_encoding") from None
    if not stream or len(stream) > MAX_BYTES:
        raise SapFlightError("incomplete_native_inline_stream")
    return stream


def frame_records(stream):
    """Keep each record namespace separate; repeated explicit stream chunks are valid."""
    position = 0
    records, active, nested = {}, {}, []
    while position < len(stream):
        if stream[position:position + 1] == b"\n":
            position += 1
            continue
        colon = stream.find(b":", position)
        if colon == position and stream[position + 1:position + 2] == b"H":
            end = stream.find(b"\n", position)
            if end == -1:
                raise SapFlightError("truncated_native_hint")
            position = end + 1
            continue
        if colon == -1 or not re.fullmatch(rb"[0-9a-f]+", stream[position:colon]):
            raise SapFlightError("invalid_native_record_boundary")
        identity, position = stream[position:colon].decode("ascii"), colon + 1
        tag = stream[position:position + 1]
        if tag == b"T" or tag and tag[0] in BINARY_TAGS:
            comma = stream.find(b",", position)
            if comma == -1 or not re.fullmatch(rb"[0-9a-f]+", stream[position + 1:comma]):
                raise SapFlightError("invalid_native_byte_length")
            size, position = int(stream[position + 1:comma], 16), comma + 1
            if size > MAX_BYTES or position + size > len(stream):
                raise SapFlightError("truncated_native_length_record")
            raw, position = stream[position:position + size], position + size
            if tag == b"T":
                value = raw.decode("utf-8")
            elif identity in active:
                if active[identity]["kind"] not in {"r", "R"} or tag != b"o" or active[identity]["models"]:
                    raise SapFlightError("unsupported_native_stream_value")
                active[identity]["bytes"].extend(raw)
                continue
            else:
                # Arbitrary typed-array values are not job models or nested
                # source frames. Their exact bytes remain in the HTTP receipt.
                value = {"native_binary_tag": tag.decode("ascii"), "bytes": len(raw)}
        else:
            end = stream.find(b"\n", position)
            if end == -1:
                raise SapFlightError("truncated_native_line_record")
            payload, position = stream[position:end].decode("utf-8"), end + 1
            if payload in {"R", "r", "X", "x"}:
                if identity in active or identity in records:
                    raise SapFlightError("conflicting_native_stream_start")
                active[identity] = {"kind": payload, "bytes": bytearray(), "models": []}
                continue
            if payload == "C":
                if identity not in active:
                    raise SapFlightError("unexpected_native_stream_close")
                current = active.pop(identity)
                if current["bytes"] or current["kind"] == "r":
                    nested.append(bytes(current["bytes"]))
                elif current["bytes"]:
                    raise SapFlightError("unexpected_native_binary_models")
                else:
                    records[identity] = current["models"]
                continue
            if payload[:1] in {"I", "H", "D", "N", "W", "J"}:
                # Import/debug/hint records are data boundaries, never code.
                continue
            try:
                value = strict_json(payload)
            except json.JSONDecodeError:
                raise SapFlightError("unsupported_native_model_record") from None
        if identity in active:
            if active[identity]["kind"] == "r" or active[identity]["bytes"]:
                raise SapFlightError("unexpected_native_byte_stream_model")
            active[identity]["models"].append(value)
        else:
            if identity in records and records[identity] != value:
                raise SapFlightError("conflicting_native_json_record")
            records[identity] = value
    if active:
        raise SapFlightError("unfinished_native_stream")
    return records, nested


def data_frames(body):
    queue, frames, total = [(inline_stream(body), 0)], [], 0
    while queue:
        stream, depth = queue.pop(0)
        total += len(stream)
        if depth > 3 or total > 4 * MAX_BYTES or len(frames) >= 16:
            raise SapFlightError("native_frame_bound_exceeded")
        prefix = stream.startswith(b"#")
        records, nested = frame_records(stream[1:] if prefix else stream)
        frames.append({"records": records, "depth": depth, "native_cache_prefix": "#" if prefix else None})
        queue.extend((item, depth + 1) for item in nested if item)
    return frames
