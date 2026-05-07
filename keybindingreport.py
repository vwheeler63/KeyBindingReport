""" ***********************************************************************
Key Binding Report
******************

KeyBindingReport is a Sublime Text Package that produces a wide variety of
reports about the current state of Sublime Text key bindings on the system
it is running on, with a choice of output formats.

See `README.md` and `src/core.py` for more details.



@version  1.0  11-Apr-2026 18:21 vw  - Created
*********************************************************************** """
import importlib
import sys
import os
from datetime import datetime



# *************************************************************************
# Data
# *************************************************************************

module_path, _ = os.path.splitext(os.path.realpath(__file__))
_, submodule_name = os.path.split(module_path)
if isinstance(__package__, str):
    package_name = __package__
else:
    package_name = 'Unknown'
this_module_name = f'{package_name}.{submodule_name}'
del _, module_path, submodule_name
_reload_indent_level = -1

# Can't use `debugging = is_debugging(DebugBits.IMPORTING)` here because
# the import required to support it causes a circular import.
t0 = datetime.now()

debugging = True
if debugging:
    print(f'{this_module_name}  >>> module execution')


# *************************************************************************
# Load / Reload
# *************************************************************************

def reload(dotted_subpkg: str | None, submodules: tuple[str, ...] = ()):
    """
    Reload each module in `submodules` only if previously loaded.  This is a
    precondition of calling ``importlib.reload()`` but is also for efficiency:

    - if Sublime Text is just starting, nothing important happens here (because
      the cached modules will not have been added to ``sys.modules`` yet), and
      and the various ``import`` statements do the loading in the usual way;

    - if ``Package Control`` is updating this Package (or the central Plugin
      was just saved during development), then this function recursively
      reloads each loaded module, and the ``import`` statements then do
      nothing since each target module will already be in ``sys.modules``.

    Note:  The below works on the basis that ``<sublime_data>/Packages``
           directory was placed in ``sys.path`` by Sublime Text.  So the
           module names being constructed below have to look like this:

               MyPackage.subdir.module
               MyPackage.subdir.subdir.module
               etc.

    :param dotted_subpkg:  dotted directory portion of module names that
                             will be found in the keys of ``sys.modules``.
                             Example:  'MyPackage.src.commands'
    :param submodules:     tuple of submodule names; CAUTION: if there
                             is just one submodule, ('module_name') is NOT
                             NOT A TUPLE and will cause that module to NOT
                             be reloaded!  It must be ('module_name',) with
                             a comma to make it a tuple.
    """
    global _reload_indent_level
    _reload_indent_level += 1
    indent = '  ' * _reload_indent_level
    if debugging:
        if _reload_indent_level == 0:
            print('vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv')
        print(f'{indent}reload():  >>> {dotted_subpkg=} {submodules=}')

    if dotted_subpkg:
        if not submodules:
            # Called from top-level Plugin.
            module_name = dotted_subpkg
            if module_name in sys.modules:
                if debugging:
                    print(f'{indent}Reloading({module_name})')
                importlib.reload(sys.modules[module_name])
        else:
            # Called from subpackage.
            for submodule in submodules:
                module_name = f'{dotted_subpkg}.{submodule}'
                if module_name in sys.modules:
                    if debugging:
                        print(f'{indent}Reloading({module_name})')
                    importlib.reload(sys.modules[module_name])

    if debugging:
        print(f'{indent}reload():  <<<')
        if _reload_indent_level == 0:
            print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')

    _reload_indent_level -= 1


reload(package_name + '.lib')  # Recurse into .lib/ subpackage.
reload(package_name + '.src')  # Recurse into .src/ subpackage.

# This needs to be BELOW the `reload()` definition above because the modules
# imported here require `reload()` to already be defined because they both
# import it and call it.
from .lib import *     # noqa: E402, F403
from .src import *     # noqa: E402, F403
from .src import core  # noqa: E402



# *************************************************************************
# Events
# *************************************************************************

def plugin_loaded():
    core.on_plugin_loaded()


def plugin_unloaded():
    core.on_plugin_unloaded()


if debugging:
    print(f'{this_module_name}  <<<')
    t1 = datetime.now()
    print(f'Time to load/reload {this_module_name}: {t1 - t0}.')
