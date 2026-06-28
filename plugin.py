""" ***********************************************************************
Package Plugin
***************************************************************************

****************************************************
>>> See `src/core.py` for Package documentation. <<<
****************************************************

This is a generic Package plugin that provides module loading and reloading
services for the package it is part of.

Module loading happens the first time Sublime Text is started through
the standard "import" machinery.

Module reloading on the other hand is uniquely fitted to a Sublime Text
environment where 2 things commonly cause the Package to need to be
reloaded periodically:

:Package development:   Changes to any Package modules are best met by
                        an entire reload of all Package modules in the
                        same order they were originally loaded in.

:Package updates:       The Package Control Package itself updates other
                        Packages at run time without re-starting the
                        Python interpreter.  When Sublime Text Packages
                        are complex enough to require sub-packages, then
                        care must be taken on these updates that no
                        in-memory references attached to parts of of the
                        old Package are still present after the reload.

This module, as the top-level Package Plugin, takes care of both of those
circumstances:  whenever its file modification date gets updated (e.g. when
it is saved or overwritten with a new version), Sublime Text reloads this
module, which in turn reloads the other modules of the Package.



@version  Current revision:  @(#) v1.1  26-Jun-2026 11:06
@version  1.1  26-Jun-2026 11:06 vw  - Replaced reloader
@version  1.0  11-Apr-2026 18:21 vw  - Created
*********************************************************************** """
from datetime import datetime
import importlib.abc
import importlib.machinery
import sys
from contextlib import nullcontext
from typing import Dict
from types import ModuleType



# *************************************************************************
# Data
# *************************************************************************

# Can't use `debugging = is_debugging(DebugBits.IMPORTING)` here because
# the import required to support it causes a circular import.
t0 = datetime.now()

debugging = False
if debugging:
    print(f'{__name__}  >>> module execution....')



# *************************************************************************
# Reloader
# *************************************************************************

class InPlaceReloader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """
    Hot-reloader for use when the containing Package is updated either
    by development or when PackageControl updates it during run time.

    This is the ``InPlaceReloader`` from the ``README.md`` file at
    https://github.com/kaste/KissReloader.

    with documentation added to help make it understandable.


    Usage
    -----

    .. code-block:: py

        import importlib.abc
        import importlib.machinery
        import sys
        from contextlib import nullcontext
        from typing import Dict
        from types import ModuleType

        ...

        def reloader(package_name=__spec__.parent, plugin_name=__name__):
            prefix = package_name + "."
            modules = {
                name: module
                for name, module in sys.modules.items()
                if name.startswith(prefix) and name != plugin_name
            }
            return InPlaceReloader(modules) if modules else nullcontext()


        with reloader():
            # import your package here ... e.g.
            from .src.commands import *


    Inheritance Design
    ------------------

    Inheriting from ``MetaPathFinder`` requires redefinition of:

    - find_spec()

    Inheriting from ``Loader`` requires redefinition of:

    - create_module(), and
    - exec_module()

    Because this class inherits from both, it is both a "Finder" and a
    "Loader", i.e. an "Importer".


    How it Works
    ------------

    The "key ingredient" in this class is that at the end of ``find_spec()``,
    objects instantiated from this class inject themselves (``self``) as
    the loader, replacing the default loader.  But JUST for the modules in
    this Package.  Thus:

    - When the ``with`` below this module is loaded for the first time, e.g.
      during Sublime Text start-up, ``reloader()`` below finds no
      already-existing modules from this Package in ``sys.modules``, and so
      returns ``nullcontext()`` instead of an object instantiated from this
      class, and so this class is not instantiated and the loading relies
      entirely on the normal import mechanisms, without the involvement of
      this class.

    - The next time the ``with`` is executed, all the imported modules in
      this Package are found in ``sys.modules``, and collected and adding
      an additional reference to them in ``self.modules``, thus preserving
      them when references to them are later removed from ``sys.modules``.
      Finally, in ``exec_module()`` below, they are re-executed in place
      (to reload them), in the same order as needed by the import statements
      (since the reloading is triggered by executing the import machinery
      called into play by the ``import`` statements themselves).
    """
    def __init__(self, modules_dict: Dict[str, ModuleType]):
        if debugging:
            print(f'In {self.__class__.__name__}.__init__()...')
            print(f'  {self=}')
            print('  Modules:')
            for module_name in modules_dict:
                print(f'    {module_name}')

        # Preserve the modules from this Package for reloading by keeping a
        # reference to them.
        self.modules = modules_dict

        # Prepare loaders list, populated (one for each module) with each
        # successful call to ``self.find_spec()``, done by import machinery.
        # Loader "interception" is done by replacing the normal loader with
        # ``self``.
        self.loaders = {}

    # =====================================================================
    # Context Manager
    # =====================================================================

    def __enter__(self):
        return self.install()

    def __exit__(self, exc_type, exc_value, traceback):
        self.uninstall()

    def install(self):
        if debugging:
            print(f'In {self.__class__.__name__}.install()...')
            print(f'  Removing Package "{__spec__.parent}" modules from `sys.modules`.')

        if len(self.modules) == 0:
            if debugging:
                print(f'  No "{__spec__.parent}" modules found to remove. Using default import machinery.')
        else:
            # Remove this Package's modules from ``sys.modules``.
            count = 0
            for name in self.modules:
                count += 1
                sys.modules.pop(name, None)
            if debugging:
                print(f'  {count} modules removed.')

            # Disconnect other likely references to those modules.
            self.clear_parent_module_attributes()
            if debugging:
                print('  Temporarily injecting self (as an "importer" [finder + loader]) into beginning')
                print('    of `sys.meta_path` list to intercept import statements from this Package that')
                print('    are not fulfilled by by a search of `sys.modules`.  The 2nd and subsequent times')
                print('    a module is imported will use the already-loaded module in `sys.modules`.')

            # Insert self (`MetaPathFinder` role, as "importer" [both finder and loader]),
            # but ONLY for modules in this Package.  This "filter" is implemented in
            # ``find_spec()`` below by it returning ``None`` when the module is not
            # part of ``self.modules``.
            sys.meta_path.insert(0, self)

        return self

    def uninstall(self):
        if debugging:
            print(f'In {self.__class__.__name__}.uninstall()...')

        if self in sys.meta_path:
            if debugging:
                print('  Removing self from `sys.meta_path` list.')
            sys.meta_path.remove(self)

    def clear_parent_module_attributes(self):
        """
        This clean-up is important.  Without it, an import such as
        ``from package.core import store`` can reuse ``package.core.store``
        directly from an already loaded parent package instead of getting it
        reloaded and replaced through the import machinery.
        """
        if debugging:
            print(f'In {self.__class__.__name__}.clear_parent_module_attributes()...')

        for name, module in self.modules.items():
            parent_name, _, attr = name.rpartition(".")
            parent = self.modules.get(parent_name)
            if parent is None:
                parent = sys.modules.get(parent_name)
            if isinstance(parent, ModuleType) and getattr(parent, attr, None) is module:
                if debugging:
                    print(f'  Found attribute {parent_name}.{attr}:  disconnecting reference.')
                delattr(parent, attr)

    # =====================================================================
    # Finder
    # =====================================================================

    def find_spec(self, fullname, path=None, target=None):
        """
        :param fullname:  Module name, from ``import`` statement.
        :param path:      If module to be imported is in a package, this is
                            the parent package's __path__ attribute.
        :param target:    Module to reload, only passed during reload.
        :return:          An instance of ``importlib.machinery.ModuleSpec``,
                            or ``None`` if module cannot be found.
        """
        if debugging:
            print(f'In {self.__class__.__name__}.find_spec():  {fullname}')
            # print(f'  {path=}')
            # print(f'  {target=}')

        # If module is not part of THIS package...
        if fullname not in self.modules:
            # report that it could not be found---not the responsibility
            # of this reloader.
            if debugging:
                print(f'  {fullname} not found in `sys.modules`:  returning `None` to use default import machinery.')
            return None

        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or spec.loader is None:
            if debugging:
                print(f'  {fullname} searched for, but not found:  returning `None` to use default import machinery.')
            return None

        # if debugging:
        #     print(f'  Module found, {spec.loader=}.')
        self.loaders[fullname] = spec.loader
        # Inject ``self`` as the loader, thus "intercepting" normal loader/reloader.
        if debugging:
            print(f'  Replacing default loader with self for {fullname}.')
        spec.loader = self
        return spec

    # =====================================================================
    # Loader
    # =====================================================================

    def create_module(self, spec):
        if debugging:
            print(f'  In {self.__class__.__name__}.create_module():  Returning existing module.')

        return self.modules[spec.name]

    def exec_module(self, module):
        if debugging:
            print(f'  In {self.__class__.__name__}.exec_module({module.__name__}).')
        loader = self.loaders[module.__name__]
        if hasattr(loader, "exec_module"):
            loader.exec_module(module)
        else:
            loader.load_module(module.__name__)  # Python 3.8


# *************************************************************************
# Load / Reload
# *************************************************************************

def reloader(package_name=__spec__.parent, plugin_name=__name__):
    prefix = package_name + "."
    modules = {
        name: module
        for name, module in sys.modules.items()
        if name.startswith(prefix) and name != plugin_name
    }
    return InPlaceReloader(modules) if modules else nullcontext()


with reloader():
    # Only `core` and the Commands are actually needed herein, but
    # the other imports are included so that they are reloaded when
    # the Package is reloaded (e.g. when this file is saved).
    if debugging:
        print('>>> from .src import *')
    from .src import *     # noqa: E402, F403
    if debugging:
        print('>>> from .src import core')
    from .src import core  # noqa: E402 -- Not required, but makes LSP-pyright happy.



# *************************************************************************
# Events
# *************************************************************************

def plugin_loaded():
    core.on_plugin_loaded()


def plugin_unloaded():
    core.on_plugin_unloaded()


if debugging:
    print(f'{__name__}  <<<')
    t1 = datetime.now()
    print(f'Time to load/reload {__name__}: {t1 - t0}.')
