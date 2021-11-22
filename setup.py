#!/usr/bin/env python
from setuptools import find_packages, setup
import subprocess
import os

from cmec_driver.cmec_global_vars import version

with open("README.md", 'r') as f:
    long_description = f.read()

packages=find_packages()

setup(
    name='cmec_driver',
    version=version,
    description='CMEC driver',
    long_description=long_description,
    url='https://github.com/cmecmetrics/cmec-driver.git',
    author='Paul Ullrich and Ana Ordonez',
    author_email='ordonez4@llnl.gov',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved :: BSD 3-Clause License',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
    ],
    keywords=['benchmarking','earth system modeling','climate modeling','model intercomparison'],
    packages=packages,
    entry_points={
        "console_scripts": [
            "cmec-driver=cmec_driver.cmec_driver:main"
        ]
    }
)
