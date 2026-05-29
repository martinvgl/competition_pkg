
# #!/usr/bin/env python3
# # -*- coding: UTF-8 -*-

# import cv2
# import numpy as np

# import rclpy
# from rclpy.duration import Duration
# from rclpy.node import Node

# from cv_bridge import CvBridge
# from sensor_msgs.msg import Image
# from geometry_msgs.msg import Twist

# from yasmin import State
# from yasmin import Blackboard


# class FollowState(State):

#     def __init__(self, node: Node):

#         super().__init__(outcomes=["person_found", "search_complete"])

#         self.node = node

#         self.bridge = CvBridge()

#         self.image_pub = self.node.create_publisher(
#             Image,
#             "debug_image",
#             10
#         )

#         self.image_sub = self.node.create_subscription(
#             Image,
#             "image_raw",
#             self.callback,
#             10
#         )

#         self.vel_pub = self.node.create_publisher(
#             Twist,
#             "cmd_vel",
#             10
#         )

#         # OpenCV HOG Person Detector
#         self.hog = cv2.HOGDescriptor()
#         self.hog.setSVMDetector(
#             cv2.HOGDescriptor_getDefaultPeopleDetector()
#         )

#         self.cmd_vel = Twist()

#         self.person_detected = False
#         self.person_lying = False

#         self.green_detected = False
#         self.red_detected = False

#     def callback(self, msg):

#         frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")

#         hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

#         h, w, _ = frame.shape

#         # =====================================================
#         # GREEN EXIT DETECTION
#         # =====================================================

#         green_min = np.array([40, 80, 80])
#         green_max = np.array([90, 255, 255])

#         green_mask = cv2.inRange(
#             hsv,
#             green_min,
#             green_max
#         )

#         green_pixels = np.sum(green_mask)

#         # =====================================================
#         # RED OBSTACLE DETECTION
#         # =====================================================

#         red_min1 = np.array([0, 150, 150])
#         red_max1 = np.array([10, 255, 255])

#         red_min2 = np.array([160, 150, 150])
#         red_max2 = np.array([179, 255, 255])

#         mask1 = cv2.inRange(hsv, red_min1, red_max1)
#         mask2 = cv2.inRange(hsv, red_min2, red_max2)

#         red_mask = mask1 + mask2

#         red_pixels = np.sum(red_mask)

#         # =====================================================
#         # PERSON DETECTION
#         # =====================================================

#         boxes, weights = self.hog.detectMultiScale(
#             frame,
#             winStride=(8, 8)
#         )

#         self.person_detected = False
#         self.person_lying = False

#         for (x, y, bw, bh) in boxes:

#             self.person_detected = True

#             cv2.rectangle(
#                 frame,
#                 (x, y),
#                 (x + bw, y + bh),
#                 (0, 255, 0),
#                 2
#             )

#             # Lying person detection
#             if bw > bh:

#                 self.person_lying = True

#                 cv2.putText(
#                     frame,
#                     "LYING PERSON",
#                     (x, y - 10),
#                     cv2.FONT_HERSHEY_SIMPLEX,
#                     0.7,
#                     (0, 0, 255),
#                     2
#                 )

#             else:

#                 cv2.putText(
#                     frame,
#                     "PERSON",
#                     (x, y - 10),
#                     cv2.FONT_HERSHEY_SIMPLEX,
#                     0.7,
#                     (255, 0, 0),
#                     2
#                 )

#         # =====================================================
#         # DECISION MAKING
#         # =====================================================

#         cmd_vel = Twist()

#         # PERSON FOUND
#         if self.person_detected:

#             self.node.get_logger().info("PERSON DETECTED")

#             cmd_vel.linear.x = 0.0
#             cmd_vel.angular.z = 0.0

#         # GREEN EXIT FOUND
#         elif green_pixels > 50000:

#             self.node.get_logger().info("GREEN EXIT DETECTED")

#             cmd_vel.linear.x = 0.10
#             cmd_vel.angular.z = 0.0

#         # RED OBSTACLE FOUND
#         elif red_pixels > 50000:

#             self.node.get_logger().info("RED OBSTACLE DETECTED")

#             cmd_vel.linear.x = 0.0
#             cmd_vel.angular.z = 0.4

#         # SEARCH MODE
#         else:

#             self.node.get_logger().info("SEARCHING...")

#             cmd_vel.linear.x = 0.03
#             cmd_vel.angular.z = 0.1

#         self.cmd_vel = cmd_vel

#         # Publish debug image
#         img_msg = self.bridge.cv2_to_imgmsg(
#             frame,
#             "bgr8"
#         )

#         self.image_pub.publish(img_msg)

#     def execute(self, blackboard: Blackboard):

#         self.node.get_logger().info("FOLLOW STATE STARTED")

#         cnt = 0
#         CNT_MAX = 300

#         while rclpy.ok():

#             self.vel_pub.publish(self.cmd_vel)

#             rclpy.spin_once(self.node)

#             self.node.get_clock().sleep_for(
#                 Duration(seconds=0.1)
#             )

#             # If person detected
#             if self.person_detected:

#                 self.vel_pub.publish(Twist())

#                 if self.person_lying:
#                     self.node.get_logger().warn(
#                         "LYING PERSON DETECTED"
#                     )

#                 return "person_found"

#             cnt += 1

#             if cnt > CNT_MAX:
#                 break

#         self.vel_pub.publish(Twist())

#         return "search_complete"

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

        super().__init__(
            outcomes=["exit_found", "search_complete"]
        )

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

        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(
            cv2.HOGDescriptor_getDefaultPeopleDetector()
        )

        self.cmd_vel = Twist()

        self.person_detected = False
        self.person_lying = False

        self.green_counter = 0
        self.exit_confirmed = False

    def callback(self, msg):

        frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # GREEN DETECTION
        green_min = np.array([40, 80, 80])
        green_max = np.array([90, 255, 255])

        green_mask = cv2.inRange(
            hsv,
            green_min,
            green_max
        )

        green_pixels = np.sum(green_mask)

        # RED DETECTION
        red_min1 = np.array([0, 150, 150])
        red_max1 = np.array([10, 255, 255])

        red_min2 = np.array([160, 150, 150])
        red_max2 = np.array([179, 255, 255])

        mask1 = cv2.inRange(hsv, red_min1, red_max1)
        mask2 = cv2.inRange(hsv, red_min2, red_max2)

        red_mask = mask1 + mask2
        red_pixels = np.sum(red_mask)

        # PERSON DETECTION
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

            if bw > bh:
                self.person_lying = True
                cv2.putText(
                    frame,
                    "IMMOBILE PERSON",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )
            else:
                cv2.putText(
                    frame,
                    "ESCORT PERSON",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 0, 0),
                    2
                )

        # GREEN CONFIRMATION
        if green_pixels > 50000:
            self.green_counter += 1
        else:
            self.green_counter = 0

        if self.green_counter > 20:
            self.exit_confirmed = True

        cmd_vel = Twist()

        # RED obstacle
        if red_pixels > 50000:

            self.node.get_logger().info("RED OBSTACLE")

            cmd_vel.linear.x = 0.0
            cmd_vel.angular.z = 0.4

        # GREEN exit
        elif green_pixels > 50000:

            self.node.get_logger().info("GREEN EXIT")

            cmd_vel.linear.x = 0.12
            cmd_vel.angular.z = 0.05

        # PERSON escort
        elif self.person_detected:

            if self.person_lying:
                self.node.get_logger().warn(
                    "IMMOBILE PERSON DETECTED"
                )
            else:
                self.node.get_logger().info(
                    "ESCORTING PERSON"
                )

            cmd_vel.linear.x = 0.06
            cmd_vel.angular.z = 0.0

        # SEARCH
        else:

            self.node.get_logger().info(
                "SEARCHING EXIT..."
            )

            cmd_vel.linear.x = 0.03
            cmd_vel.angular.z = 0.15

        self.cmd_vel = cmd_vel

        img_msg = self.bridge.cv2_to_imgmsg(
            frame,
            "bgr8"
        )

        self.image_pub.publish(img_msg)

    def execute(self, blackboard: Blackboard):

        self.node.get_logger().info(
            "FOLLOW STATE STARTED"
        )

        cnt = 0
        CNT_MAX = 600

        while rclpy.ok():

            self.vel_pub.publish(self.cmd_vel)

            rclpy.spin_once(self.node)

            self.node.get_clock().sleep_for(
                Duration(seconds=0.1)
            )

            if self.exit_confirmed:

                self.vel_pub.publish(Twist())

                self.node.get_logger().info(
                    "EXIT CONFIRMED!"
                )

                return "exit_found"

            cnt += 1

            if cnt > CNT_MAX:
                break

        self.vel_pub.publish(Twist())

        return "search_complete"
