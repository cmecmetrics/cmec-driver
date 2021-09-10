#!/usr/bin/env python
from setuptools import find_packages, setup
import subprocess
import os

exec(open('cmec_driver/version.py').read())

with open("README.md", 'r') as f:
    long_description = f.read()

packages=find_packages()

setup(
    name='cmec_driver',
    version=__version__,
    description='CMEC driver',
    long_description=long_description,
    url='https://github.com/cmecmetrics/cmec-driver.git',
    author='Paul Ullrich and Ana Ordonez',
    author_email='ordonez4@llnl.gov',
    classifiers=[
        'Development Status :: 3 - Alpha',
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
    scripts=['cmec_driver/cmec_driver.py'],
    entry_points={
        "console_scripts": [
            "cmec-driver=cmec_driver:main"
        ]
    }
)
