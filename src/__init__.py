from ..keybindingreport import reload
from ..lib.debug import IntFlag, DebugBits, is_debugging

debugging = is_debugging(DebugBits.IMPORTING)
if debugging:
    print(f'{__package__}  >>> module execution')

reload(__package__, ('core', 'data', 'output'))
reload(__package__ + '.commands')  # Recurse into .commands/ subpackage.

from . import core       # noqa: E402
from . import data       # noqa: E402
from . import output     # noqa: E402
from .commands import *  # noqa: E402

__all__ = [
    'core',

    # events/listeners

    # commands/*
    'KeyBindingReportCommand',
    "KeyBindingReportWhichBindingCommand",
    'KeyBindingReportKeysUsedCommand',
    'KeyBindingReportContextOverridesCommand',
    'KeyBindingReportOverridesCommand',
]

if debugging:
    print(f'{__package__}  <<<')
