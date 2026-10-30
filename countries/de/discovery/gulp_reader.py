"""CLI for fixed anonymous GULP job search and complete public job details."""
import argparse
import json
import sys

import gulp_jobs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["inventory", "detail"])
    parser.add_argument("--page", type=int, default=0)
    parser.add_argument("--first-page-total", type=int)
    parser.add_argument("--url")
    args = parser.parse_args()
    client = gulp_jobs.Client()
    try:
        result = gulp_jobs.read(args.operation, page=args.page, first_page_total=args.first_page_total, url=args.url, client=client)
    except (gulp_jobs.SourceError, ValueError, TypeError) as error:
        result = {**gulp_jobs.base("gulp_read_limit"), "status": "source_limited", "error": str(error),
                  "HTTP_status": getattr(error, "http_status", None), "retry_after": getattr(error, "retry_after", None),
                  "native_HTTP_request_attempts": client.request_attempts, "source_policy": client.policy,
                  "returned_count": None, "source_result_count": None}
        print(json.dumps(result, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
