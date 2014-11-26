exec { "apt-update":
    command => "/usr/bin/apt-get update"
}

Exec["apt-update"] -> Package <| |>

node default {
  package { [
  'build-essential',
  'libssl-dev',
  'docker.io',
  'rng-tools',
  'python-dev',
  'python-setuptools',
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

  service { 'rngd':
    ensure => running,
    provider => 'base',
    binary => '/usr/sbin/rngd',
    start => '/usr/sbin/rngd -r /dev/urandom',
    require => Package['rng-tools']
  }

  $dispatcher_path = "/var/lib/dispatcher"

  file { $dispatcher_path:
    ensure => directory,
    owner => 'vagrant',
    group => 'vagrant',
    mode => '0755'
  }

  $manager_cmd = "/usr/bin/python /vagrant/pixelated/pixelated-dispatcher.py manager -b docker --provider example.wazokazi.is --provider-ca /vagrant/pixelated/resources/example.wazokazi.is.ca.crt --bind 0.0.0.0"
  $ssl_options = "--sslcert /vagrant/pixelated/test/util/server.crt --sslkey /vagrant/pixelated/test/util/server.key"

  service { 'dispatcher-proxy':
    ensure => running,
    provider => 'base',
    binary => '/bin/false',
    start => "su -l vagrant -c 'nohup ${manager_cmd} -r ${$dispatcher_path} ${ssl_options} &'",
    stop => "/usr/bin/pkill -x -f '${manager_cmd} -r ${$dispatcher_path} ${ssl_options}' > /dev/null",
    status => "/usr/bin/pgrep -x -f '${manager_cmd} -r ${$dispatcher_path} ${ssl_options}'",
    hasstatus => true,
    require => [Service['docker'], File[$dispatcher_path]]
  }

  $proxy_cmd = "/usr/bin/python /vagrant/pixelated/pixelated-dispatcher.py proxy"

  service { 'pixelated-dispatcher':
    ensure => running,
    provider => 'base',
    binary => '/bin/false',
    start => "su -l vagrant -c \"nohup ${proxy_cmd} -m localhost:4443 --bind 0.0.0.0 ${ssl_options} &\"",
    stop => "/usr/bin/pkill -x -f \"${proxy_cmd} -m localhost:4443 --bind 0.0.0.0 ${ssl_options}\"",
    status => "/usr/bin/pgrep -x -f \"${proxy_cmd} -m localhost:4443 --bind 0.0.0.0 ${ssl_options}\"",
    hasstatus => true,
    require => [Service['docker'], Service['dispatcher-proxy'], File[$dispatcher_path]]
  }
}
