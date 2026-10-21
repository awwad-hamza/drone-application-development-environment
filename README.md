# Dockerized Simulation Environment To Test Autonomous Drone Applications Before Applying on Hardware

This repository provides a dockerized environment of an iris quadcopter to test your ros2 humble, ardupilot and mavros related code before transferring to a real drone. Of course it can be customized with different versions but this is an effort to help alleviate the pressure of the dependency nightmares faced my developers.

## Basic Setup

Prerequisites: an Intel/AMD x86_64 Linux PC, Docker Engine with Compose v2,
VS Code Dev Containers, a running graphical desktop, and host xauth.


1. Clone the project, then onn a HOST desktop terminal, from the project root:

   ```bash
   bash .devcontainer/prepare-display.sh
   ```

   If xauth is missing, on Ubuntu/Debian install it first:
   `sudo apt-get install xauth`.


2. In VS Code, press `CTRL + Shift + P` => **Dev Containers: Rebuild and Reopen inContainer**.

## Commands and Shortcuts

### Simulation
Gazebo opens with the Iris quadcopter on the runway. This starts the simulator
   and bridge; the drone stays on the ground until you command it to fly.
   ```bash
   start-sim
   ```

To Test it you can run in another container terminal:

   ```bash
   ros2 topic echo /mavros/state
   ```

   Expect `connected: true`. Wait for estimator/GPS initialization before flight
   commands. Run your own ROS nodes in another container terminal.

Ctrl+C in the start-sim terminal stops all three processes. Do not run a second
simulator on the same ports. Logs and simulator parameter state are saved in
`.sitl-gazebo/` in your project. Add that directory to your project's .gitignore.
The separate state directory avoids reusing the earlier headless model's EEPROM.

Individual launch commands (alternative to start-sim, in separate terminals):

```bash
start-gazebo
start-sitl
start-mavros
```
### Control
If you have a physical radio receiver connected to your PC then great. If not, here is a simulation used for testing signal related things. It provides the basic remote controls and you can modify it to fit your purposes if need be in this [file](/scripts/keyboard_rc.py) . To run it simply use this shortcut:
```bash
drone-rc
```
If you want to see inforrmation related to your drone such as input type, mode, armed/disarmed and so on use this:
```bash
drone-status
```
Shortcut to arm your drone:
```bash
drone-arm
```


 
