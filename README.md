# Emergency Evacuation Robot — competition_pkg

> Practicum in Robot Operating System (ROS) — Tamukoh Laboratory, Kyutech
> TurtleBot3 · ROS 2 · Nav2 · YASMIN

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Step 1 — Network Setup](#step-1--network-setup)
- [Step 2 — Mapping](#step-2--mapping)
- [Step 3 — Run the Robot](#step-3--run-the-robot)
- [Useful Commands](#useful-commands)
- [Package Structure](#package-structure)
- [Team](#team)

---

## Overview

This robot patrols autonomously in a known environment and detects geometric changes in real time by comparing live LiDAR scans against a pre-built reference map. When a new obstacle is detected — for example, debris from a disaster — the robot stops, performs a 360° scan to map the obstacle completely, then resumes patrol with an updated dynamic map.

**Current scope (this module):** real-time map updating + patrol with obstacle-triggered scanning. Other features of the global Emergency Evacuation Robot system (person detection, color path semantics, survivor guidance) are developed in parallel by other team members.

### State Machine

```
        ┌─────────┐   patrol    ┌─────────┐
        │  PATROL │────────────►│  PATROL │  (next waypoint)
        └─────────┘             └─────────┘
             │
             │ detected (/new_obstacle received)
             ▼
        ┌─────────┐
        │ MAPPING │  ← stops, rotates 360°, lets the mapper
        └─────────┘    capture the full obstacle
             │
             │ mapped
             ▼
        (back to PATROL)
```

---

## Architecture

For the dynamic map:

```
/map   (reference)   ──┐
/scan  (LiDAR)       ──┼──► obstacle_mapper_node ──► /updated_map
/odom  (position)    ──┘                          └──► /new_obstacle
                                                            │
                                                            ▼
                                                       patrol.py
                                                  (triggers MAPPING state)
```

### How the dynamic map works

1. At startup, `obstacle_mapper_node` receives the reference map on `/map` once and keeps an in-memory copy as the dynamic map.
2. At every LiDAR scan, each ray is projected into map coordinates using the robot's pose.
3. If the projected point lands on a cell that was **free** in the reference map but is now hit by the LiDAR, the cell is marked as an obstacle (value `100`) in the dynamic map.
4. The dynamic map is republished on `/updated_map` at 1 Hz — RViz and other subscribers see the updates live.
5. A spatial anti-duplicate filter (15 cm radius) prevents the same obstacle from triggering multiple alerts on `/new_obstacle`.

### Nodes & Topics

| Node | Executable | Role |
|---|---|---|
| `guard_robot_main` | `guard_robot` | State machine (YASMIN) — patrol + mapping |
| `obstacle_mapper_node` | `obstacle_mapper` | Dynamic map update from LiDAR vs reference |

| Topic | Type | Direction | Description |
|---|---|---|---|
| `/map` | `nav_msgs/OccupancyGrid` | in | Reference map (fixed, from map_server) |
| `/scan` | `sensor_msgs/LaserScan` | in | LiDAR data |
| `/odom` | `nav_msgs/Odometry` | in | Robot position |
| `/updated_map` | `nav_msgs/OccupancyGrid` | out | Dynamic map with new obstacles |
| `/new_obstacle` | `std_msgs/String` | out | Alert with obstacle position |
| `/cmd_vel` | `geometry_msgs/Twist` | out | Robot velocity commands (rotation in MAPPING state) |

---

## Requirements

- ROS 2 (Humble or Iron)
- TurtleBot3 Burger
- Nav2
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

To make it permanent, add to `~/.bashrc`:

```bash
echo "export ROS_DOMAIN_ID=30" >> ~/.bashrc
echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc
source ~/.bashrc
```

**Connect to the robot via SSH:**

```bash
ssh ubuntu@<ROBOT_IP>
```

---

## Step 2 — Mapping

> Do this **once** before running the robot. The map must be obstacle-free (no debris that you'll later use to trigger detection).

### Launch the virtual environment (required by the lab)

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

RViz opens automatically — you'll see the map being built in real time.

### On the Remote PC — teleoperate to build the map

```bash
ros2 run turtlebot3_teleop teleop_keyboard
```

| Key | Action |
|---|---|
| `w` | Move forward |
| `x` | Move backward |
| `a` | Turn left |
| `d` | Turn right |
| `s` | Stop |

> **Tips:** Go slowly (max 0.1 m/s). Cover the entire patrol area. At least 2 full loops give a clean map.

### Save the map

Once the map looks good in RViz:

```bash
ros2 run nav2_map_server map_saver_cli -f ~/ros2_lecture_ws/map
```

This creates two files:
- `map.pgm` — the map image
- `map.yaml` — metadata (resolution, origin)

### Record waypoint coordinates

Teleoperate the robot to each patrol corner and note the coordinates:

```bash
ros2 topic echo /odom --once
```

Note `pose.pose.position.x` and `pose.pose.position.y`, then update the `WAYPOINTS` list at the top of `competition_pkg/states/patrol.py`:

```python
WAYPOINTS = [
    {"x": 0.0, "y": 0.0,  "yaw": 0.0},
    {"x": 2.0, "y": 0.0,  "yaw": 1.5708},
    # ...
]
```

---

## Step 3 — Run the Robot

### On the Raspberry Pi

```bash
ros2 launch turtlebot3_bringup robot.launch.py
```

### On the Remote PC

```bash
ros2 launch competition_pkg guard_robot.launch.py
```

This launches automatically:
- `turtlebot3_navigation2` with the saved map (AMCL + Nav2)
- `yasmin_viewer_node` — state machine visualizer (browser at `http://localhost:5000`)
- `obstacle_mapper_node` — dynamic map publisher
- `guard_robot_main` — state machine entry point

**Press Enter in the terminal to start the robot.**

### Custom map path (optional)

```bash
ros2 launch competition_pkg guard_robot.launch.py map:=/path/to/your/map.yaml
```

---

## Useful Commands

### Monitor the robot

```bash
# New obstacle alerts (text)
ros2 topic echo /new_obstacle

# LiDAR data
ros2 topic echo /scan

# Robot position
ros2 topic echo /odom --once

# Dynamic map metadata
ros2 topic echo /updated_map --field info.width --field info.height
```

### Visualize in RViz

```bash
ros2 run rviz2 rviz2
```

Suggested displays:
- `Map` → topic `/map` (reference, grey)
- `Map` → topic `/updated_map` (dynamic, new obstacles in black) — set a different color scheme to distinguish from reference
- `LaserScan` → topic `/scan`
- `RobotModel`
- `TF`

### View the state machine

Open your browser at: `http://localhost:5000` (YASMIN Viewer). Set Layout to "grid".

### Manually trigger a detection (for testing without a physical obstacle)

```bash
ros2 topic pub --once /new_obstacle std_msgs/String "data: '[TEST] x=1.0, y=1.0'"
```

The state machine should transition `PATROL → MAPPING` and the robot should rotate 360°.

### Build after changes

```bash
cd ~/ros2_lecture_ws
colcon build --symlink-install --packages-select competition_pkg
source install/setup.bash
```

> With `--symlink-install`, Python file changes are applied immediately without rebuilding.

### Inspect ROS graph

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
│   ├── guard_robot_main.py       # YASMIN state machine entry point
│   ├── obstacle_mapper_node.py   # Dynamic map update (LiDAR vs reference)
│   └── states/
│       ├── patrol.py             # Autonomous waypoint navigation
│       └── mapping.py            # 360° scan triggered by /new_obstacle
├── launch/
│   └── guard_robot.launch.py     # Main launch file
├── setup.py                      # Package configuration
├── package.xml                   # ROS 2 dependencies
└── README.md
```

---

## Known Limitations

- The dynamic map is **cumulative**: a cell marked as obstacle stays marked, even if the obstacle is physically removed during the mission. This matches the post-disaster scenario (debris doesn't vanish).
- Robot pose comes from `/odom` (wheel odometry). On short patrols this is reliable; on longer runs, switching to `/amcl_pose` would reduce drift.
- The `MAPPING` state rotates for ~21 s at 0.3 rad/s — adjust angular velocity in `mapping.py` if needed.

---

## Team

| Member | Role | Files |
|---|---|---|
| TBD | Real-time mapping + patrol SM | `obstacle_mapper_node.py`, `patrol.py`, `mapping.py` |

---

*Lab collaboration — Kyutech · Tamukoh Laboratory*
