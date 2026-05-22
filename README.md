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


cd ~/ros2_lecture_ws
. 0_env.sh
Singularity> . /entrypoint.sh
colcon build --symlink-install
source install/setup.bash


Install OpenCV:

sudo apt update
sudo apt install python3-opencv

Install cv_bridge:

sudo apt install ros-humble-cv-bridge

Install navigation packages:

sudo apt install ros-humble-cv-bridge

Install SLAM toolbox:

sudo apt install ros-humble-slam-toolbox
5. BUILD WORKSPACE
cd ~/ros2_ws

colcon build --symlink-install

source install/setup.bash
6. RUN COMMANDS
TERMINAL 1

Start TurtleBot:

ros2 launch turtlebot3_bringup robot.launch.py
TERMINAL 2

Start camera:

ros2 run your_package fake_robot

OR actual camera node.

TERMINAL 3

Run SLAM:

ros2 launch slam_toolbox online_async_launch.py
TERMINAL 4

Run Navigation2:

ros2 launch nav2_bringup navigation_launch.py
TERMINAL 5

Run your state machine:

ros2 run your_package sm_main
7. VIEW CAMERA DEBUG
rqt_image_view

Select:

/debug_image

You will see:

Person boxes
Lying person label
Detection visualization





Person Detection → OpenCV HOG Detector

This is a machine-learning-based detector, although it's an older classical method rather than a deep neural network.