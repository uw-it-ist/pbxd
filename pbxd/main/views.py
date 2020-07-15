from . import main
from ..app import pbx


@main.route('/healthz')
def index():
    """
    Return the result of a full self diagnostic check.
    """
    return pbx.ossi_command('display time', fields={"0007ff00": ""}, debug=False)
