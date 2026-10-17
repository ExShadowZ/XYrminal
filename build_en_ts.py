"""
Generate i18n/xyrminal_en.ts from the T dictionary in tools_translate_ts.py.

Use this INSTEAD of `pyside6-lupdate` when lupdate cannot parse the
project's Python sources (e.g. on very new Python versions).

Usage:
    python build_en_ts.py
    python tools_translate_ts.py
    (then compile .qm files)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
I18N_DIR     = PROJECT_ROOT / "i18n"
OUT_PATH     = I18N_DIR / "xyrminal_en.ts"


def main() -> None:
    # import T from the existing translator script
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from tools_translate_ts import T

    I18N_DIR.mkdir(parents=True, exist_ok=True)

    root = ET.Element("TS", version="2.1", language="en_US")

    # group by context
    ctx = ET.SubElement(root, "context")
    ET.SubElement(ctx, "name").text = "XYrminal"

    count = 0
    for src in T.keys():
        msg = ET.SubElement(ctx, "message")
        src_el = ET.SubElement(msg, "source")
        src_el.text = src
        tr_el = ET.SubElement(msg, "translation")
        tr_el.text = src   # English = source
        count += 1

    body = ET.tostring(root, encoding="unicode")
    with OUT_PATH.open("w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write('<!DOCTYPE TS>\n')
        f.write(body)
        f.write("\n")

    print(f"{OUT_PATH.name}: {count} sources written")


if __name__ == "__main__":
    main()