"""************************************************************************
Keys-Used Report
****************

See docstring under ``KeyBindingReportKeysUsedCommand.run()`` method.
"""

from typing import Union
import sublime_plugin
import sublime
from ...lib.debug import IntFlag, DebugBits, is_debugging
from ...lib import ascii_table
from ...lib import output_view
from .. import platform
from .. import key_binding
from .. import data
from .. import output
from .. import core



# *************************************************************************
# Configuration
# *************************************************************************

_report_short_title = 'Keys Used'



# *************************************************************************
# Classes
# *************************************************************************

class KeyBindingReportKeysUsedCommand(sublime_plugin.ApplicationCommand):
    """ Report Keys-Used-In-All-Keymaps Report. """

    def run(self, platform_code: Union[str, None] = None):
        """
        Generate Key-Binding Keys-Used Report.

        Modifier Keys Used with how many times each.
        Main Keys Used with how many times each.

        :param platform_code:
                            Platform to simulate, or None to use current platform.
                              Constraint:  one of the strings returned by
                              ``sublime.platform()``: "windows", "linux" or "osx".
        """
        debugging = is_debugging(DebugBits.KEYS_USED_REPORT)
        if debugging:
            print('In KeyBindingReportKeysUsedCommand.run()...')

        if platform_code:
            if platform_code in platform.platform_names_by_code:
                platform.simulate_platform(platform_code)
            else:
                raise AssertionError(f'`platform_code` must be one of {platform.platform_codes!r}.')

        main_key_counts = {}
        main_key_reported = {}
        mod_key_counts = {}

        # -----------------------------------------------------------------
        # Gather data from `*.sublime-keymap` files.
        # -----------------------------------------------------------------
        keymap_paths = sublime.find_resources('*.sublime-keymap')

        for path in keymap_paths:
            try:
                keymap_resource_str = sublime.load_resource(path)
                decoded_key_bindings = sublime.decode_value(keymap_resource_str)
            except Exception as e:
                msg1 = f'{__name__}._conditionally_add_bindings_from_keymap() Error:'
                msg2 = f'  Sublime Text could not parse keymap file at\n  {path}'
                msg3 = f'  Exception:  {e}'
                msg4 =  '  Skipping file.'
                print(msg1)
                print(msg2)
                print(msg3)
                print(msg4)
                continue

            if (   decoded_key_bindings is None
                or isinstance(decoded_key_bindings, bool)
                or isinstance(decoded_key_bindings, int)
                or isinstance(decoded_key_bindings, float) ):
                decoded_key_bindings = []

            for decoded_binding in decoded_key_bindings:
                keypress_tuple = tuple(decoded_binding['keys'])

                for keypress_str in keypress_tuple:
                    keypr = key_binding.Keypress(keypress_str)
                    main_key_name = keypr.main_key_name

                    if main_key_name in main_key_counts:
                        main_key_counts[main_key_name] += 1
                    else:
                        main_key_counts[main_key_name] = 1
                        main_key_reported[main_key_name] = False

                    for mod_key in keypr.modifier_key_list:
                        if mod_key in mod_key_counts:
                            mod_key_counts[mod_key] += 1
                        else:
                            mod_key_counts[mod_key] = 1

        # -----------------------------------------------------------------
        # Modifier Keys
        # -----------------------------------------------------------------
        rows = []
        rows.append(['Key', 'Found'])  # Column headings
        rows.append(['', ''])          # Empty row

        for key_name in sorted(mod_key_counts.keys()):
            if key_name == '"':
                key_str = f'"\\{key_name}"'
            else:
                key_str = f'"{key_name}"'

            rows.append( [ key_str, str(mod_key_counts[key_name]) ] )

        mod_key_table = ascii_table.AsciiTable(rows)
        #mod_key_table.set_tight_columns([True, False])
        mod_key_table.set_column_alignments(['^', '>'])

        # -----------------------------------------------------------------
        # Documented Keys
        # ---------------
        # Sorted doesn't do well for `main_key_counts` because it mixes
        # the key groups up.  So we take another approach:  by key group
        # in sequence.  Note that this does not report all the keys
        # encountered, so an additional dictionary `main_key_reported`
        # is kept so that we can do a final loop at the end to report
        # all the keypresses encountered that did not get reported here.
        # -----------------------------------------------------------------
        rows = []
        rows.append(['Key', 'Found'])  # Column headings
        rows.append(['', ''])          # Empty row

        for key_name_group in data.key_name_groups:
            for key_name in key_name_group:
                if key_name == '"':
                    key_str = f'"\\{key_name}"'
                else:
                    key_str = f'"{key_name}"'

                if key_name in main_key_counts:
                    rows.append((key_str, str(main_key_counts[key_name])))
                    main_key_reported[key_name] = True
                else:
                    rows.append((key_str, '0'))

        documented_key_table = ascii_table.AsciiTable(rows)
        documented_key_table.set_tight_columns([True, False])
        documented_key_table.set_column_alignments(['^', '>'])

        # -----------------------------------------------------------------
        # Other Keys
        # -----------------------------------------------------------------
        rows = []
        rows.append(['Key', 'Found'])  # Column headings
        rows.append(['', ''])          # Empty row

        for key_name in sorted(main_key_reported.keys()):
            if not main_key_reported[key_name]:
                if key_name == '"':
                    key_str = f'"\\{key_name}"'
                else:
                    key_str = f'"{key_name}"'

                rows.append((key_str, str(main_key_counts[key_name])))
                main_key_reported[key_name] = True  # For tidiness.

        other_key_table = ascii_table.AsciiTable(rows)
        other_key_table.set_tight_columns([True, False])
        other_key_table.set_column_alignments(['^', '>'])

        rpt_title = f'{core.package_name}:  Keys Used in All Keymaps ({platform.platform_name})'
        content_parts = [output.report_heading(rpt_title)]
        content_parts.append('')
        content_parts.append('Modifier Keys:')
        content_parts.append( mod_key_table.to_string(ascii_table.Format.OUTLINED) )
        content_parts.append('')
        content_parts.append('Documented Keys:')
        content_parts.append( documented_key_table.to_string(ascii_table.Format.OUTLINED) )
        content_parts.append('')
        content_parts.append('Other Keys:')
        content_parts.append( other_key_table.to_string(ascii_table.Format.OUTLINED) )
        content_parts.append('')
        content = '\n'.join(content_parts)

        active_view = sublime.active_window().active_view()

        output_view.output_to_view(
                None,
                _report_short_title,
                content,
                current_view=active_view
                )

        if platform_code:
            platform.set_current_platform()

