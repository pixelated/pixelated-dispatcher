pixelated-dispatcher
====================

[![Build Status](https://travis-ci.org/pixelated-project/pixelated-dispatcher.svg?branch=master)](https://travis-ci.org/pixelated-project/pixelated-dispatcher)
[![Coverage Status](https://coveralls.io/repos/pixelated-project/pixelated-dispatcher/badge.svg?branch=master)](https://coveralls.io/r/pixelated-project/pixelated-dispatcher?branch=master)

# Run multiple single user web apps on a server

pixelated-dispatcher allows you to run multiple instances of an application that had been designed for a single user.

Aside from managing the different instances it also provides a login form to restrict access to individual agents.


**The Pixelated Dispatcher is still in early development state! Hence the setup is sometimes still less straight forward than expected. You will find more details as you go through this README.**


![High level architecture pixelated-dispatcher](https://pixelated-project.org/drawings/architecture-dispatcher.svg)


# Try it!

This repository contains a Vagrantfile that sets up a running pixelated-dispatcher installation within a virtual machine.

    vagrant up
    vagrant ssh
    
    # It takes some time to initialize the docker containers so wait until there is no docker job running for
    # a few minutes:
    docker ps  # list running docker processes or use "watch docker ps" to see when a new docker image is done.

Now you can access the agent using a browser at https://localhost:8080/

# Command line interface (CLI)

The following commands can be used to manage agents:

    # add a new user
    python pixelated/pixelated-dispatcher.py -k add <username>

    # list all users
    python pixelated/pixelated-dispatcher.py -k list
    
    # your instance is created but not yet running:
    python pixelated/pixelated-dispatcher.py -k running
    
    # start the agent for <username>
    python pixelated/pixelated-dispatcher.py -k start <username>
    
    # Call running again to see that it is now up and running
    
    # To see all possible commands or the meaning of parameters call
    python pixelated/pixelated-dispatcher.py --help

# Overview

pixelated-dispatcher is based on a combination of two deamons to provide the service.

## pixelated-dispatcher proxy

The proxy is the user facing part and the service you access when connecting to https://localhost:8080/.
It handles authentication and acts as a proxy for the agents. The intention is for this daemon to give up on
all unnecessary privileges as soon as possible. 

The entire user agent management is delegated to:

## pixelated-dispatcher manager

The manager is not accessible from the web and is responsible for managing the lifecycle of the instances.
It provides a RESTful API to create/start/stop/delete/... agents. It uses [docker](https://github.com/dotcloud/docker)
to isolate the agents from each other and to provide the necessary runtime environment.

# Development Environment

As the default provider is based on docker you need a running docker daemon somewhere. So you have to set
DOCKER_HOST to the according value, e.g.

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

For that to work you need to have the python-setuptools (>= 0.6b3), python-all (>= 2.6.6-3), debhelper (>= 7.4.3) installed.

## Installing our packages on your server

	apt-key adv --keyserver pool.sks-keyservers.net --recv-keys 0x287A1542472DC0E3
	echo "deb http://debian.mirror.iphh.net/debian wheezy-backports main" >> /etc/apt/sources.list.d/backports.list
	echo "deb http://packages.pixelated-project.org/debian wheezy-snapshots main" >> /etc/apt/sources.list.d/pixelated.list
	echo "deb http://packages.pixelated-project.org/debian wheezy main" >> /etc/apt/sources.list.d/pixelated.list
	apt-get update
	apt-get install pixelated-dispatcher
