# Coordinate Frames: glTF, Gazebo and ROS - Take 2

Start over with an incremental build up of the understanding and explanation of how these coordinate systems are used.

Use tools/maritime-workspace/notes/glTF_Gazebo_ROS_Coordinates.md as background.

##  Objective

The purpose of this document is to be a clear explanation of how coordinate frames can be conceptualized and labeled from 3D graphics (authoring 3D assets in Blender) to robotic simulation (rendering visual assets aligned with collision models in Gazebo and RViz).

### Central Issue

The main challenge that motivates this documentation is that in order to build a repeatable 3D asset workflow we need to document the conventions at every stage of this flow, and at every interface between stages:

3D graphics conventions -> glTF spec -> assimp loader -> Gazebo / ROS

Each item in the flow has its own combination of vocabulary, standards, conventions and best practices. To complicate things, these conventions are incomplete — not all of them constrain the same things — and sometimes they conflict. This requires understanding and documenting each step and, importantly, connecting the interfaces between each item so that the standards and conventions are followed, or, where necessary, documenting the variation from them.  

## How claims in this document are marked

Take 1 went wrong by building detail on assumptions that were never checked. So every claim here carries its standing:

- **[Firm]** — a standard or source says it, cited in [References](#references).
- **[Practice]** — really done that way, but no standard says so. Do not present it as a rule.
- **[Open]** — we do not know yet, or it needs a measurement nobody has made.
- **[Corrected]** — was asserted in Take 1 or in this draft and is wrong. Kept visible on purpose.





## Coordinate Conventions and Typical Practices

Here we clearly describe some of the usual conventions. The reason is that there are multiple conventions across multiple communities and fields.

## Vocabulary / Nomenclature / Glossary

Terms that have to be pinned down because they are used differently at different stages of the flow in [Central Issue](#central-issue). Organized by where in the flow each term comes from, so a reader can see which vocabulary they are standing in.

### Our formal default

**Decided.** This document uses **coordinate system** as the formal term. *Coordinate system*, *coordinate frame* and *frame* all mean the same thing here.

 The reasons 
 * ISO 9787 says "coordinate system" throughout. 
 * "coordinate system" is the native term at three of the four stages of the flow:
| Stage | Its own term |
|---|---|
| 3D graphics conventions | "coordinate system" — X3D §4.3.6, *Standard units and coordinate system* |
| glTF spec | "coordinate system" — §3.4 is titled *Coordinate System and Units* |
| assimp loader | no vocabulary of its own |
| Gazebo / ROS | "frame" — REP 103, REP 105 and tf, which identifies each by a `frame_id`; SDF also has a `<frame>` element |
* And "frame" collides three ways on the asset side, which is where the readers least able to disambiguate it are.  In the DCC world...
    - **A frame is a unit of time** in every DCC tool, and in glTF's own tooling.  To a modeler, "frame" means a point on the timeline first.
    - **3D graphics does not use "frame" for this concept anyway.** Its idiom is *space* — object space, world space, tangent space — so adopting "frame" buys nothing on that side.

*Space* was considered as the formal term for that last reason and rejected: it would import the mirror-image problem, since no roboticist says "object space". % CLAUDE: Rephrase, "Space" is an equivalent term for the conceptm cinubg from the DCC side, but confounded on the robotics side ("configuration space", etc.)

"Frame" stays legal in three narrow places: inside verbatim quotations, since REP 105 really does say "the coordinate frame called `base_link`"; when naming a ROS or SDF artifact (`frame_id`, `<frame>`, `base_link`, `base_footprint`, and the REP titles in the references); and in informal prose where nothing is ambiguous.

Two registers, copying ISO's own habit: the **full name in prose** — "the part coordinate system is referenced to the mounting face" — and the **subscripted origin symbol in tables, equations and diagram labels**, which is exactly what ISO uses `O₁`, `O_m` and `O_p` for. That removes the verbosity objection without inventing an abbreviation.

**[Open]** The document does not yet obey its own rule. Its title and objective still say "Coordinate Frames", and the eight names coined in [Our frame names](#our-frame-names) are all "*x* frame". Renaming those is pending, and it is a rename rather than a decision. % CLAUDE: Fix on next PMR

### Terms by stage of the flow

Started here; extend as terms come up. The point is to record which stage a word comes from, because most of the confusion is a term carrying its home stage's meaning into a later one.

**3D graphics / authoring stage**

- **DCC** — *digital content creation*. The collective term for 3D authoring applications: Blender, Maya, 3ds Max, Houdini, Cinema 4D. Used in ISO 17506.
- **pivot** (Maya, 3ds Max) and **object origin** (Blender) — the per-vendor names for a manipulation handle: the point an object rotates and scales about in the viewport. Neither term has a standard behind it, and the two tools do not mean quite the same thing by them — see [What survives into glTF](#what-survives-into-gltf-and-what-does-not).

The reason we don't use "frame" is because that term is severly overloaded in 
### Coordinate system, origin, and reference point

**[Firm]** A coordinate system is an origin **plus** an orientation: six numbers, a pose. An origin alone is just the point where the axes meet.

**[Corrected]** That distinction is true but it is not what we actually do, and an earlier draft of this section offered it as the whole answer. When this project "defines the origin" of a part it is not choosing a point in empty space — it is stating **which physical feature of the geometry the coordinate system is anchored to**. That act has standard names, and we borrow them rather than author our own.

**[Firm]** ISO 9787 never once defines a coordinate system by where its origin numerically sits. Every clause-3 definition uses one formula, "coordinate system **referenced to** *a physical thing*":

| Clause | Definition, verbatim |
|---|---|
| 3.4 world | "stationary coordinate system referenced to earth, which is independent of the robot motion" |
| 3.5 base | "coordinate system referenced to the base mounting surface" |
| 3.6 mechanical interface | "coordinate system referenced to the mechanical interface" |
| 3.7 tool (TCS) | "coordinate system referenced to the tool or to the end effector attached to the mechanical interface" |
| 3.11 task | "coordinate system referenced to the site of the task" |
| 3.12 object | "coordinate system referenced to the object" |
| 3.13 camera | "coordinate system referenced to the sensor which monitors the site of the task" |

**Decided.** We adopt that pattern. Every coordinate system this project defines is stated as *referenced to* a named feature, never as a set of coordinates.

**[Firm]** ISO 9787 also supplies the word for the origin considered as a located thing. §3.10: "mobile platform origin; mobile platform **reference point**: origin point of the mobile platform coordinate system". So *reference point* is the standard's own term, and we use it wherever "origin" would be ambiguous.

### The `O - X - Y - Z` notation

**[Firm]** ISO 9787 names each coordinate system by its origin and its three axes together, subscripted per system: "World coordinate system, `O₀ - X₀ - Y₀ - Z₀`", "Base coordinate system, `O₁ - X₁ - Y₁ - Z₁`", "Mechanical interface coordinate system, `O_m - X_m - Y_m - Z_m`", and so on. The notation is doing exactly the split above:

- `O₀` is the **reference point** — it fixes the coordinate system's *location* with respect to the geometry.
- `X₀ - Y₀ - Z₀` are the axes — they fix its *orientation* with respect to the geometry.

That is why the standard's clauses come in two halves, one sentence placing `O` and one or two more fixing the axes. §5.2 is the clearest case: "The origin of the base coordinate system, `O₁`, shall be defined by the manufacturer of the robot. The `+Z₁` axis is in the direction of the mechanical structure of the robot perpendicularly away from the base mounting surface."

Subscripts in use: `0` world, `1` base, `m` mechanical interface, `t` tool, `p` mobile platform, `k` task, `j` object, `c` camera.

### Specifying a coordinate system: datums and what "referenced to" means

> **OUTLINE — not yet written.** The plan for the subsection that makes "referenced to" precise. Review the structure before it gets filled in.

**Why it is needed.** "Referenced to the mounting face" is better than "origin at the centroid", but it is still loose: it does not say how much of the six degrees of freedom one face actually pins down, nor what may be named as a feature in the first place. Both questions have citable answers in the GPS (geometrical product specification) standards, so this subsection borrows rather than invents.

**0. Three things have been called "defining the coordinate system", and they are different.**
This part comes first because it is the confusion the rest depends on: "referenced to the mounting face" reads as a qualitative description, a pose is six numbers, and mixing the two feels wrong. It is not a mixture. They are three layers with a direction of travel between them.

| | What it is | Numbers? | Who produces it |
|---|---|---|---|
| **Datum specification** | which situation features the coordinate system is referenced to | none | a person, once, and it is recorded |
| **Realized pose** | what that specification evaluates to against a particular piece of geometry — the coordinate system's location and orientation in whatever ambient coordinates the geometry is expressed in | six | derived by measurement, never authored |
| **Relative pose** | the transform between two coordinate systems; this is what an SDF `<visual><pose>` or a `<joint><origin>` holds | six | computed from the two realized poses |

So *referenced to* is not a qualitative stand-in for the six numbers. It is the **rule that generates them**, and the numbers are its output:

`datum specification + vertex data → realized pose → (invert, compose with the axis-convention rotation) → the visual pose`

To write: the direct parallel in mechanical practice, which is where the whole vocabulary comes from. A drawing names datum A as a face and datum B as a bore; it does not give coordinates. A CMM then measures the part and computes the datum reference frame numerically. The qualitative statement is the specification; the six numbers are a measurement result. Nobody experiences that as a category mix-up, and it is exactly our situation.

Two consequences worth stating in the same breath. First, "referenced to" has a **formal completeness test**, so it is not merely qualitative: the named features must constrain all six degrees of freedom between them, or the coordinate system is under-determined and the leftover degrees of freedom are arbitrary — a defect in the specification, and a detectable one. Second, this names the project's actual defect precisely: today the visual poses and mounting offsets are hand-authored six-number values with no datum specification upstream of them, so a redelivered mesh cannot reproduce them and the numbers have to be re-derived by eye. The numbers are not the problem; the missing rule above them is.

**A. What may serve as a datum — four kinds, and nothing else.**
ISO 17450-1 §3.3.1.1.3 defines a **situation feature** as a "point, straight line, plane or helix, from which the location and/or orientation of a geometrical feature can be defined", adding that it "is a geometrical attribute of an ideal feature" and that "no dimensional parameters are linked to a situation feature". To write: that the list is exhaustive, with the standard's own examples (situation point of a sphere or a cone, situation straight line of a cylinder, situation plane of a plane pair). The consequence to draw out: a centroid, a bounding-box center or a "center in plan" is a *derived quantity*, not a situation feature — which is the precise reason those rules drift on redelivery while a face or a bore axis does not. Also to reconcile with the Standards Summary note below, which reaches for "a datum point … associated with a recognizable feature or a survey landmark": that instinct is right, and the refinement is that a *point* is only one of the four kinds and the weakest, because a point alone fixes no orientation at all. Vocabulary to introduce alongside: **datum**, **datum feature** and **datum system** from ISO 5459, and ASME Y14.5's **datum reference frame**, "a Cartesian coordinate system oriented on a part from selected part features", as the phrase closest to our meaning.

**B. What "referenced to" means — location, orientation, or both.**
To write: ISO's own "location **and/or** orientation" is the crux, and the *and/or* is load-bearing. A coordinate system has six degrees of freedom to pin down, three translational and three rotational, and each kind of situation feature constrains a different subset — a plane fixes one translation and two rotations; an axis fixes two translations and two rotations; a point fixes three translations and no rotation. So a single feature is almost never enough, and "referenced to" is shorthand for a *set* of features that together constrain all six. This is where ISO 5459's primary / secondary / tertiary datum ordering belongs, and where a table belongs: feature kind, what it constrains, what is left free. **[Open]** those degree-of-freedom counts are stated from the GPS invariance-class model (ISO 17450-1 §3.3.1.2 and Annex E) and must be checked against that annex before this is published as [Firm].

**C. Worked examples, one per case we actually meet.**

| Case | Situation features it is referenced to | Status |
|---|---|---|
| Manipulator base, ISO 9787 §5.2 | the base mounting surface, a **plane** — "connection surface between the arm and its supporting structure" (§3.2); `+X₁` is then fixed by a *constructed* direction through the working-space center, not by a feature | write up from the standard |
| Mechanical interface, §5.3 | the interface, a **plane**, plus its **axis**; reference point at "the centre of the mechanical interface" | write up |
| Mobile platform, §5.5 | **none given.** ISO fixes the axes functionally — "`+X_p` … in the forward direction", "`+Z_p` … in the upward direction" — and names no feature at all. This is the gap, and it is the gap for exactly our vehicles | the open question |
| Surface vessel | naval architecture already has a three-plane datum system: the **baseline**, the **centreline** plane, and a transverse plane through the **aft perpendicular**, origin at the intersection of the latter two. ISO 7462 carries the terminology and its terms are free on the ISO OBP | strong candidate for the vehicle coordinate system |
| Our parts | to be decided; the one genuine invention | open |

**D. Why this replaces the origin question.**
To write: "where does the origin sit within the part?" invites derived answers that move whenever the geometry changes. "Which situation features is the part coordinate system referenced to?" invites an answer a modeler, an integrator and an inspector can each point at, and it is checkable by measurement on redelivery — the property the rule needed and never had. Close on what this does to the delivery spec: the manifest records the named features, not a set of coordinates.

### Assumptions

* All coordinate systems are right-handed.
* All coordinate systems define rotations about x, y and z as roll, pitch and yaw respectively. 

### Standards Summary

#### ISO 9787:2013

This is our foundations for the robotics coordinate systems and motion nomenclature

Named Coordinate Systems and Notation:
* **World** ($O_0 = X_0 - Y_0 - Z_0$): 
    * $O_0$ is user defined - unconstrained on where world frame is located
    * $+Z_0$ is defined as " collinear but in the opposite direction to the acceleration of gravity vector" - which is a more exact way of saying $+Z_0$ is up.
    * $+X_0$ is  user defined - unconstrained orientation of frame, other than `+Z_0` is up.
    * Comments:
        * This is the standard we adopt in total.   
            * consistent with most (not all) other conventions and our preference.
            * clearly documented so all we need to do is say we follow 5.1 and cite the standard.
* **Base** ($O_1 = X_1 - Y_1 - Z_1$):
    * Base denotes the base of a robot.
    * $O_1$: The origin of the base shall be defined by the manufacturer of the robot. 
        * For the spec and workflow we are building this is important.  We can adapt something along the lines of "The location of the base coordinate system relative to the robot geometry SHOULD be explicity defined when commissioning the 3D asset creation.  Ideally both the robot hardware and the 3D model share the same origin location definition. This is a datum point on the robot, typically associated with a recognizable feature or a survey landmark, in order to serve as the canoncial reference location for sensors and actuators."
        This is a sticking point - and one we've gotten wrong.  








### Robotics 

There are multiple practices in robotics, so there is not just one convention. Also, these are soft conventions and there is likely a multitude of practices, good and bad, out in the wild.

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

    **[Firm]** ISO 9787 §5.5 does give the mobile platform axis rule, and it is REP 103: "The `+X_p` axis is normally taken in the forward direction of the mobile platform. The `+Z_p` axis is normally taken in the upward direction of the mobile platform." Figure 6 draws it on a four-wheeled vehicle with `Y_p` to the platform's left. So for the mobile case the robotics standard and the ROS convention agree outright, and the only thing ISO leaves open is where the origin sits — the same gap REP 105 leaves.

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
| Tool (TCS), `O_t` | §5.4 | origin **is** the TCP; `+Z_t` "tool dependent, normally in the direction of the tool" |
| Mobile platform, `O_p` | §5.5 | `+X_p` forward, `+Z_p` up — REP 103's body frame |
| Task, `O_k` | §5.6 | "the site of the task" — **defined by figure only, no axis rule** |
| Object, `O_j` | §5.7 | "the object" — figure only |
| Camera, `O_c` | §5.8 | "the sensor which monitors the site of the task" — figure only |

**[Firm]** Worth noting what the standard declines to do: §5.6 through §5.8 give no axis convention at all, only a reference to Figure 7. So ISO fixes axes for the world, base, mechanical interface, tool and mobile platform, and leaves the task, object and camera systems to the application. Annex A then works the base and mechanical interface systems through five mechanical structures — rectangular, cylindrical, polar, articulated and SCARA — and none of them is a mobile robot.

**[Firm]** The mechanical interface coordinate system is the standard name for the thing the earlier attempt in this project called an "attach" or a "slot". It has a defined origin rule — the center of the mating interface — and a defined axis rule: `+Z` along the mating normal, pointing away from the surface.

**[Firm]** The disagreement is narrower than it first looks, and worth stating precisely. ISO 9787's *mounting* frames are built around `+Z` along the mating normal (§5.3), and its *tool* frames around `+Z` "normally in the direction of the tool" (§5.4), both of which differ from a REP 103 body frame by a rotation. But its *mobile platform* frame (§5.5) is `+X` forward and `+Z` up, which is REP 103 exactly. So ISO and ROS agree about vehicles and differ only about mounting interfaces and tools, where ISO is describing a mating surface rather than a body.

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

#### Standards for 3D assets

**[Corrected]** The working assumption behind this document — solid references on the robotics side, nothing comparable for 3D assets — is wrong. The asset formats are standardized, and one of them is the format this project delivers in.

| Standard | What it is | Coordinate system it fixes |
|---|---|---|
| **ISO/IEC 12113:2022** | *Information technology — Runtime 3D asset delivery format — Khronos glTF™ 2.0.* glTF 2.0 published as an International Standard | right-handed, `+Y` up, meters, radians; front faces `+Z`, left side faces `+X` (§3.4) |
| **ISO/IEC 19775-1:2023** | *Extensible 3D (X3D) — Part 1: Architecture and base components* | §4.3.6 right-handed, `+Y` up, base unit "metres"; default viewer sits on `+Z` looking down `−Z`, so an object facing the camera faces `+Z` |
| **ISO 17506:2022** | *COLLADA digital asset schema specification for 3D visualization of industrial data* (was ISO/PAS 17506:2012) | declares its up axis per file, `<up_axis>`, rather than fixing one |

**[Firm]** Three consequences follow, and they reframe the whole problem.

First, citing glTF §3.4 *is* citing an ISO standard. The Khronos registry text and ISO/IEC 12113 are the same specification under two covers, so the asset side of this pipeline is no less formally grounded than the robotics side.

Second, the asset standards agree with each other. glTF and X3D independently land on right-handed, `+Y` up, meters, and a front that faces `+Z` — X3D by way of where it puts the default camera rather than by saying so. That agreement is worth leaning on: it is not one vendor's habit.

Third, COLLADA is the outlier and the reason it behaved differently for us. It makes the up axis a per-file *declaration* instead of a convention, which is exactly the freedom that lets a consumer ignore it — and both Gazebo and RViz do.

**[Firm]** What genuinely has no standard is narrower than "3D assets":

- **Authoring-tool vocabulary.** "Pivot" (Maya, 3ds Max) and "object origin" (Blender) are vendor terms. No standard names them, and no standard relates them to each other.
- **Blender's viewport sense of "front".** Blender's Front view (numpad 1) looks along `+Y`, so the face presented to you is the `−Y` face. Taking that as the object's front makes Blender's convention forward `−Y`, left `+X`, up `+Z`. That is a UI habit, documented only by the behavior of the view shortcuts.
- **Which way a delivered asset should face.** glTF states it without a requirement keyword and provides no property to record it, so nothing can enforce or check it.

**[Open]** OpenUSD is not standardized. The Alliance for OpenUSD is working toward a specification, but there is no ISO or equivalent text today, which matters because REP 158 is written around USD as the authoring baseline.

## Reconciling the standards

**[Firm]** The problem is not a missing standard. It is that two well-standardized communities label the same three axes differently, and an unstandardized authoring tool adds a third labeling.

### Where they agree, and it is most of it

| Property | Robotics (ISO 9787, REP 103) | 3D assets (ISO/IEC 12113, ISO/IEC 19775) | Agree? |
|---|---|---|---|
| Handedness | right-handed (ISO §4.1, REP 103 "All systems are right handed") | right-handed (glTF §3.4, X3D §4.3.6) | **yes** |
| Length unit | meter (REP 103 base units) | meter (glTF §3.4, X3D §4.3.6) | **yes** |
| Angle unit | radian (REP 103) | radian (glTF §3.4) | **yes** |
| Rotation names | roll, pitch, yaw about X, Y, Z (ISO §4.3, REP 103) | not addressed | no conflict |
| Which axis is up | `+Z` (ISO §5.1 "collinear but in the opposite direction to the acceleration of gravity"; §5.5 `+Z_p` up) | `+Y` | **no** |
| Which axis is forward | `+X` (ISO §5.5, REP 103) | `+Z` | **no** |

### The disagreement is one cyclic relabeling

**[Firm]** Write each convention as the ordered triple its `(X, Y, Z)` axes mean:

- robotics — `(forward, left, up)`
- 3D assets — `(left, up, forward)`

The same three directions in the same cyclic order, shifted by one position. Nothing is mirrored, no unit differs, no handedness differs. That is why a single rotation reconciles them, and why the reconciliation can never need a reflection or a scale.

**[Corrected]** Blender's viewport convention is *not* a third position in that cycle, which is a tidier claim than the algebra supports. Its triple is `(left, back, up)` — the front view presents the `−Y` face — and that is not a cyclic shift of `(forward, left, up)`; it shares the robotics up axis and differs in the other two. A yaw of `+90°` about that shared up axis carries Blender's axes onto REP 103's, which is why a part authored to REP 103 shows its front in Blender's **Right** view rather than its Front view. Blender is also the one convention here with no standard behind it.

### Our frame names

**[Firm where a clause is cited, otherwise ours]** Based on ISO 9787 and deliberately not identical to it. ISO is written for industrial manipulators, so three of its eight systems have no use here and it lacks a name for the thing we handle most: an ordinary rigid component that is neither a base, a tool, nor a mating surface.

| Our name | Basis | Status |
|---|---|---|
| **world frame** | ISO 9787 §5.1 world coordinate system | **adopt as-is**: `+Z` opposite gravity, origin ours to define |
| **vehicle frame** | ISO 9787 §5.5 mobile platform coordinate system | **adopt the axes as-is** (`+X` forward, `+Z` up, = REP 103); rename, because "mobile platform" reads oddly for a boat and an ROV |
| **part frame** | none — ISO numbers axes, not links | **ours.** ISO has no term for a non-root rigid body that is not a tool or an interface. This is the gap we must fill ourselves |
| **mount frame** | ISO 9787 §5.3 mechanical interface coordinate system | **narrow**: keep the origin rule (center of the interface) and drop the `+Z` mating-normal axis rule in favor of the part frame's axes, so that one convention governs every frame in a model |
| **asset frame** | glTF / ISO/IEC 12113 §3.5, the scene's implicit space | **ours, grounded in the format.** No robotics standard has this concept; it exists only inside a file |
| **node frame** | glTF / ISO/IEC 12113 §3.5 node | **adopt as-is**, the format's own term |
| **sensor frame** | ISO 9787 §5.8 camera coordinate system; REP 103 `_optical` | **adopt REP 103's**, since ISO gives no axis rule and REP 103 does (`z` forward, `x` right, `y` down) |
| *tool frame* | ISO 9787 §5.4 | **reserved, unused.** No manipulators in scope yet; adopt as-is if one arrives |

**[Open]** The mount-frame narrowing is a real decision and not yet taken. Keeping ISO's `+Z`-along-the-mating-normal rule would make every mounting face self-describing but put a second axis convention inside one model; dropping it keeps one convention but means a mount frame carries no information about which way the surface faces.

### The full reconciliation

Each row is one frame; each column is what that frame is called, or what stands in for it, in each place.

| Our frame | ISO 9787 | ROS (REP 103/105) | SDF / Gazebo | glTF (ISO/IEC 12113) | Blender | Action |
|---|---|---|---|---|---|---|
| world frame | world CS, §5.1 | `map`, `earth` (REP 105) | `<world>`, implicit world frame | — | the scene, Z-up | adopt |
| vehicle frame | mobile platform CS, §5.5 | `base_link` (REP 105) | model frame; root `<link>` | — | — | adopt axes, rename |
| part frame | — | a non-root `<link>` | `<link>` | — | the object, and its origin | **ours** |
| mount frame | mechanical interface CS, §5.3 | a massless link + fixed joint | `<frame>`, and a `<joint>` parent | — | — | narrow |
| asset frame | — | — | the `<mesh><uri>` as placed by `<visual><pose>` | scene's implicit space, §3.5 | the exported scene | ours |
| node frame | — | — | — | node, §3.5 | the object's origin | adopt |
| sensor frame | camera CS, §5.8 | `*_optical` (REP 103) | `<sensor><pose>` | — | — | adopt REP 103 |

**[Firm]** Two asymmetries in that table are the whole reason this is hard. The middle rows have no glTF column, because glTF has no concept of a link, a joint or a mount — it has nodes and geometry and nothing else. And the `asset frame` and `node frame` rows have no robotics column, because nothing in ISO 9787 or the REPs describes the inside of a mesh file. The pipeline has to join two vocabularies that do not overlap at the point where they meet.

### Adopt, narrow, or invent

**[Firm]** Summarizing what this project actually has to write down, which is much less than Take 1 assumed:

- **Adopt as-is, no project text needed:** handedness, length and angle units, roll/pitch/yaw naming, the world frame, the vehicle frame's axes, the sensor optical frame, glTF's node and scene model. All are settled by ISO 9787, REP 103 or ISO/IEC 12113 and need only a citation.
- **Narrow:** the mount frame, by dropping ISO's mating-normal axis rule (undecided, above).
- **Invent, because no standard reaches:** the part frame as a named concept; where an origin sits within a part's geometry; which asset-frame axis a delivery's forward direction occupies; and the rule joining the asset frame to the part frame — that is, the value of the visual pose.
- **[Open]** That last list is short and it is exactly the list Take 1 failed to isolate. The next increments should address it in that order.

## Next increment

The vocabulary and the standards groundwork are now settled, and the list of things this project must decide for itself is short — see "Adopt, narrow, or invent" above. Deliberately not covered yet, in the order it should be taken up:

1. One rigid body, one mesh, no joints: world frame, vehicle frame, asset frame, mesh vertices, written in the frame names agreed above. Get this airtight before adding anything.
2. The transform from the asset frame to the part frame — the value of the visual pose — and which of glTF, Gazebo and RViz applies what. Take 1's findings on this are sound and can be carried over; its framing cannot.
3. Where the origin sits within a part, and which asset-frame axis carries forward. These are the two genuine inventions.
4. A second body and a joint between them, which is where the mount-frame narrowing has to be settled.
5. Only then: the project's delivery rule.

## References

- ISO 9787:2013, *Robots and robotic devices — Coordinate systems and motion nomenclatures*. §3 terms, §4.1 right-handedness, §4.3 roll/pitch/yaw, §4.4 axis numbering, §5.1–5.8 the eight coordinate systems, Annex A worked examples. Purchased single-user copy at `tools/maritime-workspace/refs/`, which is git-ignored — cite it by clause rather than copying text. https://www.iso.org/standard/59444.html
- ISO/IEC 12113:2022, *Information technology — Runtime 3D asset delivery format — Khronos glTF™ 2.0* — the same specification as the Khronos registry text: https://www.iso.org/standard/83990.html
- ISO/IEC 19775-1:2023, *Extensible 3D (X3D) — Part 1* §4.3.6 standard units and coordinate system. Web3D publishes the text free: https://www.web3d.org/standards/number/19775-1
- ISO 17506:2022, *COLLADA digital asset schema specification*: https://www.iso.org/standard/78834.html
- ISO 8373:2012 / :2021, *Robotics — Vocabulary*. The source ISO 9787 draws its terms from: https://www.iso.org/standard/75539.html
- REP 103, *Standard Units of Measure and Coordinate Conventions* — chirality, axis orientation, the `_optical` suffix frame, rotation representation: https://www.ros.org/reps/rep-0103.html
- REP 105, *Coordinate Frames for Mobile Platforms* — `base_link`, `odom`, `map`, `earth`: https://www.ros.org/reps/rep-0105.html
- REP 120, *Coordinate Frames for Humanoid Robots* — `base_footprint` and its rationale: https://www.ros.org/reps/rep-0120.html
- URDF specification, `<joint><origin>` and `<link><inertial><origin>`: https://wiki.ros.org/urdf/XML/joint and https://wiki.ros.org/urdf/XML/link
- SDFormat specification, `<frame>` and `<joint>`: http://sdformat.org/spec
- glTF 2.0 specification, §3.4 Coordinate System and Units, §3.5 Scenes and Nodes: https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
- Blender manual, Object Origin and *Set Origin*: https://docs.blender.org/manual/en/latest/scene_layout/object/origin.html
