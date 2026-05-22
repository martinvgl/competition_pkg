# Evacuation Robot

## Test Ready Version

This version has been tested on the TurtleBot successfully. Files can be added to this version to test features.

---

## Architecture

### Detection Flow

\```
SEARCHES environment
    ↓
Avoids RED obstacles
    ↓
Moves toward GREEN exit
    ↓
Detects PERSON
    ↓
Stops
    ↓
Checks lying/standing
    ↓
Navigates to evacuation point
\```

### Mission Flow

\```
MISSION START
      ↓
Search for GREEN exit marker
      ↓
Move toward GREEN
      ↓
While moving:
    • Look for PERSONS
    • Look for RED obstacles
      ↓
If PERSON found:
    • Mark location
    • Continue mission
If RED found:
    • Avoid obstacle
    • Continue mission
If GREEN reached:
    • Scan surroundings
    • Find next GREEN
    • Continue mission
      ↓
Repeat until final exit
\```

---

## Setup

### Environment

\```bash
cd ~/ros2_lecture_ws
. 0_env.sh
Singularity> . /entrypoint.sh
colcon build --symlink-install
source install/setup.bash
\```

### Install Dependencies

\```bash
# Install OpenCV
sudo apt update
sudo apt install python3-opencv

# Install cv_bridge
sudo apt install ros-humble-cv-bridge

# Install navigation packages
sudo apt install ros-humble-cv-bridge

# Install SLAM toolbox
sudo apt install ros-humble-slam-toolbox
\```

### 5. Build Workspace

\```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
\```

---

## 6. Run Commands

### Terminal 1 — Start TurtleBot
\```bash
ros2 launch turtlebot3_bringup robot.launch.py
\```

### Terminal 2 — Start Camera
\```bash
ros2 run your_package fake_robot
# OR actual camera node
\```

### Terminal 3 — Run SLAM
\```bash
ros2 launch slam_toolbox online_async_launch.py
\```

### Terminal 4 — Run Navigation2
\```bash
ros2 launch nav2_bringup navigation_launch.py
\```

### Terminal 5 — Run State Machine
\```bash
ros2 run your_package sm_main
\```

---

## 7. View Camera Debug

\```bash
rqt_image_view
\```

Select `/debug_image`. You will see:
- Person boxes
- Lying person label
- Detection visualization

---

## Person Detection → OpenCV HOG Detector

This is a machine-learning-based detector, although it's an older classical method rather than a deep neural network.
