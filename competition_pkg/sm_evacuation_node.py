
import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist

from yasmin import StateMachine, Blackboard
from yasmin_viewer import YasminViewerPub

from .states import follow_safe_state
from .states import danger_state
from .states import caution_state
from .states import navigation_state


class StateMachineNode(Node):

    def __init__(self):
        super().__init__("sm_evacuation_node")

        self.get_logger().info(
            "Emergency Evacuation State Machine Started"
        )

        # Initialize the Blackboard
        self.blackboard = Blackboard()
        self.blackboard["current_status"] = "searching"

        # Subscription to Perception Node
        self.status_sub = self.create_subscription(
            String,
            "/evacuation_status",
            self.perception_callback,
            10,
        )

        # Publisher for Robot Movement
        self.cmd_pub = self.create_publisher(
            Twist,
            "/cmd_vel",
            10,
        )

        # Setup State Machine Architecture
        self.sm = StateMachine(outcomes=["EXIT"])

        self.sm.add_state(
            name="FOLLOW_SAFE",
            state=follow_safe_state.FollowSafeState(self),
            transitions={
                "danger": "DANGER",
                "safe": "NAVIGATION",
                "caution": "CAUTION",
                "searching": "FOLLOW_SAFE",
            },
        )

        self.sm.add_state(
            name="DANGER",
            state=danger_state.DangerState(self),
            transitions={
                "danger": "DANGER",
                "recover": "FOLLOW_SAFE",
            },
        )

        self.sm.add_state(
            name="CAUTION",
            state=caution_state.CautionState(self),
            transitions={
                "caution": "CAUTION",
                "continue": "FOLLOW_SAFE",
            },
        )

        self.sm.add_state(
            name="NAVIGATION",
            state=navigation_state.NavigationState(self),
            transitions={
                "navigating": "NAVIGATION",
                "done": "FOLLOW_SAFE",
            },
        )

        # Yasmin Visualizer Link
        YasminViewerPub(
            fsm_name="EMERGENCY_EVACUATION",
            fsm=self.sm,
        )

        # RUN STATE MACHINE IN A BACKGROUND THREAD
        # This prevents the blocking execute() from freezing the ROS node executor
        self.sm_thread = threading.Thread(target=self.run_state_machine)
        self.sm_thread.daemon = True
        self.sm_thread.start()

    def perception_callback(self, msg):
        # Safely update the shared blackboard dynamically
        self.blackboard["current_status"] = msg.data
        self.get_logger().info(f"BLACKBOARD UPDATED -> {msg.data}")

    def run_state_machine(self):
        self.get_logger().info("YASMIN State Machine Loop Thread Active.")
        try:
            final_outcome = self.sm.execute(self.blackboard)
            self.get_logger().warn(f"FSM exited with final outcome: {final_outcome}")
        except Exception as e:
            self.get_logger().error(f"FSM RUNTIME ERROR: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = StateMachineNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Force robot stop on shutdown
        stop = Twist()
        node.cmd_pub.publish(stop)
        
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()


