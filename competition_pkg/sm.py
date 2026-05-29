# #!/usr/bin/env python3
# # -*- coding: UTF-8 -*-

# """
# File: sm_main.py

# Autonomous Rescue / Evacuation Robot
# - Green Exit Following
# - Red Obstacle Avoidance
# - Person Detection
# - Navigation State Machine
# """

# # =========================================================
# # ROS2 IMPORTS
# # =========================================================

# import rclpy

# from rclpy.node import Node
# from rclpy.duration import Duration

# from geometry_msgs.msg import Twist

# # =========================================================
# # YASMIN IMPORTS
# # =========================================================

# from yasmin import StateMachine
# from yasmin_viewer import YasminViewerPub

# # =========================================================
# # CUSTOM STATES
# # =========================================================

# from .state_main import follow
# from .state_main import navigation


# class StateMachineNode(Node):
#     """
#     Main State Machine Node
#     """

#     def __init__(self):

#         super().__init__("sm_main")

#         # =====================================================
#         # START MESSAGE
#         # =====================================================

#         self.get_logger().info(
#             "\033[42m\033[30m\033[1m"
#             "==== AUTONOMOUS RESCUE ROBOT START ===="
#             "\033[0m"
#         )

#         input("Press ENTER to start...\n")

#         self.get_logger().info("Mission Started!")

#         # =====================================================
#         # VELOCITY PUBLISHER
#         # =====================================================

#         self.vel_pub = self.create_publisher(
#             Twist,
#             "cmd_vel",
#             10
#         )

#         # =====================================================
#         # CREATE STATE MACHINE
#         # =====================================================

#         sm = StateMachine(
#             outcomes=["EXIT"]
#         )

#         # =====================================================
#         # FOLLOW / SEARCH STATE
#         # =====================================================

#         sm.add_state(
#             name="Follow",

#             state=follow.FollowState(
#                 node=self
#             ),

#             transitions={
#                 "person_found": "Navigation",
#                 "search_complete": "EXIT",
#             },
#         )

#         # =====================================================
#         # NAVIGATION STATE
#         # =====================================================

#         sm.add_state(
#             name="Navigation",

#             state=navigation.NavigationState(
#                 node=self
#             ),

#             transitions={
#                 "succeed": "EXIT",
#                 "failed": "Follow",
#             },
#         )

#         # =====================================================
#         # YASMIN VIEWER
#         # =====================================================

#         YasminViewerPub(
#             fsm_name="RESCUE_ROBOT_SM",
#             fsm=sm
#         )

#         # =====================================================
#         # EXECUTE STATE MACHINE
#         # =====================================================

#         self.get_logger().info(
#             "Executing State Machine..."
#         )

#         outcome = sm()

#         self.get_logger().info(
#             f"State Machine finished with outcome: {outcome}"
#         )


# # =========================================================
# # SHUTDOWN FUNCTION
# # =========================================================

# def shutdown(node: Node):

#     node.get_logger().info(
#         "Stopping Robot..."
#     )

#     pub = node.create_publisher(
#         Twist,
#         "cmd_vel",
#         10
#     )

#     # Stop robot
#     pub.publish(Twist())

#     node.get_clock().sleep_for(
#         Duration(seconds=1)
#     )

#     node.destroy_publisher(pub)

#     node.get_logger().info(
#         "Robot stopped safely."
#     )


# # =========================================================
# # MAIN FUNCTION
# # =========================================================

# def main(args=None):

#     rclpy.init(args=args)

#     node = None

#     try:

#         node = StateMachineNode()

#     except KeyboardInterrupt:

#         print("\nKeyboard Interrupt Detected!")

#     finally:

#         if node is not None:

#             shutdown(node)

#             node.destroy_node()

#         rclpy.shutdown()


# # =========================================================
# # ENTRY POINT
# # =========================================================

# if __name__ == "__main__":

#     main()
#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
sm_main.py
Autonomous Evacuation Rescue Robot
"""

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration

from geometry_msgs.msg import Twist

from yasmin import StateMachine
from yasmin_viewer import YasminViewerPub

from .state_main import follow
from .state_main import navigation


class StateMachineNode(Node):

    def __init__(self):

        super().__init__("sm_main")

        self.get_logger().info(
            "\033[42m\033[30m\033[1m"
            "==== EVACUATION ROBOT START ===="
            "\033[0m"
        )

        input("Press ENTER to start...\n")

        self.get_logger().info("Mission Started!")

        self.vel_pub = self.create_publisher(
            Twist,
            "cmd_vel",
            10
        )

        sm = StateMachine(outcomes=["EXIT"])

        # Search / Escort State
        sm.add_state(
            name="Follow",
            state=follow.FollowState(node=self),
            transitions={
                "exit_found": "Navigation",
                "search_complete": "EXIT",
            },
        )

        # Navigation State
        sm.add_state(
            name="Navigation",
            state=navigation.NavigationState(node=self),
            transitions={
                "succeed": "EXIT",
                "failed": "Follow",
            },
        )

        YasminViewerPub(
            fsm_name="EVACUATION_SM",
            fsm=sm
        )

        self.get_logger().info("Executing State Machine...")

        outcome = sm()

        self.get_logger().info(
            f"State Machine finished: {outcome}"
        )


def shutdown(node: Node):

    node.get_logger().info("Stopping Robot...")

    pub = node.create_publisher(
        Twist,
        "cmd_vel",
        10
    )

    pub.publish(Twist())

    node.get_clock().sleep_for(
        Duration(seconds=1)
    )

    node.destroy_publisher(pub)

    node.get_logger().info("Robot stopped safely.")


def main(args=None):

    rclpy.init(args=args)

    node = None

    try:
        node = StateMachineNode()

    except KeyboardInterrupt:
        print("\nKeyboard Interrupt Detected!")

    finally:

        if node is not None:
            shutdown(node)
            node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()
