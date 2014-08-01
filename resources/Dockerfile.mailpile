# DOCKER-VERSION 1.1.0
FROM debian:latest

MAINTAINER fbernitt@thoughtworks.com

# Update packages lists
RUN apt-get update -y

# Force -y for apt-get
RUN echo "APT::Get::Assume-Yes true;" >>/etc/apt/apt.conf

# Add code & install the requirements
RUN apt-get install make python-pip git python-dev libxml2-dev python-lxml && apt-get clean

# install mailpile
RUN git clone https://github.com/pagekite/Mailpile.git /Mailpile.git

# install python dependencies
RUN pip install -r /Mailpile.git/requirements.txt

RUN /Mailpile.git/mp --setup

RUN /Mailpile.git/mp --set sys.http_host=0.0.0.0

EXPOSE 33411

CMD /Mailpile.git/mp --www


