# Coordinate Frames: glTF, Gazebo and ROS - Take 2

Start over with an incremental build up of the understanding and explanation of how these coordinate systems are used.

Use tools/maritime-workspace/notes/glTF_Gazebo_ROS_Coordinates.md as background.

##  Objective

The purpose of this document is to be a clear explanation of how coordinate frames can be conceptualized and labeled from 3D graphics (authoring 3D assets in Blender) to robotic simulation (rendering visual assets aligned with collision models in Gazebo and RViz).

## How claims in this document are marked

Take 1 went wrong by building detail on assumptions that were never checked. So every claim here carries its standing:

- **[Firm]** — a standard or source says it, cited in [References](#references).
- **[Practice]** — really done that way, but no standard says so. Do not present it as a rule.
- **[Open]** — we do not know yet, or it needs a measurement nobody has made.
- **[Corrected]** — was asserted in Take 1 or in this draft and is wrong. Kept visible on purpose.

## Coordinate Conventions and Typical Practices

Here we clearly describe some of the usual conventions. The reason is that there are multiple conventions across multiple communities and fields.

### Origin vs coordinate frame

**[Firm]** They are not synonymous, and one standard settles it cleanly. A *coordinate system* (robotics usually says *frame*, and the two words mean the same thing) is an origin **plus** an orientation — six numbers, a pose. An *origin* is only the point where the axes meet — three numbers.

ISO 9787, the dedicated standard for robot coordinate systems, is explicit about the relationship. It names each system with its origin symbol, "World coordinate system, `O₀ - X₀ - Y₀ - Z₀`", and defines the origin as a point belonging to the system: "mobile platform origin / mobile platform reference point: origin point of the mobile platform coordinate system" (§3.10). Its clauses then fix origins and axes separately — "The origin of the base coordinate system, `O₁`, shall be defined by the manufacturer of the robot. The `+Z₁` axis is in the direction of the mechanical structure of the robot perpendicularly away from the base mounting surface" (§5.2).

So, precisely:

| Term | What it is | Who says it that way |
|---|---|---|
| coordinate system | origin + orientation | ISO 9787 §5, ISO 8373 |
| frame | the same thing | REP 103, REP 105, tf |
| origin | the point alone | ISO 9787 §3.10, §5.1–5.3 |
| pivot, object origin | the point *as named*, but in practice the whole frame | Blender, Maya, 3ds Max |

**[Firm]** The trap worth naming: 3D graphics uses the word "origin" for something that is actually a full frame. Blender's object origin carries the object's local axes with it, so rotating the object rotates about those axes — position and orientation both. The word names the point; the thing is a frame. That mismatch is a large part of why these conversations go wrong.

### Robotics

There are multiple practices in robotics, so there is not just one convention. Also, these are soft conventions and there is likely a multitude of practices, good and bad, out in the wild.

**[Firm]** Two things *are* fixed across the field and are worth stating before the soft parts. All coordinate systems are right-handed: "All coordinate systems described in this International Standard are defined by the orthogonal right-hand rule" (ISO 9787 §4.1), and REP 103 says "All systems are right handed." And the rotation names agree: ISO 9787 §4.3 defines rotations `A`, `B`, `C` about `X`, `Y`, `Z` and states "A, B and C are also called roll, pitch and yaw, respectively", which is REP 103's "fixed axis roll, pitch, yaw about X, Y, Z axes respectively".

#### Categorizing links by their place in the tree

**[Firm]** The structural claim holds, with one caveat. In URDF a link has zero or one parent and any number of children, because URDF is a tree — its schema has no way to give a link two parents, so closed kinematic loops cannot be expressed at all. **[Firm]** SDF does not have that restriction: a link may be the child of more than one joint, so loops are expressible on the SDF side. A part bolted to two different parents is therefore a URDF impossibility and an SDF ordinary case.

**[Firm]** The four categories below are close to an existing standard. ISO 9787 §5 defines eight coordinate systems, and four of them correspond almost exactly to these categories. That is a good outcome: it means this taxonomy does not need inventing, and each category has a standard name and a defined origin rule.

| Category here | ISO 9787 name | ISO clause | What the standard fixes |
|---|---|---|---|
| 1. Base link, mobile | Mobile platform coordinate system, `O_p` | §5.5, term §3.10 | names the origin the "mobile platform reference point" |
| 2. Base link, fixed or passive | Base coordinate system, `O₁` | §5.2 | origin "shall be defined by the manufacturer"; `+Z₁` away from the base mounting surface |
| 3. Intermediate link | *(none)* | — | ISO numbers the **axes**, not the links: §4.4 |
| 4. End effector | Tool coordinate system (TCS), `O_t` | §5.4, term §3.7 | "referenced to the tool or to the end effector attached to the mechanical interface" |
| *(missing from the list)* | **Mechanical interface coordinate system**, `O_m` | §5.3, term §3.6 | origin "is the centre of the mechanical interface"; `+Z_m` "points perpendicularly away from the mechanical interface" |

1. **Base link, mobile.** Zero parent joints, many children. Examples: the root part (body) of flying, driving, walking, swimming robots. There is not one fixed point of the geometry that interacts with the rest of the objects, so the location of the origin of the base link relative to the geometry is a stated datum — it must be specified — and should be stable under design change.

    **[Firm]** The standards agree that it must be stated and decline to state it for you. REP 105: "The coordinate frame called `base_link` is rigidly attached to the mobile robot base. The `base_link` can be attached to the base in any arbitrary position or orientation; for every hardware platform there will be a different place on the base that provides an obvious point of reference." ISO 9787 §5.1 says the same of the world system: its origin "shall be defined by the users in accordance with their requirements".

    **[Corrected]** "No clear parent" is right about joints and wrong about frames. A mobile `base_link` does have a parent in the transform tree — REP 105 puts it under `odom`, then `map`, then `earth` — but that edge is a *published transform* produced by odometry, not a joint in the model. The model is rootless; the runtime tree is not.

    **[Firm]** "Axis midpoint projected to the ground" is a real documented pattern, though the standard example is a different frame rather than `base_link` itself. REP 120 defines `base_footprint` as "the representation of the robot position on the floor", where "The translation component of the frame should be the barycenter of the feet projections on the floor", with roll and pitch zero. Its stated rationale is stability: `base_footprint` "provides a fairly stable 2D planar representation of the humanoid even while walking and swaying with the `base_link`". **[Practice]** The wheeled-robot equivalent, the wheel-axis midpoint projected to the ground, is very widely used but is not written down in any REP.

2. **Base link, fixed or passive.** One parent, one or many children. Example: the root part (body) of a manipulator kinematic chain. There is one point in the geometry that can be taken as the definitive location of the rest of the kinematic chain in the world. The location of the base origin is often fixed — either with an overt fixed joint to something else in the world, or passively by gravity and friction.

    **[Firm]** This is the best-specified case in the standards, and the origin is tied to a physical surface rather than to the geometry as a whole. ISO 8373 defines the *base mounting surface* as the "connection surface between the arm and its supporting structure" (ISO 9787 §3.2), and ISO 9787 §5.2 references the base coordinate system to it: `+Z₁` perpendicular away from that surface, `+X₁` pointing through the projection of the centre of the working space onto it.

3. **Intermediate link.** One parent, one or more children.

    **[Corrected]** The draft said "one parent, one child". A link can branch — a torso with two arms, a hull with four thruster mounts — so one parent and *n* children is the general case, and "intermediate" should mean only "has a parent joint and at least one child".

    **[Firm]** ISO 9787 defines no coordinate system for an intermediate link. It numbers the axes instead: "axis 1 shall be the first motion closest to the base mounting surface, axis 2 the second motion, and so on, and the last the motion to which the mechanical interface is attached" (§4.4). Per-link frame placement is the business of a kinematics convention such as Denavit-Hartenberg, not of this standard.

4. **Leaf link.** One parent, no children. An end effector is one kind of leaf; so is a wheel, a sensor, a flag or a propeller.

    **[Corrected]** The draft called this category "end effector" and defined it as "intermediate link with no children". Those are two different ideas: *leaf* is structural, *end effector* is a role. Most leaves on our vehicles are not end effectors.

    **[Firm]** For the end-effector case the standard does give a frame, and a second point inside it: the tool coordinate system is "referenced to the tool or to the end effector attached to the mechanical interface" (§3.7), and the tool centre point is a "point defined for a given application with regard to the mechanical interface coordinate system" (§3.9).

**[Open]** The two structural questions — does the link have a parent joint, and does it have children — are independent, so they generate four cells, and the categories above mix that structure with the link's *role* (base, tool, wheel). Whether the eventual rule should be stated on structure, on role, or on both is not settled here.

#### Manipulation-centric (robots with static base)

**[Firm]** For kinematic chains in manipulation scenarios it is common to define the object geometry relative to the frame collocated at the joint to the parent. URDF builds this in: a joint's `<origin>` is the transform from the parent link frame to the child link frame, and everything belonging to the child — `<visual>`, `<collision>`, `<inertial>` — is then expressed in that child frame.

**[Firm]** In this convention the center of mass is *not* the frame; it is data declared against the frame. URDF states the CoM as `<inertial><origin xyz="..." rpy="..."/>`, a pose relative to the link frame, alongside `<mass>` and `<inertia>`. So a link frame at a joint and a CoM somewhere else is the normal, intended arrangement, not a compromise.

**[Practice]** In this convention frames sit on the axes of rotation, which is the Denavit-Hartenberg inheritance. ISO 9787 §4.4's axis numbering assumes the same ordering along the chain.

Examples:

- **wheel** — the origin goes on the axle, because the axle is the joint axis. **[Practice]** For a symmetric wheel the axle happens to coincide with the geometric center, which is probably why "center of the geometry" feels like the rule here; it is a coincidence of symmetry and does not generalize to a bracket or a mast.
- **manipulator arm**
    - *intermediate link* — the origin is at the joint to the previous link in the kinematic chain.
    - *base link* — the origin is the datum the whole chain is measured from, referenced to the base mounting surface per ISO 9787 §5.2. Because the base does not move, this origin doubles as the link between the robot and the world, which is why the standard makes the manufacturer declare it.

#### Mobile-centric

For a mobile robot (flying, driving, walking, swimming) there is no *joint* to a parent, because the body moves freely.

**[Corrected]** "There is not a parent" needs the same refinement as category 1: there is no parent *joint*, but there is a parent *frame* at runtime — `odom`, per REP 105 — supplied by odometry rather than by the model.

In this case it is common to choose an origin that is a physically identifiable datum and stable under design change: a machined reference face, the projection of the drive axis onto the ground plane, or for a surface vessel the waterline. **[Practice]** No standard names any of these; REP 105 explicitly leaves the choice open and only insists that the platform has "an obvious point of reference". **[Firm]** What the standards do supply is the reasoning for preferring stability: REP 120 justifies `base_footprint` on exactly that ground.

**[Open]** Whether *this* project's convention should be a stated datum per vehicle, or a single geometric rule applied to all of them, is undecided and is the question Take 1 never managed to answer cleanly.

#### Other conventions worth knowing

**[Firm]** ISO 9787 §5 defines eight coordinate systems, not four, and the four not yet mentioned are all relevant to a simulation asset pipeline:

| System | Clause | Referenced to |
|---|---|---|
| Mechanical interface, `O_m` | §5.3 | the mechanical interface; origin at its center, `+Z_m` perpendicular away from it |
| Task, `O_k` | §5.6 | "the site of the task" |
| Object, `O_j` | §5.7 | "the object" |
| Camera, `O_c` | §5.8 | "the sensor which monitors the site of the task" |

**[Firm]** The mechanical interface coordinate system is the standard name for the thing the earlier attempt in this project called an "attach" or a "slot". It has a defined origin rule — the center of the mating interface — and a defined axis rule: `+Z` along the mating normal, pointing away from the surface.

**[Firm]** Note that this is a genuine disagreement between communities, not a restatement. ISO 9787's mounting frames are built around `+Z` along the mating normal; REP 103's body frame is built around `x` forward, `y` left, `z` up. A mount frame authored to ISO and a body frame authored to REP 103 differ by a rotation, and neither is wrong.

**[Firm]** REP 103 also carries a deliberate second convention for sensors, and it is the clearest precedent in ROS for a frame that breaks the body-frame rule on purpose: "In the case of cameras, there is often a second frame defined with a `_optical` suffix. This uses a slightly different convention: z forward, x right, y down."

**[Firm]** REP 105 supplies the world-fixed frames a vehicle needs above `base_link` — `odom` (continuous, drifts), `map` (no drift, discrete jumps) and `earth` — and REP 120 adds `base_footprint`.

**[Practice]** Outside robotics, CAD assembly tools express the same idea as mating features: Onshape's "mate connector" is a named frame on a part used to assemble it against another, which is the mechanical interface coordinate system under a different name.

### 3D Graphics

A different concept, and the difference is one of purpose rather than of mathematics.

**[Firm]** The frame is called a *pivot* (Maya, 3ds Max) or an *object origin* (Blender), and it is a manipulation handle: the point about which the object rotates and scales in the viewport. The Blender manual describes the origin as the point around which an object is transformed or manipulated. Nothing about it is required to mean anything physical.

**[Practice]** A common asset convention is to place the pivot at the bottom-center of the object so that a prop dropped at `z = 0` sits on the floor; after that, at the natural articulation point (door → hinge, wheel → axle).

**[Corrected]** The draft called bottom-center "the dominant asset convention". That over-claims: it is a real and widespread practice in real-time and game pipelines, but no standard states it, and the practice varies by engine and by studio. Treat it as a habit to expect in a delivery, not as a rule to cite.

**[Firm]** Blender offers *Object → Set Origin → Origin to Center of Mass (Volume)*, alongside *Origin to Geometry*, *Origin to 3D Cursor* and *Origin to Center of Mass (Surface)*. **[Firm]** The volume option requires a manifold, watertight mesh, which is a real constraint on using it as a rule. **[Open]** Whether asset pipelines actually use it is not something this document has evidence for either way; the claim that they do not was asserted without support.

#### What survives into glTF, and what does not

**[Corrected]** Take 1 said "the pivot concept doesn't survive into glTF at all". That is wrong, and the correction matters because the rest of the pipeline depends on it.

**[Firm]** Blender's object origin *does* survive: it becomes the origin of the glTF node's frame. A glTF node carries a local transform and may instantiate at most one mesh, and the mesh's vertex positions are expressed in that node's frame. So on export, with transforms applied, the object origin is the node's origin and the vertices are measured from it; without transforms applied, the offset between them appears as the node's `translation`, `rotation` and `scale`. Either way the frame comes through intact.

Three things genuinely do not survive:

1. **[Firm]** *A pivot held separately from the transform.* Maya and 3ds Max keep rotate and scale pivots as attributes distinct from the object's transform, so the pivot can be moved without moving the object. glTF has no such separation — one frame per node, vertices expressed in it — so any DCC pivot that differs from the object's transform is baked away on export.
2. **[Firm]** *Any statement of meaning.* There is no property anywhere in glTF that records what an origin is for. Nothing can say "this origin is the mounting face" or "this axis is forward". The origin is wherever the numbers evaluate to zero.
3. **[Firm]** *Anything checkable.* Because of (2), no validator can test an origin or a facing convention. Those rules can only live in a document and in whatever places the asset into a scene.

**[Open]** Where that leaves the project's own rule is the next increment of this document, and it should not be written until the single-body case is airtight.

## Next increment

Deliberately not covered yet, in the order it should be taken up:

1. One rigid body, one mesh, no joints: world frame, body frame, mesh vertices. Get this airtight before adding anything.
2. The transform from the file's frame to the body frame, and which of glTF, Gazebo and RViz applies what.
3. A second body and a joint between them.
4. Only then: the project's delivery rule.

## References

- ISO 9787:2013, *Robots and robotic devices — Coordinate systems and motion nomenclatures*. §3 terms, §4.1 right-handedness, §4.3 roll/pitch/yaw, §4.4 axis numbering, §5.1–5.8 the eight coordinate systems. Public preview of the front matter and §3–5.3: https://cdn.standards.iteh.ai/samples/59444/075b6999979c4afa84ad1cb58620dcbc/ISO-9787-2013.pdf — clauses 5.4 onward are behind the paywall and are cited here from the §3 term definitions, which quote the same sources.
- ISO 8373:2012 / :2021, *Robotics — Vocabulary*. The source ISO 9787 draws its terms from: https://www.iso.org/standard/75539.html
- REP 103, *Standard Units of Measure and Coordinate Conventions* — chirality, axis orientation, the `_optical` suffix frame, rotation representation: https://www.ros.org/reps/rep-0103.html
- REP 105, *Coordinate Frames for Mobile Platforms* — `base_link`, `odom`, `map`, `earth`: https://www.ros.org/reps/rep-0105.html
- REP 120, *Coordinate Frames for Humanoid Robots* — `base_footprint` and its rationale: https://www.ros.org/reps/rep-0120.html
- URDF specification, `<joint><origin>` and `<link><inertial><origin>`: https://wiki.ros.org/urdf/XML/joint and https://wiki.ros.org/urdf/XML/link
- SDFormat specification, `<frame>` and `<joint>`: http://sdformat.org/spec
- glTF 2.0 specification, §3.4 Coordinate System and Units, §3.5 Scenes and Nodes: https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
- Blender manual, Object Origin and *Set Origin*: https://docs.blender.org/manual/en/latest/scene_layout/object/origin.html
