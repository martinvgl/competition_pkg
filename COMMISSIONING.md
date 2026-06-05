# Commissioning — from scratch

Complete procedure: build the map, then run the mission with the dynamic map.
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
2. Build — [env]:
   ```bash
   colcon build --symlink-install
   source install/setup.bash
   ```
3. Check executables: `ros2 pkg executables competition_pkg`
   (should list `sm_evacuation_node`, `perception_node`, `obstacle_mapper`).
4. Create the maps folder: `mkdir -p ~/ros2_lecture_ws/maps`

---

## Phase 1 — Build and save the map

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
5. **[env]** Camera: `ros2 run competition_pkg perception_node`
6. **[env]** Dynamic map: `ros2 run competition_pkg obstacle_mapper`
   - Wait for the log `Reference map received: ...`.
7. **[env]** State machine: `ros2 run competition_pkg sm_evacuation_node` then **ENTER**.

---

## Testing the dynamic map

Place a new object (not present during SLAM) on a **free** cell, within LiDAR
range and high enough to cross the scan plane. The `obstacle_mapper` terminal
prints `New obstacle at world (...)`, and the cell turns into an obstacle on
`/updated_map` in RViz.
