# The Profile

A profile narrows a base specification to a domain. This one narrows glTF 2.0 to visual models delivered for robot simulation, and states what a delivery must be.

It stands in three relationships to the standards it builds on, and every rule is one of the three: narrowing, using less than glTF allows; adding, requiring something glTF does not because Gazebo or RViz needs it; or departing, differing from the standard, which is done rarely and never silently.

Every rule carries its status. Where the text is normative, the question is settled. Where it is not, a Discuss block states a proposal not yet agreed, or an Open block names what still has to be decided. A delivery cannot fail to conform on a point marked Discuss or Open.

```{toctree}
:maxdepth: 2

The glTF Robotics Profile <profile>
```
