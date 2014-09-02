pixelated-dispatcher
====================

[![Build Status](https://travis-ci.org/pixelated-project/pixelated-dispatcher.svg?branch=master)](https://travis-ci.org/pixelated-project/pixelated-dispatcher)

# Run multiple single user web apps on a server

pixelated-dispatcher allows you to run multiple instances of an application that had been designed for a single user.

Aside from managing the different instances it also provides a login form to restrict access to individual agents.


**The Pixelated Dispatcher is still in early development state! Hence the setup is sometimes still less straight forward than expected. You will find more details as you go through this README.**

# Try it!

This repository contains a Vagrantfile that sets up a running pixelated-dispatcher installation within a virtual machine.

    vagrant up
    vagrant ssh
    
    # It takes some time to initialize the docker containers so wait until there is no docker job running for
    # a few minutes:
    docker ps  # list running docker processes
    
    cd /vagrant
    
It provides a CLI interface to manage agents:

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

Now you can [access the agent using a browser](https://localhost:8080/). To logout of a agent just call
[https://localhost:8080/auth/logout](https://localhost:8080/auth/logout) (currently there is no logout link
in the mail clients).
    
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
