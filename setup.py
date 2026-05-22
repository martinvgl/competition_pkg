from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'competition_pkg'

submodules = [f"{package_name}/states"]

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test', *submodules]),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join("share", package_name, "launch"), glob("./launch/*.launch.py")),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ros2',
    maintainer_email='ros2@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            "node1 = competition_pkg.node1:main",
            "node2 = competition_pkg.node2:main",
        ],
    },
)
