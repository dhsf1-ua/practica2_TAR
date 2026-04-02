import os
from glob import glob
from setuptools import find_packages, setup


package_name = 'p3_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.world')),
        (os.path.join('share', package_name, 'models', 'parking'), glob('models/parking/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='gca21-docker',
    maintainer_email='gca21-docker@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
		'movimiento = p3_pkg.movimiento:main',
		'dibuja_mov = p3_pkg.dibuja_mov:main',
        'aparcamiento = p3_pkg.aparcamiento:main',
        ],
    },
)
