# import time
# from geometry_msgs.msg import Twist
# from yasmin import State
# from yasmin import Blackboard

# class CautionState(State):

#     def __init__(self, node):
#         super().__init__(
#             outcomes=["caution", "continue"]
#         )
#         self.node = node

#     def execute(self, blackboard: Blackboard):
#         try:
#             status = blackboard["current_status"]
#         except KeyError:
#             status = "searching"

#         self.node.get_logger().info(f"CAUTION STATE TICK -> Status: {status}")

#         # If a person is still detected, keep moving forward but SLOWLY
#         if status == "caution":
#             cmd = Twist()
#             cmd.linear.x = 0.03   # Half the speed of searching (very slow/safe)
#             cmd.angular.z = 0.0   # Drive straight carefully
#             self.node.cmd_pub.publish(cmd)
            
#             time.sleep(0.1)
#             return "caution"
        
#         # If the person moves out of the way, continue back to standard searching/following
#         else:
#             self.node.get_logger().info("Path clear of people! Continuing.")
#             return "continue"


#!/usr/bin/env python3
import time
from geometry_msgs.msg import Twist
from yasmin import State
from yasmin import Blackboard

class CautionState(State):

    def __init__(self, node):
        super().__init__(
            outcomes=["caution", "continue"]
        )
        self.node = node
        
        # Internal step tracker for finding an alternative route
        # 0 = Stop immediately, 1 = Scan Right, 2 = Scan Left, 3 = Turn Around
        self.sequence_step = 0
        self.step_timer = 0

    def execute(self, blackboard: Blackboard):
        try:
            status = blackboard["current_status"]
        except KeyError:
            status = "searching"

        self.node.get_logger().info(f"CAUTION STATE TICK -> Status: {status}, Step: {self.sequence_step}")

        # --- CONDITION 1: Green / Clear Space Found! ---
        # The moment a green/searching route is found during a scan, 
        # stop turning immediately and move forward.
        if status == "searching" and self.sequence_step in [1, 2]:
            self.node.get_logger().info("Green/Clear route detected during scan! Transitioning to continue.")
            cmd = Twist()  # Stop turning
            self.node.cmd_pub.publish(cmd)
            self.sequence_step = 0  # Reset for next time
            self.step_timer = 0
            return "continue"

        # --- CONDITION 2: Execute Route Hunting Sequence ---
        cmd = Twist()

        # STEP 0: Stop immediately to prevent moving too close to the person
        if self.sequence_step == 0:
            cmd.linear.x = 0.0
            cmd.angular.z = 0.0
            self.step_timer += 1
            if self.step_timer >= 10:  # 10 ticks * 0.1s sleep = 1.0 second pause
                self.sequence_step = 1  # Start scanning right
                self.step_timer = 0

        # STEP 1: Scan Right First (Turn right slowly for approx 2.5 seconds to find green)
        elif self.sequence_step == 1:
            cmd.linear.x = 0.0
            cmd.angular.z = -0.3  # Negative value turns right
            self.step_timer += 1
            if self.step_timer >= 25:  # 25 ticks = 2.5 seconds
                self.sequence_step = 2  # No green on the right? Try left
                self.step_timer = 0

        # STEP 2: Scan Left (Turn back left for approx 5.0 seconds to check the other side)
        elif self.sequence_step == 2:
            cmd.linear.x = 0.0
            cmd.angular.z = 0.3   # Positive value turns left
            self.step_timer += 1
            if self.step_timer >= 50:  # 50 ticks = 5.0 seconds
                self.sequence_step = 3  # Both sides blocked? Escape/Turn around
                self.step_timer = 0

        # STEP 3: Turn Around Completely
        elif self.sequence_step == 3:
            cmd.linear.x = -0.02  # Back away slightly to keep a safe distance
            cmd.angular.z = 0.5   # Spin away quickly
            
            if status == "searching":
                self.node.get_logger().info("Found clear space while turning back. Continuing.")
                self.sequence_step = 0  
                self.step_timer = 0
                return "continue"

        # Publish the steering command calculated by our current step
        self.node.cmd_pub.publish(cmd)
        
        # Keep our 10Hz throttle rate limit
        time.sleep(0.1)
        return "caution"