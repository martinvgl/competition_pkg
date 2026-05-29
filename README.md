# Emergency Evacuation Robot — competition_pkg

> Practicum in Robot Operating System (ROS) — Kyutech
> TurtleBot3 · ROS 2 · Nav2 · YASMIN

## TO BE TESTED ##

This module implements the **real-time map updating** feature of the Emergency Evacuation Robot project: the robot patrols a known environment and detects geometric changes (new obstacles, debris) by comparing live LiDAR scans against a pre-built reference map. When a change is detected, the robot stops, rotates 360° to scan the obstacle in full, then resumes patrol.

Other features of the global project (person detection, color path semantics, survivor guidance) are developed in parallel by other team members and not covered by this module.

---

## Table of Contents

- [State Machine](#state-machine)
- [Architecture](#architecture)
- [Nodes & Topics](#nodes--topics)
- [Requirements](#requirements)
- [Installation](#installation)
- [Step 1 — Network Setup](#step-1--network-setup)
- [Step 2 — Mapping](#step-2--mapping)
- [Step 3 — Run the Robot](#step-3--run-the-robot)
- [Useful Commands](#useful-commands)
- [Package Structure](#package-structure)
- [Known Limitations](#known-limitations)

---

## State Machine

```
        ┌─────────┐  patrol   ┌─────────┐
        │ PATROL  │──────────►│ PATROL  │  (next waypoint)
        └─────────┘           └─────────┘
             │
             │ detected (alert received on /new_obstacle)
             ▼
        ┌─────────┐
        │ MAPPING │  ← stops, rotates 360° so the mapper
        └─────────┘    captures the full obstacle
             │
             │ mapped
             ▼
        (back to PATROL)
```

`PatrolState` outcomes: `"patrol"` (waypoint reached, continue) · `"detected"` (new obstacle, switch to mapping).
`MappingState` outcomes: `"mapped"` (scan complete, return to patrol).

---

## Architecture

```
/map   (reference, from map_server) ──┐
/scan  (LiDAR)                      ──┼──► obstacle_mapper_node ──► /updated_map
/odom  (robot pose)                 ──┘                          └──► /new_obstacle
                                                                          │
                                                                          ▼
                                                                     PatrolState
                                                                (triggers MAPPING)
```

### How the dynamic map works

1. At startup, `obstacle_mapper_node` receives the reference map on `/map` once and keeps a deep copy in memory as the dynamic map.
2. At every LiDAR scan, each ray is projected into map coordinates using the robot's pose from `/odom`.
3. If the projected point lands on a cell that was **free** in the reference map (value `< 20`) but is now hit by the LiDAR, the cell is marked as an obstacle (value `100`) in the dynamic map.
4. The dynamic map is republished on `/updated_map` at 1 Hz — RViz and other subscribers see updates live.
5. A spatial anti-duplicate filter (15 cm radius) prevents the same obstacle from triggering multiple alerts on `/new_obstacle`.

---

## Nodes & Topics

### Nodes

| Node name | Source file | Role |
|---|---|---|
| `obstacle_mapper_node` | `obstacle_mapper_node.py` | Continuously compares LiDAR data against the reference map and publishes a dynamic map + alerts. |

The state machine (`PatrolState` + `MappingState`) runs inside a separate node that hosts YASMIN. *(Entry-point file to be added — see Known Limitations.)*

### Topics

| Topic | Type | Direction | Description |
|---|---|---|---|
| `/map` | `nav_msgs/OccupancyGrid` | in (mapper) | Reference map, published once by `map_server`. |
| `/scan` | `sensor_msgs/LaserScan` | in (mapper) | LiDAR data. |
| `/odom` | `nav_msgs/Odometry` | in (mapper) | Robot pose. |
| `/updated_map` | `nav_msgs/OccupancyGrid` | out (mapper) | Dynamic map with newly detected obstacles, republished at 1 Hz. |
| `/new_obstacle` | `std_msgs/String` | out (mapper) → in (`PatrolState`) | Text alert with the (x, y) position of each newly detected obstacle. |
| `/cmd_vel` | `geometry_msgs/Twist` | out (`MappingState`) | Velocity command for the 360° rotation during mapping. |
| `/navigate_to_pose` | `nav2_msgs/action/NavigateToPose` | action client (`PatrolState`) | Nav2 action for waypoint navigation. |

---

## Requirements

- ROS 2 (Humble or Iron)
- TurtleBot3 Burger
- Nav2 (`turtlebot3_navigation2`)
- YASMIN (`pip install yasmin`)
- `tf_transformations`

---

## Installation

```bash
# Clone into your workspace
cd ~/ros2_lecture_ws/src/7_lectures
git clone https://github.com/martinvgl/competition_pkg.git

# Build
cd ~/ros2_lecture_ws
colcon build --symlink-install --packages-select competition_pkg

# Source
source install/setup.bash
```

---

## Step 1 — Network Setup

Run these commands **on both the Remote PC and the Raspberry Pi** before anything else.

```bash
export ROS_DOMAIN_ID=30
export TURTLEBOT3_MODEL=burger
```

To make it permanent:

```bash
echo "export ROS_DOMAIN_ID=30" >> ~/.bashrc
echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc
source ~/.bashrc
```

Connect to the robot via SSH:

```bash
ssh ubuntu@<ROBOT_IP>
```

---

## Step 2 — Mapping

> Do this **once** before running the robot. The reference map must be obstacle-free (no debris that you'll later use to trigger detection).

### Launch the virtual environment (lab setup)

```bash
cd ~/ros2_lecture_ws
. 0_env.sh
. /entrypoint.sh
```

### On the Raspberry Pi — start the robot

```bash
ros2 launch turtlebot3_bringup robot.launch.py
```

### On the Remote PC — start SLAM

```bash
ros2 launch turtlebot3_cartographer cartographer.launch.py
```

RViz opens automatically and you can see the map being built in real time.

### Teleoperate to build the map

```bash
ros2 run turtlebot3_teleop teleop_keyboard
```

| Key | Action |
|---|---|
| `w` | Forward |
| `x` | Backward |
| `a` | Turn left |
| `d` | Turn right |
| `s` | Stop |

> Go slowly (max 0.1 m/s). Cover the whole patrol area, ideally with 2 full loops.

### Save the map

```bash
ros2 run nav2_map_server map_saver_cli -f ~/ros2_lecture_ws/map
```

Creates `map.pgm` and `map.yaml`.

### Record waypoint coordinates

Teleop the robot to each patrol corner and note the coordinates:

```bash
ros2 topic echo /odom --once
```

Note `pose.pose.position.x` and `pose.pose.position.y`, then update the `WAYPOINTS` list at the top of `patrol.py`:

```python
WAYPOINTS = [
    {"x": 0.0, "y": 0.0,  "yaw": 0.0},
    {"x": 2.0, "y": 0.0,  "yaw": 1.5708},
    # ...
]
```

---

## Step 3 — Run the Robot

The robot needs three things running together:

1. **`turtlebot3_navigation2`** — provides `map_server` (publishes `/map`), AMCL, and the Nav2 action server `/navigate_to_pose` that `PatrolState` calls.
2. **`obstacle_mapper_node`** — the dynamic map node.
3. **The state machine node** — hosts `PatrolState` and `MappingState`.

### On the Raspberry Pi

```bash
ros2 launch turtlebot3_bringup robot.launch.py
```

### On the Remote PC

Launch Nav2 with the saved map:

```bash
ros2 launch turtlebot3_navigation2 navigation2.launch.py \
    map:=$HOME/ros2_lecture_ws/map.yaml
```

In a second terminal, launch the obstacle mapper:

```bash
ros2 run competition_pkg obstacle_mapper
```

In a third terminal, launch the YASMIN viewer (optional but useful for debugging):

```bash
ros2 run yasmin_viewer yasmin_viewer_node
```

Then open `http://localhost:5000` in a browser, set Layout to "grid".

In a fourth terminal, launch the state machine node (entry-point name TBD — see [Known Limitations](#known-limitations)).

> A single combined launch file will be added later so all four can be started with one command.

---

## Useful Commands

### Monitor the robot

```bash
# New obstacle alerts
ros2 topic echo /new_obstacle

# LiDAR data
ros2 topic echo /scan

# Robot pose
ros2 topic echo /odom --once

# Dynamic map metadata
ros2 topic echo /updated_map --field info.width --field info.height
```

### Visualize in RViz

```bash
ros2 run rviz2 rviz2
```

Suggested displays:
- `Map` → `/map` (reference, grey)
- `Map` → `/updated_map` (dynamic — use a different color scheme to distinguish from the reference)
- `LaserScan` → `/scan`
- `RobotModel`
- `TF`

### Manually trigger a detection (testing without a physical obstacle)

```bash
ros2 topic pub --once /new_obstacle std_msgs/String "data: '[TEST] x=1.0, y=1.0'"
```

`PatrolState` should transition to `MAPPING` and the robot should rotate 360°.

### Build after changes

```bash
cd ~/ros2_lecture_ws
colcon build --symlink-install --packages-select competition_pkg
source install/setup.bash
```

With `--symlink-install`, Python file changes apply immediately without rebuilding.

### Inspect the ROS graph

```bash
ros2 topic list
ros2 node list
rqt_graph
```

---

## Package Structure

```
competition_pkg/
├── competition_pkg/
│   ├── obstacle_mapper_node.py   # Dynamic map update (LiDAR vs reference)
│   └── states/
│       ├── patrol.py             # Autonomous waypoint navigation
│       └── mapping.py            # 360° scan triggered by /new_obstacle
├── setup.py                      # Package configuration
├── package.xml                   # ROS 2 dependencies
└── README.md
```

---

## Known Limitations

- **State machine entry-point file:** the file that instantiates `PatrolState` + `MappingState` inside a YASMIN `StateMachine` is not yet written. Until it is, the states cannot be launched as a complete behavior — only individually for unit testing.
- **Launch file:** no combined launch file yet; the four processes (Nav2, mapper, YASMIN viewer, state machine) must be started in separate terminals.
- **Cumulative map:** once a cell is marked as an obstacle in `/updated_map`, it stays marked even if the obstacle is physically removed during the mission. This matches the post-disaster scenario but means the map only grows.
- **Pose source:** robot pose comes from `/odom` (wheel odometry). On short patrols this is reliable; on longer runs, switching to `/amcl_pose` would reduce drift.
- **MAPPING duration:** ~21 s at 0.3 rad/s for the full rotation — adjust angular velocity in `mapping.py` if needed.

---

*Lab collaboration — Kyutech*
