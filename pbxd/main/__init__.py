# the order of imports is important here. "view" uses "main"
# so "main" must be imported before "views".
from ..blueprint import main  # noqa: F401
from . import views  # noqa: F401
