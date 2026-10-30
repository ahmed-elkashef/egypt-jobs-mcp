"""Fixed read-only CLI for the public Ausbildung.de internship scope."""
import argparse
import json
import sys

import ausbildung
from public_http import load_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["inventory", "detail"])
    parser.add_argument("--from", dest="offset", type=int, default=0)
    parser.add_argument("--native-binding")
    parser.add_argument("--url")
    args = parser.parse_args()
    client = ausbildung.Client()
    try:
        binding = None
        if args.native_binding is not None:
            binding = load_json(args.native_binding.encode("utf-8"))
            if not isinstance(binding, dict):
                raise ausbildung.SourceError("native_binding_must_be_an_object")
        if ((args.operation == "detail" and (args.offset != 0 or binding is not None))
                or (args.operation == "inventory" and args.url is not None)):
            raise ausbildung.SourceError("unqualified_operation_arguments")
        result = ausbildung.read(args.operation, offset=args.offset, binding=binding, url=args.url, client=client)
    except (ValueError, TypeError, RecursionError) as error:
        result = {**ausbildung.base("native_read_limit"), "status": "source_limited", "error": str(error),
                  "HTTP_status": getattr(error, "http_status", None), "retry_after": getattr(error, "retry_after", None),
                  "source_policy": client.policy, "native_HTTP_request_attempts": client.request_attempts,
                  "source_result_count": None, "returned_count": None}
        print(json.dumps(result, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
