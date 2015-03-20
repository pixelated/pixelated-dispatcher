exec { "apt-update":
    command => "/usr/bin/apt-get update"
}

Exec["apt-update"] -> Package <| |>

node default {
  package { [
  'build-essential',
  'libcurl4-openssl-dev',
  'libssl-dev',
  'docker.io',
  'rng-tools',
  'python-dev',
  'python-setuptools',
  'python-pycurl',
  'gnupg',
  'libffi-dev']:
    ensure => latest
  }

  service { 'docker':
    ensure => running,
    require => Package['docker.io']
  }

  user { 'vagrant':
    ensure => present,
    groups => 'docker'
  }

  exec { 'install-pip':
    command => '/usr/bin/easy_install pip',
    creates => '/usr/local/bin/pip',
    require => [Package['python-setuptools']]
  }


  package { 'scrypt':
    ensure => latest,
    provider => 'pip',
    require => [Exec['install-pip'], Package['python-dev']]
  }

  exec { 'install-dispatcher-dependencies':
    command => '/usr/local/bin/pip install -r requirements.txt',
    cwd => '/vagrant',
    require => [Exec['install-pip'], Package['python-dev'], Package['libffi-dev']]
  }

  exec { 'install-dispatcher':
    command => '/usr/bin/python setup.py'
    cwd => '/vagrant',
    require => [Exec['install-dispatcher-dependencies'], Exec['install-pip'], Package['python-dev'], Package['libffi-dev']]
  }

  service { 'rngd':
    ensure => running,
    provider => 'base',
    binary => '/usr/sbin/rngd',
    start => '/usr/sbin/rngd -r /dev/urandom',
    require => Package['rng-tools']
  }

  exec { 'docker-pull-logspout':
    command => '/usr/bin/docker pull gliderlabs/logspout',
    unless => '/usr/bin/docker images | grep logspout',
    require => Service['docker']
  }

  exec { 'docker-run-logspout':
    command => '/usr/bin/docker run --volume=/var/run/docker.sock:/tmp/docker.sock --net=host --detach gliderlabs/logspout syslog://localhost:514',
    unless => '/usr/bin/docker ps | grep logspout',
    require => [Exec['docker-pull-logspout'], Service['rsyslog']]
  }

  service { 'rsyslog':
    ensure => running,
    require => File['/etc/rsyslog.d/udp.conf']
  }

  file { '/etc/rsyslog.d/udp.conf':
    ensure => file,
    notify => Service['rsyslog'],
    content => "\$ModLoad imudp\n\$UDPServerRun 514\n"
  }

  $dispatcher_path = "/var/lib/dispatcher"

  file { $dispatcher_path:
    ensure => directory,
    owner => 'vagrant',
    group => 'vagrant',
    mode => '0755'
  }

  $manager_cmd = "/usr/bin/python /vagrant/pixelated-dispatcher.py manager -b docker --provider try.pixelated-project.org --provider-ca /vagrant/pixelated/resources/try.pixelated-project.org.ca.crt --bind 0.0.0.0"
  $ssl_options = "--sslcert /vagrant/pixelated/test/util/server.crt --sslkey /vagrant/pixelated/test/util/server.key"

  service { 'dispatcher-manager':
    ensure => running,
    provider => 'base',
    binary => '/bin/false',
    start => "su -l vagrant -c 'nohup ${manager_cmd} -r ${$dispatcher_path} ${ssl_options} &'",
    stop => "/usr/bin/pkill -x -f '${manager_cmd} -r ${$dispatcher_path} ${ssl_options}' > /dev/null",
    status => "/usr/bin/pgrep -x -f '${manager_cmd} -r ${$dispatcher_path} ${ssl_options}'",
    hasstatus => true,
    require => [Service['docker'], File[$dispatcher_path]]
  }

  $proxy_cmd = "/usr/bin/python /vagrant/pixelated-dispatcher.py proxy"

  service { 'dispatcher-proxy':
    ensure => running,
    provider => 'base',
    binary => '/bin/false',
    start => "su -l vagrant -c \"nohup ${proxy_cmd} -m localhost:4443 --bind 0.0.0.0 ${ssl_options} &\"",
    stop => "/usr/bin/pkill -x -f \"${proxy_cmd} -m localhost:4443 --bind 0.0.0.0 ${ssl_options}\"",
    status => "/usr/bin/pgrep -x -f \"${proxy_cmd} -m localhost:4443 --bind 0.0.0.0 ${ssl_options}\"",
    hasstatus => true,
    require => [Service['docker'], Service['dispatcher-manager'], File[$dispatcher_path]]
  }
}
