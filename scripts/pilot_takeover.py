import time
from mavros_msgs.msg import RCIn
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy


class PilotTakeover(Exception):
    pass


class PilotTakeoverGuard:
    def __init__(self, node):
        self.state = None
        self.state_time = self.rc_time = 0.0
        self.rc5 = None
        self.enabled = False
        self.reason = None
        self.expected_modes = {"GUIDED"}
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.subscription = node.create_subscription(
            RCIn, "/mavros/rc/in", self.receive_rc, qos
        )

    def cancel(self, reason):
        if self.reason is None:
            self.reason = reason

    def observe_state(self, msg):
        self.state = msg
        self.state_time = time.monotonic()
        if self.enabled and msg.connected and msg.mode:
            if msg.mode not in self.expected_modes:
                self.cancel(f"Flight mode changed to {msg.mode}")
            elif msg.mode == "LAND" and "LAND" in self.expected_modes:
                self.expected_modes = {"LAND"}

    def receive_rc(self, msg):
        self.rc_time = time.monotonic()
        self.rc5 = msg.channels[4] if len(msg.channels) >= 5 else None
        if self.enabled and self.rc_valid() and self.rc5 > 1230:
            self.cancel("RC mode switch selected ALT_HOLD")

    def rc_valid(self):
        return self.rc5 is not None and 900 <= self.rc5 <= 2200

    def fresh(self):
        now = time.monotonic()
        return (
            self.state is not None
            and self.state.connected
            and now - self.state_time < 3.0
            and self.rc_valid()
            and now - self.rc_time < 1.5
        )

    def ready(self):
        return (
            self.fresh()
            and self.state.mode == "GUIDED"
            and self.rc5 <= 1230
        )

    def begin(self):
        if not self.ready():
            raise RuntimeError("Select GUIDED on the RC controller first")
        self.enabled = True
        self.check()

    def check(self):
        if not self.enabled:
            return
        if self.reason is not None:
            raise PilotTakeover(self.reason)
        if not self.fresh():
            raise RuntimeError("Fresh connected state/RC telemetry was lost")
        if self.rc5 > 1230 or self.state.mode not in self.expected_modes:
            self.cancel("Pilot selected another mode")
            raise PilotTakeover(self.reason)

    def expect_land(self):
        self.check()
        if "LAND" not in self.expected_modes:
            self.expected_modes = {"GUIDED", "LAND"}
