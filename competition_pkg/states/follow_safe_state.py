# #!/usr/bin/env python3

# import rclpy

# from std_msgs.msg import String

# from yasmin import State
# from yasmin import Blackboard


# class FollowSafeState(State):

#     def __init__(self, node):

#         super().__init__(outcomes=["danger", "safe", "caution"])

#         self.node = node

#         self.current_status = "searching"

#         self.status_sub = self.node.create_subscription(
#             String,
#             "/evacuation_status",
#             self.status_callback,
#             10,
#         )

#     def status_callback(self, msg):

#         self.current_status = msg.data

#     def execute(self, blackboard: Blackboard):

#         while rclpy.ok():

#             rclpy.spin_once(self.node)

#             self.node.get_logger().info(
#                 f"Current Status: {self.current_status}"
#             )

#             if self.current_status == "danger":
#                 return "danger"

#             elif self.current_status == "caution":
#                 return "caution"

#             elif self.current_status == "safe":
#                 return "safe"





# ##############################
# #!/usr/bin/env python3

# import rclpy
# from geometry_msgs.msg import Twist
# from yasmin import State
# from yasmin import Blackboard


# class FollowSafeState(State):

#     def __init__(self, node):
#         super().__init__(outcomes=["danger", "safe", "caution", "searching"])
#         self.node = node
#         self.movement_timer = 0 

#     def execute(self, blackboard: Blackboard):
#         # Read status updated globally by the subscription callback
#         status = self.node.current_status

#         if status == "searching":
#             cmd = Twist()
#             self.movement_timer += 1

#             # Alternate driving patterns to roam "here and there"
#             if (self.movement_timer % 40) < 20:
#                 cmd.linear.x = 0.15   
#                 cmd.angular.z = 0.25  
#                 self.node.get_logger().info("Searching: Driving curves left...")
#             else:
#                 cmd.linear.x = 0.10   
#                 cmd.angular.z = -0.4  
#                 self.node.get_logger().info("Searching: Adjusting angle right...")

#             self.node.cmd_pub.publish(cmd)
#             return "searching"  # Transitions back into itself cleanly via the SM configuration

#         elif status == "danger":
#             return "danger"

#         elif status == "caution":
#             return "caution"

#         elif status == "safe":
#             return "safe"


###################WORKING##################
#!/usr/bin/env python3
# import time  
# from geometry_msgs.msg import Twist
# from yasmin import State     
# from yasmin import Blackboard
# class FollowSafeState(State):

#     def __init__(self, node):
#         super().__init__(
#             outcomes=["danger", "safe", "caution", "searching"]
#         )
#         self.node = node
#         self.movement_timer = 0

#     def execute(self, blackboard: Blackboard):
#         # Grab the live status directly from the subscribed node data
#         status = self.node.current_status

#         self.node.get_logger().info(f"FOLLOW_SAFE -> Current View: {status}")

#         # Check conditions and return the YASMIN outcome instantly
#         if status == "danger":
#             self.node.get_logger().warn("TRANSITION -> DANGER")
#             return "danger"

#         if status == "safe":
#             self.node.get_logger().info("TRANSITION -> NAVIGATION")
#             return "safe"

#         if status == "caution":
#             self.node.get_logger().info("TRANSITION -> CAUTION")
#             return "caution"

#         # Searching behavior (if no color or status is 'searching')
#         cmd = Twist()
#         self.movement_timer += 1

#         if (self.movement_timer % 80) < 40:
#             cmd.linear.x = 0.08
#             cmd.angular.z = 0.20
#         else:
#             cmd.linear.x = 0.08
#             cmd.angular.z = -0.20

#         self.node.cmd_pub.publish(cmd)
#         return "searching"




import time
from geometry_msgs.msg import Twist
from yasmin import State
from yasmin import Blackboard

class FollowSafeState(State):

    def __init__(self, node):
        super().__init__(
            outcomes=["danger", "safe", "caution", "searching"]
        )
        self.node = node
        self.movement_timer = 0

    def execute(self, blackboard: Blackboard):
        # Fetch the background-updated variable from the blackboard safely
        try:
            status = blackboard["current_status"]
        except KeyError:
            status = "searching"

        self.node.get_logger().info(f"FOLLOW_SAFE TICK -> Status: {status}")

        # Check conditions and return the structural transition outcome strings
        if status == "danger":
            self.node.get_logger().warn("TRANSITION -> SWITCHING TO DANGER")
            return "danger"

        if status == "safe":
            self.node.get_logger().info("TRANSITION -> SWITCHING TO NAVIGATION")
            return "safe"

        if status == "caution":
            self.node.get_logger().info("TRANSITION -> SWITCHING TO CAUTION")
            return "caution"

        # Default Searching Behavior (wobbling forward pattern)
        cmd = Twist()
        self.movement_timer += 1

        if (self.movement_timer % 80) < 40:
            cmd.linear.x = 0.08
            cmd.angular.z = 0.20
        else:
            cmd.linear.x = 0.08
            cmd.angular.z = -0.20

        self.node.cmd_pub.publish(cmd)
        
        # Micro-sleep allows the parallel ROS subscription callback thread 
        # to cleanly update the blackboard data without race delays
        time.sleep(0.1)
        
        return "searching"