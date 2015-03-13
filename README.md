Pixelated Dispatcher
====================

[![Build Status](https://travis-ci.org/pixelated-project/pixelated-dispatcher.svg?branch=master)](https://travis-ci.org/pixelated-project/pixelated-dispatcher)
[![Coverage Status](https://coveralls.io/repos/pixelated-project/pixelated-dispatcher/badge.svg?branch=master)](https://coveralls.io/r/pixelated-project/pixelated-dispatcher?branch=master)

The Pixelated Dispatcher is used to host Pixelated for more than one user. It allows you to run, manage and restrict access (using a login form) to different instances of the [pixelated-user-agent](https://github.com/pixelated-project/pixelated-user-agent).

By default, the Pixelated Dispatcher will connect to our test provider, `try.pixelated-project.org`. In order to run your own provider, see [pixelated-platform](https://github.com/pixelated-project/pixelated-platform).

**The Pixelated Dispatcher is still in early development state!**

![High level architecture pixelated-dispatcher](https://pixelated-project.org/assets/images/pixelated-dispatcher.png)


# Getting started

This repository contains a `Vagrantfile` that helps set up a running pixelated-dispatcher installation within a virtual machine. Just [install vagrant](https://www.vagrantup.com/downloads.html), fork/clone this repository and, in the project's root folder, run:

    vagrant up

After all the dependencies are downloaded and the service is running, you can access the login page at [https://localhost:8080/](https://localhost:8080/). By default, the dispatcher will connect to our test provider at `try.pixelated-project.org`.

Now that the service is running, you can login to the virtual machine with `vagrant ssh` and run our suite of automated tests:

    cd /vagrant
    python setup.py test



# Debian packages

We have Debian packages available in our repositories. Use these commands to install them:

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
