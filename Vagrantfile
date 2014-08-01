# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  #config.vm.box = "box-cutter/debian75"
  config.vm.box = "fbernitt/debian-testing-amd64"   # use testing as we need docker support

  config.vm.provision "puppet" do |puppet|
    puppet.manifests_path = "scripts/puppet"
  end

  config.vm.network "forwarded_port", guest: 8080, host: 8080
  config.vm.network "forwarded_port", guest: 4443, host: 4443
end
