"""Synthetic native protocol regressions; no real bootstrap or applicant fixture."""

import importlib
import json
import sys
from pathlib import Path
from unittest import TestCase

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
f = importlib.import_module("native_flight")


def document(stream, split=False):
    values = [stream[: len(stream) // 2], stream[len(stream) // 2 :]] if split else [stream]
    return (
        "<html>"
        + "".join(
            "<script>self.__next_f.push("
            + json.dumps([1, v]).replace("<", r"\u003c")
            + ");</script>"
            for v in values
        )
        + "</html>"
    ).encode()


class NativeFlightTests(TestCase):
    def test_fragmented_json_and_idless_resource_hint_do_not_lose_records(self):
        stream = ':HL["/static/synthetic.css"]\n1:{"answer":42}\n'
        self.assertEqual(f.records_from_html(document(stream, True)), {"1": {"answer": 42}})

    def test_native_utf8_text_record_is_complete_and_never_executed(self):
        text = "Überprüfung\n<script>never_execute()</script>"
        stream = "2:T" + format(len(text.encode()), "x") + "," + text + '1:{"description":"$2"}\n'
        records = f.records_from_html(document(stream, True))
        self.assertEqual(f.resolve(records["1"], records)["description"], text)

    def test_react_element_props_reference_retains_native_identity(self):
        records = {
            "1": [
                "$",
                "component",
                None,
                {
                    "preloadedState": {
                        "selected": {"id": "NATIVE-2"},
                        "jobs": [{"job": "$1:props:preloadedState:selected"}],
                    }
                },
            ]
        }
        result = f.resolve(records["1"][3]["preloadedState"], records)
        self.assertEqual(result["jobs"][0]["job"]["id"], "NATIVE-2")

    def test_unknown_cyclic_and_undefined_references_are_not_invented(self):
        records = {"1": {"self": "$1:self"}}
        self.assertEqual(f.resolve("$1:self", records), "$1:self")
        self.assertEqual(f.resolve("$abc:missing", records), "$abc:missing")
        self.assertIsNone(f.resolve("$undefined", records))

    def test_malformed_boundary_truncated_native_text_and_conflicts_refused(self):
        for stream in ["bad-boundary", "1:T10,short", '1:{"id":1}\n1:{"id":2}\n']:
            with self.assertRaises(ValueError):
                f.records_from_html(document(stream))

    def test_search_bootstrap_filters_unrelated_tracking_state(self):
        state = {
            "preloadedState": {
                "api": {"queries": {}},
                "searchQuery": {"query": {"page": 2}},
                "userTracking": {"unrelated": "must not be returned"},
            }
        }
        result = f.public_search_state(document("1:" + json.dumps(state) + "\n"))
        self.assertEqual(result["searchQuery"]["query"]["page"], 2)
        self.assertNotIn("userTracking", result)

    def test_no_bootstrap_is_never_an_empty_market(self):
        with self.assertRaises(ValueError):
            f.public_search_state(b"<html>Security check</html>")

    def test_multiple_different_search_states_refuse_ambiguous_source(self):
        stream = (
            "1:"
            + json.dumps({"preloadedState": {"api": {"queries": {}}, "searchQuery": {"page": 1}}})
            + "\n2:"
            + json.dumps({"preloadedState": {"api": {"queries": {}}, "searchQuery": {"page": 2}}})
            + "\n"
        )
        with self.assertRaisesRegex(ValueError, "unambiguous"):
            f.public_search_state(document(stream))
