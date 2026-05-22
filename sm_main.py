#!/usr/bin/env python3
# -*-encoding:UTF-8-*-

"""
File: sm_main.py
Author: Kyutech ROS Group

Main node — assembles PatrolState and MappingState into a YASMIN state machine.

State machine layout (only 2 states: PATROL and MAPPING):

           "patrol"
            ┌───┐
            │   │   (loops on itself: next waypoint)
            ▼   │
        ┌───────────┐
        │  PATROL   │
        └───────────┘
            │
            │ "detected"  (alert received on /new_obstacle)
            ▼
        ┌───────────┐
        │  MAPPING  │   stops, rotates 360° to let
        └───────────┘   obstacle_mapper_node capture the
            │           full obstacle
            │ "mapped"
            ▼
        (back to PATROL)

PATROL keeps an internal waypoint index that advances at each successful
visit, so a single state is enough to cycle through all waypoints.

The state machine never exits on its own — patrol is an infinite loop.
Stop with Ctrl+C.
"""

# Import modules (ROS2 related)
import rclpy
from rclpy.node import Node

# Import modules (YASMIN related)
from yasmin import StateMachine
from yasmin_viewer import YasminViewerPub

# Import the state classes
from competition_pkg.states.patrol import PatrolState
from competition_pkg.states.mapping import MappingState


class StateMachineNode(Node):
    """StateMachineNode class (inherits from Node class)
    Node class that executes the state machine
    """

    def __init__(self):
        """Class initialization method"""
        # Override the constructor of the inherited Node class
        super().__init__("sm_main")

        # Create an instance of the StateMachine class
        # Outcome "EXIT" is declared but never reached in this state machine
        sm = StateMachine(outcomes=["EXIT"])

        # Add PATROL state to the state machine
        sm.add_state(
            name="PATROL",  # State name
            state=PatrolState(node=self),  # State instance
            transitions={  # Dictionary defining transitions to next states
                "patrol": "PATROL",      # Waypoint reached → continue patrol
                "detected": "MAPPING",   # New obstacle → switch to mapping
            },
        )

        # Add MAPPING state to the state machine
        sm.add_state(
            name="MAPPING",
            state=MappingState(node=self),
            transitions={
                "mapped": "PATROL",  # Scan complete → return to patrol
            },
        )

        # Publish state machine information to YASMIN Viewer
        # (accessible at http://localhost:5000 when yasmin_viewer_node is running)
        YasminViewerPub(fsm_name="SM_EVAC", fsm=sm)

        # Wait for the user to press Enter before starting
        # (matches the lab convention from Sample 2)
        self.get_logger().info("<< PLEASE ENTER TO START >>")
        input()

        # Execute the state machine
        outcome = sm()

        # Display log
        self.get_logger().info(
            f"State Machine finished with outcome: {outcome}")


def main(args=None):
    rclpy.init(args=args)
    try:
        node = StateMachineNode()
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()