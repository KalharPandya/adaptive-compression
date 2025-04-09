from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="adaptive-compression",
    version="0.1.0",
    description="An adaptive marker-based compression algorithm that dynamically selects optimal compression methods",
    author="Kalhar Pandya",
    author_email="66383494+KalharPandya@users.noreply.github.com", 
    url="https://github.com/KalharPandya/adaptive-compression",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "acompress=main:main",
        ],
    },
)
