"""Console entry point for `gltf-check`."""

import argparse
import json
import pathlib
import sys

from .rules import ADVISORY, FAIL, PASS, SKIP, WARN, check_file

MARK = {FAIL: "FAIL", WARN: "warn", ADVISORY: "note", PASS: "ok", SKIP: "--"}
ORDER = {FAIL: 0, WARN: 1, ADVISORY: 2, PASS: 3, SKIP: 4}


def render(path, findings, verbose, width=88):
    lines = [str(path)]
    shown = [f for f in findings if verbose or f.level in (FAIL, WARN, ADVISORY)]
    for f in sorted(shown, key=lambda f: (ORDER[f.level], f.section)):
        lines.append(f"  {MARK[f.level]:>4}  §{f.section:<4} {f.summary}")
        if f.detail and f.level != PASS:
            for chunk in wrap(f.detail, width - 14):
                lines.append(f"              {chunk}")
    return "\n".join(lines)


def wrap(text, width):
    words, line, out = text.split(), "", []
    for w in words:
        if line and len(line) + 1 + len(w) > width:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        out.append(line)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="gltf-check",
        description="Check a glTF file against the glTF Robotics Profile.")
    parser.add_argument("files", nargs="+", type=pathlib.Path)
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="show rules that passed as well")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--strict", action="store_true",
                        help="treat SHOULD violations as failures too")
    args = parser.parse_args(argv)

    failed = False
    payload = []
    for path in args.files:
        try:
            findings = check_file(path)
        except Exception as exc:
            print(f"{path}: {type(exc).__name__}: {exc}", file=sys.stderr)
            failed = True
            continue
        bad = [f for f in findings
               if f.level == FAIL or (args.strict and f.level == WARN)]
        failed = failed or bool(bad)
        if args.json:
            payload.append({"file": str(path), "conforms": not bad,
                            "findings": [vars(f) for f in findings]})
        else:
            print(render(path, findings, args.verbose))
            n_fail = sum(1 for f in findings if f.level == FAIL)
            n_warn = sum(1 for f in findings if f.level == WARN)
            verdict = ("conforms" if not n_fail and not n_warn else
                       f"{n_fail} failed, {n_warn} to review")
            print(f"  -> {verdict}\n")

    if args.json:
        print(json.dumps(payload, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
