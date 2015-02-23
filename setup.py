#
# Copyright (c) 2014 ThoughtWorks Deutschland GmbH
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.
import os

from setuptools import setup, find_packages
from setuptools.command.install import install


class write_login_banner(install):
    """Customized setuptools install command - prints a friendly greeting."""
    def run(self):
        os.system("echo '<pre>' > disptacher_banner.html; git log -5 >> dispatcher_banner.html echo '</pre>' > dispatcher_banner.html")
        install.run(self)


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
    data_files=[('/etc/pixelated/', ['dispatcher_banner.html'])],
    cmdclass={
        'install': write_login_banner,
    },


    author="Folker Bernitt",
    author_email="fbernitt@thoughtworks.com",
    description="Pixelated-dispatcher dispatches between multiple pixelated user agent instances",
    long_description=read('README.md'),
    license="AGPL",
    keywords=['pixelated', 'email'],
    install_requires=[
        'gnupg',
        'bottle',
        'tornado',
        'requests',
        'scrypt',
        'psutil',
        'docker-py',
        'srp',
        'leap.common',
        'pycurl'
    ],
    test_suite='nose.collector',
    tests_require=[
        'nose',
        'mock',
        'httmock',
        'tempdir'],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'pixelated-dispatcher = pixelated.pixelated_dispatcher:main'
        ]
    },
    include_package_data=True
)
