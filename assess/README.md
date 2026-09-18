# glTF example assessment

Tooling to look at glTF assets somebody else wrote, and a list of the ones worth looking at.

This is the bottom-up half of the visual model work. [`model-spec.md`](../../../src/bluerobotics_models/docs/reference/model-spec.md) is the top-down half: it states what a delivered model must be, rule by rule, with the reasoning in the pipeline review beside it. Several of its rules are still open, and the arguments for and against them keep turning on what other people actually do. This directory answers that empirically, over a list of examples that grows, with an assessment that is re-run rather than rewritten.

| file | |
|---|---|
| [criteria.md](criteria.md) | what we assess and why, criterion by criterion -- the hand-edited half that carries the judgement |
| [examples.yaml](examples.yaml) | the list of assets; one block per model or library |
| [visual-notes.yaml](visual-notes.yaml) | the answers to the questions no measurement can settle -- up, forward, and what the origin sits on |
| [findings.md](findings.md) | the prose: what the corpus says, and what it means for the spec |
| [ASSESSMENT.md](ASSESSMENT.md) | generated; never hand-edit |
| `gltf_assess.py` | the tool |
| `cache/`, `rig/`, `results.json`, `run.log` | generated, and not worth committing |

## Running it

```bash
./gltf_assess.py                  # assess everything, rewrite ASSESSMENT.md
./gltf_assess.py --only fuel/     # just the ids with this prefix
./gltf_assess.py --list           # expand the registry and stop
./gltf_assess.py --refresh        # ignore the cache and re-measure
```

Host Python, no ROS and no Gazebo: it parses the files rather than loading them. `PyYAML` is the only dependency outside the standard library. `gh` is used when it is authenticated, for listing a GitHub repository's contents, and falls back to the unauthenticated API when it is not.

## Adding an example

One block in `examples.yaml` and a re-run. Every measurement is cached against its source URI, so adding the fifty-first asset measures one asset; everything else is read from `cache/`.

```yaml
  - id: fuel/forklift
    group: fuel
    fuel: OpenRobotics/Forklift
    note: The best-authored glTF asset in Fuel.
```

The four ways to name assets are `url:` for one file anywhere, `fuel:` for a Fuel model, `github:` with a `glob:` for a repository, and `path:` for local files. The last three expand: a Fuel model with no `file:` named, or a repository glob, becomes every glTF file it matches, which is how a library of seventeen models enters the list as one block. `skip: true` parks an entry without deleting it, which is how our own parts sit on the list unassessed.

## Why it does not download anything

The assets worth reading are large -- 85 MB for one warehouse, 429 MB for the largest model in Fuel -- and almost nothing worth knowing lives in the geometry. A `.glb` states its JSON chunk length in bytes 12 to 16, so two HTTP range requests yield the entire structure of the file: nodes, meshes, materials, extensions, triangle counts, texture slots and MIME types. Image dimensions come from a few kilobytes of PNG or JPEG header each, read out of the binary chunk in place. Only UV range needs vertex data, and it is bounded by a byte budget and sampled when the data is too scattered to fetch in one request.

The practical effect is that the current corpus -- 309 MB of asset -- is assessed by fetching 75 MB, and the largest single cost is the optional UV measurement that `budget_mb` caps. Below that budget a file is simply fetched whole, because three range requests over a small file cost more than the file. Adding the forty-eighth asset costs one asset, which is what makes it reasonable to keep adding to the list and to run the whole thing from CI.

## The visual rig

    ./gltf_assess.py --rig jetty/Forklift

Four of the criteria in group D are not measurable at all: which axis is up, which way the part faces, what the origin sits on, and whether our `gltf_up:=z` rotation is the one that makes the part stand up. A glTF file records vertex positions and node transforms and nothing else -- there is no up axis in it and no mounting face -- so these are answered by looking. The command writes a Gazebo world and a URDF placing the asset at the origin beside an axis marker, and a second copy with our rotation applied beside its own marker, then prints the commands to view both in Gazebo and in RViz. The answers go in [visual-notes.yaml](visual-notes.yaml) and come back into the report next to the measurement. The protocol, and how to choose which assets are worth the minute, are in [criteria.md](criteria.md) under group D.

## What it cannot tell you

The tool reads the file. It does not load it, and the distinction matters more here than it usually would: `model-spec.md` section 12 is explicit that valid, intended, compliant and usable are four different questions that fail independently. In particular, what gz-common's loader builds from a file is not always what the file says -- submesh names come from nodes rather than meshes, extensions are parsed and then ignored, and the installed version differs from the branch. That is what `glb_probe` is for, inside drydock, and `criteria.md` marks the criteria that need it. Anything visual needs a window and a person.

## Automating it

The shape this wants to end up in, and the reason the registry and the cache are separate from the report:

- A GitHub Action on `maritime-workspace` that runs the tool on a change to `examples.yaml`, commits the regenerated `ASSESSMENT.md`, and opens the diff for review. Adding an example becomes a pull request whose diff is exactly what the new asset changed about the corpus.
- A scheduled run that re-measures with `--refresh`, so an upstream asset that changes is noticed. jetty_demo and ARIAC are both moving targets.
- The cache is content-addressed by source URI; committing it would make runs reproducible offline, at the cost of a few hundred kilobytes of JSON per asset. Not done yet, and worth deciding before the list gets much longer.

- A rendered view rather than a markdown table. `results.json` is the machine-readable form of everything measured, one object per asset, and it is written on every run for exactly this reason: a dashboard would read that file rather than parse `ASSESSMENT.md`. The report is deliberately the plain-text form first, because it diffs and a dashboard does not.

None of that is set up. The tool is written so that it can be: it is idempotent, it writes one file, and it fails an unreachable asset into the report rather than into an exception.
