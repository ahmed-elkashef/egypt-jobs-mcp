"""CLI for exact original anonymous state-portal reads, currently Berlin only."""
from __future__ import annotations

import argparse
import json
import sys

import berlin
from network import SourceError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["state_inventory", "state_detail"])
    parser.add_argument("--provider", choices=["berlin"], required=True)
    parser.add_argument("--scope", choices=["all", "student_entry"])
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--first-page-total", type=int)
    parser.add_argument("--url")
    args = parser.parse_args()
    try:
        if args.operation == "state_inventory":
            if args.url or not args.scope:
                raise SourceError("Only native inventory scope/offset/initial-total arguments")
            result = berlin.inventory(args.scope, args.start, first_page_total=args.first_page_total)
        else:
            if args.scope or args.start != 0 or args.first_page_total is not None or not args.url:
                raise SourceError("Only exact acquired public advert URI")
            result = berlin.detail(args.url)
    except (SourceError, ValueError, TypeError) as error:
        result = {**berlin.base("berlin_state_read_limit"), "status": "source_limited",
                  "error": str(error), "evidence": getattr(error, "evidence", {}),
                  "returned_count": None, "source_result_count": None}
        print(json.dumps(result, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
