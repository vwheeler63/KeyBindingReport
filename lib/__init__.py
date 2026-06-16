from ..keybindingreport import reload

debugging = False
if debugging:
    print(f'{__package__}  >>> module execution....')

if __package__ is not None:
    reload(__package__, ('debug', 'rst_utils', 'output_view', 'ascii_table'))

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
from . import debug          # noqa: E402
from . import rst_utils      # noqa: E402
from . import output_view    # noqa: E402
from . import ascii_table    # noqa: E402

__all__ = [
    'debug',
    'rst_utils',
    'output_view',
    'ascii_table',
]

if debugging:
    print(f'{__package__}  <<<')
