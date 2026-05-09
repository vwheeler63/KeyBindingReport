"""
Which Binding Report
====================

This logic is launched via the ``KeyBindingReportWhichBindingCommand``
command at the end of this file.  The details of the algorithm are in
the docstring for that command.
"""
import json
import pprint
from datetime import datetime
import sublime_plugin
import sublime
from ...lib.debug import DebugBits, is_debugging
from ...lib import output_view
from .. import core
from .. import data
from .. import output


# *************************************************************************
# Configuration
# *************************************************************************

_cfg_report_title = 'Which Binding?'



# *************************************************************************
# Classes
# *************************************************************************

class KeyBindingReportWhichBindingCommand(sublime_plugin.TextCommand):
    """
    Generate Key-Binding Report for specified keypress or keypress sequence,
    based on context in current View.

    Inheriting from TextCommand is needed because this is the only
    way to get Views that may not be part of a Sheet, but may
    instead be part of the UI (e.g. Find textbox).  This is needed
    to feed into the context-query engine.
    """

    def _heading(self, title: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        parts = []
        parts.append('')
        parts.append(title)
        parts.append('*' * len(title))
        parts.append('')
        parts.append(f'Report generated:  {timestamp}')

        return '\n'.join(parts)

    def run(
            self         : sublime_plugin.TextCommand,
            edit         : sublime.Edit,
            keypress_list: list[str] = ["ctrl+k", "ctrl+u"]
            ):
        """
        By specified key based on current scope Report binding selected the
        same way Sublime Text selects it:  reverse search selecting first
        binding where current scope matches key context.  Generate output
        in format `fmt`.

        :param self:            KeyBindingReportCommand object connected to current View
        :param edit:            sublime.Edit connected to current View, needed to edit Buffer
        :param keypress_list:   "keys" list ("keys" element from JSON key binding).
        :param fmt:             Which output format
        :return:  None
        """
        debugging = is_debugging(DebugBits.WHICH_BINDING_REPORT)
        if debugging:
            print('>\n>\n>\n>')
            print('In KeyBindingReportWhichBindingCommand.run()...')
            print(f'  {keypress_list=}')

        t0 = datetime.now()
        key_groups = None
        key_names = None
        limit_to_packages = None
        view = self.view
        key_data = data.KeyBindingData()
        key_data.generate(key_groups, key_names, [keypress_list], limit_to_packages, view)
        binding = key_data.which_binding(keypress_list, self.view)
        keypress_list_json = json.dumps(keypress_list)
        t1 = datetime.now()

        # TODO: rmv after testing.
        # Write verification/validation files.
        main_key_path = r'r:\by_main_key.txt'
        key_seq_path  = r'r:\by_key_seq.txt'
        key_data.dump_to_files(main_key_path, key_seq_path)
        t2 = datetime.now()

        # =================================================================
        # Generate report.
        # =================================================================
        title = f'{core.package_name}:  Which Key Binding?'

        content_parts = []
        content_parts.append(output.heading(title))
        heading = f'Binding Selected for {keypress_list_json} in Current Context:'
        underline = '=' * len(heading)
        content_parts.append('')
        content_parts.append('')
        content_parts.append('')
        content_parts.append(heading)
        content_parts.append(underline)
        content_parts.append('')

        if binding:
            binding_repr = binding.formatted(0, include_source=True)
            content_parts.append(binding_repr)
        else:
            content_parts.append('No binding found.')

        # -----------------------------------------------------------------
        # Finally, assemble parts into 1 string, and push to report View.
        # -----------------------------------------------------------------
        content_parts.append('')
        content = '\n'.join(content_parts)

        rpt_view = output_view.output_to_view(
                None,
                _cfg_report_title,
                content,
                current_view=view
                )

        rpt_view.window().bring_to_front()
        t3 = datetime.now()

        print('Time to generate data structures: ', str(t1 - t0))
        print('Time to write files             : ', str(t2 - t1))
        print('Time to generate report         : ', str(t3 - t2))
        print('Total                           : ', str(t3 - t0))
