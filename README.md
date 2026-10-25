# Dockerized Simulation Environment for Drone Application Development

This repository provides a Dockerized simulation environment for testing ROS 2 Humble, ArduPilot, and MAVROS applications before trying them on a real drone. It runs an Iris quadcopter in Gazebo Harmonic with ArduCopter SITL, so developers can work without installing the full toolchain on their host computer and live through the dependency nightmare.

The current setup uses ROS 2 Humble, ArduCopter 4.5.7, MAVROS, and Gazebo Harmonic. These versions can be changed in the project configuration.

## Basic Setup

Prerequisites: an Intel/AMD x86_64 Linux PC, Docker Engine with Compose v2,
VS Code Dev Containers, a running graphical desktop, and host xauth.


1. Clone the project. On a host terminal, from the project root, prepare display access:

   ```bash
   bash .devcontainer/prepare-display.sh
   ```

   If xauth is missing, install it first:
   `sudo apt-get install xauth`.


2. In VS Code, press `CTRL + Shift + P` and run **Dev Containers: Rebuild and Reopen inContainer**. It might take some time for your first build.

## Commands and Shortcuts

### Start the simulation
In a terminal inside the container, run:
   ```bash
   start-sim
   ```
Gazebo opens with the Iris quadcopter on the runway. The simulator starts Gazebo, ArduCopter SITL, and MAVROS; the drone stays on the ground until you command it to fly.

In another container terminal, check the connection and vehicle state:
   ```bash
  drone-status
   ```

  Wait for `connected: true` and for the estimator and GPS to initialize before sending flight commands. Press Ctrl+C in the `start-sim` terminal to stop all three processes.



You can also start each process separately, in its own terminal:
```bash
start-gazebo
start-sitl
start-mavros
```
### Keyboard RC control
If you don’t have a physical radio receiver connected to a flight controller, you can use the keyboard controller to send virtual RC input to SITL:
```bash
drone-rc
```
The controller is in [`scripts/keyboard_rc.py`](scripts/keyboard_rc.py) and can be modified for your needs. It tests RC input in the simulator; it does not simulate a physical radio link, receiver wiring, or radio signal loss.

### Check status and request arming
Use this shortcut to view the MAVROS connection, mode, and armed state:
```bash
drone-status
```
To request ALT_HOLD mode and arming in SITL:
```bash
drone-arm
```
This sends an arming request; it does not guarantee the vehicle will arm. Check drone-status for `mode: ALT_HOLD` and `armed: true` before increasing throttle. Wait for estimator and GPS initialization first.

Example Script that takes off, hovers for 5 seconds by default, then lands (you can change the hover time as a parameter, example: 30):
```bash
drone-takeoff-land 30
```
 
