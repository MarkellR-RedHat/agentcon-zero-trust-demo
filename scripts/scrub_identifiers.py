#!/usr/bin/env python3
"""Replace the laptop's identifiers in a results package with fixed placeholders, and log every replacement.

    python scripts/scrub_identifiers.py runs/qwen-r2 --home "$HOME" --user "$(oc whoami)" --project "$NS"

Text files only (.txt, .log, .md, .json, .yaml, .yml). Each exact string given is replaced everywhere it
appears: the home directory becomes /Users/USER (or /home/USER), the user name becomes USER, the project
becomes PROJECT. Nothing else in any file changes. The script writes <runs_dir>/SCRUB-LOG.txt listing each
file and how many replacements it received, so the edit is on the record. Run files under the lane
folders are never touched: they carry no identifiers by construction, and a run file must never be edited.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TEXT = {".txt", ".log", ".md", ".json", ".yaml", ".yml"}
LANES = ("bare-none", "guarded-blunt", "guarded-scoped")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("runs_dir")
    p.add_argument("--home", default="", help="the laptop home directory, e.g. $HOME")
    p.add_argument("--user", default="", help="the login name, e.g. $(oc whoami) or $(whoami)")
    p.add_argument("--project", default="", help="the OpenShift project, e.g. $NS")
    args = p.parse_args()
    root = Path(args.runs_dir)

    pairs: list[tuple[str, str]] = []
    if args.home:
        home = args.home.rstrip("/")
        placeholder = "/Users/USER" if home.startswith("/Users/") else "/home/USER"
        pairs.append((home, placeholder))
    if args.project:
        pairs.append((args.project, "PROJECT"))
    if args.user:
        pairs.append((args.user, "USER"))
    pairs = [(a, b) for a, b in pairs if a and len(a) >= 3]
    if not pairs:
        print("nothing to scrub: give --home, --user or --project", file=sys.stderr)
        return 1

    log = [f"scrubbed by scripts/scrub_identifiers.py: {len(pairs)} identifiers -> placeholders"]
    total = 0
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in TEXT or f.name == "SCRUB-LOG.txt":
            continue
        if any(part in LANES for part in f.relative_to(root).parts[:1]):
            continue  # never edit a run file
        body = f.read_text(errors="replace")
        n = 0
        for a, b in pairs:
            n += body.count(a)
            body = body.replace(a, b)
        if n:
            f.write_text(body)
            log.append(f"{f.relative_to(root)}: {n} replacements")
            total += n
    log.append(f"total replacements: {total}")
    (root / "SCRUB-LOG.txt").write_text("\n".join(log) + "\n")
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
