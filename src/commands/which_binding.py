"""
Which Binding Report
====================

This logic is launched via the ``KeyBindingReportWhichBindingCommand``
command at the end of this file.  The details of the algorithm are in
the docstring for that command.
"""
from datetime import datetime
from typing import List
import sublime_plugin
import sublime
from sublime import Region, View
from sublime_types import Point
from ...lib.ascii_table import Format, Generator
from ...lib.debug import IntFlag, DebugBits, is_debugging
from .. import core


class KeyBindingReportWhichBindingCommand(sublime_plugin.TextCommand):
    """ Generate Key-Binding Report for specified keypress. """

    def run(
            self         : sublime_plugin.TextCommand,
            edit         : sublime.Edit,
            keypress_list: List[List[str]] = [["f2"]],
            format       : Format   = Format.OUTLINED
            ):
        """
        By specified key based on current scope Report binding selected the
        same way Sublime Text selects it:  reverse search selecting first
        binding where current scope matches key context.  Generate output
        in format `format`.

        :param self:            KeyBindingReportCommand object connected to current View
        :param edit:            sublime.Edit connected to current View, needed to edit Buffer
        :param keypress_list:   List, tuple or set of "keys" (same format as "keys"
                                  elements from JSON key bindings).  Note that this enables
                                  you to specify more than one "keys" value.  Example:
                                  ``[["ctrl+k", "ctrl+u"], ["ctrl+shift+p"]]``
        :param format:          Which output format (ascii_table.Format)
        :return:  None
        """
        print(f"It's me.... {__name__}")
        from ...lib import context
        # context._snippet_triggers_dictionary()
        print(self.view)
        print(self.view.element())
        return

        debugging = is_debugging(DebugBits.WHICH_BINDING_REPORT)
        t0 = datetime.now()
        #core.build_report_data(package, key_group, key_name)
        t1 = datetime.now()
