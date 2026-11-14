from setuptools import find_packages, setup

setup(
    name="evokenet-node",
    version="0.1.1",
    description="Conservative node client for the Evoke Net pilot",
    python_requires=">=3.10",
    package_dir={"": "src"},
    packages=find_packages("src"),
    entry_points={"console_scripts": ["evokenet=evokenet_node.cli:main"]},
)
