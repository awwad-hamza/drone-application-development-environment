#!/usr/bin/env python3
import socket
import struct
import time
import tkinter as tk
import rclpy
from mavros_msgs.msg import State
from std_msgs.msg import Bool
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

DESTINATION = ("127.0.0.1", 5501)
STICK_AMOUNT = 200
THROTTLE_RATE = 250  # PWM units per second

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
pressed = set()
release_jobs = {}
throttle = 1000.0
mode_pwm = 1000  # CH5: GUIDED=1000, ALT_HOLD=2000
previous_time = time.monotonic()
stop_latched = False
stop_requested = False
live_state = None
live_state_time = 0.0

root = tk.Tk()
root.title("SITL Keyboard Radio")
root.geometry("620x560")
root.configure(bg="#172033")

tk.Label(
    root,
    text="KEYBOARD RADIO",
    font=("Sans", 20, "bold"),
    bg="#172033", fg="white",
).pack(pady=(20, 12))

tk.Label(
    root,
    text=(
        "W / S       Throttle increase / decrease\n"
        "A / D       Yaw left / right\n"
        "↑ / ↓       Pitch forward / backward\n"
        "← / →       Roll left / right\n\n"
        "C: throttle centre     Esc: close\n"
        "1: GUIDED             2: ALT_HOLD\n"
        "Hold SPACE: motor stop   R: reset after disarm"
    ),
    font=("Monospace", 13),
    justify="left",
    bg="#172033", fg="#cbd5e1",
).pack()

values = tk.StringVar()
tk.Label(
    root, textvariable=values,
    font=("Monospace", 12),
    bg="#172033", fg="#67e8f9",
).pack(pady=18)

tk.Label(
    root,
    text="Click this window to control. Throttle holds its position.",
    bg="#172033", fg="#cbd5e1",
).pack()


rclpy.init()
ros_node = rclpy.create_node("keyboard_rc_safety")

state_qos = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
)
stop_qos = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)

def receive_state(msg):
    global live_state, live_state_time
    live_state, live_state_time = msg, time.monotonic()

state_sub = ros_node.create_subscription(
    State, "/mavros/state", receive_state, state_qos
)
stop_pub = ros_node.create_publisher(
    Bool, "/x650/safety/stop_requested", stop_qos
)
stop_pub.publish(Bool(data=False))

notice = tk.StringVar(
    value="Motor stop uses RC7. Release can restart armed motors."
)
tk.Label(
    root, textvariable=notice, wraplength=580,
    bg="#172033", fg="#fbbf24",
).pack(pady=8)

def stop_active():
    return stop_latched or "space" in pressed

def confirmed_disarmed():
    return (
        live_state is not None
        and live_state.connected
        and time.monotonic() - live_state_time < 3.0
        and not live_state.armed
    )

def request_stop():
    global stop_requested
    if not stop_requested:
        stop_requested = True
        stop_pub.publish(Bool(data=True))
    notice.set("Stop requested. Releasing SPACE can restart armed motors.")

def reset_stop():
    global stop_latched, stop_requested
    if "space" in pressed or not confirmed_disarmed():
        notice.set(
            "Release SPACE and confirm SITL is disarmed before pressing R."
        )
        return
    stop_latched = stop_requested = False
    stop_pub.publish(Bool(data=False))
    notice.set(
        "Stop reset. A cancelled flight script must be restarted explicitly."
    )

def focus_lost(event):
    global stop_latched
    if stop_active():
        stop_latched = True
        request_stop()
        notice.set(
            "Focus lost during stop: STOP HELD. Disarm SITL, then press R."
        )
    pressed.clear()

def close():
    if stop_active() and not confirmed_disarmed():
        notice.set("Stop is active: disarm SITL before closing this window.")
        return
    ros_node.destroy_node()
    rclpy.try_shutdown()
    sock.close()
    root.destroy()


def select_mode(pwm):
    global mode_pwm
    mode_pwm = pwm
    root.focus_set()


mode_buttons = tk.Frame(root, bg="#172033")
mode_buttons.pack(pady=8)
tk.Button(
    mode_buttons, text="1: GUIDED",
    command=lambda: select_mode(1000),
).pack(side="left", padx=8)
tk.Button(
    mode_buttons, text="2: ALT_HOLD",
    command=lambda: select_mode(2000),
).pack(side="left", padx=8)


def key_down(event):
    global throttle
    key = event.keysym.lower()

    # X11 can report release/press pairs during keyboard auto-repeat.
    job = release_jobs.pop(key, None)
    if job is not None:
        root.after_cancel(job)

    if key == "escape":
        close()
        return

    if key == "space":
        request_stop()
    if key == "r":
        reset_stop()

    if key in ("1", "2"):
        select_mode(1000 if key == "1" else 2000)

    if key == "c":
        throttle = 1500.0

    pressed.add(key)


def finish_release(key):
    release_jobs.pop(key, None)
    pressed.discard(key)


def key_up(event):
    key = event.keysym.lower()
    old_job = release_jobs.pop(key, None)
    if old_job is not None:
        root.after_cancel(old_job)
    release_jobs[key] = root.after(10, finish_release, key)


def tick():
    global throttle, previous_time

    for _ in range(4):
        rclpy.spin_once(ros_node, timeout_sec=0.0)
    now = time.monotonic()
    dt = min(now - previous_time, 0.1)
    previous_time = now

    throttle += (
        int("w" in pressed) - int("s" in pressed)
    ) * THROTTLE_RATE * dt
    throttle = max(1000.0, min(2000.0, throttle))

    roll = 1500 + STICK_AMOUNT * (
        int("right" in pressed) - int("left" in pressed)
    )
    pitch = 1500 + STICK_AMOUNT * (
        int("down" in pressed) - int("up" in pressed)
    )
    yaw = 1500 + STICK_AMOUNT * (
        int("d" in pressed) - int("a" in pressed)
    )

    # Default ArduCopter mapping:
    # CH1 roll, CH2 pitch, CH3 throttle, CH4 yaw.
    # Zero leaves the other SITL channels unchanged.
    stop_pwm = 2000 if stop_active() else 1000
    channels = [
        roll, pitch, round(throttle), yaw, mode_pwm, 0, stop_pwm
    ] + [0] * 9
    sock.sendto(struct.pack("<16H", *channels), DESTINATION)

    values.set(
        f"Roll {roll:4d}   Pitch {pitch:4d}\n"
        f"Throttle {round(throttle):4d}   Yaw {yaw:4d}\n"
        f"CH5 {mode_pwm}: requesting {'GUIDED' if mode_pwm == 1000 else 'ALT_HOLD'}\n"
        f"CH7 {stop_pwm}: {'STOP REQUESTED' if stop_pwm == 2000 else 'stop released'}\n"
        f"Stop event: {'reset with R after disarm' if stop_requested else 'ready'}"
    )
    root.after(20, tick)


root.bind("<KeyPress>", key_down)
root.bind("<KeyRelease>", key_up)
root.bind("<FocusOut>", focus_lost)
root.focus_set()
root.protocol("WM_DELETE_WINDOW", close)

tick()
root.mainloop()
