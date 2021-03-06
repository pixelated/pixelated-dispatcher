exec { "apt-update":
    command => "/usr/bin/apt-get update"
}

Exec["apt-update"] -> Package <| |>

node default {
  package { [
  'build-essential',
  'libcurl4-openssl-dev',
  'libssl-dev',
  'rng-tools',
  'python-dev',
  'python-setuptools',
  'python-pycurl',
  'gnupg',
  'libffi-dev']:
    ensure => latest
  }

  exec { 'install docker':
    command => '/bin/bash -c "/usr/bin/curl -sSL https://get.docker.com/ | /bin/bash"',
    /* creates => '/usr/bin/docker' */
  }

  service { 'docker':
    ensure => running,
    require => Exec['install docker'],
  }

  user { 'vagrant':
    ensure => present,
    groups => 'docker',
    require => Exec['install docker'],
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
    command => '/usr/bin/python setup.py develop',
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

  $manager_cmd = "/usr/bin/python /vagrant/pixelated-dispatcher.py manager -b docker --leap-provider try.pixelated-project.org --bind 0.0.0.0"
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

  notify { "${manager_cmd} -r ${$dispatcher_path} ${ssl_options}": }

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

  notify { "nohup ${proxy_cmd} -m localhost:4443 --bind 0.0.0.0 ${ssl_options}":
  }
}
