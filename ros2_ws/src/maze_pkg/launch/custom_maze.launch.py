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
