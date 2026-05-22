#!/usr/bin/env python3
# -*-encoding:UTF-8-*-

"""
File: states/mapping.py
Author: Kyutech ROS Group

MappingState — le robot s'arrête, tourne sur lui-même pour scanner
l'obstacle complet, puis met à jour la carte dynamique.

Outcomes :
  "mapped"  → obstacle scanné et ajouté à la carte dynamique
"""

# Import external modules
import math

# Import modules (ROS2 related)
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from geometry_msgs.msg import Twist

# Import modules (YASMIN related)
from yasmin import State
from yasmin import Blackboard


class MappingState(State):
    """MappingState class (inherits from State class)
    Stops the robot and performs a 360° scan to map new obstacles
    """

    def __init__(self, node: Node):
        """Class initialization method"""
        super().__init__(outcomes=["mapped"])

        self.node = node

        self.vel_pub = self.node.create_publisher(
            msg_type=Twist, topic="cmd_vel", qos_profile=10
        )

    def execute(self, blackboard: Blackboard) -> str:
        """Mapping state execution method

        Args:
            blackboard (Blackboard): Shared blackboard object

        Returns:
            str: outcome string
        """
        self.node.get_logger().info("State: Mapping — scanning surroundings...")

        # 1. Stop the robot
        self.vel_pub.publish(Twist())
        self.node.get_clock().sleep_for(Duration(seconds=1))

        # 2. Rotate 360° slowly so the LiDAR captures the full obstacle
        # obstacle_mapper_node listens to /scan continuously,
        # so just rotating is enough to get a full scan
        twist = Twist()
        twist.angular.z = 0.3  # rad/s

        # Time for a full 360° rotation : 2π / 0.3 ≈ 21 seconds
        rotation_time = int((2 * math.pi / 0.3))  # seconds

        self.node.get_logger().info(
            f"Rotating 360° ({rotation_time}s) to scan obstacle...")

        for _ in range(rotation_time):
            self.vel_pub.publish(twist)
            self.node.get_clock().sleep_for(Duration(seconds=1))
            rclpy.spin_once(self.node, timeout_sec=0.1)

        # 3. Stop after full rotation
        self.vel_pub.publish(Twist())
        self.node.get_clock().sleep_for(Duration(seconds=1))

        self.node.get_logger().info("360° scan complete — obstacle mapped.")
        return "mapped"
