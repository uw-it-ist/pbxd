from . import v3
from flask import request, abort
from ..app import logger
from ..app import pbx


@v3.route('/', methods=['POST'])
def pbx_command():
    try:  # to parse the requested v3 command
        data = request.get_json(silent=True)
        logger.info(request.data)
        termtype = data['termtype']
        command = data['command']
        fields = data.get('fields')
        debug = data.get('debug', False)
    except Exception as e:
        logger.error(f'Error in v3, failed to process request with exception: {str(e)}')
        abort(400, description='Bad request')

    return pbx.send_pbx_command(termtype, command, fields=fields, debug=debug)
