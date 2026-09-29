"""Console entry point for `gltf-check`."""

import argparse
import json
import pathlib
import sys

from .rules import ADVISORY, FAIL, PASS, SKIP, WARN, check_file

# One word per outcome, used everywhere the outcome is shown: beside each
# finding, in the tally, and in the legend. The same word in every place so
# that a reader never has to map "warn" onto "to review".
MARK = {FAIL: "FAIL", WARN: "WARN", ADVISORY: "OPEN", PASS: "PASS", SKIP: "SKIP"}
ORDER = {FAIL: 0, WARN: 1, ADVISORY: 2, PASS: 3, SKIP: 4}

# What each mark obliges the reader to do. The normative strength behind a
# mark is here rather than on each finding, because a rule can mix them: Scenes
# and nodes fails on a root transform (MUST) and warns on the root name (SHOULD).
LEGEND = [
    ("PASS", "the rule is satisfied"),
    ("FAIL", "a MUST in the profile is violated; the delivery is not compliant"),
    ("WARN", "a SHOULD is violated, or a MUST the file alone cannot settle; review before delivering"),
    ("OPEN", "the profile has not settled this point (the profile's Open issues section); nothing to fix, something to discuss"),
    ("SKIP", "nothing in the file for the rule to examine"),
]

SCOPE = (
    "This answers only the 'compliant' question of the profile's Conformance testing section: does the file satisfy "
    "the rules that can be decided by reading it. Valid (Khronos validator), intended "
    "(reference viewer) and usable (glb_probe, Gazebo, RViz) are separate checks."
)

# What each rule tests, stated independently of what it found. A verdict on its
# own is not readable without this: "PASS UV sets" tells you a rule passed and not
# which question was asked.
TITLES = {
    "File naming": "named <part>.visual.glb, with <part> in lowercase snake_case",
    "File format": "delivered as binary .glb rather than .gltf",
    "The manifest": "carries a KHR_xmp_json_ld manifest, and its contents agree with the file",
    "Asset header": "asset header declares glTF 2.0 and no minVersion",
    "Units": "in meters at real-world scale, checked against the cited dimension",
    "Axes": "declares +X forward and +Z up, per ISO 9787 and REP 103",
    "Scenes and nodes": "exactly one scene and one named node, with no children and no transform",
    "Datum specification": "names the datum point its origin is referenced to",
    "Geometry": "every primitive is triangles carrying POSITION, NORMAL and TEXCOORD_0",
    "UV sets": "UV coordinates present, and inside the range 0 to 1",
    "Primitives": "a primitive exists only to carry a material distinct from its siblings",
    "Materials": "every primitive has a material, with metalness stated rather than defaulted",
    "Textures": "textures are PNG in the linear slots and at most 2048 px on a side",
    "Transparency": "transparency declared per material: MASK for cutouts, never BLEND on an opaque part",
    "Prohibited content": "no prohibited extension, animation, skin, camera or light",
    "Authoring toolchain": "records the exporter that produced it",
}


def section_key(section):
    """Profile order, which is the order TITLES is written in."""
    names = list(TITLES)
    return names.index(section) if section in names else len(names)


def legend(width=88):
    """The key to the marks, and what this tool does and does not answer."""
    lines = ["marks:"]
    for mark, meaning in LEGEND:
        lines.append(f"  {mark}  {meaning}")
    lines.append("")
    lines.extend(wrap(SCOPE, width))
    return "\n".join(lines)


def render(path, findings, verbose, quiet, width=88):
    """One block per profile section: what was tested, then the verdict, then why.

    Profile order rather than severity order, so the output reads as a checklist
    that can be compared against the profile itself. Passing checks are shown by
    default -- a report that lists only problems cannot tell you whether the
    thing you cared about was examined at all.
    """
    lines = [str(path)]
    by_section = {}
    for f in findings:
        by_section.setdefault(f.section, []).append(f)

    for section in sorted(by_section, key=section_key):
        group = by_section[section]
        if quiet and all(f.level in (PASS, SKIP) for f in group):
            continue
        title = TITLES.get(section, "")
        lines.append(f"  {section}: {title}")
        for f in sorted(group, key=lambda f: ORDER[f.level]):
            lines.append(f"    {MARK[f.level]:>4}  {f.summary}")
            if f.detail and (verbose or f.level != PASS):
                for chunk in wrap(f.detail, width - 12):
                    lines.append(f"          {chunk}")
    return "\n".join(lines)


def sections(findings, level):
    """The sections carrying a finding at `level`, in profile order, by name."""
    found = sorted({f.section for f in findings if f.level == level}, key=section_key)
    return ", ".join(found)


def verdict(findings, strict=False):
    """The closing two lines: the tally, then whether the file is compliant.

    Compliant is the profile's Conformance testing section's word: every MUST satisfied. A SHOULD
    violation therefore does not break it unless --strict says to count it, and
    that is the same rule the exit code and the JSON use.
    """
    n = {level: sum(1 for f in findings if f.level == level) for level in ORDER}
    tally = ", ".join(f"{n[level]} {MARK[level]}" for level in ORDER if n[level])
    lines = [f"  {len(findings)} checks: {tally}"]

    if n[FAIL]:
        what = "a MUST is violated" if n[FAIL] == 1 else f"{n[FAIL]} MUSTs are violated"
        lines.append(f"  -> not compliant: {what} in {sections(findings, FAIL)}")
    elif n[WARN] and strict:
        lines.append(f"  -> not compliant under --strict: {n[WARN]} WARN counted as failures "
                     f"({sections(findings, WARN)})")
    elif n[WARN]:
        lines.append(f"  -> compliant; {n[WARN]} WARN to review before delivering "
                     f"({sections(findings, WARN)})")
    else:
        lines.append("  -> compliant")
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
        description="Check a glTF file against the Honu glTF Asset Profile.",
        epilog=legend(),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", type=pathlib.Path)
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="show the explanatory detail on passing checks too (few carry any)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="show only the sections with something to report")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--strict", action="store_true",
                        help="treat SHOULD violations (WARN) as failures too")
    args = parser.parse_args(argv)

    if not args.json:
        print(legend() + "\n")

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
            payload.append({"file": str(path), "compliant": not bad, "conforms": not bad,
                            "findings": [dict(vars(f), mark=MARK[f.level],
                                              tested=TITLES.get(f.section, ""))
                                         for f in findings]})
        else:
            print(render(path, findings, args.verbose, args.quiet))
            print(verdict(findings, args.strict) + "\n")

    if args.json:
        print(json.dumps(payload, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
