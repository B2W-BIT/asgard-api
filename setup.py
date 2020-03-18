from codecs import open  # To use a consistent encoding
from os import path

from setuptools import (  # Always prefer setuptools over distutils
    find_packages,
    setup,
)

here = path.abspath(path.dirname(__file__))

setup(
    name="asgard-api",
    version="0.96.0",
    description="API for the Asgard Project",
    long_description="",
    url="https://github.com/B2W-BIT/asgard-api",
    # Author details
    author="Dalton Barreto",
    author_email="daltonmatos@gmail.com",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    packages=find_packages(exclude=["contrib", "docs", "tests*"]),
    install_requires=[],
    entry_points={},
)
