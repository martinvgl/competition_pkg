#!/usr/bin/env python3
# -*-encoding:UTF-8-*-

"""
File: obstacle_mapper_node.py
Author: Kyutech ROS Group

Nœud autonome qui compare les données LiDAR avec la carte de référence
et publie une carte dynamique mise à jour avec les nouveaux obstacles.

eng: compare reference map and actual environment, and spot new obstacles.

Logique :
  - Carte de référence (/map) : chargée une fois au démarrage  - reference map
  - LiDAR (/scan)             : écouté en continu  - continuous listening
  - Position (/odom)          : pour convertir les points LiDAR en coordonnées carte  - LiDAR point to map coordinates
  → Si un point LiDAR tombe sur une cellule LIBRE dans la référence
    → marquer comme OBSTACLE dans la carte dynamique
  → Publier la carte dynamique sur /updated_map

  eng: 
  → if a LiDAR point correspond to a FREE cell from the reference, 
    → write as OBSTACLE
  → Publish the map on /updated_map

Topics :
  Subscriptions :
    /map    (nav_msgs/OccupancyGrid) : carte de référence (fixe)
    /scan   (sensor_msgs/LaserScan)  : données LiDAR
    /odom   (nav_msgs/Odometry)      : position + orientation du robot
  Publications :
    /updated_map  (nav_msgs/OccupancyGrid) : carte dynamique
    /new_obstacle (std_msgs/String)        : alerte nouvel obstacle (position)
"""

import math
import copy

import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid, Odometry
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from geometry_msgs.msg import Quaternion


# ── Seuils ───────────────────────────────────────────────────────────────────
FREE_THRESHOLD     = 20    # Valeur max pour considérer une cellule comme libre
OBSTACLE_VALUE     = 100   # Valeur pour marquer un obstacle
MIN_RANGE          = 0.12  # Distance minimale LiDAR valide [m]
NEW_OBSTACLE_DIST  = 0.15  # Distance min entre deux nouveaux obstacles [m]


def quaternion_to_yaw(q: Quaternion) -> float:
    """Convert quaternion to yaw angle (rad)"""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def world_to_map(x: float, y: float, grid: OccupancyGrid):
    """Convert world coordinates (m) to map cell indices (col, row)

    Args:
        x (float): World x [m]
        y (float): World y [m]
        grid (OccupancyGrid): Reference map

    Returns:
        tuple (col, row) or None if out of bounds
    """
    res = grid.info.resolution
    ox  = grid.info.origin.position.x
    oy  = grid.info.origin.position.y
    col = int((x - ox) / res)
    row = int((y - oy) / res)
    w   = grid.info.width
    h   = grid.info.height
    if 0 <= col < w and 0 <= row < h:
        return col, row
    return None


def map_index(col: int, row: int, grid: OccupancyGrid) -> int:
    """Convert (col, row) to flat array index"""
    return row * grid.info.width + col


class ObstacleMapperNode(Node):
    """ObstacleMapperNode — detects new obstacles and updates the dynamic map"""

    def __init__(self):
        super().__init__("obstacle_mapper_node")

        # ── State ────────────────────────────────────────────────────────────
        self.reference_map   = None   # OccupancyGrid — carte de référence (fixe)
        self.dynamic_map     = None   # OccupancyGrid — carte dynamique (mise à jour)
        self.robot_x         = 0.0
        self.robot_y         = 0.0
        self.robot_yaw       = 0.0
        self.new_obstacles   = []     # Liste des positions des nouveaux obstacles

        # ── Subscribers ──────────────────────────────────────────────────────
        self.create_subscription(
            OccupancyGrid, "/map",  self.map_cb,  10)
        self.create_subscription(
            LaserScan,     "/scan", self.scan_cb, 10)
        self.create_subscription(
            Odometry,      "/odom", self.odom_cb, 10)

        # ── Publishers ───────────────────────────────────────────────────────
        self.map_pub = self.create_publisher(
            OccupancyGrid, "/updated_map",  10)
        self.alert_pub = self.create_publisher(
            String,        "/new_obstacle", 10)

        # ── Timer : publish updated map at 1 Hz ──────────────────────────────
        self.create_timer(1.0, self.publish_map)

        self.get_logger().info("Obstacle mapper node started.")
        self.get_logger().info("Waiting for reference map on /map...")

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def map_cb(self, msg: OccupancyGrid):
        """Receive reference map — called once at startup"""
        if self.reference_map is None:
            self.reference_map = msg
            # Deep copy as dynamic map base
            self.dynamic_map = copy.deepcopy(msg)
            self.get_logger().info(
                f"Reference map received: "
                f"{msg.info.width}x{msg.info.height} cells, "
                f"resolution={msg.info.resolution}m/cell")

    def odom_cb(self, msg: Odometry):
        """Update robot position from odometry"""
        self.robot_x   = msg.pose.pose.position.x
        self.robot_y   = msg.pose.pose.position.y
        self.robot_yaw = quaternion_to_yaw(msg.pose.pose.orientation)

    def scan_cb(self, msg: LaserScan):
        """Process LiDAR scan and detect new obstacles"""
        if self.reference_map is None or self.dynamic_map is None:
            return

        new_found = False

        for i, r in enumerate(msg.ranges):
            # Skip invalid readings
            if not (MIN_RANGE < r < msg.range_max):
                continue

            # Compute angle of this beam in world frame
            angle = msg.angle_min + i * msg.angle_increment + self.robot_yaw

            # Compute world position of the obstacle point
            ox = self.robot_x + r * math.cos(angle)
            oy = self.robot_y + r * math.sin(angle)

            # Convert to map cell
            cell = world_to_map(ox, oy, self.reference_map)
            if cell is None:
                continue

            col, row = cell
            idx = map_index(col, row, self.reference_map)

            ref_value = self.reference_map.data[idx]
            dyn_value = self.dynamic_map.data[idx]

            # If cell was FREE in reference but is now hit by LiDAR
            # → new obstacle !
            if ref_value < FREE_THRESHOLD and dyn_value < OBSTACLE_VALUE:
                # Mark as obstacle in dynamic map
                self.dynamic_map.data[idx] = OBSTACLE_VALUE

                # Check it's not too close to an already reported obstacle
                if self._is_new_obstacle(ox, oy):
                    self.new_obstacles.append((ox, oy))
                    new_found = True
                    self.get_logger().warn(
                        f"New obstacle at world ({ox:.2f}, {oy:.2f}) "
                        f"— map cell ({col}, {row})")
                    self._publish_alert(ox, oy)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _is_new_obstacle(self, x: float, y: float) -> bool:
        """Check that this obstacle is far enough from already known ones"""
        for (kx, ky) in self.new_obstacles:
            if math.hypot(x - kx, y - ky) < NEW_OBSTACLE_DIST:
                return False
        return True

    def _publish_alert(self, x: float, y: float):
        """Publish alert message with obstacle position"""
        msg = String()
        msg.data = f"[NEW OBSTACLE] position: x={x:.2f}m, y={y:.2f}m"
        self.alert_pub.publish(msg)

    def publish_map(self):
        """Publish the dynamic map at 1 Hz"""
        if self.dynamic_map is None:
            return
        self.dynamic_map.header.stamp = self.get_clock().now().to_msg()
        self.map_pub.publish(self.dynamic_map)

    def get_new_obstacles(self):
        """Return list of new obstacle positions (for state machine)"""
        return list(self.new_obstacles)


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
