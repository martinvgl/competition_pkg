#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
import numpy as np
import cv2
from cv_bridge import CvBridge

class FakeRobot(Node):
    def __init__(self):
        super().__init__('fake_robot')
        self.pub_image = self.create_publisher(Image, 'image_raw', 10)
        self.sub_cmd = self.create_subscription(Twist, 'cmd_vel', self.cmd_callback, 10)
        self.bridge = CvBridge()
        self.timer = self.create_timer(0.1, self.publish_image)

    def publish_image(self):
        # Publish a dummy 640x480 black image
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        msg = self.bridge.cv2_to_imgmsg(img, 'bgr8')
        self.pub_image.publish(msg)

    def cmd_callback(self, msg):
        # Print velocity commands
        print(f"Received cmd_vel: linear={msg.linear.x}, angular={msg.angular.z}")

def main(args=None):
    rclpy.init(args=args)
    node = FakeRobot()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()


# WEBCAM

# import cv2
# import rclpy

# from rclpy.node import Node

# from sensor_msgs.msg import Image
# from geometry_msgs.msg import Twist

# from cv_bridge import CvBridge


# class FakeRobot(Node):

#     def __init__(self):

#         super().__init__("fake_robot")

#         # Camera publisher
#         self.pub_image = self.create_publisher(
#             Image,
#             "image_raw",
#             10
#         )

#         # Velocity subscriber
#         self.sub_cmd = self.create_subscription(
#             Twist,
#             "cmd_vel",
#             self.cmd_callback,
#             10
#         )

#         self.bridge = CvBridge()

#         # Laptop webcam
#         self.cap = cv2.VideoCapture(0)

#         if not self.cap.isOpened():

#             self.get_logger().error(
#                 "Cannot open webcam!"
#             )

#             raise RuntimeError(
#                 "Cannot open webcam"
#             )

#         # Lower resolution for faster processing
#         self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
#         self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

#         # Publish camera at 10 Hz
#         self.timer = self.create_timer(
#             0.1,
#             self.publish_image
#         )

#         self.get_logger().info(
#             "Fake Robot Started"
#         )

#     def publish_image(self):

#         ret, frame = self.cap.read()

#         if not ret:

#             self.get_logger().warn(
#                 "Failed to grab frame"
#             )

#             return

#         msg = self.bridge.cv2_to_imgmsg(
#             frame,
#             encoding="bgr8"
#         )

#         self.pub_image.publish(msg)

#     def cmd_callback(self, msg):

#         print(
#             f"[CMD_VEL] "
#             f"linear={msg.linear.x:.2f} "
#             f"angular={msg.angular.z:.2f}"
#         )

#     def destroy_node(self):

#         if hasattr(self, "cap"):
#             self.cap.release()

#         super().destroy_node()


# def main(args=None):

#     rclpy.init(args=args)

#     node = FakeRobot()

#     try:

#         rclpy.spin(node)

#     except KeyboardInterrupt:

#         pass

#     finally:

#         node.destroy_node()

#         rclpy.shutdown()


# if __name__ == "__main__":

#     main()