# competition_pkg

Emergency evacuation robot for the **TurtleBot3**, built on **ROS 2**, **YASMIN**,
**OpenCV + YOLOv8** and the **Nav2** map server / AMCL.

The robot explores an environment looking for a safe path (green), avoids danger
(red), slows down near people, and drives along the safe path toward the exit.
In parallel, a dedicated node compares the live LiDAR against a pre-built map and
flags obstacles that were not there during mapping.

## Architecture

```
camera ──/image_raw──► perception_node ──/evacuation_status──► sm_evacuation_node
                       (YOLOv8 + color)                              │
                                                                 /cmd_vel
                                                                     │
                                                                     ▼
                                                          TurtleBot3 bringup
                                                          (OpenCR / motors)

/map + /scan ──► obstacle_mapper ──► /updated_map  +  /new_obstacle   (observation only)
```

Perception turns the camera into a single high-level status word. The state
machine decides how to move from that word and drives the robot through
`/cmd_vel`. The obstacle mapper runs alongside, purely observational: it never
sends motion commands.

## Nodes

### `perception_node`

Reads the camera and publishes one status word for the state machine.

- Detects people with **YOLOv8** (`yolov8n.pt`, person class only).
- Detects **red** (danger) and **green** (safe path) with HSV color masks.
- Decision priority each frame: green present -> `safe`; else red present ->
  `danger`; else a person present -> `caution`; else -> `searching`.

| Direction | Topic                | Type                  |
| --------- | -------------------- | --------------------- |
| Sub       | `/image_raw`         | `sensor_msgs/Image`   |
| Pub       | `/evacuation_status` | `std_msgs/String`     |
| Pub       | `/people_count`      | `std_msgs/String`     |

`/evacuation_status` carries one of `safe` / `danger` / `caution` / `searching`.
`/people_count` carries a text line such as `People detected: 2`.

### `sm_evacuation_node`

The mission state machine (YASMIN). It subscribes to `/evacuation_status`,
updates a blackboard, and runs four states that publish velocity commands. Its
progress can be inspected live with the YASMIN viewer.

| Direction | Topic                | Type                  |
| --------- | -------------------- | --------------------- |
| Sub       | `/evacuation_status` | `std_msgs/String`     |
| Pub       | `/cmd_vel`           | `geometry_msgs/Twist` |

`/cmd_vel` is consumed by the TurtleBot3 bringup (OpenCR / motors), started
separately from this package.

#### States

| State         | Entered on  | Behaviour                                            | Exits to |
| ------------- | ----------- | ---------------------------------------------------- | -------- |
| `FOLLOW_SAFE` | start / `searching` | Wobbles forward (0.08 m/s, alternating turn) to search | DANGER / CAUTION / NAVIGATION |
| `NAVIGATION`  | `safe`      | Drives straight at 0.15 m/s while the green path is visible | FOLLOW_SAFE |
| `DANGER`      | `danger`    | Stops and scans/turns to get clear of the red obstacle | FOLLOW_SAFE |
| `CAUTION`     | `caution`   | Stops near the person, scans right then left for a clear route, turns around if blocked | FOLLOW_SAFE |

Each state returns to `FOLLOW_SAFE` once its condition clears, so the machine
loops continuously through the mission.

### `obstacle_mapper`

Standalone node that builds a dynamic map of obstacles that appeared after the
reference map was made. It is fully decoupled from the state machine and only
observes.

- Loads the reference map once from `/map`.
- For each LiDAR scan, looks up the robot pose from **TF2** (`map -> base_link`)
  at the scan timestamp (uses AMCL localisation when available, falls back
  gracefully if TF2 is not ready yet).
- A LiDAR point landing on a cell that was **free** in the reference map marks
  that cell as an obstacle in a dynamic copy of the map.
- Publishes the dynamic map on `/updated_map` (1 Hz) and an alert on
  `/new_obstacle` for each newly detected obstacle.

| Direction | Topic           | Type                      |
| --------- | --------------- | ------------------------- |
| Sub       | `/map`          | `nav_msgs/OccupancyGrid`  |
| Sub       | `/scan`         | `sensor_msgs/LaserScan`   |
| Pub       | `/updated_map`  | `nav_msgs/OccupancyGrid`  |
| Pub       | `/new_obstacle` | `std_msgs/String`         |

## Dependencies

ROS 2 dependencies are declared in `package.xml` (rclpy, the message packages,
`cv_bridge`, `tf2_ros`, `tf2_geometry_msgs`, `turtlebot3_navigation2`, `yasmin`,
`yasmin_viewer`) and can be installed with `rosdep`.

YOLOv8 needs the Python package **ultralytics**, which is not a ROS dependency:

```bash
pip install ultralytics
```

The `yolov8n.pt` weights are downloaded automatically on first run.

## Build

```bash
colcon build --symlink-install
source install/setup.bash
```

## Run

Prerequisites running first:
- TurtleBot3 **bringup** (provides `/scan`, `/odom`, `/tf`, accepts `/cmd_vel`).
- **`turtlebot3_navigation2`** with a saved map (provides `/map` and the
  `map -> base_link` transform via AMCL). Set the initial pose in RViz with
  **2D Pose Estimate** so the obstacle mapper gets a valid pose.
- A **camera** publishing on `/image_raw`.

Then start the package nodes, each in its own sourced terminal:

```bash
ros2 run competition_pkg perception_node
ros2 run competition_pkg obstacle_mapper
ros2 run competition_pkg sm_evacuation_node
```

## Useful commands

```bash
ros2 pkg executables competition_pkg          # list the entry points
ros2 topic echo /evacuation_status            # current perception status word
ros2 topic echo /people_count                 # people detected
ros2 topic echo /new_obstacle                 # new-obstacle alerts
ros2 topic hz /updated_map                    # dynamic map rate (~1 Hz)
ros2 run yasmin_viewer yasmin_viewer_node      # state machine viewer (see node log for URL)
```

In RViz, add a **Map** display on `/updated_map` (next to `/map`) to see the
newly detected obstacles overlaid on the reference map.

To save the dynamic map (with `obstacle_mapper` running):

```bash
ros2 run nav2_map_server map_saver_cli -t /updated_map \
    -f ~/ros2_lecture_ws/maps/updated_map \
    --ros-args -p map_subscribe_transient_local:=false
```
