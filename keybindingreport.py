""" ***********************************************************************
Key Binding Report
***************************************************************************

KeyBindingReport is a Sublime Text Package that produces a wide variety of
reports about the current state of Sublime Text key bindings on the system
it is running on, with a choice of output formats.



Package Overview
****************

Directory        Description
./lib/           Reusable Components
./messages/      Install and update messages for PackageControl to display
./resources/     Package resource files (commands, menus, settings)
./src/           Python source code for Package logic
./src/commands/  Package Commands, one per file

This file:  coordinates it at the top.  It's function is to load
(or reload) all the modules in the Package as a response to being
loaded itself.  This happens:

- at Sublime Text start-up,
- when PackageControl updates the package, and
- when this file is saved during development.



The Big Report
**************

While there are smaller, more narrowly-focused reports, the one "big"
report that this package was written for (and supplies logic for most
of the reports in the Tools > KeyBindingReport > ... menu) is contained
in these files:

- ./src/commands/report.py   <-- The `KeyBindingReportCommand` Command
- ./src/data.py              <-- Gathers input data from system-wide key
                                   binding resources.  That data thereafter
                                   lives in a `KeyBindingData` object
                                   until it is disposed of.
- ./src/output.py            <-- Reads from `KeyBindingData` objects and
                                   produces output in specified format.



Other Reports
*************

The following reports also use `data.py` to gather their data, but
to a lesser extent:

- full_overrides.py
- context_overrides.py
- which_binding.py

The logic for the remaining reports is contained in their respective
Command files.

See `README.md` and `src/core.py` for more details.



@version  1.0  11-Apr-2026 18:21 vw  - Created
*********************************************************************** """
from datetime import datetime
import importlib.abc
import importlib.machinery
import sys
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

# from . import lib            # noqa: E402


# -------------------------------------------------------------------------
# kiss-reloader, from:
# https://github.com/kaste/KissReloader#add-a-reloader-to-your-package
# -------------------------------------------------------------------------
class InPlaceReloader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """
    Inheriting from ``MetaPathFinder`` requires redefinition of:

    - find_spec()

    Inheriting from ``Loader`` requires redefinition of:

    - create_module(), and
    - exec_module()

    Because this class inherits from both, it is both a "Finder" and a
    "Loader", i.e. an "Importer".

    The "key ingredient" in this class is that at the end of ``find_spec()``,
    objects instantiated from this class inject themselves (``self``) as
    the loader, replacing the default loader.  Thus:

    - When the ``with`` below this class is executed for the first time,
      ``__init__()`` below finds no already-existing modules from this Package
      in ``sys.modules``, and so the Package relies upon normal importing
      to import all the modules involved in this Package.

    - The next time the ``with`` is executed, all the imported modules in
      this Package are found in ``sys.modules``, and are "reused" and
      re-executed in place (to reload them), in the same order as needed
      by import statements.
    """
    def __init__(self, package_name=__spec__.parent, plugin_name=__name__):
        if debugging:
            print(f'In {self.__class__.__name__}.__init__()...')
            print(f'  {self=}')
            print(f'  {package_name=}')
            print(f'  {plugin_name=}')

        # Remember Package name for debug output later.
        self.prefix = package_name + "."

        # Preserve actual modules from this Package for reloading.
        self.modules = {
            name: module
            for name, module in sys.modules.items()
            if name.startswith(self.prefix) and name != plugin_name
        }
        if debugging:
            print('  self.modules:')
            for name in self.modules:
                print(f'    {name}')

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
            print(f'  Removing Package "{self.prefix}" modules from `sys.modules`.')

        if len(self.modules) == 0:
            if debugging:
                print(f'  No "{self.prefix}" modules found to remove. Using default import machinery.')
        else:
            count = 0
            for name in self.modules:
                count += 1
                sys.modules.pop(name, None)
            if debugging:
                print(f'  {count} modules removed.')

            self.clear_parent_module_attributes()
            if debugging:
                print('  Temporarily injecting self (as an "importer" [finder + loader]) into beginning')
                print('    of `sys.meta_path` list to intercept import statements from this Package that')
                print('    are not fulfilled by by a search of `sys.modules`.  The 2nd and subsequent times')
                print('    a module is imported will use the already-loaded module in `sys.modules`.')
            sys.meta_path.insert(0, self)

        return self

    def uninstall(self):
        if self in sys.meta_path:
            if debugging:
                print('Removing self from `sys.meta_path` list.')
            sys.meta_path.remove(self)

    def clear_parent_module_attributes(self):
        """
        This clean-up is important. Without it, an import such as
        ``from package.core import store`` can reuse ``package.core.store``
        directly from an already loaded parent package and never ask the
        import machinery to reload ``package.core.store``.
        """
        if debugging:
            print(f'In {self.__class__.__name__}.clear_parent_module_attributes()...')

        for name, module in self.modules.items():
            parent_name, _, attr = name.rpartition(".")
            parent = self.modules.get(parent_name)
            if isinstance(parent, ModuleType) and getattr(parent, attr, None) is module:
                if debugging:
                    print(f'  Found attribute {parent_name}.{attr}:  disconnecting it.')
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
            print('  Replacing default loader with self.')
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
            print(f'  In {self.__class__.__name__}.exec_module().')
        self.loaders[module.__name__].exec_module(module)



# *************************************************************************
# Load / Reload
# *************************************************************************

with InPlaceReloader():
    # Only `core` and the Commands are actually needed herein, but
    # the other imports are included so that they are reloaded when
    # the Package is reloaded (e.g. when this file is saved).
    from . import lib            # noqa: E402, F401
    from .src import *           # noqa: E402, F403
    from .src import core        # noqa: E402 -- Not required, but makes LSP-pyright happy.



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
