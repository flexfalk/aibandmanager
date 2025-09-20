from setuptools import setup, find_packages

setup(
    name="aibandmanager",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[],
    author="Your Name",
    description="AI Band Manager for gig investigation, email, and scheduling.",
)