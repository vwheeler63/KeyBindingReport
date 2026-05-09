"""
Report Key Bindings that fully override other key bindings.
***********************************************************

See ``context_overrides.py`` docstring for detailed description.
"""
import pprint
from datetime import datetime
import sublime_plugin
import sublime
from ...lib.debug import DebugBits, is_debugging
from ...lib import ascii_table
from ...lib import output_view
from .. import data


# *************************************************************************
# Configuration
# *************************************************************************

_cfg_report_title = 'Full Key-Binding Overrides'



# *************************************************************************
# Constants
# *************************************************************************



# *************************************************************************
# Classes
# *************************************************************************

class KeyBindingReportFullOverridesCommand(sublime_plugin.TextCommand):
    """ Report Key Bindings that override other key bindings. """
    def _heading(self, title: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        parts = ['']
        parts.append(title)
        parts.append('*' * len(title))
        parts.append('')
        parts.append('Bindings lowest in each list override bindings higher in that list.')
        parts.append('')
        parts.append(f'Report generated:  {timestamp}')

        return '\n'.join(parts)

    def run(self, edit):
        """
        Report Key Bindings that override other key bindings.
        """
        debugging = is_debugging(DebugBits.FULL_OVERRIDES_REPORT)
        if debugging:
            print('>\n>\n>\n>')
            print('In KeyBindingReportFullOverridesCommand.run()...')

        t0 = datetime.now()
        key_data = data.KeyBindingData()
        # Generate ALL overrides minus bindings that
        # do not match current context.
        override_list = key_data.binding_overrides()
        # binding = key_data.which_binding(keypress_list, self.view)
        # keypress_list_json = json.dumps(keypress_list)
        t1 = datetime.now()

        # TODO: rmv after testing.
        # Write verification/validation files.
        main_key_path = r'r:\by_main_key.txt'
        key_seq_path  = r'r:\by_key_seq.txt'
        key_data.dump_to_files(main_key_path, key_seq_path)
        t2 = datetime.now()
        return

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
