#!/usr/bin/env bash
# Build the robomini_vision package.
#
#   ./build.sh
#   ./build.sh --packages-select robomini_vision
#
# It forces the system Python (/usr/bin/python3) and the ROS Jazzy toolchain,
# because a conda Python/OpenCV on PATH produces ABI errors with rclpy/cv_bridge.
set -euo pipefail

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_ROOT="${SIM_ROOT:-$HOME/Gitclone/Vision_robomini/robomini_sim}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/jazzy/setup.bash}"

if [ -n "${CONDA_PREFIX:-}" ]; then
  echo "[build] WARNING: conda is active ($CONDA_PREFIX); using /usr/bin first instead."
fi
export PATH=/usr/bin:/bin:/usr/local/bin:$PATH

if [ ! -f "$SIM_ROOT/ros2_ws/install/setup.bash" ]; then
  echo "[build] ERROR: sim workspace not built: $SIM_ROOT/ros2_ws/install/setup.bash" >&2
  echo "        build robomini_sim first (scripts/build.sh in that repo)." >&2
  exit 1
fi

# ROS setup.bash references unbound variables; relax nounset while sourcing.
set +u
# shellcheck disable=SC1090
source "$ROS_SETUP"
# shellcheck disable=SC1090
source "$SIM_ROOT/ros2_ws/install/setup.bash"
set -u

cd "$CODE_ROOT/ros2_ws"
exec colcon build --symlink-install "$@"
