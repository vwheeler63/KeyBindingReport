import sublime_plugin
import sublime
from ...lib.ascii_table import Format, Generator
from ...lib.debug import IntFlag, DebugBits, is_debugging
from .. import core
from ..core import KeyGroup


class KeyBindingReportCommand(sublime_plugin.TextCommand):
    """ Generate Key-Binding Report in specified format.

    This needs to inherit from `sublime_plugin.TextCommand` because
    the report is generated in the CURRENT CONTEXT, which is gotten
    from `self.view`'s first caret.
    """
    def run(
            self      : sublime_plugin.TextCommand,
            edit      : sublime.Edit,
            packages  : str      = ['Default'],
            key_groups: KeyGroup = [KeyGroup.F_KEYS],
            key_names : str      = [],
            format    : Format   = Format.OUTLINED,
            flags     : int      = 0
            ):
        """
        Generate `key_group` Key-Binding Report in format `format`.

        Key:
            I = ignored

        class KeyGroup(IntEnum):
            # Non-negative values index into ``key_name_groups``.
            ALL_KEYS      = -3
            SPECIFIED_KEY = -2
            KEY_SEQUENCES = -1  # Multiple-key-press sequences, e.g. ["ctrl+k", "ctrl+u"]

            LETTER_KEYS   = 0
            NUMBER_KEYS   = 1
            SYMBOL_KEYS   = 2
            NAMED_KEYS    = 3
            KEYPAD_KEYS   = 4
            F_KEYS        = 5

        class FlagBits(IntFlag):
            SHOW_UNBOUND_KEY_COMBINATIONS = 0b00000001
            SHOW_PACKAGE_NAME             = 0b00000010
            ADD_COMMENTS_COLUMN           = 0b00000100
            INCLUDE_UNTRANSLATED_CONTEXTS = 0b00001000
            INCLUDE_ENGLISH_CONTEXTS      = 0b00010000

            NONE                          = 0b00000000
            ALL                           = 0b11111111
            ANY                           = 0b11111111

        +-----------------------------------------+---------------------------+
        | Description                             |          Arguments        |
        |                                         +---------+-------------+---+
        |                                         | package | key_group   |key|
        +=========================================+=========+=============+===+
        | By Package.  Output all key bindings    |'pkgname'| ALL_KEYS    |I  |
        | contained in Package (e.g. Default or   |         |             |   |
        | a 3rd-party Package). This also implies |         |             |   |
        | that the look-up data structures can    |         |             |   |
        | also be limited to that Package.        |         |             |   |
        +-----------------------------------------+---------+-------------+---+
        | By specified key limited to a Package.  |'pkgname'|SPECIFIED_KEY|'a'|
        | Output all of key's binding(s).         |         |             |   |
        +-----------------------------------------+---------+-------------+---+
        | By specified key.  Output that key's    | None    |SPECIFIED_KEY|'a'|
        | bindings in all Packages that contain   |         |             |   |
        | binding(s) for that key.                |         |             |   |
        +-----------------------------------------+---------+-------------+---+
        | By specified ``KeyGroup``, using        | None    |KEY_SEQUENCES|I  |
        | bindings from all Packages.             |         |- F_KEYS     |   |
        +-----------------------------------------+---------+-------------+---+
        | By specified ``KeyGroup``, limited      |'pkgname'|KEY_SEQUENCES|I  |
        | to a Package.                           |         |- F_KEYS     |   |
        +-----------------------------------------+---------+-------------+---+

        :param self:          KeyBindingReportCommand object connected to current View
        :param edit:          sublime.Edit connected to current View, needed to edit Buffer
        :param packages:      Name of package; None or '' when not applicable
        :param key_groups:    Which key group to report on
        :param key_names:     Key name; ignored when not applicable
        :param format:        Which output format (ascii_table.Format)
        :param flags:         Any bitwise-OR-ed combination of `FlagBits` bits.
        :return:  None
        """
        t0 = datetime.now()
        core.build_lookup_data(package, key_group, key_name)
        t1 = datetime.now()
        print('Time to build data structures: ', str(t1 - t0))
        llstKeyGroup = key_name_groups[key_group]

        # import os
        # this_dir, _ = os.path.split(__file__)
        # tgt_file = os.path.join(this_dir, 'by_main_key.txt')
        # with open(tgt_file, 'w', encoding='utf-8') as f:
        #     print(f'Writing to [{tgt_file}]...')
        #     f.write(pprint.pformat(gdictByMainKey))
        # tgt_file = os.path.join(this_dir, 'by_key_seq.txt')
        # with open(tgt_file, 'w', encoding='utf-8') as f:
        #     print(f'Writing to [{tgt_file}]...')
        #     f.write(pprint.pformat(gdictByKeySquence))

        tgt_file = r'r:\by_main_key.txt'
        with open(tgt_file, 'w', encoding='utf-8') as f:
            # print(f'Writing to [{tgt_file}]...')
            f.write(pprint.pformat(gdictByMainKey))
        tgt_file = r'r:\by_key_seq.txt'
        with open(tgt_file, 'w', encoding='utf-8') as f:
            # print(f'Writing to [{tgt_file}]...')
            f.write(pprint.pformat(gdictByKeySquence))
        t2 = datetime.now()
        print('Time write files             : ', str(t2 - t1))
        print('Total                        : ', str(t2 - t0))
