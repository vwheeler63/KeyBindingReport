from ..keybindingreport import reload
from ..lib.debug import IntFlag, DebugBits, is_debugging

debugging = is_debugging(DebugBits.IMPORTING)
if debugging:
    print(f'{__package__}  >>> module execution')

reload(__package__, ('core'))
reload(__package__ + '.commands')  # Recurse into .commands/ subpackage.

from . import core
from .commands import *

__all__ = [
    'core',

    # commands/*
    'KeyBindingReportCommand',
    "KeyBindingReportWhichBindingCommand",
]

if debugging:
    print(f'{__package__}  <<<')
