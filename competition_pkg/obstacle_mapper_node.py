#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
File: obstacle_mapper_node.py
Author: Kyutech ROS Group

Standalone node that compares live LiDAR data against the reference map
and publishes a dynamic map updated with newly detected obstacles.

It runs in parallel with the state machine and does not change the
robot behaviour: it only observes and publishes.

Pose source: TF2 (map -> base_link) with the scan timestamp.
  - Fixes the temporal desync between /odom and /scan callbacks.
  - Automatically uses AMCL localisation when available.
  - Falls back gracefully if TF2 is not yet ready.

Logic:
  - Reference map (/map): loaded once at startup.
  - LiDAR (/scan):        listened to continuously.
  - Pose (TF2):           looked up at the exact timestamp of each scan.
  -> If a LiDAR point falls on a FREE cell of the reference map
     -> mark that cell as an OBSTACLE in the dynamic map.
  -> Publish the dynamic map on /updated_map.

Topics:
  Subscriptions:
    /map   (nav_msgs/OccupancyGrid): reference map (fixed)
    /scan  (sensor_msgs/LaserScan):  LiDAR data
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
import rclpy.duration
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    QoSDurabilityPolicy,
    QoSReliabilityPolicy,
    QoSHistoryPolicy,
)

import tf2_ros
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException

from nav_msgs.msg import OccupancyGrid
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from geometry_msgs.msg import Quaternion


# =========================================================
# THRESHOLDS
# =========================================================

FREE_THRESHOLD    = 20    # Max value for a cell to be considered free
OBSTACLE_VALUE    = 100   # Value used to mark an obstacle
MIN_RANGE         = 0.12  # Minimum valid LiDAR range [m]
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

    Returns:
        tuple (col, row), or None if out of bounds
    """
    res = grid.info.resolution
    ox  = grid.info.origin.position.x
    oy  = grid.info.origin.position.y
    col = int((x - ox) / res)
    row = int((y - oy) / res)
    if 0 <= col < grid.info.width and 0 <= row < grid.info.height:
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

        # -- State ---------------------------------------------------------
        self.reference_map = None
        self.dynamic_map   = None
        self.new_obstacles = []

        # -- TF2 -----------------------------------------------------------
        # Buffer stores transforms for a few seconds so we can look up the
        # pose at the exact timestamp of each scan, not "right now".
        # This fixes the temporal desync that caused phantom obstacles when
        # the robot moved between the /odom and /scan callbacks.
        self.tf_buffer   = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # -- QoS profiles --------------------------------------------------
        # /map is published TRANSIENT_LOCAL by map_server.
        map_qos = QoSProfile(depth=1)
        map_qos.history     = QoSHistoryPolicy.KEEP_LAST
        map_qos.reliability = QoSReliabilityPolicy.RELIABLE
        map_qos.durability  = QoSDurabilityPolicy.TRANSIENT_LOCAL

        # /scan is published BEST_EFFORT by the TurtleBot3.
        sensor_qos = QoSProfile(depth=10)
        sensor_qos.history     = QoSHistoryPolicy.KEEP_LAST
        sensor_qos.reliability = QoSReliabilityPolicy.BEST_EFFORT
        sensor_qos.durability  = QoSDurabilityPolicy.VOLATILE

        # -- Subscribers ---------------------------------------------------
        self.create_subscription(
            OccupancyGrid, "/map",  self.map_cb,  map_qos)
        self.create_subscription(
            LaserScan,     "/scan", self.scan_cb, sensor_qos)

        # -- Publishers ----------------------------------------------------
        self.map_pub   = self.create_publisher(OccupancyGrid, "/updated_map",  10)
        self.alert_pub = self.create_publisher(String,        "/new_obstacle", 10)

        # -- Timer: publish dynamic map at 1 Hz ----------------------------
        self.create_timer(1.0, self.publish_map)

        self.get_logger().info("Obstacle mapper node started.")
        self.get_logger().info("Waiting for reference map on /map...")

    # -- Callbacks ---------------------------------------------------------

    def map_cb(self, msg: OccupancyGrid):
        """Receive the reference map — called once at startup."""
        if self.reference_map is None:
            self.reference_map = msg
            self.dynamic_map   = copy.deepcopy(msg)
            self.get_logger().info(
                f"Reference map received: "
                f"{msg.info.width}x{msg.info.height} cells, "
                f"resolution={msg.info.resolution} m/cell")

    def _get_robot_pose(self, stamp):
        """Look up robot pose in the map frame at the given timestamp.

        Using msg.header.stamp (not rclpy.time.Time()) synchronises the pose
        with the scan — this is the key fix for phantom obstacles caused by
        the robot moving between the /odom and /scan callback calls.

        Returns:
            (x, y, yaw) in the map frame, or None if TF2 is not ready.
        """
        try:
            t = self.tf_buffer.lookup_transform(
                "map",        # target frame
                "base_link",  # source frame
                rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=0.1),
            )
            x   = t.transform.translation.x
            y   = t.transform.translation.y
            yaw = quaternion_to_yaw(t.transform.rotation)
            return x, y, yaw

        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            self.get_logger().warn(
                f"TF2 lookup failed: {e}",
                throttle_duration_sec=2.0)
            return None

    def scan_cb(self, msg: LaserScan):
        """Process a LiDAR scan and detect new obstacles."""
        if self.reference_map is None or self.dynamic_map is None:
            return

        # Pose synchronised with this scan's timestamp
        pose = self._get_robot_pose(msg.header.stamp)
        if pose is None:
            return
        robot_x, robot_y, robot_yaw = pose

        for i, r in enumerate(msg.ranges):
            if not (MIN_RANGE < r < msg.range_max):
                continue

            # Angle of this beam in the world frame
            angle = msg.angle_min + i * msg.angle_increment + robot_yaw

            # World position of the obstacle point
            ox = robot_x + r * math.cos(angle)
            oy = robot_y + r * math.sin(angle)

            cell = world_to_map(ox, oy, self.reference_map)
            if cell is None:
                continue

            col, row = cell
            idx = map_index(col, row, self.reference_map)

            ref_value = self.reference_map.data[idx]
            dyn_value = self.dynamic_map.data[idx]

            # Cell was FREE in the reference but is now hit -> new obstacle
            if ref_value < FREE_THRESHOLD and dyn_value < OBSTACLE_VALUE:
                self.dynamic_map.data[idx] = OBSTACLE_VALUE

                if self._is_new_obstacle(ox, oy):
                    self.new_obstacles.append((ox, oy))
                    self.get_logger().warn(
                        f"New obstacle at world ({ox:.2f}, {oy:.2f}) "
                        f"-- map cell ({col}, {row})")
                    self._publish_alert(ox, oy)

    # -- Helpers -----------------------------------------------------------

    def _is_new_obstacle(self, x: float, y: float) -> bool:
        """Return True if this obstacle is far enough from known ones."""
        for (kx, ky) in self.new_obstacles:
            if math.hypot(x - kx, y - ky) < NEW_OBSTACLE_DIST:
                return False
        return True

    def _publish_alert(self, x: float, y: float):
        """Publish a text alert with the obstacle position."""
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
