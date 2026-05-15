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


def simulate_platform(platform_code: str):
    """ Set data` module attributes in which platform plays a role. """
    if platform_code not in (windows_platform_code, linux_platform_code, osx_platform_code):
        raise AssertionError(f'`platform_code` not recognozed: [{platform_code}].')

    debugging = is_debugging(DebugBits.PLATFORM)

    global platform
    global platform_name
    global platform_name_w_parens

    platform = platform_code
    platform_name = platform_names_by_code[platform_code]
    platform_name_w_parens = '(' + platform_name + ')'

    if debugging:
        show_platform()


def simulate_windows_platform():
    simulate_platform(windows_platform_code)


def simulate_linux_platform():
    simulate_platform(linux_platform_code)


def simulate_osx_platform():
    simulate_platform(osx_platform_code)


def set_current_platform():
    simulate_platform(execution_platform)


set_current_platform()


