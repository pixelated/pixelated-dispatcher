class UserAlreadyExistsError(Exception):
    pass


class UserNotExistError(Exception):
    pass


class InstanceAlreadyExistsError(Exception):
    pass


class InstanceAlreadyRunningError(Exception):
    pass


class InstanceNotFoundError(Exception):
    pass


class InstanceNotRunningError(Exception):
    pass
