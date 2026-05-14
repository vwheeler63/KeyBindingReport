"""************************************************************************
Key-Binding Platform
***************************************************************************"""

import sublime
from ..lib.debug import DebugBits, is_debugging



# *************************************************************************
# Configuration
# *************************************************************************



# *************************************************************************
# Constants
# *************************************************************************

windows_platform_code = 'windows'
linux_platform_code   = 'linux'
osx_platform_code     = 'osx'



# *************************************************************************
# Data
# *************************************************************************

platform               = sublime.platform()
platform_name          = ''
platform_name_w_parens = ''
cmd_col_hdg            = 'W'
cmd_key_name           = '⊞ Windows'
alt_col_hdg            = 'A'
alt_key_name           = 'Alt'
ctrl_col_hdg           = 'C'
ctrl_key_name          = 'Ctrl'
shift_col_hdg          = 'S'
shift_key_name         = 'Shift'
modifier_key_names_by_modifier_code_bit = {}



# *************************************************************************
# Utilities
# *************************************************************************



# *************************************************************************
# Function Definitions
# *************************************************************************

def is_windows() -> bool:
    return (( platform == windows_platform_code ))


def is_linux() -> bool:
    return (( platform == linux_platform_code ))


def is_osx() -> bool:
    return (( platform == osx_platform_code ))


def show_platform():
    print(f'{platform               = }')
    print(f'{platform_name          = }')
    print(f'{platform_name_w_parens = }')
    print(f'{cmd_col_hdg            = }')
    print(f'{cmd_key_name           = }')
    print(f'{alt_col_hdg            = }')
    print(f'{alt_key_name           = }')
    print(f'{ctrl_col_hdg           = }')
    print(f'{ctrl_key_name          = }')
    print(f'{shift_col_hdg          = }')
    print(f'{shift_key_name         = }')
    print(f'{modifier_key_names_by_modifier_code_bit = }')


def set_platform(platform_code: str):
    """ Set data` module attributes in which platform plays a role. """
    if platform_code not in (windows_platform_code, linux_platform_code, osx_platform_code):
        raise AssertionError(f'`platform_code` not recognozed: [{platform_code}].')

    debugging = is_debugging(DebugBits.PLATFORM)

    global platform
    global platform_name
    global platform_name_w_parens
    global cmd_col_hdg
    global cmd_key_name
    global alt_col_hdg
    global alt_key_name
    global ctrl_col_hdg
    global ctrl_key_name
    global shift_col_hdg
    global shift_key_name
    global modifier_key_names_by_modifier_code_bit

    platform = platform_code

    platform_name = {
        windows_platform_code: 'Windows',
        linux_platform_code  : 'Linux',
        osx_platform_code    : 'OSX',
    }[platform]

    platform_name_w_parens = '(' + platform_name + ')'

    # Column headings rely on platform_name.
    if platform == osx_platform_code:
        cmd_col_hdg    = 'C'
        cmd_key_name   = '⌘ Command'
        alt_col_hdg    = 'O'
        alt_key_name   = '⌥ Option'
        ctrl_col_hdg   = '^'
        ctrl_key_name  = 'Ctrl'
        shift_col_hdg  = 'S'
        shift_key_name = 'Shift'

        modifier_key_names_by_modifier_code_bit = {
            1: 'Shift',
            2: 'Ctrl',
            4: 'Option',
            8: 'Command',
        }
    else:
        cmd_col_hdg    = 'W'
        cmd_key_name   = '⊞ Windows'
        alt_col_hdg    = 'A'
        alt_key_name   = 'Alt'
        ctrl_col_hdg   = 'C'
        ctrl_key_name  = 'Ctrl'
        shift_col_hdg  = 'S'
        shift_key_name = 'Shift'

        modifier_key_names_by_modifier_code_bit = {
            1: 'Shift',
            2: 'Ctrl',
            4: 'Alt',
            8: '⌘',
        }

    if debugging:
        show_platform()


def simulate_windows_platform():
    set_platform(windows_platform_code)


def simulate_linux_platform():
    set_platform(linux_platform_code)


def simulate_osx_platform():
    set_platform(osx_platform_code)


def set_current_platform():
    set_platform(sublime.platform())


set_current_platform()


