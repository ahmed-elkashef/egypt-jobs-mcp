"""Read one inert JSON data object with explicit JavaScript undefined values.

No website code is evaluated. Undefined is retained as unknown (None), and the
conversion count remains explicit. All other non-JSON expressions fail closed.
"""

import json
import re

from lxml import html


class NativeObjectError(ValueError):
    pass


def crate_object(body):
    scripts = html.fromstring(body).xpath('//script[@id="runtime-config"]')
    if len(scripts) != 1:
        raise NativeObjectError("One native runtime data object is required")
    source = scripts[0].text or ""
    match = re.match(r"^\s*window\.crate\s*=\s*", source)
    if not match:
        raise NativeObjectError("Unrecognised native object declaration")
    source = source[match.end() :]
    pieces = []
    index = 0
    quoted = False
    escaped = False
    unknowns = 0
    while index < len(source):
        char = source[index]
        if quoted:
            pieces.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            index += 1
            continue
        if char == '"':
            quoted = True
            pieces.append(char)
            index += 1
            continue
        if (
            source.startswith("undefined", index)
            and (index == 0 or not (source[index - 1].isalnum() or source[index - 1] == "_"))
            and (
                index + 9 == len(source)
                or not (source[index + 9].isalnum() or source[index + 9] == "_")
            )
        ):
            pieces.append("null")
            index += 9
            unknowns += 1
            continue
        pieces.append(char)
        index += 1
    inert = "".join(pieces)

    def reject_constant(_value):
        raise NativeObjectError("Nonfinite native literal refused")

    try:
        result, end = json.JSONDecoder(parse_constant=reject_constant).raw_decode(inert)
    except ValueError as error:
        raise NativeObjectError("Only inert JSON plus undefined is supported") from error
    if not isinstance(result, dict) or inert[end:].strip() not in {"", ";"}:
        raise NativeObjectError("Trailing website expressions or non-object data refused")
    return result, unknowns
