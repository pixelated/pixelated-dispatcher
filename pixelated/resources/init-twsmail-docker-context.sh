#!/bin/bash

cat << 'EOFPATCH' > fake-smail-back.patch
diff --git a/lib/smail/server.rb b/lib/smail/server.rb
index fa9c9a3..f75d378 100644
--- a/lib/smail/server.rb
+++ b/lib/smail/server.rb
@@ -59,21 +59,7 @@ module Smail
     post '/control/mailset/:name/load' do |name| json control_mailset_load(name) end


-    # pass all other requests to asset server
-    get '/*' do
-      url = "http://localhost:9000/#{params['splat'][0]}"
-
-      resp = Net::HTTP.get_response(URI.parse(url))
-      if resp.is_a?(Net::HTTPSuccess)
-        res = resp.body.to_s.gsub(/(href|src)=("|')\//, '\1=\2' + url + '/')
-        content_type resp.content_type
-        status resp.code
-        res
-      else
-        status resp.code
-        resp.message
-      end
-    end
+    get "/"	do File.read(File.join(settings.root, 'public', 'index.html')) end


     include Smail::Fake
EOFPATCH

cat << 'EOFBOWER' > bower.patch
diff --git a/bower.json b/bower.json
index f8eebac..a962fdb 100644
--- a/bower.json
+++ b/bower.json
@@ -17,5 +17,9 @@
     "handlebars": "~1.3.0",
     "typeahead.js": "~0.10.2",
     "almond": "~0.2.9"
+  },
+  "resolutions": {
+    "jasmine-jquery": "~1.7.0",
+    "jquery": ">=1.8.0"
   }
 }
EOFBOWER

cat << 'EOFSCSS' > scss.patch
diff --git a/app/scss/foundation.scss b/app/scss/foundation.scss
index 7918cf2..58473d4 100644
--- a/app/scss/foundation.scss
+++ b/app/scss/foundation.scss
@@ -1,3 +1,4 @@
+@charset "UTF-8";
 @import 'compass/css3';

 meta {
diff --git a/app/scss/main.scss b/app/scss/main.scss
index 23de32b..4f7043a 100644
--- a/app/scss/main.scss
+++ b/app/scss/main.scss
@@ -1,3 +1,4 @@
+@charset "UTF-8";
 @import "reset.scss";
 @import "foundation.scss";
 @import "compass/css3";
EOFSCSS

cat << 'EOFDOCKER' > Dockerfile
# DOCKER-VERSION 1.1.0
FROM debian:latest

MAINTAINER fbernitt@thoughtworks.com

# Update packages lists
RUN apt-get update -y

# Force -y for apt-get
RUN echo "APT::Get::Assume-Yes true;" >>/etc/apt/apt.conf

# Add code & install the requirements
RUN apt-get install curl build-essential procps locales wget python-dev git

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
    \curl "https://www.npmjs.org/install.sh" | clean=no sh

ADD fake-smail-back.patch /fake-smail-back.patch

ADD bower.patch /bower.patch

ADD scss.patch /scss.patch

ADD fake-smail-back /fake-smail-back

ADD smail-front /smail-front

ENV LANGUAGE C.UTF-8
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

RUN /bin/bash -l -c "cd /fake-smail-back && patch -p1 < /fake-smail-back.patch"

RUN /bin/bash -l -c "cd /fake-smail-back && bundle install"

RUN /bin/bash -l -c "cd /smail-front && patch -p1 < /bower.patch"

RUN /bin/bash -l -c "cd /smail-front && patch -p1 < /scss.patch"

RUN /bin/bash -l -c "cd /smail-front && bundle install && npm install && node_modules/bower/bin/bower --allow-root install && ./go --force && ln -s /smail-front/dist /fake-smail-back/public"

#ENTRYPOINT /bin/bash -l -c "cd /fake-smail-back && ./go"

EXPOSE 4567

EOFDOCKER



# 192.168.135.17 => gitlab.dfi.local (but DNS lookup not working)
#git clone git@github.com:twsmail/fake-smail-back.git
git clone http://192.168.135.17/dfi/smail-front.git

#git clone git@github.com:twsmail/smail-front.git
git clone http://192.168.135.17/dfi/fake-smail-back.git

exit 0
