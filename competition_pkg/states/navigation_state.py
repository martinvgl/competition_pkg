


#!/usr/bin/env python3
#!/usr/bin/env python3
# from geometry_msgs.msg import Twist
# from yasmin import State
# from yasmin import Blackboard

# class NavigationState(State):

#     def __init__(self, node):
#         super().__init__(
#             outcomes=[
#                 "navigating",
#                 "done"
#             ]
#         )
#         self.node = node

#     def execute(self, blackboard: Blackboard):
#         status = blackboard["current_status"]
#         self.node.get_logger().info(f"NAVIGATION STATE TICK -> Status: {status}")

#         # If higher priority signals break the safe path, exit navigation
#         if status in ["danger", "caution"]:
#             return "done"

#         # If GREEN path is solid, drive forward confidently
#         if status == "safe":
#             cmd = Twist()
#             cmd.linear.x = 0.15  # Full cruising speed
#             cmd.angular.z = 0.0
#             self.node.cmd_pub.publish(cmd)
            
#             return "navigating"
        
#         # If green disappears and goes back to searching
#         else:
#             self.node.get_logger().info("Safe path lost. Returning to search behavior.")
#             return "done"




import time  # <--- Import time for the loop delay
from geometry_msgs.msg import Twist
from yasmin import State
from yasmin import Blackboard

class NavigationState(State):

    def __init__(self, node):
        super().__init__(
            outcomes=[
                "navigating",
                "done"
            ]
        )
        self.node = node

    def execute(self, blackboard: Blackboard):
        # Safe lookup for the live status
        try:
            status = blackboard["current_status"]
        except KeyError:
            status = "searching"

        self.node.get_logger().info(f"NAVIGATION STATE TICK -> Status: {status}")

        # If higher priority signals (Red/Person) break the safe path, exit navigation immediately
        if status in ["danger", "caution"]:
            self.node.get_logger().warn(f"Navigation interrupted by: {status.upper()}")
            return "done"

        # If GREEN path is solid, drive forward confidently at cruising speed
        if status == "safe":
            cmd = Twist()
            cmd.linear.x = 0.15  # Full cruising speed
            cmd.angular.z = 0.0
            self.node.cmd_pub.publish(cmd)
            
            # --- CRITICAL FIX: Throttle the background loop rate ---
            time.sleep(0.1) 
            return "navigating"
        
        # If green disappears and goes back to searching, drop out to follow_safe
        else:
            self.node.get_logger().info("Safe path lost. Returning to search behavior.")
            return "done"