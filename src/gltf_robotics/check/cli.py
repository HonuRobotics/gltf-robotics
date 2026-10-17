"""Console entry point for `gltf-check`."""

import argparse
import importlib.metadata
import json
import os
import pathlib
import shutil
import sys

from .rules import ADVISORY, FAIL, PASS, SKIP, WARN, Model, check_file

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
    "File naming": "named <part>_visual.glb, with <part> in lowercase snake_case",
    "File format": "delivered as binary .glb rather than .gltf",
    "The manifest": "carries a KHR_xmp_json_ld manifest, and its contents agree with the file",
    "Asset header": "asset header declares glTF 2.0 and no minVersion",
    "Units": "in meters at real-world scale, checked against the cited dimension",
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


# Where the Markdown report goes unless --report names another file.
DEFAULT_REPORT = "gltf-check-output.md"

# ANSI colour per mark, used only when stdout is a terminal and NO_COLOR is unset.
COLOR = {"FAIL": "31;1", "WARN": "33;1", "OPEN": "36", "PASS": "32", "SKIP": "2"}


def legend():
    """The key to the marks: in --help, and at the top of a report."""
    lines = ["Each test is marked as one of:"]
    for mark, meaning in LEGEND:
        lines.append(f"  {mark}  {meaning}")
    return "\n".join(lines)


def table(rows):
    """Rows as a pipe-separated Markdown table, columns padded to line up."""
    rows = [[cell.replace("|", "\\|") for cell in row] for row in rows]
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    lines = [" | ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip() for row in rows]
    lines.insert(1, "-|-".join("-" * w for w in widths))
    return lines


def in_order(findings):
    """Profile order, worst mark first within a section."""
    return sorted(findings, key=lambda f: (section_key(f.section), ORDER[f.level]))


def sections(findings, level):
    """The sections carrying a finding at `level`, in profile order, by name."""
    found = sorted({f.section for f in findings if f.level == level}, key=section_key)
    return ", ".join(found)


def tally(findings):
    n = {level: sum(1 for f in findings if f.level == level) for level in ORDER}
    marks = ", ".join(f"{n[level]} {MARK[level]}" for level in ORDER if n[level])
    return f"{len(findings)} checks: {marks}"


def verdict_line(findings, strict=False):
    """Whether the file is compliant, and why not.

    Compliant is the profile's Conformance testing section's word: every MUST satisfied. A SHOULD
    violation therefore does not break it unless --strict says to count it, and
    that is the same rule the exit code and the JSON use.
    """
    n_fail = sum(1 for f in findings if f.level == FAIL)
    n_warn = sum(1 for f in findings if f.level == WARN)
    if n_fail:
        what = "a MUST is violated" if n_fail == 1 else f"{n_fail} MUSTs are violated"
        return f"NOT compliant: {what} in {sections(findings, FAIL)}"
    if n_warn and strict:
        return f"NOT compliant under --strict: {n_warn} WARN counted as failures ({sections(findings, WARN)})"
    if n_warn:
        return f"compliant; {n_warn} WARN to review before delivering ({sections(findings, WARN)})"
    return "compliant"


def verdict(findings, strict=False):
    """The tally and the verdict, as a two-item list under Summary."""
    return "\n".join(["Summary:", "", f"* {tally(findings)}", f"* {verdict_line(findings, strict)}"])


def brief(text, width):
    """The reason in full when it fits in two lines, else its first sentence and a pointer to -v."""
    if len(wrap(text, width)) <= 2:
        return text
    end = text.find(". ")
    return text if end < 0 else text[: end + 1] + " (more with -v)"


def paint(mark, color):
    return f"\033[{COLOR[mark]}m{mark}\033[0m" if color else mark


def render(path, findings, verbose=False, quiet=False, strict=False, width=88, color=False):
    """The terminal view: verdict first, then each problem, then the passes in one line.

    Profile order within the problems, so the list can be compared against the
    profile itself. Passing checks are named rather than hidden -- a report that
    lists only problems cannot tell you whether the thing you cared about was
    examined at all -- but collapsed, so the problems are what the eye lands on.
    """
    lines = [f"{path}  {verdict_line(findings, strict)}", f"  {tally(findings)}", ""]
    ordered = in_order(findings)
    problems = [f for f in ordered if f.level in (FAIL, WARN, ADVISORY)]
    name_width = max((len(f.section) for f in ordered), default=0)

    def entry(f):
        out = [f"  {paint(MARK[f.level], color):4}  {f.section.ljust(name_width)}  {f.summary}"]
        detail = f.detail if verbose else brief(f.detail, width - 8)
        if detail and (verbose or f.level != PASS):
            out.extend(f"        {chunk}" for chunk in wrap(detail, width - 8))
        return out

    for f in problems:
        lines.extend(entry(f))

    for level in (PASS, SKIP):
        group = [f for f in ordered if f.level == level]
        if not group or quiet:
            continue
        if verbose:
            lines.append("")
            for f in group:
                lines.extend(entry(f))
        else:
            names = list(dict.fromkeys(f.section for f in group))
            text = f"{len(group)}: " + ", ".join(names)
            chunks = wrap(text, width - 8)
            lines.append(("" if level == SKIP else "\n") + f"  {paint(MARK[level], color)}  {chunks[0]}")
            lines.extend(f"        {chunk}" for chunk in chunks[1:])
    return "\n".join(lines)


def structure(model):
    """The file's scene -> node -> mesh -> primitive -> material tree, as text lines.

    The scene the file opens is starred. Nodes and meshes no scene reaches are
    listed after the tree, since a viewer never shows them.
    """
    nodes, meshes = model.get("nodes"), model.get("meshes")
    materials, scenes = model.get("materials"), model.get("scenes")
    default = model.gltf.get("scene", 0 if scenes else None)
    reached_nodes, reached_meshes, out = set(), set(), []

    def name(item):
        return f" '{item['name']}'" if item.get("name") else ""

    def node_lines(i, prefix, last):
        reached_nodes.add(i)
        node = nodes[i] if i < len(nodes) else {}
        moved = [k for k in ("translation", "rotation", "scale", "matrix") if k in node]
        branch = "└─ " if last else "├─ "
        out.append(f"{prefix}{branch}node[{i}]{name(node)}" + (f"  ({', '.join(moved)})" if moved else ""))
        inner = prefix + ("   " if last else "│  ")
        kids = node.get("children", [])
        m = node.get("mesh")
        if m is not None:
            reached_meshes.add(m)
            mesh = meshes[m] if m < len(meshes) else {}
            out.append(f"{inner}{'└─ ' if not kids else '├─ '}mesh[{m}]{name(mesh)}")
            mesh_prefix = inner + ("   " if not kids else "│  ")
            prims = mesh.get("primitives", [])
            for pi, prim in enumerate(prims):
                mat = prim.get("material")
                label = (f"material[{mat}]{name(materials[mat])}" if mat is not None and mat < len(materials)
                         else "no material")
                out.append(f"{mesh_prefix}{'└─ ' if pi == len(prims) - 1 else '├─ '}primitive[{pi}] -> {label}")
        for k, c in enumerate(kids):
            node_lines(c, inner, k == len(kids) - 1)

    for si, scene in enumerate(scenes):
        star = "* " if si == default else "  "
        out.append(f"{star}scene[{si}]{name(scene)}")
        roots = scene.get("nodes", [])
        for k, r in enumerate(roots):
            node_lines(r, "   ", k == len(roots) - 1)

    stray_nodes = [i for i in range(len(nodes)) if i not in reached_nodes]
    stray_meshes = [i for i in range(len(meshes)) if i not in reached_meshes]
    if stray_nodes:
        out.append("not in any scene: " + ", ".join(f"node[{i}]{name(nodes[i])}" for i in stray_nodes))
    if stray_meshes:
        out.append("not used by any node: " + ", ".join(f"mesh[{i}]{name(meshes[i])}" for i in stray_meshes))
    if not scenes:
        out.append("no scenes")
    out.append("")
    out.append("* the scene the file opens")
    return out


def version():
    try:
        return importlib.metadata.version("gltf-robotics")
    except importlib.metadata.PackageNotFoundError:
        return "source"


def report(results, strict=False):
    """The full record as Markdown: legend, a matrix across files, then each file in full.

    `results` is a list of (path, findings, model). Every test is listed with what
    it tests and what it found, the reasons behind anything but a pass follow,
    and the file's structure tree closes each section.
    """
    out = ["# gltf-check report", "", f"gltf-robotics {version()}", "", "Each test is marked as one of:", ""]
    out += [f"- **{mark}** {meaning}" for mark, meaning in LEGEND]
    out += ["", SCOPE, ""]

    if len(results) > 1:
        out += ["## Summary", ""]
        names = [str(pathlib.Path(p).name) for p, _, _ in results]
        rows = [["Test", *names]]
        for section in TITLES:
            marks = []
            for _, findings, _ in results:
                levels = [f.level for f in findings if f.section == section]
                marks.append(MARK[min(levels, key=ORDER.get)] if levels else "")
            if any(marks):
                rows.append([section, *marks])
        rows.append(["Verdict", *["NOT compliant" if verdict_line(f, strict).startswith("NOT") else "compliant"
                                  for _, f, _ in results]])
        out += table(rows) + [""]

    for path, findings, model in results:
        out += [f"## {pathlib.Path(path).name}", "", f"**{verdict_line(findings, strict)}**", "",
                tally(findings), "", "### Tests", ""]
        rows = [["Result", "Test name", "Test description", "Notes"]]
        rows += [[MARK[f.level], f.section, TITLES.get(f.section, ""), f.summary] for f in in_order(findings)]
        out += table(rows) + [""]
        explained = [f for f in in_order(findings) if f.detail and f.level != PASS]
        if explained:
            out += ["### Notes", ""]
            out += [f"- **{MARK[f.level]}** {f.section}: {f.detail}" for f in explained]
            out += [""]
        out += ["### Structure", "", "```text", *structure(model), "```", ""]
    return "\n".join(out)


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
        epilog=legend() + "\n\n" + "\n".join(wrap(SCOPE, 88)),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", type=pathlib.Path)
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="list every test with its finding, and the full reason behind each")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="show only the tests with something to report (no PASS or SKIP lines)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--report", type=pathlib.Path, metavar="FILE.md", default=pathlib.Path(DEFAULT_REPORT),
                        help="where to write the full record as Markdown: every test, the reasons, "
                             f"the scene/node/mesh tree, and a matrix across files (default: {DEFAULT_REPORT})")
    parser.add_argument("--strict", action="store_true",
                        help="treat SHOULD violations (WARN) as failures too")
    args = parser.parse_args(argv)

    color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    width = shutil.get_terminal_size((88, 24)).columns

    failed = False
    payload, results, compliant = [], [], []
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
        compliant.append(not bad)
        results.append((path, findings, Model(path)))
        if args.json:
            payload.append({"file": str(path), "compliant": not bad, "conforms": not bad,
                            "findings": [dict(vars(f), mark=MARK[f.level],
                                              tested=TITLES.get(f.section, ""))
                                         for f in findings]})
        else:
            print(render(path, findings, args.verbose, args.quiet, args.strict, width, color) + "\n")

    if args.json:
        print(json.dumps(payload, indent=1))
    elif len(args.files) > 1:
        print(f"{len(args.files)} files: {sum(compliant)} compliant, "
              f"{len(compliant) - sum(compliant)} NOT compliant"
              + (f", {len(args.files) - len(compliant)} unreadable" if len(compliant) < len(args.files) else ""))
    args.report.write_text(report(results, args.strict) + "\n")
    print(f"report written to {args.report}", file=sys.stderr if args.json else sys.stdout)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
