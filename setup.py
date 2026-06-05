from setuptools import setup
from glob import glob
import os

package_name = 'competition_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name, package_name + '/states'],
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name],
        ),
        (
            'share/' + package_name,
            ['package.xml'],
        ),
        (
            os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py'),
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ros2',
    maintainer_email='ros2@todo.todo',
    description='Emergency evacuation robot',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
    'console_scripts': [
        'sm_evacuation_node = competition_pkg.sm_evacuation_node:main',
        'perception_node = competition_pkg.perception_node:main',
        'obstacle_mapper = competition_pkg.obstacle_mapper_node:main',
    ],
} ,
)
