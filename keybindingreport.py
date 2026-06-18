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



# *************************************************************************
# Data
# *************************************************************************

# Can't use `debugging = is_debugging(DebugBits.IMPORTING)` here because
# the import required to support it causes a circular import.
t0 = datetime.now()

debugging = False
if debugging:
    print(f'{__name__}  >>> module execution....')

from . import lib  # noqa: E402



# *************************************************************************
# Load / Reload
# *************************************************************************
lib.reloader.reload(__spec__.parent + '.lib')  # Recurse into .lib/ subpackage.
lib.reloader.reload(__spec__.parent + '.src')  # Recurse into .src/ subpackage.

# This needs to be BELOW the `reload()` definition above because the modules
# imported here require `reload()` to already be defined because they need
# to call it during the imports below.
from .src import *     # noqa: E402, F403
from .src import core  # noqa: E402  # Not required, but makes LSP-pyright happy.



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
