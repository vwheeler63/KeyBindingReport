"""************************************************************************
Which Binding Report
********************
"""
import os
from typing import List
from datetime import datetime
import sublime_plugin
import sublime
from sublime_types import Event, Value
from ...lib.debug import IntFlag, DebugBits, is_debugging
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

class KeypressListInputHandler(sublime_plugin.TextInputHandler):
    def initial_text(self):
        """
        Initial text shown in the text entry box. Empty by default.
        """
        return 'ctrl+k, ctrl+u'

    def placeholder(self):
        """
        This placeholder text is shown in the background of the text entry
        box (grayed out) whenever it is empty.  Empty by default.
        """
        return 'Enter keypress or keypress sequence to test.'

    def description(self, text):
        """
        The text to show in the *Command Palette* when this input handler is not
        at the top of the input handler stack.  Defaults to the text the user
        entered.
        """
        return '<keypress_list>'

    def preview(self, text):
        """
        Called whenever the user changes the text in the entry box. The returned
        value (either plain text or HTML) will be shown in the preview area of
        the *Command Palette*.
        """
        return sublime.Html(f'<strong>Keypress:</strong> <em>[{text}]</em>')

    def validate(self, text: str, event: Event | None = None) -> bool:
        """
        Called when user hits [Enter] to submit input.  If this method returns
        `False`, nothing happens.  If it returns `True`, the input sequence proceeds.
        Default implementation returns `True`.

        :param event:  Gets passed when `want_event` returns `True`.  User hitting
                       plain [enter] results in `event` containing
                         `{'modifier_keys': {}}`.
                       [ctrl+enter] results in `event` containing
                         `{'modifier_keys': {'ctrl': True, 'primary': True}}`.
                       [shift+ctrl+alt] results in `event` containing
                         `{'modifier_keys': {'alt': True, 'ctrl': True, 'primary': True, 'shift': True}}`
        """
        print(f'validate({text=}, {event=}) running...')
        result = True

        if text == 'Hello':
            result = False

        return result

    def cancel(self):
        """
        Called as an "event hook" if/when user cancels input sequence with [Esc]
        or [Backspace] to go back.
        """
        print('User cancelled at KeypressListInputHandler.')

    def confirm(self, text: str, event: Event | None = None):
        """
        Called when the input is accepted, after the user has pressed enter and
        the text has been validated.

        :param event:  Gets passed when `want_event` returns `True`.  User hitting
                       plain [enter] results in `event` containing
                         `{'modifier_keys': {}}`.
                       [ctrl+enter] results in `event` containing
                         `{'modifier_keys': {'ctrl': True, 'primary': True}}`.
                       [shift+ctrl+alt] results in `event` containing
                         `{'modifier_keys': {'alt': True, 'ctrl': True, 'primary': True, 'shift': True}}`
        """
        print(f'KeypressList.confirm():  Got [{text}].  Event object below.')
        print(f'{event=}')

    def want_event(self) -> bool:
        """
        Whether the `validate()` and `confirm()` methods should received a
        second `Event`-type parameter.  Returns `False` by default.
        """
        return True

    def next_input(self, args):
        if 'platform_code' not in args:
            return PlatformCodeInputHandler()

class PlatformCodeInputHandler(sublime_plugin.ListInputHandler):
    def list_items(self) -> tuple[list[tuple[str, Value]], int]:
        """
        This method should return the items to show in the list.

        The returned value may be a ``list`` items or a 2-element ``tuple`` containing a
        list of items and an ``int`` index of the item to pre-select.

        The each list item may be one of:

        - a string used for both the row text and the value passed to the command;
        - a 2-element tuple containing a string for the row text, and a ``Value``
        to pass to the command; or
        - a ``sublime.ListInputItem`` object.
        """
        choice_list = [
            ('Windows', 'windows'),
            ('Linux', 'linux'),
            ('OSX', 'osx')
        ]
        code_list = [
            'windows',
            'linux',
            'osx'
        ]
        default_idx = code_list.index(platform.execution_platform)
        return (choice_list, default_idx)

    def description(self, value, text: str) -> str:
        """
        The text to show in the *Command Palette* when this input handler is not
        at the top of the input handler stack. Defaults to the text of the list
        item the user selected.
        """
        return f'Platform = [{text}] code = [{value}]'

    def preview(self, text):
        """
        Called whenever the user changes the text in the entry box. The returned
        value (either plain text or HTML) will be shown in the preview area of
        the *Command Palette*.
        """
        return sublime.Html(f'<strong>platform_code:</strong> <em>{text}</em>')

    def cancel(self):
        """
        Called as an "event hook" if/when user cancels input sequence with [Esc]
        or [Backspace] to go back.
        """
        print('User cancelled at PlatformCodeInputHandler.')

    def confirm(self, text: str, event: Event | None = None):
        """
        Called when the input is accepted, after the user has pressed enter and
        the text has been validated.

        :param event:  Gets passed when `want_event` returns `True`.  User hitting
                       plain [enter] results in `event` containing
                         `{'modifier_keys': {}}`.
                       [ctrl+enter] results in `event` containing
                         `{'modifier_keys': {'ctrl': True, 'primary': True}}`.
                       [shift+ctrl+alt] results in `event` containing
                         `{'modifier_keys': {'alt': True, 'ctrl': True, 'primary': True, 'shift': True}}`
        """
        print(f'PlatformCode.confirm():  Got [{text}].  Event object below.')
        self.selected_value = text


class KeyBindingReportWhichBindingCommand(sublime_plugin.TextCommand):
    """
    Generate Key-Binding Report for specified keypress or keypress sequence,
    based on context in current View.

    Inheriting from TextCommand is needed because this is the only
    way to get Views that may not be part of a Sheet, but may
    instead be part of the UI (e.g. Find textbox).  This is needed
    to feed into the context-query engine.
    """
    def input(self, args):
        """
        If this returns something other than ``None``, user will be
        prompted for specified input before the Command is run.
        """
        if 'keypress_list' not in args:
            return KeypressListInputHandler()

    def input_description(self):
        return 'Which Binding?'

    def run(self,
            edit         : sublime.Edit,
            keypress_list: List[str] | str,
            platform_code: str | None
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

        t0 = datetime.now()

        if platform_code and platform_code not in platform.platform_names_by_code:
            raise AssertionError(f'`platform_code` must be one of {platform.platform_codes!r}.')

        # =================================================================
        # Adjust ``keypress_list`` if needed.  It can come from a user
        # prompt from ``KeypressListInputHandler`` in which case it will
        # be a string.
        # =================================================================
        if isinstance(keypress_list, str):
            if ',' in keypress_list:
                temp_list = keypress_list.split(',')
                keypress_list = []
                for item in temp_list:
                    keypress_list.append(item.strip())
            else:
                keypress_list = [keypress_list.strip()]

        # =================================================================
        # Gather data about current editing context.
        # =================================================================
        view          = self.view
        live_sel_list = view.sel()
        first_sel     = live_sel_list[0]
        caret_pt      = first_sel.begin()
        row, col      = view.rowcol(caret_pt)
        element       = view.element()
        window        = view.window()
        file          = view.file_name()
        scope         = view.scope_name(caret_pt).strip()
        if debugging:
            print(f'  {first_sel=}')
            print(f'  {caret_pt=}')
            print(f'  {row=}')
            print(f'  {col=}')
            print(f'  {element=}')
            print(f'  {window=}')
            print(f'  {file=}')
            print(f'  {scope=}')

        # =================================================================
        # Discover which binding applies, if any.
        # =================================================================
        key_data = data.KeyBindingData()

        if platform_code:
            platform.simulate_platform(platform_code)

        binding = key_data.which_binding(keypress_list, view)

        t1 = datetime.now()

        if debugging:
            # Write verification/validation files.
            temp_dir = sublime.cache_path()
            main_key_path = os.path.join(temp_dir, 'by_main_key.txt')
            key_seq_path = os.path.join(temp_dir, 'by_key_seq.txt')
            leading_keys_path = os.path.join(temp_dir, 'leading_keys.txt')
            key_data.dump_to_files(main_key_path, key_seq_path)
            key_data.dump_leading_keys_data(leading_keys_path)

        t2 = datetime.now()

        # =================================================================
        # Generate report.
        # =================================================================
        # Title
        title = f'{core.package_name}:  Which Key Binding?'

        # Note
        note_parts = [f'Binding Selected for {keypress_list} in Current Context:']
        if element:
            note_parts.append(f'    View({view.id()}) is part of the user interface:  {element}.')
            note_parts.append(f'    Line : "{row + 1}, Col: {col + 1}"')
            note_parts.append(f'    Scope: "{scope}"')
        elif window:
            if view.is_scratch():
                note_parts.append(f'    View({view.id()}) is a scratch view, not editing a file.')
                note_parts.append(f'    Line : "{row + 1}, Col: {col + 1}"')
                note_parts.append(f'    Scope: "{scope}"')
            elif file:
                note_parts.append(f'    View({view.id()}) is editing file:')
                note_parts.append(f'      {file}')
                note_parts.append(f'    Line : "{row + 1}, Col: {col + 1}"')
                note_parts.append(f'    Scope: "{scope}"')
            else:
                note_parts.append(f"    View({view.id()})'s is in window {window}.")
        else:
            note_parts.append(f"    View({view.id()})'s exact nature is not recognized.")

        note = '\n'.join(note_parts)

        # Content
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

        content_parts.append('')
        content = '\n'.join(content_parts)

        # Push to report View.
        rpt_view = output_view.output_to_view(
                None,
                _report_title,
                content,
                current_view=view
                )

        # Bring report view to front.
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
