<<<<<<< HEAD
#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    launch_file_dir = os.path.join(
        get_package_share_directory('turtlebot3_gazebo'),
        'launch',
    )
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    x_pose = LaunchConfiguration('x_pose', default='-2.25')
    y_pose = LaunchConfiguration('y_pose', default='2.25')

    world = os.path.join(
        get_package_share_directory('maze_pkg'),
        'worlds',
        'custom_maze.world',
    )

    gazebo_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={'world': world}.items(),
    )

    robot_state_publisher_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(launch_file_dir, 'robot_state_publisher.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    spawn_turtlebot_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(launch_file_dir, 'spawn_turtlebot3.launch.py')
        ),
        launch_arguments={
            'x_pose': x_pose,
            'y_pose': y_pose,
        }.items(),
    )

    ld = LaunchDescription()
    ld.add_action(gazebo_cmd)
    ld.add_action(robot_state_publisher_cmd)
    ld.add_action(spawn_turtlebot_cmd)

    return ld
=======
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_maze    = get_package_share_directory('maze_pkg')
    pkg_gazebo  = get_package_share_directory('gazebo_ros')
    pkg_tb3_gz  = get_package_share_directory('turtlebot3_gazebo')

    world_file = os.path.join(pkg_maze, 'worlds', 'custom_maze.world')

    # Robot burger por defecto, cambia a 'waffle' para el otro
    tb3_model = os.environ.get('TURTLEBOT3_MODEL', 'burger')
    urdf_file = os.path.join(
        get_package_share_directory('turtlebot3_description'),
        'urdf', f'turtlebot3_{tb3_model}.urdf'
    )
    with open(urdf_file, 'r') as f:
        robot_desc = f.read()

    return LaunchDescription([

        # Gazebo
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_gazebo, 'launch', 'gazebo.launch.py')
            ),
            launch_arguments={'world': world_file, 'verbose': 'false'}.items(),
        ),

        # Robot State Publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_desc}],
        ),

        # Spawn robot en la esquina inferior izquierda del laberinto
        # El laberinto va de -2.5 a 2.5 en x e y
        # La entrada suele estar arriba a la izquierda → x=-2.25, y=2.25
        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=[
                '-topic', 'robot_description',
                '-entity', f'turtlebot3_{tb3_model}',
                '-x', '-2.25',
                '-y',  '2.25',
                '-z',  '0.01',
                '-Y',  '0.0',
            ],
            output='screen',
        ),
    ])
>>>>>>> c9c271dc55f8cd94745a69edee69e28ffaf32bd6
