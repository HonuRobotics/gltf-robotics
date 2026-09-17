# Coordinate Frames: glTF, Gazebo and ROS - Take 2

Start over with an incremental build up of the understanding and explanation of how these coordinate systems are use.

Use tools/maritime-workspace/notes/glTF_Gazebo_ROS_Coordinates.md as background.

##  Objective

The purpose of this document is to be a clear explanation of of coordinate frames can be conceptualized and labeled from 3D graphics (authoring 3D assets in Blender) to robotic simulation (rendering visual assets aligned with collision models in Gazebo and RVIZ).

## Coordinate Conventions and Typical Practices

Here we clearly describe some of they usual conventions.   The reason is that there are multiple conventions across muliple communities and fields.

Origin vs coordinate frame:   The using of these terms can be confusing. % CLAUDE: Any definitions from either community?  Are they synonymous?  Maybe use an existing definition(s) and cite?

### Robotics

There are multiple practices in robotics, so there is not just one convention.  Also, these are soft conventions and there is likely a multitude of practices, good and bad, out in the wild.

% CLAUDE: Here are the categories I can come up with for different types of links.  Key questions to categorize a robotic convention: based on inputs (parents) and children.  All links have zero or one parents and zero, one or multiple childern.   

1) Base link, mobile: No clear parent, many children.
Examples: The root part (body) of flying, driving, walking, swimming robots.   There is not one fixed point of the geometry that interacts with the rest of the objects.  In this case the location of the origin of the base link relative to the geometry of the base object is a stated datum (must be specified) and  stable under design change.  A common convention for land robots is to define the location of the origin as the "axis midpoint projected to the ground".   This must be definined and documented.
2) Base link, fixed or passive: One parent, one or many childrn.  Examples: root part (body) of a manipulator kinematic chain.   There is one point in the geometry that can be considered as the definitive location of the rest of the knematic chain the world.  Unlike the location of the base origin is often fixed - either with an overt fixed joint to something else in the world or just passively (gravity)
3) Intermediate link - one parent, one child
4) End effector - intermediate link with no children


#### Manipulation-centric (robots with static base)

For kinematic chains in manipulation scenarios it is common to define the geometry by defining the object geometry relative to the frame collocated at the joint to the parent.  In this case the location of the CoM is defined relative to this link frame (e.g., ).   In this convestion, frames are are at the axes of rotation.   

Examples: 

- wheel: Origin of the part is placed 
- manipulator arm
    - intermediate link: origin of the part is where it the joint to the previous link in the kinematic chain.
    - base link: origin of the part is where it is located in the world.  Because robot 

#### Mobile-Centric

For a mobile robot (flying, driving, walking, swimming), there is not a *joint* t the parent becuase it moves.   In this case it is common to choose an 


#### % CLAUDE: Other conventions?



### 3D Graphics

Different concept entirely.

The frame (a *pivot* (Maya/Max) or *object origin* (Blender). It's a manipulation handle: the point the object rotates and scales about in the viewport. 

The dominant asset convention is bottom-center on the ground plane, so a prop dropped at z=0 sits on the floor; after that, the natural articulation point (door→hinge, wheel→axle).

Blender even has Set Origin → Origin to Center of Mass (Volume) as a menu item, and it isn't what asset pipelines use.

One more thing worth knowing: the pivot concept doesn't survive into glTF at all. There's no pivot property. Blender's object origin becomes either a node translation or gets baked into the vertices. The manipulation handle is lost; only the frame remains. % CLAUDE:  Explain a bit more. 