"""Read-only CLI for original native ROR release and directory contracts."""
import argparse
import json
import sys

import ror
from ror import SourceError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["release", "directory"])
    parser.add_argument("--record-id")
    parser.add_argument("--country", choices=sorted(ror.COUNTRIES))
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--snapshot-sha256")
    args = parser.parse_args()
    try:
        if args.operation == "release":
            if args.country or args.offset != 0 or args.limit != 200 or args.snapshot_sha256:
                raise SourceError("only_exact_release_metadata_or_concept_resolution_arguments")
            result = ror.release(args.record_id)
        else:
            result = ror.directory(args.record_id, args.country, args.offset, args.limit, args.snapshot_sha256)
    except (SourceError, ValueError, TypeError, OSError) as error:
        result = {**ror.base("ror_read_limit"), "status": "source_limited", "organization_count": None,
                  "error": getattr(error, "code", "native_ROR_contract_or_cache_unavailable"),
                  "HTTP_status": getattr(error, "http_status", None), "retry_after": getattr(error, "retry_after", None)}
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
