# palimpsest/setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as req_file:
    requirements = req_file.read().splitlines()

setup(
    name="palimpsest",
    version="0.1.0",
    author="Palimpsest Team",
    author_email="info@palimpsestproject.org",
    description="A system for analyzing and finding connections between literary texts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/palimpsest/palimpsest",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "palimpsest=src.main:main",
        ],
    },
)