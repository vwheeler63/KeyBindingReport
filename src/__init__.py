debugging = True
if debugging:
    print(f'{__name__}  >>> module execution....')

# TODO: remove remnants of `reloader` if `InPlaceReloader` works out.
# from ..lib import reloader  # noqa: E402

# # These reload needs to include all the used modules in this directory, and
# # all the subdirectories below it through a command that looks like
# # ``reload(__spec__.parent + '.subdirectory_name')``.  This is because the
# # normal ``import`` statements will not do anything once they have been
# # loaded since they are already present in ``sys.modules``.  But when they
# # have since been modified, this forces them to be reloaded.
# reloader.reload(__spec__.parent, ('core', 'platform', 'smart_context', 'key_binding', 'data', 'output'))
# reloader.reload(__spec__.parent + '.commands')  # Recurse into .commands/ subpackage.

# These imports are *below* the calls to ``reload()`` because when they are
# above the calls to ``reload()``, then the reloads re-load the just-imported
# modules---double work:  unnecessary.  Whereas, when they are below the
# calls to ``reload()``, then by design, the first time these modules are
# loaded, the calls to ``reload()`` do nothing, and the import statements
# do the loading work.
#
# In contrast, while the Package is being developed or enhanced, saving the
# top-level Plugin (or when the Package is updated by the ``PackageDev``
# Package during run time), causes the ``reload()`` calls to do their job
# of reloading updated modules, and the import statements to do nothing.
#
# This is by design.
from . import core           # noqa: E402
from . import platform       # noqa: E402, F401
from . import smart_context  # noqa: E402, F401
from . import key_binding    # noqa: E402, F401
from . import data           # noqa: E402, F401
from . import output         # noqa: E402, F401
from .commands import *      # noqa: E402, F403

__all__ = [
    'core',

    # Events and Listeners

    # Commands from ./commands/*
    'KeyBindingReportCommand',                  # noqa: F405
    "KeyBindingReportWhichBindingCommand",      # noqa: F405
    'KeyBindingReportKeysUsedCommand',          # noqa: F405
    'KeyBindingReportKeysAvailableCommand',     # noqa: F405
    'KeyBindingReportContextOverridesCommand',  # noqa: F405
    'KeyBindingReportOverridesCommand',         # noqa: F405
]

if debugging:
    print(f'{__name__}  <<<')
