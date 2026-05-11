from ...keybindingreport import reload

debugging = True
if debugging:
    print(f'{__package__}  >>> module execution....')

# These reload needs to include all the used modules in this directory, and
# all the subdirectories below it through a command that looks like
# ``reload(__package__ + '.subdirectory_name')``.  This is because the
# normal ``import`` statements will not do anything once they have been
# loaded since they are already present in ``sys.modules``.  But when they
# have since been modified, this forces them to be reloaded.
if __package__ is not None:
    reload(__package__, (
            'report',
            'which_binding',
            'keys_used',
            'context_overrides',
            'full_overrides'
            )
          )

# These imports are *below* the calls to ``reload()`` because when they are
# above them, the calls to ``reload()`` then reloads the just-imported
# modules---double work:  unnecessary.  Whereas, when they are below the
# calls to ``reload()``, then by design, the first time these modules are
# loaded, the calls to ``reload()`` do nothing, and the import statements
# do the work.
#
# In contrast, while the Package is being developed or enhanced, saving the
# top-level Plugin (or when the Package is updated by the ``PackageDev``
# Package during run time), causes the ``reload()`` calls to do their job
# of reloading updated modules, and the import statements to do nothing.
# This is by design.
#
# This set of imports is important to get the Commands and Listener symbols
# boosted up to the top-level module via the ``__all__`` attribute below.
from .report             import KeyBindingReportCommand                  # noqa: E402
from .which_binding      import KeyBindingReportWhichBindingCommand      # noqa: E402
from .keys_used          import KeyBindingReportKeysUsedCommand          # noqa: E402
from .context_overrides  import KeyBindingReportContextOverridesCommand  # noqa: E402
from .full_overrides     import KeyBindingReportOverridesCommand         # noqa: E402

__all__ = [
    'KeyBindingReportCommand',
    'KeyBindingReportWhichBindingCommand',
    'KeyBindingReportKeysUsedCommand',
    'KeyBindingReportContextOverridesCommand',
    'KeyBindingReportOverridesCommand',
]

if debugging:
    print(f'  {__package__}  <<<')
