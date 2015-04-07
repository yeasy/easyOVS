#!/usr/bin/env python

"""Setuptools params"""

from setuptools import setup, find_packages
from os.path import join

# Get version number from source tree
import sys
sys.path.append('.')
from easyovs import VERSION

scripts = [join('bin', filename) for filename in ['easyovs']]

modname = distname = 'easyovs'

setup(
    name=distname,
    version=VERSION,
    description='Easy way to manage OpenvSwitch bridges',
    author='Baohua Yang',
    author_email='yangbaohua@gmail.com',
    #packages=['easyovs'],
    packages=find_packages(),
    long_description="""
        EasyOVS provides more convenient and fluent way to operation your OpenvSwitch bridges,
        such as list them, show the port, dump their flows and add/del some flows.
        See https://github.com/yeasy/easyOVS
        """,
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: System :: Systems Administration",
        ],
    keywords='Cloud OpenStack OpenvSwitch SDN',
    license='BSD',
    install_requires=[
        'oslo.config>=1.2',
        'python-keystoneclient>=1.0',
        'python-neutronclient>=1.0',
        'setuptools>=1.0',
    ],
    scripts=scripts,
)
