import os
import sys
import logging
from flask import Flask
import atexit
import json
from .pbx import definity
import time

logging.captureWarnings(True)
logger = logging.getLogger(__name__)


# setup the config for the PBX connection
logger.info('Loading pbxd config {}'.format(os.environ['PBXD_CONF']))
with open(os.environ['PBXD_CONF']) as json_file:
    config = json.load(json_file)

pbx = definity.Terminal(
    config['connection_command'],
    config['pbx_username'],
    config['pbx_password'],
    pbx_command_timeout=os.environ['PBX_COMMAND_TIMEOUT']
)


# when flask exits disconnect cleanly from the pbx
@atexit.register
def pbx_disconnect():
    if pbx.connected_termtype is not None:
        logger.info('Logging out of pbx')
        pbx.disconnect()


def load():
    app = Flask(__name__, static_folder=None)
    app.config['JSON_SORT_KEYS'] = False  # preserve the field order from the PBX

    # set flask logging to match gunicorn level
    if __name__ != '__main__':
        gunicorn_logger = logging.getLogger('gunicorn.error')
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)

        definity_logger = logging.getLogger('pbxd.pbx.definity')
        definity_logger.handlers = gunicorn_logger.handlers
        definity_logger.setLevel(gunicorn_logger.level)

    # set the env variable APPLICATION_ROOT to the URL path where the app is served
    app.config["APPLICATION_ROOT"] = os.environ.get("APPLICATION_ROOT", "/")
    logger.debug('using app root {}'.format(app.config['APPLICATION_ROOT']))
    prefix = app.config["APPLICATION_ROOT"]
    if app.config["APPLICATION_ROOT"] == "/":
        prefix = ""

    # connect to the PBX when the worker starts
    try:
        pbx.connect()
    except Exception as e:
        if 'Too many logins' in str(e):
            logger.error(e)
            time.sleep(10)
            sys.exit(1)  # gunicorn respawns the worker
        else:  # this raises an Exception and stops the container
            raise Exception('Unable to connect to PBX. {}'.format(e))

    # register the blueprint routes
    from .main import main
    app.register_blueprint(main, url_prefix='{}/'.format(prefix))

    from .v2 import v2
    app.register_blueprint(v2, url_prefix='{}/v2/'.format(prefix))

    from .v3 import v3
    app.register_blueprint(v3, url_prefix='{}/v3/'.format(prefix))

    # log the URL paths that are registered
    for url in app.url_map.iter_rules():
        logger.info(repr(url))

    return app
