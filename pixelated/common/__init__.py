import ssl
import logging
from logging.handlers import SysLogHandler

logger = logging.getLogger('pixelated.startup')


def init_logging(name, level=logging.INFO, config_file=None):
    global logger
    logger_name = 'pixelated.%s' % name

    logging.basicConfig(level=level)
    if config_file:
        logging.config.fileConfig(config_file)
    else:
        formatter = logging.Formatter('%(asctime)s %(name)s: %(levelname)s %(message)s', '%b %e %H:%M:%S')
        syslog = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_DAEMON)
        syslog.setFormatter(formatter)
        logger.addHandler(syslog)

    logger.name = logger_name
    logger.info('Initialized logging')


def latest_available_ssl_version():
    try:
        return ssl.PROTOCOL_TLSv1_2
    except AttributeError:
        return ssl.PROTOCOL_TLSv1
