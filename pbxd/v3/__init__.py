# the order of imports is important here. "v3" uses "api"
# so "v3" must be imported before "views".
from ..blueprint import v3  # noqa: F401
from . import views  # noqa: F401
