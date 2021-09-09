#!/usr/bin/env python
from setuptools import find_packages, setup
from codecs import open
import subprocess
import os

version = '1.0.0-alpha'

# Create version file
p = subprocess.Popen(
    ("git",
     "describe",
     "--tags"),
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE)
try:
    descr = p.stdout.readlines()[0].strip().decode("utf-8")
    version = "-".join(descr.split("-")[:-2])
    if version == "":
        version = descr
except:
    descr = version

p = subprocess.Popen(
    ("git",
     "log",
     "-n1",
     "--pretty=short"),
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE)
try:
    commit = p.stdout.readlines()[0].split()[1].decode("utf-8")
except:
    commit = ""

f = open("version.py", "w")
f.writelines("__version__ = '%s'" % version)
f.writelines("__git_tag_describe__ = '%s'" % descr)
f.writelines("__git_sha1__ = '%s'" % commit)
f.close()

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
    scripts=['cmec-driver.py']
)
