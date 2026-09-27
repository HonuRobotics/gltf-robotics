# The Profile

A profile narrows a base specification to a domain. This one narrows glTF 2.0 to visual models delivered for robot simulation, and states what a delivery must be.

It stands in three relationships to the standards it builds on, and every rule is one of the three: narrowing, using less than glTF allows; adding, requiring something glTF does not because Gazebo or RViz needs it; or departing, differing from the standard, which is done rarely and never silently.

Every rule carries its status. Where the text is normative, the question is settled. Everything unsettled is marked with a single Open block: a question with no answer proposed, a proposal not yet agreed, or a rule stated in its simplest form on purpose with a more capable version plausible later. A delivery cannot fail to conform on a point marked Open.

```{toctree}
:maxdepth: 2

The glTF Robotics Profile <profile>
```
