#!/usr/bin/env python3

# from yasmin import State
# from yasmin import Blackboard


# class DangerState(State):

#     def __init__(self, node):

#         super().__init__(outcomes=["recover"])

#         self.node = node

#     def execute(self, blackboard: Blackboard):

#         self.node.get_logger().warn(
#             "DANGER DETECTED"
#         )

#         return "recover"





#!/usr/bin/env python3
import time
from geometry_msgs.msg import Twist
from yasmin import State
from yasmin import Blackboard

class DangerState(State):

    def __init__(self, node):
        super().__init__(
            outcomes=["danger", "recover"]
        )
        self.node = node

    def execute(self, blackboard: Blackboard):
        try:
            status = blackboard["current_status"]
        except KeyError:
            status = "searching"

        self.node.get_logger().error(f"DANGER STATE TICK -> Status: {status}")
import time
from geometry_msgs.msg import Twist
from yasmin import State
from yasmin import Blackboard

class DangerState(State):

    def __init__(self, node):
        super().__init__(
            outcomes=["danger", "recover"]
        )
        self.node = node
        
        # Internal step tracker for the danger sequence
        # 0 = Stop, 1 = Scan Left, 2 = Scan Right, 3 = Turn Back
        self.sequence_step = 0
        self.step_timer = 0

    def execute(self, blackboard: Blackboard):
        try:
            status = blackboard["current_status"]
        except KeyError:
            status = "searching"

        self.node.get_logger().error(f"DANGER STATE TICK -> Status: {status}, Step: {self.sequence_step}")

        # --- CONDITION 1: Clear Space Found! ---
        # If we are looking around (Steps 1 or 2) and the vision clears up completely,
        # immediately stop turning and switch back to searching/following!
        if status == "searching" and self.sequence_step in [1, 2]:
            self.node.get_logger().info("Clear space detected during scan! Transitioning to recover.")
            cmd = Twist()  # Stop turning
            self.node.cmd_pub.publish(cmd)
            self.sequence_step = 0  # Reset for next time
            self.step_timer = 0
            return "recover"

        # --- CONDITION 2: Execute Danger Avoidance Sequence ---
        cmd = Twist()

        # STEP 0: Stop completely for a moment (approx 1.5 seconds)
        if self.sequence_step == 0:
            cmd.linear.x = 0.0
            cmd.angular.z = 0.0
            self.step_timer += 1
            if self.step_timer >= 15:  # 15 ticks * 0.1s sleep = 1.5 seconds
                self.sequence_step = 1
                self.step_timer = 0

        # STEP 1: Scan Left (Turn left slowly for approx 2 seconds)
        elif self.sequence_step == 1:
            cmd.linear.x = 0.0
            cmd.angular.z = 0.3  # Turn left
            self.step_timer += 1
            if self.step_timer >= 20:  # 20 ticks = 2.0 seconds
                self.sequence_step = 2  # Move to next step if still red
                self.step_timer = 0

        # STEP 2: Scan Right (Turn back right for approx 4 seconds to check the other side)
        elif self.sequence_step == 2:
            cmd.linear.x = 0.0
            cmd.angular.z = -0.3  # Turn right
            self.step_timer += 1
            if self.step_timer >= 40:  # 40 ticks = 4.0 seconds
                self.sequence_step = 3  # Still blocked? Time to turn around
                self.step_timer = 0

        # STEP 3: Turn Around completely (Escape)
        elif self.sequence_step == 3:
            cmd.linear.x = 0.0
            cmd.angular.z = 0.5  # Spin faster to completely turn back
            
            # If the camera finally loses the red danger zone, we can recover
            if status != "danger":
                self.node.get_logger().info("Turned away from danger. Recovering.")
                self.sequence_step = 0  # Reset sequence tracker
                self.step_timer = 0
                return "recover"

        # Publish the command calculated by our current step
        self.node.cmd_pub.publish(cmd)
        
        # Keep our 10Hz throttle rate limit
        time.sleep(0.1)
        return "danger"
