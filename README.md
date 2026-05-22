# Evacuation Robot — competition_pkg

> Practicum in Robot Operating System (ROS) — Tamukoh Laboratory, Kyutech  
> TurtleBot3 · ROS 2 · Nav2 · YASMIN · OpenCV

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

This robot patrols autonomously in a known environment.  


### State Machine



## Architecture


For the dynamic map:
```
/map   (reference) ──┐
/scan  (LiDAR)     ──┼──► obstacle_mapper_node ──► /updated_map
/odom  (position)  ──┘                         └──► /new_obstacle
                                                         │
                                                    patrol.py
                                                    (triggers Mapping state)
```

### Nodes & Topics

#### Dynamic Map ####
| Node | Executable | Role |
|---|---|---|
| `guard_robot_main` | `guard_robot` | State machine (YASMIN) |
| `obstacle_mapper_node` | `obstacle_mapper` | Dynamic map update |

| Topic | Type | Description |
|---|---|---|
| `/map` | `OccupancyGrid` | Reference map (fixed) |
| `/updated_map` | `OccupancyGrid` | Dynamic map with new obstacles |
| `/new_obstacle` | `String` | Alert with obstacle position |
| `/scan` | `LaserScan` | LiDAR data |
| `/cmd_vel` | `Twist` | Robot velocity commands |
| `/alert` | `String` | General alert messages |
| `/buzzer` | `Bool` | Buzzer command (OpenCR) |

---

## Requirements

- ROS 2 (Humble or Iron)
- TurtleBot3 Burger
- Nav2
- YASMIN (`pip install yasmin`)
- OpenCV (`pip install opencv-python`)
- cv_bridge
- tf_transformations

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
# Set ROS domain (same value on both machines)
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

> Do this **once** before running the robot. The map must be obstacle-free.

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

RViz opens automatically. You will see the map being built in real time.

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

> **Tips:** Go slowly (max 0.1 m/s). Cover the entire patrol area. Do at least 2 full loops for a clean map.

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

Note `pose.pose.position.x` and `pose.pose.position.y`, then update the `WAYPOINTS` list in `competition_pkg/states/patrol.py`.

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
- `turtlebot3_navigation2` with the saved map
- `yasmin_viewer_node` (state machine visualizer)
- `obstacle_mapper_node` (dynamic map)
- `guard_robot_main` (state machine)

**Press Enter in the terminal to start the robot.**

### Custom map path (optional)

```bash
ros2 launch competition_pkg guard_robot.launch.py map:=/path/to/your/map.yaml
```

---

## Useful Commands

### Monitor the robot

```bash
# Current state machine state
ros2 topic echo /state

# New obstacle alerts
ros2 topic echo /new_obstacle

# General alerts
ros2 topic echo /alert

# LiDAR data
ros2 topic echo /scan

# Robot position
ros2 topic echo /odom --once
```

### Visualize in RViz

```bash
ros2 run rviz2 rviz2
```

Add these displays in RViz:
- `Map` → topic `/map` (reference, grey)
- `Map` → topic `/updated_map` (dynamic, shows new obstacles in black)
- `LaserScan` → topic `/scan`
- `RobotModel`

### View camera feed

```bash
ros2 run rqt_image_view rqt_image_view /detection_image
```

### View state machine (YASMIN Viewer)

Open your browser at: `http://localhost:5000`

### Manually trigger a detection (for testing)

```bash
# Simulate a new obstacle alert
ros2 topic pub --once /new_obstacle std_msgs/String "data: '[TEST] x=1.0, y=1.0'"

# Simulate a person detection
ros2 topic pub --once /detection_status std_msgs/String "data: 'person'"
```

### Build after changes

```bash
cd ~/ros2_lecture_ws
colcon build --symlink-install --packages-select competition_pkg
source install/setup.bash
```

> 💡 With `--symlink-install`, Python file changes are applied immediately without rebuilding.

### Check topic list

```bash
ros2 topic list
```

### Check node list

```bash
ros2 node list
```

---

## Package Structure

```
competition_pkg/
├── competition_pkg/
│   ├── guard_robot_main.py       # Main node — YASMIN state machine
│   ├── obstacle_mapper_node.py   # Dynamic map update (LiDAR vs reference)
│   └── states/
│       ├── patrol.py             # Autonomous waypoint navigation
│       ├── mapping.py            # 360° scan on new obstacle
│       ├── detection.py          # Person detection (HOG / OpenCV)
│       ├── alert.py              # Buzzer + alert publication
│       ├── track.py              # Visual tracking of detected person
│       └── return_base.py        # Return to base (NavigateToPose)
├── launch/
│   └── guard_robot.launch.py     # Main launch file
├── setup.py                      # Package configuration
├── package.xml                   # ROS 2 dependencies
└── README.md
```

---

## Team

| Member | Role | File |
|---|---|---|


---

*Lab collaboration — Kyutech*


* FOG parkinson's disease *
* Shibata Lab *
