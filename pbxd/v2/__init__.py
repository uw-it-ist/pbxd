# the order of imports is important here. "views" uses "v2"
# so "v2" must be imported before "views".
from ..blueprint import v2  # noqa: F401
from . import views  # noqa: F401
