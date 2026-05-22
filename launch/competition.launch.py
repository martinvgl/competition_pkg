#!/usr/bin/env python3
# -*-encoding:UTF-8-*-

"""
File: competition.launch.py
Author: Kyutech ROS Group

Launch file that starts everything needed to run the Emergency Evacuation Robot:
    1. turtlebot3_navigation2  (provides /map, AMCL, and Nav2 action server)
    2. yasmin_viewer_node      (state machine visualizer at http://localhost:5000)
    3. obstacle_mapper_node    (dynamic map: LiDAR vs reference comparison)
    4. sm_main                 (YASMIN state machine: PATROL + MAPPING)

Usage:
    ros2 launch competition_pkg competition.launch.py
    ros2 launch competition_pkg competition.launch.py map:=/path/to/map.yaml
"""

import os

from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    """Method to generate launch description information

    Returns:
        launch.LaunchDescription: Object containing launch settings
    """

    # ── LaunchConfig: map file path ────────────────────────────────────────
    map_file = LaunchConfiguration(
        variable_name="map",
        # Default: ~/ros2_lecture_ws/map.yaml (matches Sample 2 of the lecture)
        default=os.path.join(
            os.getenv("HOME"),
            "ros2_lecture_ws",
            "map.yaml",
        ),
    )

    # ── LaunchConfig: use_sim_time ─────────────────────────────────────────
    # false = system clock, true = simulation clock (Gazebo)
    use_sim_time = LaunchConfiguration(
        variable_name="use_sim_time",
        default="false",
    )

    # Get path to the turtlebot3_navigation2 launch directory
    nav2_launch_file_dir = os.path.join(
        get_package_share_directory("turtlebot3_navigation2"),
        "launch",
    )

    return LaunchDescription(
        [
            # ── Argument definitions ───────────────────────────────────────
            DeclareLaunchArgument(
                name="map",
                default_value=map_file,
                description="Full path to map file to load",
            ),
            DeclareLaunchArgument(
                name="use_sim_time",
                default_value="false",
                description="Use simulation (Gazebo) clock if true",
            ),

            # ── 1. Nav2 + map_server + AMCL ───────────────────────────────
            IncludeLaunchDescription(
                launch_description_source=PythonLaunchDescriptionSource(
                    os.path.join(
                        nav2_launch_file_dir,
                        "navigation2.launch.py",
                    )
                ),
                launch_arguments={
                    "map": map_file,
                    "use_sim_time": use_sim_time,
                }.items(),
            ),

            # ── 2. YASMIN Viewer ──────────────────────────────────────────
            Node(
                package="yasmin_viewer",
                executable="yasmin_viewer_node",
                name="yasmin_viewer_node",
                parameters=[{"use_sim_time": use_sim_time}],
                output="screen",
            ),

            # ── 3. Obstacle mapper ────────────────────────────────────────
            Node(
                package="competition_pkg",
                executable="obstacle_mapper",
                name="obstacle_mapper_node",
                parameters=[{"use_sim_time": use_sim_time}],
                output="screen",
            ),

            # ── 4. State machine main ─────────────────────────────────────
            Node(
                package="competition_pkg",
                executable="sm_main",
                name="sm_main",
                parameters=[{"use_sim_time": use_sim_time}],
                output="screen",
                # Required so the input() prompt in sm_main works correctly
                # (without this, the SM blocks waiting on stdin invisibly)
                emulate_tty=True,
            ),
        ]
    )
