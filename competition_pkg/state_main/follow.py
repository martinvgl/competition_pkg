
#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import cv2
import numpy as np

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node

from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist

from yasmin import State
from yasmin import Blackboard


class FollowState(State):

    def __init__(self, node: Node):

        super().__init__(outcomes=["person_found", "search_complete"])

        self.node = node

        self.bridge = CvBridge()

        self.image_pub = self.node.create_publisher(
            Image,
            "debug_image",
            10
        )

        self.image_sub = self.node.create_subscription(
            Image,
            "image_raw",
            self.callback,
            10
        )

        self.vel_pub = self.node.create_publisher(
            Twist,
            "cmd_vel",
            10
        )

        # OpenCV HOG Person Detector
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(
            cv2.HOGDescriptor_getDefaultPeopleDetector()
        )

        self.cmd_vel = Twist()

        self.person_detected = False
        self.person_lying = False

        self.green_detected = False
        self.red_detected = False

    def callback(self, msg):

        frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        h, w, _ = frame.shape

        # =====================================================
        # GREEN EXIT DETECTION
        # =====================================================

        green_min = np.array([40, 80, 80])
        green_max = np.array([90, 255, 255])

        green_mask = cv2.inRange(
            hsv,
            green_min,
            green_max
        )

        green_pixels = np.sum(green_mask)

        # =====================================================
        # RED OBSTACLE DETECTION
        # =====================================================

        red_min1 = np.array([0, 150, 150])
        red_max1 = np.array([10, 255, 255])

        red_min2 = np.array([160, 150, 150])
        red_max2 = np.array([179, 255, 255])

        mask1 = cv2.inRange(hsv, red_min1, red_max1)
        mask2 = cv2.inRange(hsv, red_min2, red_max2)

        red_mask = mask1 + mask2

        red_pixels = np.sum(red_mask)

        # =====================================================
        # PERSON DETECTION
        # =====================================================

        boxes, weights = self.hog.detectMultiScale(
            frame,
            winStride=(8, 8)
        )

        self.person_detected = False
        self.person_lying = False

        for (x, y, bw, bh) in boxes:

            self.person_detected = True

            cv2.rectangle(
                frame,
                (x, y),
                (x + bw, y + bh),
                (0, 255, 0),
                2
            )

            # Lying person detection
            if bw > bh:

                self.person_lying = True

                cv2.putText(
                    frame,
                    "LYING PERSON",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )

            else:

                cv2.putText(
                    frame,
                    "PERSON",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 0, 0),
                    2
                )

        # =====================================================
        # DECISION MAKING
        # =====================================================

        cmd_vel = Twist()

        # PERSON FOUND
        if self.person_detected:

            self.node.get_logger().info("PERSON DETECTED")

            cmd_vel.linear.x = 0.0
            cmd_vel.angular.z = 0.0

        # GREEN EXIT FOUND
        elif green_pixels > 50000:

            self.node.get_logger().info("GREEN EXIT DETECTED")

            cmd_vel.linear.x = 0.10
            cmd_vel.angular.z = 0.0

        # RED OBSTACLE FOUND
        elif red_pixels > 50000:

            self.node.get_logger().info("RED OBSTACLE DETECTED")

            cmd_vel.linear.x = 0.0
            cmd_vel.angular.z = 0.4

        # SEARCH MODE
        else:

            self.node.get_logger().info("SEARCHING...")

            cmd_vel.linear.x = 0.03
            cmd_vel.angular.z = 0.1

        self.cmd_vel = cmd_vel

        # Publish debug image
        img_msg = self.bridge.cv2_to_imgmsg(
            frame,
            "bgr8"
        )

        self.image_pub.publish(img_msg)

    def execute(self, blackboard: Blackboard):

        self.node.get_logger().info("FOLLOW STATE STARTED")

        cnt = 0
        CNT_MAX = 300

        while rclpy.ok():

            self.vel_pub.publish(self.cmd_vel)

            rclpy.spin_once(self.node)

            self.node.get_clock().sleep_for(
                Duration(seconds=0.1)
            )

            # If person detected
            if self.person_detected:

                self.vel_pub.publish(Twist())

                if self.person_lying:
                    self.node.get_logger().warn(
                        "LYING PERSON DETECTED"
                    )

                return "person_found"

            cnt += 1

            if cnt > CNT_MAX:
                break

        self.vel_pub.publish(Twist())

        return "search_complete"
# #!/usr/bin/env python3
# # -*-encoding:UTF-8-*-

# """
# File: navigation.py
# Author: Tomoaki Fujino（Kyushu Institute of Technology, Hibikino-Musashi@Home）
# """

# # Import external modules
# import numpy as np
# import cv2

# # Import ROS2 related modules
# import rclpy
# from rclpy.duration import Duration
# from rclpy.node import Node
# from cv_bridge import CvBridge, CvBridgeError
# from sensor_msgs.msg import Image
# from geometry_msgs.msg import Twist

# # Import YASMIN related modules
# # https://github.com/uleroboticsgroup/yasmin.git
# from yasmin import State
# from yasmin import Blackboard


# class FollowState(State):
#     """FollowState class (inherits from State class)
#     Detects red regions and follows them
#     """

#     def __init__(self, node: Node):
#         """Class initialization method"""
#         # Override the constructor of the inherited State class
#         # The outcomes argument specifies the possible results to return when the state completes
#         super().__init__(outcomes=["outcome"])
#         self.node = node

#         self.bridge = CvBridge()
#         self.image_pub = self.node.create_publisher(
#             msg_type=Image, topic="masked_image", qos_profile=10
#         )
#         self.image_sub = self.node.create_subscription(
#             msg_type=Image, topic="image_raw", callback=self.callback, qos_profile=10
#         )

#         self.vel_pub = self.node.create_publisher(msg_type=Twist, topic="cmd_vel", qos_profile=10)

#         self.cmd_vel = Twist()
#         self.detect_log = "stop"

#     def callback(self, msg: Image):
#         try:
#             cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
#         except CvBridgeError as e:
#             self.node.get_logger().info(e)

#         # ========================= state =====================================
#         # Red color masking process
#         # =====================================================================
#         hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
#         h, w, ch = hsv.shape
#         hsv1 = hsv

#         # Red color range 1
#         hsv_min = np.array([0, 150, 150])
#         hsv_max = np.array([10, 255, 255])
#         mask1 = cv2.inRange(hsv, hsv_min, hsv_max)

#         # Red color range 2
#         hsv_min = np.array([160, 150, 150])
#         hsv_max = np.array([179, 255, 255])
#         mask2 = cv2.inRange(hsv, hsv_min, hsv_max)

#         # Red region mask
#         mask = mask1 + mask2
#         masked_hsv = cv2.bitwise_and(hsv1, hsv1, mask=mask)

#         # Calculate red region
#         ones = np.ones((h, w))
#         masked = cv2.bitwise_and(ones, ones, mask=mask)

#         # Calculate red regions in left, center, and right
#         ones_left = sum(sum(masked[0:h, 0 : int(w / 3)]))
#         ones_center = sum(sum(masked[0:h, int(w / 3) : int(2 * w / 3)]))
#         ones_right = sum(sum(masked[0:h, int(2 * w / 3) : w]))

#         # Set cmd_vel
#         cmd_vel = Twist()
#         if (ones_left > ones_center) and (ones_left > ones_right):
#             detect_log = "Left side"
#             cmd_vel.linear.x = 0.00
#             cmd_vel.angular.z = 0.20
#         elif (ones_center > ones_left) and (ones_center > ones_right):
#             detect_log = "Center"
#             cmd_vel.linear.x = 0.05
#             cmd_vel.angular.z = 0.00
#         elif (ones_right > ones_left) and (ones_right > ones_center):
#             detect_log = "Right side"
#             cmd_vel.linear.x = 0.00
#             cmd_vel.angular.z = -0.20
#         else:
#             detect_log = "stop"
#             cmd_vel.linear.x = 0.00
#             cmd_vel.angular.z = 0.00

#         self.detect_log = detect_log
#         self.cmd_vel = cmd_vel

#         # Publish results
#         try:
#             img_cv = cv2.cvtColor(masked_hsv, cv2.COLOR_HSV2BGR)
#             img_msg = self.bridge.cv2_to_imgmsg(img_cv, "bgr8")
#             self.image_pub.publish(img_msg)
#         except CvBridgeError as e:
#             self.node.get_logger().info(e)

#     def execute(self, blackboard: Blackboard) -> str:
#         """
#         Follow state execution method

#         Args:
#             blackboard (CustomBlackboard): CustomBlackboard object

#         Returns:
#             str: outcomes string
#         """
#         self.node.get_logger().info("Follow")
#         self.node.get_logger().info("Start!!")
#         cnt = 0
#         CNT_MAX = 10
#         while rclpy.ok():  # Execute loop while the node is operating correctly
#             self.node.get_logger().info(self.detect_log)
#             self.vel_pub.publish(self.cmd_vel)
#             self.node.get_clock().sleep_for(Duration(seconds=1))

#             cnt += 1
#             rclpy.spin_once(self.node)
#             if cnt > CNT_MAX:
#                 break
#         # Send stop command to the robot
#         self.vel_pub.publish(Twist())
#         self.node.get_logger().info("Stop!!")
#         self.node.get_clock().sleep_for(Duration(seconds=1))
#         return "outcome"
