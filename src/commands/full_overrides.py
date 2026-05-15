"""
Report Key Bindings that fully override other key bindings.
***********************************************************

See ``context_overrides.py`` docstring for detailed description.
"""
from datetime import datetime
import sublime_plugin
from ...lib.debug import DebugBits, is_debugging
from ...lib import output_view
from .. import core
from .. import data
from .. import output


# *************************************************************************
# Configuration
# *************************************************************************

_report_title = 'Key-Binding Overrides'



# *************************************************************************
# Constants
# *************************************************************************



# *************************************************************************
# Classes
# *************************************************************************

class KeyBindingReportOverridesCommand(sublime_plugin.ApplicationCommand):
    """ Report Key Bindings that override other key bindings. """
    def run(self):
        """
        Report Key Bindings that override other key bindings.
        """
        debugging = is_debugging(DebugBits.FULL_OVERRIDES_REPORT)
        if debugging:
            print(f'In {self.__class__.__name__}.run()...')

        t0 = datetime.now()
        key_data = data.KeyBindingData()
        # Generate ALL overrides minus bindings that
        # do not match current context.
        override_list = key_data.binding_overrides()
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
        list_sep = '-' * 75
        title = f'{core.package_name}:  Key-Binding Overrides'
        note = 'Bindings lowest in each list override bindings higher in that list.'

        content_parts = []
        content_parts.append(output.report_heading(title, note))
        content_parts.append('')

        if override_list:
            for override_set in override_list:
                content_parts.append(list_sep)
                for binding in override_set:
                    content_parts.append(binding.formatted(0, True))
                    content_parts.append('')
        else:
            content_parts.append('')
            content_parts.append('No overriding key bindings found.')

        # -----------------------------------------------------------------
        # Finally, assemble parts into 1 string, and push to report View.
        # -----------------------------------------------------------------
        content_parts.append('')
        content = '\n'.join(content_parts)

        rpt_view = output_view.output_to_view(
                None,
                _report_title,
                content,
                current_view=None
                )

        window = rpt_view.window()
        if window:
            window.bring_to_front()

        t3 = datetime.now()

        if debugging:
            print('Time to compute overrides: ', str(t1 - t0))
            print('Time to write files      : ', str(t2 - t1))
            print('Time to generate report  : ', str(t3 - t2))
            print('Total                    : ', str(t3 - t0))
