from pixelated.exceptions import UserAlreadyExistsError, UserNotExistError
from ConfigParser import ConfigParser
import re
from os.path import join, isdir, exists
from os import mkdir, listdir


class UserConfig(object):
    __slots__ = ('_username', '_path', '_config')

    validate_config = re.compile('^[a-zA-Z0-9_]+[.][a-zA-Z0-9_]+$')

    def __init__(self, username, path):
        self._username = username
        self._path = path
        self._config = dict()

    def __eq__(self, other):
        return isinstance(other, UserConfig) and other.username == self.username and other.path == self.path

    def __setitem__(self, name, value):
        if UserConfig.validate_config.match(name):
            self._config[name] = value
        else:
            raise KeyError('Invalid config name %s' % name)

    def __getitem__(self, name):
        return self._config[name]

    @property
    def username(self):
        return self._username

    @property
    def path(self):
        return self._path

    @classmethod
    def read_from(cls, username, path, config_file_fd):
        parser = ConfigParser()
        parser.readfp(config_file_fd)

        values = dict()
        for section in parser.sections():
            for (key, value) in parser.items(section):
                values['%s.%s' % (section, key)] = value

        config = UserConfig(username, path)
        config._config = values

        return config

    def write_to(self, fd):
        cfg = ConfigParser()

        for key, value in self._config.iteritems():
            section, name = key.split('.')
            if not cfg.has_section(section):
                cfg.add_section(section)
            cfg.set(section, name, value)

        cfg.write(fd)


class Users(object):
    __slots__ = ('_root_path', '_users')

    validate_username = re.compile('^[a-z0-9_.-]+$')

    def __init__(self, root_path):
        if not exists(root_path) or not isdir(root_path):
            raise ValueError('%s does not exist or is not a folder' % root_path)
        self._root_path = root_path
        self._users = []

        self._autodetect_users()

    def _autodetect_users(self):
        dirs = [f for f in listdir(self._root_path) if isdir(join(self._root_path, f))]
        for dir in dirs:
            self._users.append(dir)

    def add(self, username):
        if not Users.validate_username.match(username):
            raise ValueError('Username %s contains invalid chars' % username)
        if username in self._users:
            raise UserAlreadyExistsError('User with name %s already exists' % username)

        user_folder = join(self._root_path, username)

        if not exists(user_folder):
            mkdir(user_folder)
        self._create_user_config(username)
        self._users.append(username)

    def _create_user_config(self, username):
        config_file = join(self._root_path, username, 'user.cfg')
        if not exists(config_file):
            with open(config_file, 'w') as fd:
                UserConfig(username, join(self._root_path, username)).write_to(fd)

    def list(self):
        return self._users

    def has_user(self, username):
        return username in self._users

    def config(self, username):
        if username in self._users:
            data_path = join(self._root_path, username)
            user_config = join(data_path, 'user.cfg')
            with open(user_config, 'r') as fd:
                return UserConfig.read_from(username, data_path, fd)
        raise UserNotExistError('User with name %s does not exist' % username)

    def update_config(self, config):
        data_path = join(self._root_path, config.username)
        user_config = join(data_path, 'user.cfg')

        with open(user_config, 'w') as fd:
            config.write_to(fd)
