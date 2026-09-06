#!/usr/bin/env python3
"""Reformat keymap layer bindings into rows matching the shield's physical layout.

Keymap viewers that infer rows from newlines (and the split gap from column
spacing) render a flattened one-line layer as a single row.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYMAP = ROOT / "config/toucan.keymap"
DTSI = ROOT / "boards/shields/toucan/toucan.dtsi"

INDENT = " " * 16
CLOSE_INDENT = " " * 12
SEP = 2


def physical_slots():
    attrs = re.findall(
        r"&key_physical_attrs\s+\d+\s+\d+\s+(-?\d+)\s+(-?\d+)", DTSI.read_text()
    )
    slots = [(int(y) // 100, int(x) // 100) for x, y in attrs]
    if len(set(slots)) != len(slots):
        sys.exit("physical layout: two keys share a row/column slot")
    return slots


def split_bindings(text):
    out = []
    for token in text.split():
        if token.startswith("&"):
            out.append([token])
        elif out:
            out[-1].append(token)
        else:
            sys.exit("bindings do not start with '&'")
    return [" ".join(parts) for parts in out]


def render(bindings, slots):
    grid = {}
    for binding, slot in zip(bindings, slots):
        grid[slot] = binding
    rows = sorted({r for r, _ in slots})
    cols = sorted({c for _, c in slots})
    width = {c: max((len(grid[(r, c)]) for r in rows if (r, c) in grid), default=0) for c in cols}

    lines = []
    for r in rows:
        line = ""
        for c in cols:
            cell = grid.get((r, c), "")
            line += cell.ljust(width[c]) + " " * SEP
        lines.append(INDENT + line.rstrip())
    return "bindings = <\n" + "\n".join(lines) + "\n" + CLOSE_INDENT + ">;"


def main():
    check = "--check" in sys.argv
    slots = physical_slots()
    src = KEYMAP.read_text()

    def sub(match):
        bindings = split_bindings(match.group(1))
        if len(bindings) != len(slots):
            sys.exit(
                f"layer has {len(bindings)} bindings, physical layout has {len(slots)}"
            )
        return render(bindings, slots)

    out = re.sub(r"bindings = <\n\s*(&.*?)\n\s*>;", sub, src, flags=re.S)

    if "".join(out.split()) != "".join(src.split()):
        sys.exit("formatter changed more than whitespace; aborting")

    if out == src:
        return 0
    if check:
        print(f"{KEYMAP.relative_to(ROOT)} is not formatted; run scripts/format_keymap.py")
        return 1
    KEYMAP.write_text(out)
    print(f"formatted {KEYMAP.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
