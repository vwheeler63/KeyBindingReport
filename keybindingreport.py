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

debugging = True
if debugging:
    print(f'{__name__}  >>> module execution....')

# from . import lib            # noqa: E402


# -------------------------------------------------------------------------
# kiss-reloader
# Ref:  https://github.com/kaste/KissReloader#add-a-reloader-to-your-package
# -------------------------------------------------------------------------
class InPlaceReloader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, package_name=__spec__.parent, plugin_name=__name__):
        prefix = package_name + "."
        self.modules = {
            name: module
            for name, module in sys.modules.items()
            if name.startswith(prefix) and name != plugin_name
        }
        self.loaders = {}

    def __enter__(self):
        return self.install()

    def __exit__(self, exc_type, exc_value, traceback):
        self.uninstall()

    def install(self):
        for name in self.modules:
            sys.modules.pop(name, None)

        self.clear_parent_module_attributes()
        sys.meta_path.insert(0, self)
        return self

    def uninstall(self):
        if self in sys.meta_path:
            sys.meta_path.remove(self)

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.modules:
            return None

        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or spec.loader is None:
            return None

        self.loaders[fullname] = spec.loader
        spec.loader = self
        return spec

    def create_module(self, spec):
        return self.modules[spec.name]

    def exec_module(self, module):
        self.loaders[module.__name__].exec_module(module)

    def clear_parent_module_attributes(self):
        for name, module in self.modules.items():
            parent_name, _, attr = name.rpartition(".")
            parent = self.modules.get(parent_name)
            if isinstance(parent, ModuleType) and getattr(parent, attr, None) is module:
                delattr(parent, attr)


with InPlaceReloader():
    # Only `core` and the Commands are actually needed herein, but
    # the other imports are included so that they are reloaded when
    # the Package is reloaded (e.g. when this file is saved).
    from . import lib            # noqa: E402, F401
    from .src import *           # noqa: E402, F403
    from .src import core        # noqa: E402 -- Not required, but makes LSP-pyright happy.



# *************************************************************************
# Load / Reload
# *************************************************************************
# lib.reloader.reload(__spec__.parent + '.lib')  # Recurse into .lib/ subpackage.
# lib.reloader.reload(__spec__.parent + '.src')  # Recurse into .src/ subpackage.

# This needs to be BELOW the `reload()` definition above because the modules
# imported here require `reload()` to already be defined because they need
# to call it during the imports below.
# from .src import *     # noqa: E402, F403
# from .src import core  # noqa: E402  # Not required, but makes LSP-pyright happy.



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
