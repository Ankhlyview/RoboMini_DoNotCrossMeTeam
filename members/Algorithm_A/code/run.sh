#!/usr/bin/env bash
# Start the vision auto-aim node against an already running robomini_sim.
#
#   ./run.sh                         # blue, fire enabled
#   ./run.sh side:=red               # red side
#   ./run.sh fire:=false             # detect + aim, do not shoot
#   ./run.sh show_window:=true       # local OpenCV window
#   ./run.sh save_dir:=$PWD/Pic/vision_debug
#
# Start the simulation in another terminal first:
#   ros2 launch robomini_sim sim.launch.py
set -euo pipefail

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_ROOT="${SIM_ROOT:-$HOME/Gitclone/Vision_robomini/robomini_sim}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/jazzy/setup.bash}"

if [ -n "${CONDA_PREFIX:-}" ]; then
  echo "[run] WARNING: conda is active ($CONDA_PREFIX); using /usr/bin first instead."
fi
export PATH=/usr/bin:/bin:/usr/local/bin:$PATH

# ROS setup.bash references unbound variables; relax nounset while sourcing.
set +u
# shellcheck disable=SC1090
source "$ROS_SETUP"
# shellcheck disable=SC1090
source "$SIM_ROOT/ros2_ws/install/setup.bash"
# shellcheck disable=SC1090
source "$CODE_ROOT/ros2_ws/install/setup.bash"
set -u

if ! ros2 topic list 2>/dev/null | grep -q '^/camera/image_raw$'; then
  echo "[run] WARNING: /camera/image_raw not found. Is robomini_sim running?" >&2
fi

exec ros2 launch robomini_vision aim.launch.py "$@"
