#!/usr/bin/env python3
# -*-encoding:UTF-8-*-

"""
File: states/patrol.py
Author: Kyutech ROS Group

PatrolState — navigation autonome sur une liste de waypoints.
Utilise l'action NavigateToPose de Nav2.
Structure identique à navigation.py du package d'exemple du labo.

eng:

PatrolState: autonomous navigation on a waypoint list

Outcomes :
  "detected" → un obstacle proche détecté par le LiDAR (possible intrus)
  "patrol"   → waypoint atteint, continuer la patrouille
"""

# Import modules (ROS2 related)
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.action.client import ClientGoalHandle
from geometry_msgs.msg import PoseStamped
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String
import tf_transformations
import math

# Import modules (YASMIN related)
from yasmin import State
from yasmin import Blackboard


# ── Waypoints du circuit de patrouille ──────────────────────────────────────
# Adapter ces valeurs à votre environnement réel (en mètres, frame "map")
WAYPOINTS = [
    {"x": 0.0, "y": 0.0,  "yaw": 0.0},       # Base (point de départ)
    {"x": 2.0, "y": 0.0,  "yaw": 1.5708},    # Coin avant-droit
    {"x": 2.0, "y": 2.0,  "yaw": 3.1416},    # Coin arrière-droit
    {"x": 0.0, "y": 2.0,  "yaw": -1.5708},   # Coin arrière-gauche
]


class PatrolState(State):
    """PatrolState class (inherits from State class)
    Navigates autonomously along a list of waypoints
    """

    def __init__(self, node: Node):
        """Class initialization method"""
        super().__init__(outcomes=["detected", "patrol"])

        self.node = node
        self.waypoint_index = 0
        self.new_obstacle_detected = False

        # Action client for Nav2
        self.nav_to_pose_client = ActionClient(
            node=self.node,
            action_type=NavigateToPose,
            action_name="/navigate_to_pose",
        )

        # Listen to obstacle mapper alerts
        self.node.create_subscription(
            msg_type=String,
            topic="/new_obstacle",
            callback=self.obstacle_cb,
            qos_profile=10,
        )

    def obstacle_cb(self, msg: String):
        """Called when obstacle_mapper_node detects a new obstacle"""
        self.node.get_logger().warn(f"New obstacle signaled: {msg.data}")
        self.new_obstacle_detected = True

    def goToPose(self, x: float, y: float, yaw: float) -> bool:
        """Navigate to a specified pose

        Args:
            x (float): X coordinate [m]
            y (float): Y coordinate [m]
            yaw (float): Orientation [rad]

        Returns:
            bool: True if goal accepted, False otherwise
        """
        while not self.nav_to_pose_client.wait_for_server(timeout_sec=1.0):
            self.node.get_logger().info(
                "'NavigateToPose' action server not available, waiting...")

        pose = PoseStamped()
        pose.header.stamp = self.node.get_clock().now().to_msg()
        pose.header.frame_id = "map"
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = 0.0

        quat = tf_transformations.quaternion_from_euler(0, 0, yaw)
        pose.pose.orientation.x = quat[1]
        pose.pose.orientation.y = quat[2]
        pose.pose.orientation.z = quat[3]
        pose.pose.orientation.w = quat[0]

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = pose

        self.node.get_logger().info(
            f"Patrol → waypoint {self.waypoint_index}: "
            f"(x={x:.2f}, y={y:.2f}, yaw={math.degrees(yaw):.0f}°)")

        send_goal_future = self.nav_to_pose_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self.node, send_goal_future)

        self._goal_handle = send_goal_future.result()
        if not self._goal_handle.accepted:
            self.node.get_logger().error("Goal rejected!")
            return False

        self._result_future = self._goal_handle.get_result_async()
        return True

    def isNavComplete(self) -> bool:
        """Check if navigation is complete"""
        if not self._result_future:
            return True
        rclpy.spin_until_future_complete(
            self.node, self._result_future, timeout_sec=0.10)
        if self._result_future.result():
            self._status = self._result_future.result().status
            return True
        return False

    def execute(self, blackboard: Blackboard) -> str:
        """Patrol state execution method

        Args:
            blackboard (Blackboard): Shared blackboard object

        Returns:
            str: outcome string
        """
        self.node.get_logger().info("State: Patrol")

        wp = WAYPOINTS[self.waypoint_index]
        self._result_future = None
        self._status = None
        self.new_obstacle_detected = False

        if not self.goToPose(wp["x"], wp["y"], wp["yaw"]):
            return "patrol"

        # Wait for navigation, but interrupt if new obstacle detected
        while not self.isNavComplete():
            rclpy.spin_once(self.node, timeout_sec=0.1)
            if self.new_obstacle_detected:
                self._goal_handle.cancel_goal_async()
                self.node.get_logger().warn(
                    "Navigation interrupted — new obstacle detected!")
                return "detected"

        # Advance to next waypoint (circular)
        self.waypoint_index = (self.waypoint_index + 1) % len(WAYPOINTS)
        blackboard.last_waypoint = self.waypoint_index

        if self._status == GoalStatus.STATUS_SUCCEEDED:
            self.node.get_logger().info("Waypoint reached!")
            return "patrol"
        else:
            return "detected"
