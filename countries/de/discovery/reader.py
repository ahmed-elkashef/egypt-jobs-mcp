"""CLI for exact German student-market and organisation-directory reads."""

from __future__ import annotations

import argparse
import json
import sys

import handwerk
import meinpraktikum
import organisations
from network import SourceError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["mein_inventory", "mein_detail", "organisation_directory", "hand_inventory", "hand_detail"])
    parser.add_argument("--scope", choices=["internships", "working_student", "apprenticeships"])
    parser.add_argument("--postal-code")
    parser.add_argument("--radius-km", type=int, default=25)
    parser.add_argument("--first-native-pages", type=int)
    parser.add_argument("--url")
    parser.add_argument("--directory", choices=["higher_education", "staffing_members"])
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--personal-noncommercial-use", action="store_true")
    args = parser.parse_args()
    try:
        if args.operation == "hand_inventory":
            if args.url or args.directory:
                raise SourceError("Only native Handwerk scope/postcode/radius/page arguments are supported")
            result = handwerk.inventory(args.scope, args.postal_code, args.radius_km, args.page,
                                        first_native_pages=args.first_native_pages,
                                        personal_noncommercial_use=args.personal_noncommercial_use)
        elif args.operation == "hand_detail":
            if args.scope or args.directory or args.postal_code or args.radius_km != 25 or args.first_native_pages is not None or args.page != 1 or not args.url:
                raise SourceError("Only an exact standalone chamber primary URI is supported")
            result = handwerk.detail(args.url, personal_noncommercial_use=args.personal_noncommercial_use)
        elif args.postal_code or args.radius_km != 25 or args.first_native_pages is not None:
            raise SourceError("Geographic Handwerk arguments cannot alter another reader")
        elif args.operation == "mein_inventory":
            if args.url or args.directory or not args.scope:
                raise SourceError("Only exact scope/page/personal-use inventory arguments are supported")
            result = meinpraktikum.inventory(args.scope, args.page, personal_noncommercial_use=args.personal_noncommercial_use)
        elif args.operation == "mein_detail":
            if args.scope or args.directory or args.page != 1 or not args.url:
                raise SourceError("Only exact public advert URL/personal-use detail arguments are supported")
            result = meinpraktikum.detail(args.url, personal_noncommercial_use=args.personal_noncommercial_use)
        else:
            if args.url or args.scope or not args.directory:
                raise SourceError("Only exact directory/page/personal-use arguments are supported")
            result = organisations.directory(args.directory, args.page, personal_noncommercial_use=args.personal_noncommercial_use)
    except (SourceError, ValueError, TypeError) as error:
        result = {
            "status": "source_limited", "source": "handwerk" if args.operation.startswith("hand_") else {"higher_education": "hochschulkompass", "staffing_members": "gvp_staffing"}.get(args.directory, "meinpraktikum"),
            "error": str(error), "evidence": getattr(error, "evidence", {}),
            "returned_count": None, "source_result_count": None,
            "coverage_complete": False, "full_posting_reviewed": False, "reviewed_by_model": False,
        }
        print(json.dumps(result, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
