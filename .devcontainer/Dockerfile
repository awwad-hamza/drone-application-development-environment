
FROM ros:humble-ros-base

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    git \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    python3-pip \
    build-essential \
    geographiclib-tools \
    libgeographic-dev \
    && rm -rf /var/lib/apt/lists/*

# Workspace for MAVROS and its dependencies
WORKDIR /opt/mavros_ws

RUN mkdir -p src && \
    git clone --branch ros2 --recursive \
    https://github.com/mavlink/mavros.git src/mavros

RUN rosdep init 2>/dev/null || true && rosdep update

RUN apt-get update && \
    rosdep install --from-paths src --ignore-src -r -y \
    --rosdistro humble

RUN . /opt/ros/humble/setup.sh && \
    colcon build --symlink-install

# Source ROS and MAVROS in every interactive shell
RUN echo 'source /opt/ros/humble/setup.bash' >> /etc/bash.bashrc && \
    echo 'source /opt/mavros_ws/install/setup.bash' >> /etc/bash.bashrc

WORKDIR /workspaces/x650-autonomy
CMD ["bash"]
