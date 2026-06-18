debugging = True
if debugging:
    print(f'{__name__}  >>> module execution....')

from ...lib import reloader  # noqa: E402

# These reload needs to include all the used modules in this directory, and
# all the subdirectories below it through a command that looks like
# ``reload(__spec__.parent + '.subdirectory_name')``.  This is because the
# normal ``import`` statements will not do anything once they have been
# loaded since they are already present in ``sys.modules``.  But when they
# have since been modified, this forces them to be reloaded.
if __spec__.parent is not None:
    reloader.reload(
            __spec__.parent,
            (
                'report',
                'which_binding',
                'keys_used',
                'keys_available',
                'context_overrides',
                'full_overrides'
            )
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
#
# This set of imports is important to get the Commands and Listener symbols
# boosted up to the top-level module via the ``__all__`` attribute below.
from .report             import KeyBindingReportCommand                  # noqa: E402
from .which_binding      import KeyBindingReportWhichBindingCommand      # noqa: E402
from .keys_used          import KeyBindingReportKeysUsedCommand          # noqa: E402
from .keys_available     import KeyBindingReportKeysAvailableCommand     # noqa: E402
from .context_overrides  import KeyBindingReportContextOverridesCommand  # noqa: E402
from .full_overrides     import KeyBindingReportOverridesCommand         # noqa: E402

__all__ = [
    'KeyBindingReportCommand',
    'KeyBindingReportWhichBindingCommand',
    'KeyBindingReportKeysUsedCommand',
    'KeyBindingReportKeysAvailableCommand',
    'KeyBindingReportContextOverridesCommand',
    'KeyBindingReportOverridesCommand',
]

if debugging:
    print(f'  {__name__}  <<<')
