"""CLI for original anonymous AUBI-plus native inventory and public adverts."""
from __future__ import annotations

import argparse
import json
import sys

import aubiplus

from network import SourceError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["inventory", "detail"])
    parser.add_argument("--scope", choices=list(aubiplus.SCOPES))
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--first-page-total", type=int)
    parser.add_argument("--continuation-url")
    parser.add_argument("--url")
    args = parser.parse_args()
    try:
        if args.operation == "inventory":
            if args.url or not args.scope:
                raise SourceError("Only explicit native inventory scope/page/counter/next-URI arguments")
            result = aubiplus.read("inventory", scope=args.scope, page=args.page,
                                   first_page_total=args.first_page_total, continuation_url=args.continuation_url)
        else:
            if args.scope or args.page != 1 or args.first_page_total is not None or args.continuation_url or not args.url:
                raise SourceError("Only exact acquired native advert URI")
            result = aubiplus.read("detail", url=args.url)
    except (SourceError, ValueError, TypeError) as error:
        result = {**aubiplus.base("aubi_plus_read_limit"), "status": "source_limited", "error": str(error),
                  "evidence": getattr(error, "evidence", {}), "returned_count": None, "source_result_count": None}
        print(json.dumps(result, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
