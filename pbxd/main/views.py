from . import main
from ..app import pbx


@main.route('/ready')
def readiness():
    """
    Report that a worker is ready to handle a request.
    """
    return 'OK'


@main.route('/healthz')
def liveness():
    """
    Check if the application is able to perform its function.
    """
    return pbx.ossi_command('display time', fields={"0007ff00": ""}, debug=False)
