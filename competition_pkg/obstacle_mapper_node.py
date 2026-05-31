#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
File: obstacle_mapper_node.py
Author: Kyutech ROS Group

Standalone node that compares live LiDAR data against the reference map
and publishes a dynamic map updated with newly detected obstacles.

It runs in parallel with the state machine and does not change the
robot behaviour: it only observes and publishes.

Logic:
  - Reference map (/map): loaded once at startup.
  - LiDAR (/scan):        listened to continuously.
  - Pose (/odom):         used to convert LiDAR points into map coordinates.
  -> If a LiDAR point falls on a FREE cell of the reference map
     -> mark that cell as an OBSTACLE in the dynamic map.
  -> Publish the dynamic map on /updated_map.

Topics:
  Subscriptions:
    /map   (nav_msgs/OccupancyGrid): reference map (fixed)
    /scan  (sensor_msgs/LaserScan):  LiDAR data
    /odom  (nav_msgs/Odometry):      robot position + orientation
  Publications:
    /updated_map  (nav_msgs/OccupancyGrid): dynamic map
    /new_obstacle (std_msgs/String):        new-obstacle alert (position)
"""

# =========================================================
# IMPORTS
# =========================================================

import math
import copy

import rclpy

from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    QoSDurabilityPolicy,
    QoSReliabilityPolicy,
    QoSHistoryPolicy,
)

from nav_msgs.msg import OccupancyGrid, Odometry
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from geometry_msgs.msg import Quaternion


# =========================================================
# THRESHOLDS
# =========================================================

FREE_THRESHOLD = 20      # Max value for a cell to be considered free
OBSTACLE_VALUE = 100     # Value used to mark an obstacle
MIN_RANGE = 0.12         # Minimum valid LiDAR range [m]
NEW_OBSTACLE_DIST = 0.15  # Minimum distance between two new obstacles [m]


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def quaternion_to_yaw(q: Quaternion) -> float:
    """Convert a quaternion to a yaw angle (rad)."""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def world_to_map(x: float, y: float, grid: OccupancyGrid):
    """Convert world coordinates (m) to map cell indices (col, row).

    Args:
        x (float): World x [m]
        y (float): World y [m]
        grid (OccupancyGrid): Reference map

    Returns:
        tuple (col, row), or None if out of bounds
    """
    res = grid.info.resolution
    ox = grid.info.origin.position.x
    oy = grid.info.origin.position.y
    col = int((x - ox) / res)
    row = int((y - oy) / res)
    w = grid.info.width
    h = grid.info.height
    if 0 <= col < w and 0 <= row < h:
        return col, row
    return None


def map_index(col: int, row: int, grid: OccupancyGrid) -> int:
    """Convert (col, row) to a flat array index."""
    return row * grid.info.width + col


# =========================================================
# NODE
# =========================================================

class ObstacleMapperNode(Node):
    """Detects new obstacles and updates the dynamic map."""

    def __init__(self):
        super().__init__("obstacle_mapper_node")

        # =====================================================
        # STATE
        # =====================================================

        self.reference_map = None   # OccupancyGrid: reference map (fixed)
        self.dynamic_map = None      # OccupancyGrid: dynamic map (updated)
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_yaw = 0.0
        self.new_obstacles = []      # Positions of the new obstacles

        # =====================================================
        # SUBSCRIBERS
        # =====================================================

        # /map is published "latched" (transient_local) by map_server and
        # slam_toolbox, so the subscription must match to receive the map
        # even when this node starts after the publisher.
        map_qos = QoSProfile(depth=1)
        map_qos.history = QoSHistoryPolicy.KEEP_LAST
        map_qos.reliability = QoSReliabilityPolicy.RELIABLE
        map_qos.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL

        self.create_subscription(
            OccupancyGrid, "/map", self.map_cb, map_qos)
        self.create_subscription(
            LaserScan, "/scan", self.scan_cb, 10)
        self.create_subscription(
            Odometry, "/odom", self.odom_cb, 10)
        
         # Sensor topics (/scan, /odom) are published BEST_EFFORT, so the
        # subscriptions must match or no messages are received.
        sensor_qos = QoSProfile(depth=10)
        sensor_qos.history = QoSHistoryPolicy.KEEP_LAST
        sensor_qos.reliability = QoSReliabilityPolicy.BEST_EFFORT
        sensor_qos.durability = QoSDurabilityPolicy.VOLATILE

        self.create_subscription(
            OccupancyGrid, "/map", self.map_cb, map_qos)
        self.create_subscription(
            LaserScan, "/scan", self.scan_cb, sensor_qos)
        self.create_subscription(
            Odometry, "/odom", self.odom_cb, sensor_qos)

        # =====================================================
        # PUBLISHERS
        # =====================================================

        self.map_pub = self.create_publisher(
            OccupancyGrid, "/updated_map", 10)
        self.alert_pub = self.create_publisher(
            String, "/new_obstacle", 10)

        # =====================================================
        # TIMER: publish the updated map at 1 Hz
        # =====================================================

        self.create_timer(1.0, self.publish_map)

        self.get_logger().info("Obstacle mapper node started.")
        self.get_logger().info("Waiting for reference map on /map...")

    # =====================================================
    # CALLBACKS
    # =====================================================

    def map_cb(self, msg: OccupancyGrid):
        """Receive the reference map (called once at startup)."""
        if self.reference_map is None:
            self.reference_map = msg
            # Deep copy used as the dynamic map base
            self.dynamic_map = copy.deepcopy(msg)
            self.get_logger().info(
                f"Reference map received: "
                f"{msg.info.width}x{msg.info.height} cells, "
                f"resolution={msg.info.resolution}m/cell")

    def odom_cb(self, msg: Odometry):
        """Update the robot pose from odometry."""
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y
        self.robot_yaw = quaternion_to_yaw(msg.pose.pose.orientation)

    def scan_cb(self, msg: LaserScan):
        """Process a LiDAR scan and detect new obstacles."""
        if self.reference_map is None or self.dynamic_map is None:
            return

        for i, r in enumerate(msg.ranges):
            # Skip invalid readings
            if not (MIN_RANGE < r < msg.range_max):
                continue

            # Angle of this beam in the world frame
            angle = msg.angle_min + i * msg.angle_increment + self.robot_yaw

            # World position of the obstacle point
            ox = self.robot_x + r * math.cos(angle)
            oy = self.robot_y + r * math.sin(angle)

            # Convert to a map cell
            cell = world_to_map(ox, oy, self.reference_map)
            if cell is None:
                continue

            col, row = cell
            idx = map_index(col, row, self.reference_map)

            ref_value = self.reference_map.data[idx]
            dyn_value = self.dynamic_map.data[idx]

            # Cell was FREE in the reference but is now hit by the LiDAR
            # -> new obstacle
            if ref_value < FREE_THRESHOLD and dyn_value < OBSTACLE_VALUE:
                # Mark it as an obstacle in the dynamic map
                self.dynamic_map.data[idx] = OBSTACLE_VALUE

                # Keep only obstacles far enough from known ones
                if self._is_new_obstacle(ox, oy):
                    self.new_obstacles.append((ox, oy))
                    self.get_logger().warn(
                        f"New obstacle at world ({ox:.2f}, {oy:.2f}) "
                        f"-- map cell ({col}, {row})")
                    self._publish_alert(ox, oy)

    # =====================================================
    # HELPERS
    # =====================================================

    def _is_new_obstacle(self, x: float, y: float) -> bool:
        """Return True if this obstacle is far enough from known ones."""
        for (kx, ky) in self.new_obstacles:
            if math.hypot(x - kx, y - ky) < NEW_OBSTACLE_DIST:
                return False
        return True

    def _publish_alert(self, x: float, y: float):
        """Publish an alert message with the obstacle position."""
        msg = String()
        msg.data = f"[NEW OBSTACLE] position: x={x:.2f}m, y={y:.2f}m"
        self.alert_pub.publish(msg)

    def publish_map(self):
        """Publish the dynamic map at 1 Hz."""
        if self.dynamic_map is None:
            return
        self.dynamic_map.header.stamp = self.get_clock().now().to_msg()
        self.map_pub.publish(self.dynamic_map)

    def get_new_obstacles(self):
        """Return the list of new obstacle positions."""
        return list(self.new_obstacles)


# =========================================================
# MAIN
# =========================================================

def main(args=None):
    rclpy.init(args=args)
    node = ObstacleMapperNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
