"""Run every adapter on its fixture and print what the extractor will receive.

    python demo.py
"""

from __future__ import annotations

import os

from ingestion import ingest_file, ingest_text

HERE = os.path.dirname(__file__)
FIX = os.path.join(HERE, "fixtures")


def show(doc) -> None:
    print("=" * 78)
    print(f"source_type : {doc.source_type.value}")
    print(f"source_name : {doc.source_name}")
    print(f"meta        : {doc.meta}")
    if doc.warnings:
        print("warnings    :")
        for w in doc.warnings:
            print(f"   - {w}")
    print("-" * 78)
    print(doc.markdown)
    print()


def main() -> None:
    with open(os.path.join(FIX, "paste_two_quotes.txt"), encoding="utf-8") as f:
        show(ingest_text(f.read(), source_name="paste_two_quotes.txt"))

    for name in ("dell_bom.xlsx", "supermicro_quote.pdf", "hpe_bom.csv"):
        path = os.path.join(FIX, name)
        with open(path, "rb") as f:
            show(ingest_file(f.read(), name))


if __name__ == "__main__":
    main()
