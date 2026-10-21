# syntax=docker/dockerfile:1
FROM ros:humble-ros-base

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg git build-essential cmake pkg-config \
    python3-colcon-common-extensions python3-rosdep \
    geographiclib-tools ros-humble-mavros ros-humble-mavros-extras \
    libgl1-mesa-dri libglx-mesa0 \
    && rm -rf /var/lib/apt/lists/*

# Binary Gazebo packages for Ubuntu 22.04 (the Humble base).
RUN curl -fsSL --retry 3 https://packages.osrfoundation.org/gazebo.gpg \
      -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable jammy main" \
      > /etc/apt/sources.list.d/gazebo-stable.list \
    && apt-get update && apt-get install -y --no-install-recommends \
      gz-harmonic libgz-sim8-dev rapidjson-dev libopencv-dev \
      libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
      gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl \
    && rm -rf /var/lib/apt/lists/*

RUN geographiclib-get-geoids egm96-5 \
    && test -s /usr/share/GeographicLib/geoids/egm96-5.pgm

# Download an official PREBUILT autopilot.
# This development image targets an Intel/AMD x86_64 PC.
ARG COPTER_VERSION=4.5.7

RUN test "$(dpkg --print-architecture)" = amd64 \
    && mkdir -p /opt/sitl/params \
    && curl -fL --retry 3 \
      "https://firmware.ardupilot.org/Copter/stable-${COPTER_VERSION}/SITL_x86_64_linux_gnu/arducopter" \
      -o /opt/sitl/arducopter \
    && chmod +x /opt/sitl/arducopter \
    && /opt/sitl/arducopter --help > /opt/sitl/help.txt \
    && for name in copter gazebo-iris; do \
      curl -fsSL --retry 3 \
        "https://raw.githubusercontent.com/ArduPilot/ardupilot/Copter-${COPTER_VERSION}/Tools/autotest/default_params/${name}.parm" \
        -o "/opt/sitl/params/${name}.parm"; \
    done

# Only this small plugin project is built from source.
ENV GZ_VERSION=harmonic
ARG GAZEBO_PLUGIN_REF=main
ARG PLUGIN_BUILD_JOBS=2

RUN git clone --depth 1 --branch "${GAZEBO_PLUGIN_REF}" \
      https://github.com/ArduPilot/ardupilot_gazebo.git /opt/ardupilot_gazebo \
    && git -C /opt/ardupilot_gazebo rev-parse HEAD \
      > /opt/ardupilot_gazebo/BUILD_COMMIT \
    && cmake -S /opt/ardupilot_gazebo \
      -B /opt/ardupilot_gazebo/build \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_DISABLE_FIND_PACKAGE_ament_cmake=TRUE \
    && cmake --build /opt/ardupilot_gazebo/build \
      -j "${PLUGIN_BUILD_JOBS}" \
    && test -f /opt/ardupilot_gazebo/build/libArduPilotPlugin.so

ENV GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ardupilot_gazebo/build
ENV GZ_SIM_RESOURCE_PATH=/opt/ardupilot_gazebo/models:/opt/ardupilot_gazebo/worlds
ENV QT_X11_NO_MITSHM=1

# Launcher scripts from .devcontainer/scripts.
COPY scripts/ /usr/local/bin/

RUN chmod +x \
      /usr/local/bin/start-sim \
      /usr/local/bin/start-sitl \
      /usr/local/bin/start-gazebo \
      /usr/local/bin/start-mavros \
    && echo 'source /opt/ros/humble/setup.bash' >> /etc/bash.bashrc \
    && echo '[ ! -f /workspaces/x650-autonomy/install/setup.bash ] || source /workspaces/x650-autonomy/install/setup.bash' >> /etc/bash.bashrc

WORKDIR /workspaces/x650-autonomy
CMD ["bash"]

# Runtime dependencies for the Gazebo camera plugin and keyboard controller.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      libdebuginfod1 \
      python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Shared shortcuts from the mounted repository:
# drone-arm, drone-status, drone-rc.
RUN echo '[ ! -f /workspaces/x650-autonomy/scripts/drone_commands.sh ] || source /workspaces/x650-autonomy/scripts/drone_commands.sh' \
    >> /etc/bash.bashrc