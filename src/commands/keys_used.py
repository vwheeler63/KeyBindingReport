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

_cfg_report_title = 'Keys Used Report'


# *************************************************************************
# Constants
# *************************************************************************



# *************************************************************************
# Classes
# *************************************************************************

class KeyBindingReportKeysUsedCommand(sublime_plugin.ApplicationCommand):
    """ Generate Key-Binding Keys-Used Report. """

    def _heading(self, title: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        parts = ['']
        parts.append(title)
        parts.append('*' * len(title))
        parts.append('')
        parts.append(f'Report generated:  {timestamp}')

        return '\n'.join(parts)

    def run(self):
        """
        Generate Key-Binding Keys-Used Report.

        Modifier Keys Used with how many times each.
        Main Keys Used with how many times each.
        """
        debugging = is_debugging(DebugBits.KEYS_USED_REPORT)
        if debugging:
            print('>\n>\n>\n>')
            print('In KeyBindingReportKeysUsedCommand.run()...')

        main_key_counts = {}
        main_key_reported = {}
        mod_key_counts = {}

        # -----------------------------------------------------------------
        # Gather data from `*.sublime-keymap` files.
        # -----------------------------------------------------------------
        keymap_paths = sublime.find_resources('*.sublime-keymap')

        for path in keymap_paths:
            keymap_resource_str = sublime.load_resource(path)
            decoded_key_bindings = sublime.decode_value(keymap_resource_str)

            for decoded_binding in decoded_key_bindings:
                keypress_tuple_bep = tuple(decoded_binding['keys'])

                for keypress_str in keypress_tuple_bep:
                    main_key_name, binding_lists_by_mod_code = \
                            data.main_key_and_bindings_by_mod_code(keypress_str)

                    if main_key_name in [' ']:
                        print(f'  {main_key_name=} {path=} {keypress_str=}')

                    if main_key_name in main_key_counts:
                        main_key_counts[main_key_name] += 1
                    else:
                        main_key_counts[main_key_name] = 1
                        main_key_reported[main_key_name] = False

                    for mod_key in binding_lists_by_mod_code:
                        if mod_key in [' ']:
                            print(f'  {mod_key=} {path=} {keypress_str=}')
                        if mod_key in mod_key_counts:
                            mod_key_counts[mod_key] += 1
                        else:
                            mod_key_counts[mod_key] = 1

        # -----------------------------------------------------------------
        # Modifier Keys
        # -----------------------------------------------------------------
        rows = [('Key', 'Found')]      # Column headings
        rows.append(('', ''))          # Empty row

        for key_name in sorted(mod_key_counts.keys()):
            if key_name == '"':
                key_str = f'"\\{key_name}"'
            else:
                key_str = f'"{key_name}"'

            rows.append((key_str, str(mod_key_counts[key_name])))

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
        rows = [('Key', 'Found')]      # Column headings
        rows.append(('', ''))          # Empty row

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
        rows = [('Key', 'Found')]      # Column headings
        rows.append(('', ''))          # Empty row

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

        content_parts = [self._heading(_cfg_report_title)]
        content_parts.append('')
        content_parts.append('Modifier Keys:')
        content_parts.append( mod_key_table.as_string(ascii_table.Format.OUTLINED) )
        content_parts.append('')
        content_parts.append('Documented Keys:')
        content_parts.append( documented_key_table.as_string(ascii_table.Format.OUTLINED) )
        content_parts.append('')
        content_parts.append('Other Keys:')
        content_parts.append( other_key_table.as_string(ascii_table.Format.OUTLINED) )
        content_parts.append('')
        content = '\n'.join(content_parts)

        active_view = sublime.active_window().active_view()

        output_view.output_to_view(
                None,
                _cfg_report_title,
                content,
                current_view=active_view
                )
