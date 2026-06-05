# import cv2
# import numpy as np
# import rclpy
# from rclpy.node import Node
# from sensor_msgs.msg import Image
# from std_msgs.msg import String
# from cv_bridge import CvBridge

# class PerceptionNode(Node):

#     def __init__(self):
#         super().__init__("perception_node")

#         self.bridge = CvBridge()

#         # --- INITIALIZE OPENCV PERSON DETECTOR ---
#         # HOG (Histogram of Oriented Gradients) is built into OpenCV for human detection
#         self.hog = cv2.HOGDescriptor()
#         self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

#         # Image subscription from camera
#         self.image_sub = self.create_subscription(
#             Image,
#             "/image_raw",
#             self.image_callback,
#             10,
#         )

#         # Status publisher to drive the YASMIN state machine
#         self.status_pub = self.create_publisher(
#             String,
#             "/evacuation_status",
#             10,
#         )

#         # Status of individuals detected
#         self.people_pub = self.create_publisher(
#             String,
#             "/people_count",
#             10,
#         )

#         self.get_logger().info("Perception Node Started with HOG Person Detection")

#     def image_callback(self, msg):
#         # Convert ROS Image to OpenCV frame
#         frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")

#         # Convert to HSV color space for Red and Green
#         hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

#         # --- COLOR CALIBRATIONS ---
#         # RED = DANGER
#         lower_red = np.array([0, 150, 150])
#         upper_red = np.array([10, 255, 255])

#         # GREEN = SAFE
#         lower_green = np.array([40, 100, 100])
#         upper_green = np.array([90, 255, 255])

#         # Generate original masks
#         red_mask = cv2.inRange(hsv, lower_red, upper_red)
#         green_mask = cv2.inRange(hsv, lower_green, upper_green)

#         # Count original pixel thresholds
#         red_pixels = np.sum(red_mask > 0)
#         green_pixels = np.sum(green_mask > 0)

#         # --- PERSON DETECTION LOGIC (Replaces Yellow) ---
#         # Downscale the frame layout slightly to ensure faster processing speeds
#         processing_frame = cv2.resize(frame, (640, 480))
        
#         # detectMultiScale searches the matrix and returns bounding boxes around people
#         (boxes, weights) = self.hog.detectMultiScale(
#             processing_frame, 
#             winStride=(8, 8), 
#             padding=(4, 4), 
#             scale=1.05
#         )
#         person_detected = len(boxes) > 0

#         status_msg = String()

#         # --- STATE MACHINE MATCHING LOGIC ---
#         # 1. Check for red danger blocks first
#         if red_pixels > 1000:
#             status_msg.data = "danger"
#             self.get_logger().warn("DANGER DETECTED (RED)")

#         # 2. Check for human presence next (Replaces Yellow Caution)
#         elif person_detected:
#             status_msg.data = "caution"
#             self.get_logger().info(f"CAUTION AREA -> {len(boxes)} PERSON DETECTED! SLOWING DOWN.")

#         # 3. Check for green exit tracking indicators
#         elif green_pixels > 1000:
#             status_msg.data = "safe"
#             self.get_logger().info("SAFE PATH (GREEN)")

#         # 4. Default state when nothing is found
#         else:
#             status_msg.data = "searching"
#             self.get_logger().info("SEARCHING FOR SAFE PATH")

#         # Publish the outcome string to the State Machine Node
#         self.status_pub.publish(status_msg)

#         # Publish the actual number of detected people
#         people_msg = String()
#         people_msg.data = f"People detected: {len(boxes)}"
#         self.people_pub.publish(people_msg)


# def main(args=None):
#     rclpy.init(args=args)
#     node = PerceptionNode()
    
#     try:
#         rclpy.spin(node)
#     except KeyboardInterrupt:
#         node.get_logger().info("Shutting down Perception Node...")
#     finally:
#         node.destroy_node()
#         rclpy.shutdown()


# if __name__ == "__main__":
#     main()


#############################WORKING########################

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
from ultralytics import YOLO

class PerceptionNode(Node):

    def __init__(self):
        super().__init__("perception_node")

        self.bridge = CvBridge()

        # --- INITIALIZE OPENCV PERSON DETECTOR ---
        # HOG (Histogram of Oriented Gradients) is built into OpenCV for human detection
        #self.hog = cv2.HOGDescriptor()
        #self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        self.model = YOLO("yolov8n.pt")

        # Image subscription from camera
        self.image_sub = self.create_subscription(
            Image,
            "/image_raw",
            self.image_callback,
            10,
        )

        # Status publisher to drive the YASMIN state machine
        self.status_pub = self.create_publisher(
            String,
            "/evacuation_status",
            10,
        )

        # Status of individuals detected
        self.people_pub = self.create_publisher(
            String,
            "/people_count",
            10,
        )

        self.get_logger().info("Perception Node Started with HOG Person Detection")

    def image_callback(self, msg):
        # Convert ROS Image to OpenCV frame
        frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")

        # Convert to HSV color space for Red and Green
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # --- COLOR CALIBRATIONS ---
        # RED = DANGER
        lower_red = np.array([0, 150, 150])
        upper_red = np.array([10, 255, 255])

        # GREEN = SAFE
        lower_green = np.array([40, 100, 100])
        upper_green = np.array([90, 255, 255])

        # Generate original masks
        red_mask = cv2.inRange(hsv, lower_red, upper_red)
        green_mask = cv2.inRange(hsv, lower_green, upper_green)

        # Count original pixel thresholds
        red_pixels = np.sum(red_mask > 0)
        green_pixels = np.sum(green_mask > 0)

        # --- PERSON DETECTION LOGIC (Replaces Yellow) ---
        # Downscale the frame layout slightly to ensure faster processing speeds
        # processing_frame = cv2.resize(frame, (640, 480))
        
        # detectMultiScale searches the matrix and returns bounding boxes around people
       
        # (boxes, weights) = self.hog.detectMultiScale(
        #     processing_frame, 
        #     winStride=(8, 8), 
        #     padding=(4, 4), 
        #     scale=1.05
        # )
        
        results = self.model(frame, classes=0, verbose=False)
        boxes = results[0].boxes


        person_detected = len(boxes) > 0

        status_msg = String()

        # --- STATE MACHINE MATCHING LOGIC ---

        # 1. Check for green exit tracking indicators
        if green_pixels > 1000:
            status_msg.data = "safe"
            self.get_logger().info("SAFE PATH (GREEN)")
        # 2. Check for red danger blocks first
        elif red_pixels > 1000:
            status_msg.data = "danger"
            self.get_logger().warn("DANGER DETECTED (RED)")
        # 3. Check for human presence next (Replaces Yellow Caution)
        elif person_detected:
            status_msg.data = "caution"
            self.get_logger().info(f"CAUTION AREA -> {len(boxes)} PERSON DETECTED! SLOWING DOWN.")



        # 4. Default state when nothing is found
        else:
            status_msg.data = "searching"
            self.get_logger().info("SEARCHING FOR SAFE PATH")

        # Publish the outcome string to the State Machine Node
        self.status_pub.publish(status_msg)

        # Publish the actual number of detected people
        people_msg = String()
        people_msg.data = f"People detected: {len(boxes)}"
        self.people_pub.publish(people_msg)


def main(args=None):
    rclpy.init(args=args)
    node = PerceptionNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down Perception Node...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()




# import cv2
# import numpy as np
# import rclpy
# from rclpy.node import Node
# from sensor_msgs.msg import Image
# from std_msgs.msg import String
# from cv_bridge import CvBridge
# from ultralytics import YOLO

# class PerceptionNode(Node):

#     def __init__(self):
#         super().__init__("perception_node")

#         self.bridge = CvBridge()

#         # --- INITIALIZE OPENCV PERSON DETECTOR ---
#         # HOG (Histogram of Oriented Gradients) is built into OpenCV for human detection
#         #self.hog = cv2.HOGDescriptor()
#         #self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

#         self.model = YOLO("yolov8n.pt")

#         # Image subscription from camera
#         self.image_sub = self.create_subscription(
#             Image,
#             "/image_raw",
#             self.image_callback,
#             10,
#         )

#         # Status publisher to drive the YASMIN state machine
#         self.status_pub = self.create_publisher(
#             String,
#             "/evacuation_status",
#             10,
#         )

#         # Status of individuals detected
#         self.people_pub = self.create_publisher(
#             String,
#             "/people_count",
#             10,
#         )

#         self.get_logger().info("Perception Node Started with HOG Person Detection")

#     def image_callback(self, msg):
#         # Convert ROS Image to OpenCV frame
#         frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")

#         # Convert to HSV color space for Red and Green
#         hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

#         # # --- COLOR CALIBRATIONS ---
#         # # RED = DANGER
#         # lower_red = np.array([0, 150, 150])
#         # upper_red = np.array([10, 255, 255])

#         # # GREEN = SAFE
#         # lower_green = np.array([40, 100, 100])
#         # upper_green = np.array([90, 255, 255])

#         h, s, v = cv2.split(hsv)
#         clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#         v_equalized = clahe.apply(v)
        
#         hsv_balanced = cv2.merge([h, s, v_equalized])
#         hsv = cv2.GaussianBlur(hsv_balanced, (5, 5), 0)

#         # RED = DANGER
#         lower_red = np.array([0, 150, 150])
#         upper_red = np.array([10, 255, 255])

#         lower_green = np.array([35, 60, 60])   
#         upper_green = np.array([85, 255, 255])

#         # Generate original masks
#         red_mask = cv2.inRange(hsv, lower_red, upper_red)
#         green_mask = cv2.inRange(hsv, lower_green, upper_green)

#         # Count original pixel thresholds
#         red_pixels = np.sum(red_mask > 0)
#         green_pixels = np.sum(green_mask > 0)

#         # --- PERSON DETECTION LOGIC (Replaces Yellow) ---
#         # Downscale the frame layout slightly to ensure faster processing speeds
#         # processing_frame = cv2.resize(frame, (640, 480))
        
#         # detectMultiScale searches the matrix and returns bounding boxes around people
       
#         # (boxes, weights) = self.hog.detectMultiScale(
#         #     processing_frame, 
#         #     winStride=(8, 8), 
#         #     padding=(4, 4), 
#         #     scale=1.05
#         # )
        
#         results = self.model(frame, classes=0, verbose=False)
#         boxes = results[0].boxes


#         person_detected = len(boxes) > 0

#         status_msg = String()

#         # --- STATE MACHINE MATCHING LOGIC ---
#         # 1. Check for red danger blocks first
#         if red_pixels > 1000:
#             status_msg.data = "danger"
#             self.get_logger().warn("DANGER DETECTED (RED)")

#         # 2. Check for human presence next (Replaces Yellow Caution)
#         elif person_detected:
#             status_msg.data = "caution"
#             self.get_logger().info(f"CAUTION AREA -> {len(boxes)} PERSON DETECTED! SLOWING DOWN.")

#         # 3. Check for green exit tracking indicators
#         elif green_pixels > 1000:
#             status_msg.data = "safe"
#             self.get_logger().info("SAFE PATH (GREEN)")

#         # 4. Default state when nothing is found
#         else:
#             status_msg.data = "searching"
#             self.get_logger().info("SEARCHING FOR SAFE PATH")

#         # Publish the outcome string to the State Machine Node
#         self.status_pub.publish(status_msg)

#         # Publish the actual number of detected people
#         people_msg = String()
#         people_msg.data = f"People detected: {len(boxes)}"
#         self.people_pub.publish(people_msg)


# def main(args=None):
#     rclpy.init(args=args)
#     node = PerceptionNode()
    
#     try:
#         rclpy.spin(node)
#     except KeyboardInterrupt:
#         node.get_logger().info("Shutting down Perception Node...")
#     finally:
#         node.destroy_node()
#         rclpy.shutdown()


# if __name__ == "__main__":
#     main()