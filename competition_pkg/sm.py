#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
File: sm_main.py

Autonomous Rescue / Evacuation Robot
- Green Exit Following
- Red Obstacle Avoidance
- Person Detection
- Navigation State Machine
"""

# =========================================================
# ROS2 IMPORTS
# =========================================================

import rclpy

from rclpy.node import Node
from rclpy.duration import Duration

from geometry_msgs.msg import Twist

# =========================================================
# YASMIN IMPORTS
# =========================================================

from yasmin import StateMachine
from yasmin_viewer import YasminViewerPub

# =========================================================
# CUSTOM STATES
# =========================================================

from .state_main import follow
from .state_main import navigation


class StateMachineNode(Node):
    """
    Main State Machine Node
    """

    def __init__(self):

        super().__init__("sm_main")

        # =====================================================
        # START MESSAGE
        # =====================================================

        self.get_logger().info(
            "\033[42m\033[30m\033[1m"
            "==== AUTONOMOUS RESCUE ROBOT START ===="
            "\033[0m"
        )

        input("Press ENTER to start...\n")

        self.get_logger().info("Mission Started!")

        # =====================================================
        # VELOCITY PUBLISHER
        # =====================================================

        self.vel_pub = self.create_publisher(
            Twist,
            "cmd_vel",
            10
        )

        # =====================================================
        # CREATE STATE MACHINE
        # =====================================================

        sm = StateMachine(
            outcomes=["EXIT"]
        )

        # =====================================================
        # FOLLOW / SEARCH STATE
        # =====================================================

        sm.add_state(
            name="Follow",

            state=follow.FollowState(
                node=self
            ),

            transitions={
                "person_found": "Navigation",
                "search_complete": "EXIT",
            },
        )

        # =====================================================
        # NAVIGATION STATE
        # =====================================================

        sm.add_state(
            name="Navigation",

            state=navigation.NavigationState(
                node=self
            ),

            transitions={
                "succeed": "EXIT",
                "failed": "Follow",
            },
        )

        # =====================================================
        # YASMIN VIEWER
        # =====================================================

        YasminViewerPub(
            fsm_name="RESCUE_ROBOT_SM",
            fsm=sm
        )

        # =====================================================
        # EXECUTE STATE MACHINE
        # =====================================================

        self.get_logger().info(
            "Executing State Machine..."
        )

        outcome = sm()

        self.get_logger().info(
            f"State Machine finished with outcome: {outcome}"
        )


# =========================================================
# SHUTDOWN FUNCTION
# =========================================================

def shutdown(node: Node):

    node.get_logger().info(
        "Stopping Robot..."
    )

    pub = node.create_publisher(
        Twist,
        "cmd_vel",
        10
    )

    # Stop robot
    pub.publish(Twist())

    node.get_clock().sleep_for(
        Duration(seconds=1)
    )

    node.destroy_publisher(pub)

    node.get_logger().info(
        "Robot stopped safely."
    )


# =========================================================
# MAIN FUNCTION
# =========================================================

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


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()
# #!/usr/bin/env python3
# # -*-encoding:UTF-8-*-

# """
# File: sm_main.py
# Author: Tomoaki Fujino（Kyushu Institute of Technology, Hibikino-Musashi@Home）

# """

# # Import modules (ROS2 related)
# import rclpy
# from rclpy.node import Node
# from rclpy.duration import Duration
# from geometry_msgs.msg import Twist


# # Import modules (YASMIN related)
# # https://github.com/uleroboticsgroup/yasmin.git
# from yasmin import StateMachine
# from yasmin_viewer import YasminViewerPub

# # Import modules (Custom: Each state)
# from .state_main import follow, navigation


# class StateMachineNode(Node):
#     """StateMachineNode class (inherits from Node class)
#     Node class that executes the state machine
#     """

#     def __init__(self):
#         """Class initialization method"""
#         super().__init__("sm_main")

#         self.get_logger().info("\033[43m\033[30m\033[1m<< PLEASE ENTER TO START >>\033[0m")
#         input()
#         self.get_logger().info("Task Start!!")

#         self.vel_pub = self.create_publisher(msg_type=Twist, topic="cmd_vel", qos_profile=10)

#         # Create an instance of the StateMachine class
#         sm = StateMachine(outcomes=["EXIT"])

#         # Add FollowState to the state machine
#         sm.add_state(
#             name="Follow",
#             state=follow.FollowState(node=self),
#             transitions={"outcome": "Navigation"},
#         )

#         # Add NavigationState to the state machine
#         sm.add_state(
#             name="Navigation",
#             state=navigation.NavigationState(node=self),
#             transitions={"succeed": "EXIT", "failed": "Follow"},
#         )

#         # Publish state machine information to Yasmin Viewer
#         YasminViewerPub(fsm_name="SM_MAIN", fsm=sm)

#         # Execute the state machine
#         outcome = sm()
#         self.get_logger().info("State Machine finished with outcome: " + outcome)


# def shutdown(node: Node):
#     """Shutdown function
#     Stop TurtleBot3 when terminating

#     Args:
#         node (Node): Node object
#     """
#     node.get_logger().info("Follow State Cleanup!!")
#     pub = node.create_publisher(Twist, "cmd_vel", 10)
#     pub.publish(Twist())
#     node.get_clock().sleep_for(Duration(nanoseconds=100))
#     node.destroy_publisher(pub)


# def main(args=None):
#     """Main function"""
#     # Initialize ROS2 Python client library
#     rclpy.init(args=args)

#     # Create an instance of StateMachineNode class
#     try:
#         node = StateMachineNode()
#     except KeyboardInterrupt:
#         pass
#     finally:
#         shutdown(node)
#         node.destroy_node()
#         rclpy.shutdown()


# if __name__ == "__main__":
#     main()
