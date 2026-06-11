"""************************************************************************
Keys-Available Report
*********************

See docstring under ``KeyBindingReportKeysAvailableCommand.run()`` method.
"""

import sublime_plugin
from ...lib.debug import DebugBits, is_debugging
from ...lib import ascii_table
from .. import platform
from .. import data
from .. import output



# *************************************************************************
# Configuration
# *************************************************************************



# *************************************************************************
# Constants
# *************************************************************************



# *************************************************************************
# Classes
# *************************************************************************

class KeyBindingReportKeysAvailableCommand(sublime_plugin.TextCommand):
    """ Report Keys-Available Based on All Keymaps Report. """

    def run(self, edit, platform_code: str | None = None):
        """
        Generate Key-Binding Keys-Available Report.

        Main Keys Available with which keypresses, squashed to just the key if
        no keypresses are mapped with that main key.

        :param platform_code:
                            Platform to simulate, or None to use current platform.
                              Constraint:  one of the strings returned by
                              ``sublime.platform()``: "windows", "linux" or "osx".
        """
        debugging = is_debugging(DebugBits.KEYS_AVAILABLE_REPORT)
        if debugging:
            print('In KeyBindingReportKeysAvailableCommand.run()...')

        if platform_code:
            if platform_code in platform.platform_names_by_code:
                platform.simulate_platform(platform_code)
            else:
                raise AssertionError(f'`platform_code` must be one of {platform.platform_codes!r}.')

        flags = (
                  data.FlagBits.INCLUDE_UNBOUND_KEYPRESSES_ONLY
                | data.FlagBits.INCLUDE_WINDOWS_KEY
                )

        # Note:  passing "key_groups": [data.KeyGroup.ALL] does not work
        # because that causes multi-keypress bindings to be included as well,
        # and that domain is not relevant to "keys available".
        key_group_list = []
        for i in range(data.KeyGroup.FIRST, data.KeyGroup.LAST + 1):
            key_group_list.append(i)

        args = {
            "key_groups"       : key_group_list,
            #"limit_to_packages": ["Default"],
            "fmt"              : ascii_table.Format.OUTLINED,
            "flags"            : flags
        }

        self.view.run_command('key_binding_report', args)

        if platform_code:
            platform.set_current_platform()

