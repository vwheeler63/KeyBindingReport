"""************************************************************************
Key-Binding Platform
***************************************************************************"""

import sublime
from ..lib.debug import DebugBits, is_debugging



# *************************************************************************
# Configuration
# *************************************************************************

cfg_key_col_heading      = 'Key'
cfg_context_col_heading  = 'Ctxt'
cfg_command_col_heading  = 'Command'
cfg_args_col_heading     = 'Args'



# *************************************************************************
# Constants
# *************************************************************************

windows_platform_code = 'windows'
linux_platform_code   = 'linux'
osx_platform_code     = 'osx'

platform_codes = (
    windows_platform_code,
    linux_platform_code,
    osx_platform_code,
)

platform_names_by_code = {
    windows_platform_code: 'Windows',
    linux_platform_code  : 'Linux',
    osx_platform_code    : 'OSX',
}



# *************************************************************************
# Data
# *************************************************************************

execution_platform      = sublime.platform()
execution_platform_name = platform_names_by_code[execution_platform]
platform                = sublime.platform()
platform_name           = ''
platform_name_w_parens  = ''

cmd_col_heading   = ''
cmd_key_name      = ''
alt_col_heading   = ''
alt_key_name      = ''
ctrl_col_heading  = ''
ctrl_key_name     = ''
shift_col_heading = ''
shift_key_name    = ''



# *************************************************************************
# Utilities
# *************************************************************************

def show_platform():
    print(f'{platform               = }')
    print(f'{platform_name          = }')
    print(f'{platform_name_w_parens = }')


def show_platform_based_key_names():
    print(f'{cmd_col_heading   = }')
    print(f'{cmd_key_name      = }')
    print(f'{alt_col_heading   = }')
    print(f'{alt_key_name      = }')
    print(f'{ctrl_col_heading  = }')
    print(f'{ctrl_key_name     = }')
    print(f'{shift_col_heading = }')
    print(f'{shift_key_name    = }')



# *************************************************************************
# Function Definitions
# *************************************************************************

def update_modifier_key_names():
    debugging = is_debugging(DebugBits.PLATFORM)

    global cmd_col_heading
    global cmd_key_name
    global alt_col_heading
    global alt_key_name
    global ctrl_col_heading
    global ctrl_key_name
    global shift_col_heading
    global shift_key_name

    # Column headings rely on platform_name.
    if is_osx():
        cmd_col_heading   = 'C'
        cmd_key_name      = '⌘ Command'
        alt_col_heading   = 'O'
        alt_key_name      = '⌥ Option (Alt)'
        ctrl_col_heading  = '^'
        ctrl_key_name     = 'Ctrl'
        shift_col_heading = 'S'
        shift_key_name    = 'Shift'
    else:
        cmd_col_heading   = 'W'
        cmd_key_name      = '⊞ Windows'
        alt_col_heading   = 'A'
        alt_key_name      = 'Alt'
        ctrl_col_heading  = 'C'
        ctrl_key_name     = 'Ctrl'
        shift_col_heading = 'S'
        shift_key_name    = 'Shift'

    if debugging:
        show_platform_based_key_names()


def is_windows() -> bool:
    return (( platform == windows_platform_code ))


def is_linux() -> bool:
    return (( platform == linux_platform_code ))


def is_osx() -> bool:
    return (( platform == osx_platform_code ))


def simulate_platform(platform_code: str):
    """ Set data` module attributes in which platform plays a role. """
    if platform_code not in (windows_platform_code, linux_platform_code, osx_platform_code):
        raise AssertionError(f'`platform_code` not recognized: [{platform_code}].')

    debugging = is_debugging(DebugBits.PLATFORM)

    global platform
    global platform_name
    global platform_name_w_parens

    platform = platform_code
    platform_name = platform_names_by_code[platform_code]
    platform_name_w_parens = '(' + platform_name + ')'

    if debugging:
        show_platform()

    update_modifier_key_names()


def simulate_windows_platform():
    simulate_platform(windows_platform_code)


def simulate_linux_platform():
    simulate_platform(linux_platform_code)


def simulate_osx_platform():
    simulate_platform(osx_platform_code)


def set_current_platform():
    simulate_platform(execution_platform)


set_current_platform()


