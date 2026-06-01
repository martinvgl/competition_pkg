# competition_pkg

Autonomous evacuation/rescue robot for the TurtleBot3, built on a YASMIN state
machine, with an added **dynamic obstacle map** feature.

The robot explores the environment with its camera, looks for a person, and
navigates to the evacuation point. In parallel, a dedicated node compares the
live LiDAR against a pre-built reference map and flags obstacles that were not
there during mapping.

## Nodes

- **`sm`** — the mission state machine (`Follow` -> `Navigation`). `Follow`
  uses the camera to search the environment (person / green exit / red
  obstacle) and stops on a person; `Navigation` sends a Nav2 goal to the
  evacuation point.
- **`fakerobot`** — a camera stub used for testing without the real robot. It
  publishes a dummy image on `image_raw` and prints the `cmd_vel` it receives.
  With the stub, no real detection happens (the image is blank).
- **`obstacle_mapper`** — the dynamic obstacle map. A standalone node that runs
  alongside the state machine and only observes: it never sends motion commands.

## Dynamic obstacle map

`obstacle_mapper` loads the reference map once from `/map`, then continuously
compares each LiDAR point (`/scan`) against it, using the robot pose (`/odom`)
to place points on the grid. When a point lands on a cell that was **free** in
the reference, the cell is marked as an obstacle in a dynamic copy of the map.
The dynamic map is published on `/updated_map` (1 Hz), and each newly detected
obstacle triggers an alert on `/new_obstacle`.

It is fully decoupled from the state machine, so it can be tested on its own
with just the robot bringup and the navigation stack running.

### Topics

| Direction | Topic           | Type                      |
| --------- | --------------- | ------------------------- |
| Sub       | `/map`          | `nav_msgs/OccupancyGrid`  |
| Sub       | `/scan`         | `sensor_msgs/LaserScan`   |
| Sub       | `/odom`         | `nav_msgs/Odometry`       |
| Pub       | `/updated_map`  | `nav_msgs/OccupancyGrid`  |
| Pub       | `/new_obstacle` | `std_msgs/String`         |

## Build

From the workspace, inside the configured environment:

```bash
colcon build --symlink-install
source install/setup.bash
```

## Run

Each node runs in its own terminal (environment sourced):

```bash
ros2 run competition_pkg fakerobot          # camera stub (or use the real camera)
ros2 run competition_pkg obstacle_mapper    # dynamic obstacle map
ros2 run competition_pkg sm                 # mission state machine (press ENTER)
```

The mission needs the TurtleBot3 bringup and `turtlebot3_navigation2` (with a
saved map) running first. The dynamic obstacle map needs a reference map on
`/map`, which `turtlebot3_navigation2` provides.

## Useful commands

```bash
ros2 pkg executables competition_pkg        # check entry points
ros2 topic hz /updated_map                  # dynamic map publishing (~1 Hz)
ros2 topic echo /new_obstacle               # new-obstacle alerts
ros2 run yasmin_viewer yasmin_viewer_node   # state machine viewer (http://localhost:8080)
rqt_image_view                              # camera debug image (/debug_image)
```

In RViz, add a **Map** display on `/updated_map` (next to `/map`) to see the
newly detected obstacles overlaid on the reference map.

## Full setup

For the complete step-by-step commissioning (mapping the area, then running the
mission), see `MISE_EN_SERVICE.md`.
