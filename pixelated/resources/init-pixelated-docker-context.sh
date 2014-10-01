#!/bin/bash
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.

cat << 'EOFDOCKER' > Dockerfile
# DOCKER-VERSION 1.1.0
FROM debian:testing

MAINTAINER fbernitt@thoughtworks.com

# Update packages lists
RUN apt-get update -y

# Force -y for apt-get
RUN echo "APT::Get::Assume-Yes true;" >>/etc/apt/apt.conf

# Add code & install the requirements
RUN apt-get install curl build-essential procps locales wget python-dev git python-pip python-virtualenv bzip2 libpng12-dev

# Configure timezone and locale
RUN echo "Europe/Berlin" > /etc/timezone; dpkg-reconfigure -f noninteractive tzdata
RUN dpkg-reconfigure locales && \
    locale-gen C.UTF-8 && \
    /usr/sbin/update-locale LANG=C.UTF-8

# install RVM, Ruby, and Bundler
RUN \curl -L https://get.rvm.io | bash -s stable --ruby --autolibs=enable --auto-dotfiles

RUN /bin/bash -l -c "rvm requirements"

RUN /bin/bash -l -c "gem install bundle"

RUN echo "deb http://ftp.us.debian.org/debian wheezy-backports main" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install nodejs nodejs-legacy && \
    \curl "https://www.npmjs.org/install.sh" | clean=no npm_install=1.4.21 sh

ADD pixelated-user-agent /pixelated-user-agent

ENV LANGUAGE C.UTF-8
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

RUN /bin/bash -l -c "cd /pixelated-user-agent/web-ui && bundle install"
RUN /bin/bash -l -c "cd /pixelated-user-agent/web-ui && npm install"
RUN /bin/bash -l -c "cd /pixelated-user-agent/web-ui && node_modules/bower/bin/bower --allow-root install"
RUN /bin/bash -l -c "cd /pixelated-user-agent/web-ui && ./go build"

RUN /bin/bash -l -c "cd /pixelated-user-agent/fake-service && pip install -r requirements.txt"

#ENTRYPOINT /bin/bash -l -c "cd /pixelated-user-agent/py-fake-service && ./go"

EXPOSE 4567

EOFDOCKER

git clone https://github.com/pixelated-project/pixelated-user-agent.git

exit 0
