#!/usr/bin/env python3
import socket
import struct
import time
import tkinter as tk

DESTINATION = ("127.0.0.1", 5501)
STICK_AMOUNT = 200
THROTTLE_RATE = 250  # PWM units per second

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
pressed = set()
release_jobs = {}
throttle = 1000.0
mode_pwm = 1000  # CH5: GUIDED=1000, ALT_HOLD=2000
previous_time = time.monotonic()

root = tk.Tk()
root.title("SITL Keyboard Radio")
root.geometry("620x430")
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
        "1: GUIDED             2: ALT_HOLD"
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


def close():
    sock.close()
    root.destroy()


def select_mode(pwm):
    global mode_pwm
    mode_pwm = pwm


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
    channels = [roll, pitch, round(throttle), yaw, mode_pwm] + [0] * 11
    sock.sendto(struct.pack("<16H", *channels), DESTINATION)

    values.set(
        f"Roll {roll:4d}   Pitch {pitch:4d}\n"
        f"Throttle {round(throttle):4d}   Yaw {yaw:4d}\n"
        f"CH5 {mode_pwm}: requesting {'GUIDED' if mode_pwm == 1000 else 'ALT_HOLD'}\n"
        "Confirm actual mode with drone-status"
    )
    root.after(20, tick)


root.bind("<KeyPress>", key_down)
root.bind("<KeyRelease>", key_up)
root.bind("<FocusOut>", lambda event: pressed.clear())
root.protocol("WM_DELETE_WINDOW", close)

tick()
root.mainloop()
