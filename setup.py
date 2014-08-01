#
# Copyright 2014 ThoughtWorks Deutschland GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import os

from setuptools import setup, find_packages


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="pixelated-dispatcher",
    version="0.1",
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),

    author="Folker Bernitt",
    author_email="fbernitt@thoughtworks.com",
    description="Pixelated-dispatcher dispatches between multiple pixelated user agent instances",
    long_description=read('README.md'),
    license="ALv2",
    keywords=['pixelated', 'email'],
    install_requires=[
        'python-gnupg',
        'bottle',
        'tornado',
        'requests',
        'scrypt',
        'psutil',
        'tempdir',
        'docker-py'
    ],
    test_suite='nose.collector',
    tests_require=[
        'nose',
        'mock',
        'httmock'],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'pixelated-dispatcher = pixelated-dispatcher:main'
        ]
    }
)
