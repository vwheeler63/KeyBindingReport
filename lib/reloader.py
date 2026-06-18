import importlib
import sys
from typing import Tuple


debugging = True
if debugging:
    print(f'{__name__}  >>> module execution....')

_reload_indent_level = -1


def reload(dotted_subpkg: str, submodules: Tuple[str, ...] | None = None):
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
        print(f'{indent}reload():  >>>\n  {indent}{dotted_subpkg=}\n  {indent}{submodules=}\n  {indent}{_reload_indent_level=}')

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


if debugging:
    print(f'{__name__}  <<<')
