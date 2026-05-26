"""************************************************************************
Which Binding Report
********************
"""
from datetime import datetime
import sublime_plugin
import sublime
from ...lib.debug import DebugBits, is_debugging
from ...lib import output_view
from .. import platform
from .. import core
from .. import data
from .. import output


# *************************************************************************
# Configuration
# *************************************************************************

_report_title = 'Which Binding?'



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

    def run(self,
            edit         : sublime.Edit,
            keypress_list: list[str] = ["ctrl+k", "ctrl+u"],
            platform_code: str | None = None
            ):
        """
        By specified key based on current scope Report binding selected the
        same way Sublime Text selects it:  reverse search selecting first
        binding where current scope matches key context.  Generate output
        in format `fmt`.

        :param self:           KeyBindingReportCommand object connected to current View
        :param edit:           sublime.Edit connected to current View, needed to edit Buffer
        :param keypress_list:  "keys" list ("keys" element from JSON key binding).
        :param platform_code:  Platform to simulate, or None to use current platform.
                                 Constraint:  one of the strings returned by
                                 ``sublime.platform()``: "windows", "linux" or "osx".
        :return:  None
        """
        debugging = is_debugging(DebugBits.WHICH_BINDING_REPORT)
        if debugging:
            print('In KeyBindingReportWhichBindingCommand.run()...')
            print(f'  {keypress_list=}')
            print(f'  {platform_code=}')

        if platform_code and platform_code not in platform.platform_names_by_code:
            raise AssertionError(f'`platform_code` must be one of {platform.platform_codes!r}.')

        t0 = datetime.now()
        key_data = data.KeyBindingData()

        if platform_code:
            platform.simulate_platform(platform_code)

        binding = key_data.which_binding(keypress_list, self.view)

        t1 = datetime.now()

        # TODO: rmv after testing.
        # Write verification/validation files.
        main_key_path = r'r:\by_main_key.txt'
        key_seq_path  = r'r:\by_key_seq.txt'
        key_data.dump_to_files(main_key_path, key_seq_path)
        key_data.dump_leading_keys_data(r'r:\leading_keys.txt')
        t2 = datetime.now()

        # =================================================================
        # Generate report.
        # =================================================================
        title = f'{core.package_name}:  Which Key Binding?'
        note = f'Binding Selected for {keypress_list} in Current Context:'

        content_parts = []
        content_parts.append(output.report_heading(title, note))
        content_parts.append('')

        if binding:
            binding_repr = binding.formatted(0, include_source=True)
            content_parts.append(binding_repr)

            leading_key_count = key_data.leading_key_count_in_key_sequences(keypress_list)
            if leading_key_count:
                plural_suffix = 's' if leading_key_count > 1 else ''
                content_parts.append('')
                content_parts.append(f'Notable:  Keypress "{keypress_list[0]}" is also the leading')
                content_parts.append(f'          keypress in {leading_key_count} keypress sequence{plural_suffix}.')
        else:
            content_parts.append('No binding found.')

        # -----------------------------------------------------------------
        # Finally, assemble parts into 1 string, and push to report View.
        # -----------------------------------------------------------------
        content_parts.append('')
        content = '\n'.join(content_parts)

        rpt_view = output_view.output_to_view(
                None,
                _report_title,
                content,
                current_view=self.view
                )

        win = rpt_view.window()
        if win:
            win.bring_to_front()

        t3 = datetime.now()

        if platform_code:
            platform.set_current_platform()

        if debugging:
            print('Time to generate data structures: ', str(t1 - t0))
            print('Time to write files             : ', str(t2 - t1))
            print('Time to generate report         : ', str(t3 - t2))
            print('Total                           : ', str(t3 - t0))
