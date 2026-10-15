from setuptools import setup, find_packages

setup(
    name="optiguard",
    version="1.0.0",
    description="Adaptive Compiler Optimization Framework with Degradation Detection and Safe Rollback",
    author="OptiGuard Team",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "optiguard=optiguard.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Compilers",
    ],
)
