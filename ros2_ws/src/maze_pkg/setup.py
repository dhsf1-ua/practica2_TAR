import os
<<<<<<< HEAD

from setuptools import find_packages
from setuptools import setup


package_name = 'maze_pkg'


def package_files(directories):
    data_files = []

    for directory in directories:
        for path, _, filenames in os.walk(directory):
            if not filenames:
                continue

            install_path = os.path.join('share', package_name, path)
            file_paths = [os.path.join(path, filename) for filename in filenames]
            data_files.append((install_path, file_paths))

    return data_files


setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=[]),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ] + package_files(['launch', 'worlds', 'models']),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Carlos',
    maintainer_email='carlos@example.com',
    description='Paquete para resolver laberintos con Turtlebot 3.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'res_maze = maze_pkg.res_maze:main',
=======
from glob import glob
from setuptools import find_packages, setup

package_name = 'maze_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.world')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='daniel-docker',
    maintainer_email='daniel-docker@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
>>>>>>> c9c271dc55f8cd94745a69edee69e28ffaf32bd6
        ],
    },
)
