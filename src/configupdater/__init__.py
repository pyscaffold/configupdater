from importlib.metadata import PackageNotFoundError, version

try:
    # Change here if project is renamed and does not equal the package name
    dist_name = "ConfigUpdater"
    __version__ = version(dist_name)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
finally:
    del version, PackageNotFoundError

from . import configupdater, parser

# import everything and rely on __ALL__
from .configupdater import *
from .parser import *

__all__ = list(set(configupdater.__all__ + parser.__all__))
