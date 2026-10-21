# X650 visual simulation environment

ROS 2 Humble → MAVROS → ArduCopter SITL ↔ Gazebo Harmonic / Iris.

This replaces the earlier headless Dockerfile. It downloads prebuilt MAVROS,
Gazebo and the official ArduCopter 4.5.7 Linux executable. Only the small
ardupilot_gazebo plugin project is compiled. No ArduPilot checkout, Waf build,
ROS source build, DDS agent or Gazebo source build is involved.

The first image build still downloads several large Gazebo/development packages;
time depends on your connection and machine. Subsequent starts reuse the image.
Editing your bind-mounted ROS code does not rebuild the simulator.

## Install into your project

Prerequisites: an Intel/AMD x86_64 Linux PC, Docker Engine with Compose v2,
VS Code Dev Containers, a running graphical desktop, and host xauth.

1. Back up your old .devcontainer directory. Copy this archive's .devcontainer
   directory into the root of your x650-autonomy project, replacing the old config.
2. In a HOST desktop terminal, from the project root:

   ```bash
   bash .devcontainer/prepare-display.sh
   ```

   If xauth is missing, on Ubuntu/Debian install it first:
   `sudo apt-get install xauth`.
3. In VS Code, run **Dev Containers: Rebuild Container**.
4. In a terminal INSIDE the container:

   ```bash
   start-sim
   ```

   Gazebo opens with the Iris quadcopter on the runway. This starts the simulator
   and bridge; the drone stays on the ground until you command it to fly.
5. In another container terminal:

   ```bash
   ros2 topic echo /mavros/state
   ```

   Expect `connected: true`. Wait for estimator/GPS initialization before flight
   commands. Run your own ROS nodes in another container terminal.

Ctrl+C in the start-sim terminal stops all three processes. Do not run a second
simulator on the same ports. Logs and simulator parameter state are saved in
`.sitl-gazebo/` in your project. Add that directory to your project's .gitignore.
The separate state directory avoids reusing the earlier headless model's EEPROM.

## Graphics

The default Compose file passes /dev/dri through for Intel/AMD Mesa graphics.
It uses your X11 session, or XWayland when your Wayland desktop provides DISPLAY.
It copies an authentication cookie rather than disabling X access controls.
Rerun prepare-display.sh after desktop login changes and recreate the container
if the display environment changed. Never commit the generated cookie or .env.

For NVIDIA, install/configure NVIDIA Container Toolkit on the host. In
compose.yaml remove the `devices: /dev/dri` mapping if unsuitable, add
`gpus: all` under x650-dev (Compose 2.30+), and add these environment values:

```yaml
NVIDIA_VISIBLE_DEVICES: all
NVIDIA_DRIVER_CAPABILITIES: graphics,display,utility,compute
```

If your PC has no /dev/dri or usable GPU passthrough, remove `devices` and add
`LIBGL_ALWAYS_SOFTWARE: "1"` to environment. Software rendering will be slower.

## Development

```bash
colcon build --symlink-install
source install/setup.bash
```

Build only your application packages here; MAVROS is already installed.
Keep Docker's build cache enabled. Reopen/start the container for routine use;
rebuild it only when changing the environment. The build context contains only
the Dockerfile and launcher scripts, so changing your ROS code cannot invalidate
the simulator installation layers.

Individual launch commands (alternative to start-sim, in separate terminals):

```bash
start-gazebo
start-sitl
start-mavros
```

## Scope and validation

Iris is a generic X-frame quadcopter, not a tuned X650 model. Its mass, inertia,
motors and sensor configuration need tuning for meaningful X650 performance tests.
Match COPTER_VERSION to your Pixhawk firmware when possible; changing versions
requires a published SITL binary and matching parameter files at that version.
GAZEBO_PLUGIN_REF defaults to main; the exact built revision is recorded in
/opt/ardupilot_gazebo/BUILD_COMMIT. Pin a suitable tag/branch for a frozen setup.

Use this image on the PC. Build/install your application for the Pi's architecture
and use MAVROS's serial FCU URL there instead of the simulation TCP URL. Simulation
does not validate real sensor wiring, UART configuration or flight dynamics.

The launcher scripts, configuration structure and archive were checked locally.
Docker and a graphical session were unavailable in the authoring environment, so
the full image build, GPU display and flight connection have NOT been run here.
The Dockerfile checks the downloaded SITL binary's ability to execute and the
built plugin's presence during your build. If startup fails, inspect:

```bash
tail -n 60 .sitl-gazebo/gazebo.log
tail -n 60 .sitl-gazebo/sitl.log
tail -n 60 .sitl-gazebo/mavros.log
```

Official references:
- https://github.com/ArduPilot/ardupilot_gazebo
- https://gazebosim.org/docs/harmonic/install_ubuntu/
- https://firmware.ardupilot.org/Copter/stable-4.5.7/SITL_x86_64_linux_gnu/
- https://github.com/mavlink/mavros/blob/ros2/docs/installation.md
