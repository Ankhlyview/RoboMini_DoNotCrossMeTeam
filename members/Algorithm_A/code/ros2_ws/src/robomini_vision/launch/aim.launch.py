"""Launch the traditional-vision auto-aim node.

The simulation itself is started separately:

    ros2 launch robomini_sim sim.launch.py          # terminal 1
    ros2 launch robomini_vision aim.launch.py       # terminal 2

Common overrides:

    ros2 launch robomini_vision aim.launch.py side:=red
    ros2 launch robomini_vision aim.launch.py fire:=false
    ros2 launch robomini_vision aim.launch.py show_window:=true
    ros2 launch robomini_vision aim.launch.py save_dir:=$HOME/.../Pic/vision_debug
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    params = os.path.join(get_package_share_directory("robomini_vision"),
                          "config", "params.yaml")

    side = LaunchConfiguration("side")
    fire = LaunchConfiguration("fire")
    show_window = LaunchConfiguration("show_window")
    save_dir = LaunchConfiguration("save_dir")
    compare_gt = LaunchConfiguration("compare_ground_truth")
    lead_latency = LaunchConfiguration("lead_latency")
    process_rate = LaunchConfiguration("process_rate")
    fire_tolerance = LaunchConfiguration("fire_tolerance")
    max_snap_error = LaunchConfiguration("max_snap_error")
    debug_rate = LaunchConfiguration("debug_rate")

    return LaunchDescription([
        DeclareLaunchArgument("side", default_value="blue",
                              description="blue or red (must match sim side)"),
        DeclareLaunchArgument("fire", default_value="true",
                              description="publish mode 2 when aligned"),
        DeclareLaunchArgument("show_window", default_value="false",
                              description="open an OpenCV window (needs DISPLAY)"),
        DeclareLaunchArgument("save_dir", default_value="",
                              description="optional directory for annotated snapshots"),
        DeclareLaunchArgument("compare_ground_truth", default_value="false",
                              description="log error against /rune/state (diagnostic only)"),
        DeclareLaunchArgument("lead_latency", default_value="0.06",
                              description="extra lead time for a moving target (s)"),
        DeclareLaunchArgument("process_rate", default_value="20.0",
                              description="image processing rate (Hz)"),
        DeclareLaunchArgument("fire_tolerance", default_value="0.022",
                              description="alignment tolerance before firing (rad)"),
        DeclareLaunchArgument("max_snap_error", default_value="0.05",
                              description="max distance to the rune circle (m)"),
        DeclareLaunchArgument("debug_rate", default_value="10.0",
                              description="debug image rate (Hz)"),
        Node(
            package="robomini_vision",
            executable="aim_node",
            name="robomini_aim",
            output="screen",
            parameters=[
                params,
                {
                    "side": side,
                    "fire": ParameterValue(fire, value_type=bool),
                    "show_window": ParameterValue(show_window, value_type=bool),
                    "save_dir": save_dir,
                    "compare_ground_truth": ParameterValue(compare_gt, value_type=bool),
                    "lead_latency": ParameterValue(lead_latency, value_type=float),
                    "process_rate": ParameterValue(process_rate, value_type=float),
                    "fire_tolerance": ParameterValue(fire_tolerance, value_type=float),
                    "max_snap_error": ParameterValue(max_snap_error, value_type=float),
                    "debug_rate": ParameterValue(debug_rate, value_type=float),
                },
            ],
        ),
    ])
