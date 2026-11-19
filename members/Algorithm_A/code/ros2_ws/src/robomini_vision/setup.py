import os
from glob import glob

from setuptools import setup

package_name = "robomini_vision"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        (os.path.join("share", package_name), ["package.xml"]),
        (os.path.join("share", package_name, "config"), glob("config/*")),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Algorithm_A",
    maintainer_email="algorithm-a@robomini.local",
    description="Traditional-vision auto-aim for the ROBOMINI energy rune simulation.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "aim_node = robomini_vision.aim_node:main",
        ],
    },
)
