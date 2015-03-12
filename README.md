pixelated-dispatcher
====================

[![Build Status](https://travis-ci.org/pixelated-project/pixelated-dispatcher.svg?branch=master)](https://travis-ci.org/pixelated-project/pixelated-dispatcher)
[![Coverage Status](https://coveralls.io/repos/pixelated-project/pixelated-dispatcher/badge.svg?branch=master)](https://coveralls.io/r/pixelated-project/pixelated-dispatcher?branch=master)

The `pixelated-dispatcher` is what you will need to host Pixelated for more than one user. It allows you to run, manage and restrict access (using a login form) to different instances of the [pixelated-user-agent](https://github.com/pixelated-project/pixelated-user-agent).


**The Pixelated Dispatcher is still in early development state! Hence the setup is sometimes still less straight forward than expected. You will find more details as you go through this README.**

![High level architecture pixelated-dispatcher](https://pixelated-project.org/assets/images/pixelated-dispatcher.png)


# Try it!

## Vagrant

This repository contains a `Vagrantfile` that helps set up a running pixelated-dispatcher installation within a virtual machine in case you just want to look around. Just [install vagrant](https://www.vagrantup.com/downloads.html), fork/clone this repository and, in the project's root folder, run:

    vagrant up

After all the dependencies are downloaded and the service is running, you can access the login page at [https://localhost:8080/](https://localhost:8080/).
To login to the virtual machine, use `vagrant ssh`.

## Debian packages

We have debian packages available in our repository. Use these commands to install them:

```bash
apt-key adv --keyserver pool.sks-keyservers.net --recv-keys 0x287A1542472DC0E3
apt-key adv --keyserver pool.sks-keyservers.net --recv-keys 0x1E34A1828E207901

echo "deb http://debian.mirror.iphh.net/debian wheezy-backports main" >> /etc/apt/sources.list.d/backports.list
echo "deb http://packages.pixelated-project.org/debian wheezy-snapshots main" >> /etc/apt/sources.list.d/pixelated.list
echo "deb http://packages.pixelated-project.org/debian wheezy main" >> /etc/apt/sources.list.d/pixelated.list
echo "deb http://deb.leap.se/0.6 wheezy main" >> /etc/apt/sources.list.d/leap.list

apt-get update
apt-get install -t wheezy-backports pixelated-dispatcher
```

# Command line interface (CLI)

The pixelated dispatcher has a command line interface that can be used to monitor and manage the user agent instances. To see everything the `pixelated-dispatcher` command can do, run:

    pixelated-dispatcher --help


> OBS 1: If you're running the Vagrant box, the `pixelated-dispatcher` won't be automatically added to your PATH, so it must be ran as `python pixelated/pixelated-dispatcher.py` from inside the `/vagrant` folder).

> OBS 2: The CLI interface by default won't work if an invalid certificate is being used on the dispatcher. To bypass this, use the `-k / --no-check-certificate` parameter.


# Architecture Overview

The pixelated-dispatcher is a combination of two daemons: the `pixelated-dispatcher proxy` and the `pixelated-dispatcher manager`.

The `proxy` is the user facing part and the service you access when connecting to https://localhost:8080/.
It handles authentication and acts as a proxy for the agents. The intention is for this daemon to give up on all unnecessary privileges as soon as possible.

The `manager` is responsible for managing the lifecycle of the user agent instances. It is not accessible from the web, but provides a REST-ful API to create/start/stop/delete agents. It uses [docker](https://github.com/dotcloud/docker) to isolate the user-agent's processes from each other and to provide the necessary runtime environment.

Both the `proxy` and the `manager` need to be running for the pixelated-dispatcher to work correctly.


# Development Environment (if you're not using Vagrant)

As the default provider is based on docker you need a running docker daemon somewhere. So you have to set DOCKER_HOST to the according value, e.g.

    export DOCKER_HOST=tcp://192.168.59.103:2375

If you are working on OS X, we recommend [boot2docker](http://boot2docker.io/) as there is no native docker support.

To setup a dev environment, call:

    git clone git@github.com:pixelated-project/pixelated-dispatcher.git
    virtualenv pixelated_dispatcher_venv   # or created elsewhere
    source pixelated_dispatcher_venv/bin/activate
    cd pixelated-dispatcher
    pip install -r requirements.txt

    python setup.py test


# Packages

You can build a debian package from sources by running

	./package/debian-package.sh

For that to work you need to have the `python-setuptools (>= 0.6b3)`, `python-all (>= 2.6.6-3)` and `debhelper (>= 7.4.3)` installed.

