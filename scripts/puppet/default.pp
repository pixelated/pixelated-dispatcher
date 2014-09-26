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
  'python-pip',
  'python-dev',
  'python-tornado',
  'python-bottle',
  'python-requests',
  'python-gnupg',
  'gnupg']:
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

  package { 'scrypt':
    ensure => latest,
    provider => 'pip',
    require => [Package['python-pip'], Package['python-dev']]
  }

  exec { 'install-dispatcher-dependencies':
    command => '/usr/bin/pip install -r requirements.txt',
    cwd => '/vagrant',
    require => [Package['python-pip'], Package['python-dev']]
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

  $server_cmd = "/usr/bin/python /vagrant/pixelated/pixelated-dispatcher.py server -b docker"
  $ssl_options = "--sslcert /vagrant/pixelated/test/util/server.crt --sslkey /vagrant/pixelated/test/util/server.key"

  service { 'dispatcher-server':
    ensure => running,
    provider => 'base',
    binary => '/bin/false',
    start => "su -l vagrant -c 'nohup ${server_cmd} -r ${$dispatcher_path} ${ssl_options} &'",
    stop => "/usr/bin/pkill -x -f '${server_cmd} -r ${$dispatcher_path} ${ssl_options}' > /dev/null",
    status => "/usr/bin/pgrep -x -f '${server_cmd} -r ${$dispatcher_path} ${ssl_options}'",
    hasstatus => true,
    require => [Service['docker'], File[$dispatcher_path]]
  }

  $dispatcher_cmd = "/usr/bin/python /vagrant/pixelated/pixelated-dispatcher.py dispatcher"

  service { 'pixelated-dispatcher':
    ensure => running,
    provider => 'base',
    binary => '/bin/false',
    start => "su -l vagrant -c \"nohup ${dispatcher_cmd} -s localhost:4443 --bind 0.0.0.0 ${ssl_options} &\"",
    stop => "/usr/bin/pkill -x -f \"${dispatcher_cmd} -s localhost:4443 --bind 0.0.0.0 ${ssl_options}\"",
    status => "/usr/bin/pgrep -x -f \"${dispatcher_cmd} -s localhost:4443 --bind 0.0.0.0 ${ssl_options}\"",
    hasstatus => true,
    require => [Service['docker'], Service['dispatcher-server'], File[$dispatcher_path]]
  }
}
