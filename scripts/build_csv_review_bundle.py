#!/usr/bin/env python3
"""Build only the private CSV slice; never package credentials or install a service."""
import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "server/csv_review.py", "server/csv_checks.py", "server/csv_native.py", "server/csv_context.py",
    "server/review_decisions.py", "server/test_review_decisions.py", "scripts/test_durable_review_browser.py",
    "server/test_csv_review.py", "server/test_csv_checks.py", "server/test_csv_native.py", "server/test_csv_context.py",
    "extension/csv-review.html", "extension/csv-review.css", "extension/csv-review.js",
    "extension/setup.css", "extension/icons/icon128.png", "scripts/test_csv_review_browser.py",
    "scripts/csv_native_acceptance.py", "docs/csv-review.md", "docs/product-development.md", "docs/roadmap.md",
    "scripts/build_csv_review_bundle.py", "scripts/test_csv_bundle.py", "docs/detector-evaluation.md",
    "docs/receipts/csv-review-20261007.md", "docs/receipts/native-schema-20261007.md",
    "docs/receipts/reporting-context-20261007.md",
    "docs/receipts/durable-review-20261008.md",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New ZIP path in an existing private directory; never overwrites.")
    args = parser.parse_args()
    payloads = [(path, (ROOT / path).read_bytes()) for path in FILES]
    with args.output.open("xb") as output, zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path, data in payloads:
            item = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100600 << 16
            bundle.writestr(item, data)
    print(hashlib.sha256(args.output.read_bytes()).hexdigest() + "  " + args.output.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
