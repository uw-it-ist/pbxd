from . import v3
from flask import request, abort
from ..app import logger
from ..app import pbx
from flask import current_app as app


@v3.route('/<pbx_name>', methods=['POST'])
def pbx_command(pbx_name):
    if pbx_name != app.config["PBX_NAME"]:
        logger.error('connected to the wrong PBX: {} != {}'.format(pbx_name, app.config["PBX_NAME"]))
        abort(500)

    try:  # to parse the requested v3 command
        data = request.get_json(silent=True)
        logger.debug(request.data)
        termtype = data['termtype']
        command = data['command']
        fields = data.get('fields')
        debug = data.get('debug', False)
    except Exception:
        abort(400, description='Bad request')

    return pbx.send_pbx_command(termtype, command, fields=fields, debug=debug)
