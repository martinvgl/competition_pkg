# Commissioning — from scratch

Complete procedure for the autonomous evacuation robot: build the reference map,
then run the full mission (perception, state machine, dynamic obstacle map).
Course method (Cartographer + `turtlebot3_navigation2`).

## Environment setup — in every `ros2` terminal

```bash
cd ~/ros2_lecture_ws
. 0_env.sh
. /entrypoint.sh
. 4a_turtlebot3_settings.sh
source install/setup.bash
```

Passwords: `turtlebot3_mode` -> `r0s1ecture` ; SSH robot -> `turtlebot`.
**[robot]** terminals (time sync, SSH) run without the environment.

---

## Phase 0 — Setup (once only)

1. Place the package: `mv competition_pkg ~/ros2_lecture_ws/src/`
2. Install the YOLOv8 dependency (not a ROS package):
   ```bash
   pip install ultralytics
   ```
   The `yolov8n.pt` weights are downloaded automatically on the first run of
   `perception_node`.
3. Build — [env]:
   ```bash
   colcon build --symlink-install
   source install/setup.bash
   ```
4. Check executables: `ros2 pkg executables competition_pkg`
   (should list `sm_evacuation_node`, `perception_node`, `obstacle_mapper`).
5. Create the maps folder: `mkdir -p ~/ros2_lecture_ws/maps`

---

## Phase 1 — Build and save the reference map

The reference map must be built in the **clean environment** — no temporary
obstacles. This is the baseline the dynamic map will compare against.

1. **[robot]** Time sync: `turtlebot3_mode`
2. **[robot]** Robot:
   ```bash
   ssh -YC turtle@192.168.11.2
   ros2 launch ros2_lecture bringup.launch.py
   ```
3. **[env]** SLAM: `ros2 launch turtlebot3_cartographer cartographer.launch.py`
4. **[env]** RViz: `rviz2`
   - Fixed Frame = `map`, add **Map** display on `/map`, **LaserScan** on `/scan`.
5. **[env]** Teleop: `ros2 run turtlebot3_teleop teleop_keyboard`
   - Drive **slowly** (A W S X D) to cover the entire area.
   - **Note the robot's starting position.**
6. **[env]** Save the map (Cartographer still running):
   ```bash
   ros2 run nav2_map_server map_saver_cli -f ~/ros2_lecture_ws/maps/competition_map
   ```
7. `Ctrl+C` on Cartographer, teleop and bringup.

---

## Phase 2 — Mission

1. **[robot]** Time sync: `turtlebot3_mode` (keep running).
2. **[robot]** Robot:
   ```bash
   ssh -YC turtle@192.168.11.2
   ros2 launch ros2_lecture bringup.launch.py
   ```
   - **Start the robot at the starting position noted in Phase 1.**
3. **[env]** Localisation + navigation (opens RViz):
   ```bash
   ros2 launch turtlebot3_navigation2 navigation2.launch.py \
       map:=$HOME/ros2_lecture_ws/maps/competition_map.yaml
   ```
4. **RViz**:
   - Fixed Frame = `map`.
   - **2D Pose Estimate** tool: click the robot's actual position and drag
     in the direction it is facing.
   - Add a **Map** display on `/updated_map`.
5. **[env]** Perception: `ros2 run competition_pkg perception_node`
   - Requires `/image_raw` published by the robot bringup (camera).
6. **[env]** Dynamic map: `ros2 run competition_pkg obstacle_mapper`
   - Wait for the log `Reference map received: ...`.
7. **[env]** State machine: `ros2 run competition_pkg sm_evacuation_node` then **ENTER**.

---

## Physical setup for the mission

Place the following in the environment before starting the mission:

- **Green signs / tape** on the floor or walls along the safe path. The robot
  follows the green path and drives toward the exit (`NAVIGATION` state).
- **Red signs** in restricted or dangerous areas. The robot stops and rotates
  to get clear (`DANGER` state).
- **A person** somewhere in the environment. The robot slows down and scans for
  an alternative route when a person is detected (`CAUTION` state).
- **New obstacles** (not present during mapping) to trigger the dynamic map.
  Place them in open, free-space areas away from walls.

---

## Testing each feature

### Perception

In a sourced terminal, monitor the status word published by `perception_node`:

```bash
ros2 topic echo /evacuation_status     # safe / danger / caution / searching
ros2 topic echo /people_count          # "People detected: N"
```

Show each sign to the camera in turn and confirm the correct status word appears.

### State machine

Open the YASMIN viewer to watch state transitions in real time:

```bash
ros2 run yasmin_viewer yasmin_viewer_node
```

Then open the URL printed in the terminal (typically `http://localhost:5000`).
Verify that showing a green sign triggers `NAVIGATION`, a red sign triggers
`DANGER`, and a person triggers `CAUTION`.

### Dynamic obstacle map

Place a new object (not present during SLAM) on a **free** cell, within LiDAR
range and high enough to cross the scan plane. The `obstacle_mapper` terminal
prints `New obstacle at world (...)`, and the cell turns into an obstacle on
`/updated_map` in RViz.

To save the updated map at any point:

```bash
ros2 run nav2_map_server map_saver_cli -t /updated_map \
    -f ~/ros2_lecture_ws/maps/updated_map \
    --ros-args -p map_subscribe_transient_local:=false
```
