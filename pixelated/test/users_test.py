import unittest

from pixelated.users import Users, UserConfig
from pixelated.exceptions import UserAlreadyExistsError, UserNotExistError

from tempdir import TempDir
from os.path import join, exists
from os import mkdir
from tempfile import NamedTemporaryFile


class UserConfigTest(unittest.TestCase):
    def test_config_expects_username_and_root_path(self):
        cfg = UserConfig('name', '/path/to/user/root')

        self.assertEqual('name', cfg.username)
        self.assertEqual('/path/to/user/root', cfg.path)

    def test_store_arbitrary_values(self):
        cfg = UserConfig('name', '/path/to/user/root')

        cfg['section.value'] = 'some value'
        cfg['other_section.other_value'] = 'other value'

        with self.assertRaises(KeyError):
            cfg['invalid'] = 'some value'

        with self.assertRaises(KeyError):
            cfg['section.value.toomuch'] = 'some value'

        self.assertEqual('some value', cfg['section.value'])

    def test_that_config_can_be_written_to_file(self):
        cfg = UserConfig('name', '/path/to/user/root')

        cfg['section.one'] = 'first value'
        cfg['section.two'] = 'second value'

        with NamedTemporaryFile() as tmp:
            cfg.write_to(tmp)

            tmp.seek(0)
            self.assertEqual('[section]\none = first value\ntwo = second value\n\n', tmp.read())

    def test_that_config_can_be_read_from_file(self):
        with NamedTemporaryFile() as tmp:
            tmp.write('[section]\none = first value\ntwo = second value\n\n')
            tmp.seek(0)

            cfg = UserConfig.read_from('name', 'path/to/user/root', tmp)

            self.assertEqual('first value', cfg['section.one'])


class UsersTest(unittest.TestCase):

    def setUp(self):
        self._tmpdir = TempDir()
        self.root_path = self._tmpdir.name
        self.users = Users(self.root_path)

    def test_that_constructor_throws_exception_if_root_path_does_not_exist(self):
        self.assertRaises(ValueError, Users, '/does/not/exist')

    def tearDown(self):
        self._tmpdir.dissolve()

    def test_add_user(self):
        self.users.add('name')

    def test_user_cannot_be_added_twice(self):
        self.users.add('name')
        self.assertRaises(UserAlreadyExistsError, self.users.add, 'name')

    def test_list_empty(self):
        self.assertEqual([], self.users.list())

    def test_list_single_user(self):
        self.users.add('name')

        self.assertEqual(['name'], self.users.list())

    def test_get_user_config_throws_exception_if_user_not_exists(self):
        self.assertRaises(UserNotExistError, self.users.config, 'name')

    def test_add_user_creates_data_folder_and_config(self):
        self.users.add('name')

        data_path = join(self.root_path, 'name')
        config_file = join(data_path, 'user.cfg')
        self.assertTrue(exists(data_path))
        self.assertTrue(exists(config_file))

    def test_add_user_does_not_override_existing_config(self):
        data_path = join(self.root_path, 'name')
        config_file = join(data_path, 'user.cfg')
        mkdir(data_path)
        with open(config_file, 'w') as fd:
            fd.write('[section]\none = first value\ntwo = second value\n\n')

        self.users.add('name')

        data_path = join(self.root_path, 'name')
        config_file = join(data_path, 'user.cfg')
        with open(config_file, 'r') as fd:
            self.assertEqual('[section]\none = first value\ntwo = second value\n\n', fd.read())

    def test_add_validates_username(self):
        self.users.add('a_name.with-valid-chars')

        with self.assertRaises(ValueError):
            self.users.add('CapitalLetters')
        with self.assertRaises(ValueError):
            self.users.add('some/name/with/slashes')

        with self.assertRaises(ValueError):
            self.users.add('name with spaces')

        with self.assertRaises(ValueError):
            self.users.add('name=with%&')

    def test_loads_all_existing_users_on_startup(self):
        user1_data_path = join(self.root_path, 'user1')
        mkdir(user1_data_path)
        user1_config_path = join(self.root_path, 'user1', 'user.cfg')
        with open(user1_config_path, 'w') as fd:
            fd.write('[section]\none = first value\ntwo = second value\n\n')

        users = Users(self.root_path)

        self.assertEqual(['user1'], users.list())
        self.assertEqual('first value', users.config('user1')['section.one'])

    def test_update_user_config(self):
        self.users.add('name')
        config = self.users.config('name')

        config['foo.bar'] = 'some value'
        self.users.update_config(config)

        config = self.users.config('name')
        self.assertEqual('some value', config['foo.bar'])

    def test_has_user(self):
        self.users.add('name')

        self.assertTrue(self.users.has_user('name'))
        self.assertFalse(self.users.has_user('other'))
