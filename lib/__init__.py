debugging = True
if debugging:
    print(f'{__name__}  >>> module execution....')

from . import reloader  # noqa: E402

if __spec__.parent is not None:
    reloader.reload(
            __spec__.parent,
            ('debug', 'rst_utils', 'output_view', 'ascii_table')
            # This list intentionally omits 'reloader' so that its
            # `_reload_indent_level` state doesn't get disturbed while
            # reloading is going on.  It does not change very often.
            # The cost is:  when it does change, ST has to be re-started.
            )

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
    print(f'{__name__}  <<<')
