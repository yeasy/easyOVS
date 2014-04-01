#!/usr/bin/env python

"Setuptools params"

from setuptools import setup, find_packages
from os.path import join

# Get version number from source tree
import sys
sys.path.append( '.' )
from easyovs.util import VERSION

scripts = [ join( 'bin', filename ) for filename in [ 'easyovs' ] ]

modname = distname = 'easyovs'

setup(
    name=distname,
    version=VERSION,
    description='A easier platform to manage OpenvSwitch bridges',
    author='Baohua Yang',
    author_email='yangbaohua@gmail.com',
    packages=[ 'easyovs'],
    long_description="""
        EasyOVS provides more convinient and fluent way to operation your OpenvSwitch bridges,
        such as list them, dump their flows and add/del some flows.
        https://github.com/yeasy/easyOVS
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
        'setuptools'
    ],
    scripts=scripts,
)
