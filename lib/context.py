"""************************************************************************
Sublime Text Context Match Checker
==================================

How Context Works:
==================

See http://crystal-clear-research.com/docs/quickrefs/sublime_text/key_bindings.html#context
for terminology and understandings required to use this module.

Summary
=======

In the below, from a high level, a `context` is a list of conditions
that all must be true for a key binding to be selected by Sublime Text.

From a lower level, a `context` is a list of dictionary objects with
a specific format.  Keys:

.. code-block:: json

    {
        // Condition to check
        "key": "<condition>",       // Required:  see <condition> below

        // Type of comparison
        "operator": "<operator>",   // Optional:  Default:  "equal"

        // Value to test against
        "operand": "<operand>",     // Optional:  Default:  true

        // When there are multiple selections (carets), this indicates whether the
        // test needs to be satisfied for all of them (true), or just one (false).
        "match_all": false,         // Optional:  Default:  false
    }


Design
======

A.  There is a concept of a context object.

    1.  It has:
        +   a full live collection of `on_query_context()` functions
            +   Called when one of the "key" (condition) names is not among the
                recognized set.  This list is called until a value not ``None``
                is returned and then that particular condition "passes" or
                tests TRUE or FALSE based on the Boolean return value.

                These are loaded when the Context class is instantiated.

        +   a full live collection of Snippets within current view of Sublime Text.
            +   There are 3 "key" (condition) names that have to do with Snippets
                and 2 of them require parsing the actual snippet files to determine
                whether the condition tests TRUE or not.  This collection is used
                when those condition names show up.

                These are loaded when the Context class is instantiated.
        +   ...
        +   ...
        +   ...
    2.  It can be asked:
        +   query(self, view, json_binding: dict, path: str)
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...
    3.  It can be requested to change context objects as follows:
        +   ...
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...


Data Flow
=========

When Context is instantiated, it loads up the required reference data
from the Sublime Text environment.

context.matches() function answers this question with a returned Boolean:

    is the passed ``context`` object a match for the current conditions
    with ``view`` and/or its window and/or Sublime Text application?

Each time context.matches(view, keypress_list, context) is called, each
supported condition in the context is tested.

If a condition name is not among the standard names, the collection of live
`on_query_context()` functions is called to determine the answer.  If no
`on_query_context()` returns a value that is not ``None``, then the
returned value is ``False``.  Otherwise, the returned value is the Boolean
value returned from the first `on_query_context()` to return a Boolean value.


Efficiency Note
===============

Because of the data that must be gathered about the current Sublime Text
environment includes all `on_query_context()` functions of all loaded
Packages, as well as all Snippet files known to Sublime Text, and these
resources are loaded when the object is instantiated, it is wise to be
careful the Context lifetime.  It certainly should never be instantiated
inside a loop, as this would slow it down immensely.



@version  Current revision:  @(#) v1.0  16-Apr-2026 15:35
@version  1.0  16-Apr-2026 15:35  vw  - Created.
***************************************************************************"""

import re
from enum import IntFlag, IntEnum
from typing import Tuple, List
from sublime import Region
from ..lib.debug import IntFlag, DebugBits, is_debugging
from ..lib import key_binding


# =========================================================================
# Constants
# =========================================================================

# System-wide list of `on_query_context()` functions for when there
# is a key-binding context not among the standard list.
_on_query_context_list = []

# System-wide list of Snippets
_snippet_list = []

# Regex to extract setting name from a "settings.xxxx" condition.
_setting_name_from_condition = re.compile(r'^setting\.(.+)$')

# Condition names grouped by ConditionGroup enumeration.
_condition_name_groups = [
    # VIEW          == 0
    # Includes logic related to View, selections, scope and text.
    [
        'num_selections',
        'selection_empty',
        'eol_selector',
        'is_javadoc',
        'selector',
        'following_text',
        'has_snippet',
        'indented_block',
        'preceding_text',
        'read_only',
        'text',
        'has_snippet',
            # Implemented similar to 'preceding_text' consulting the
            # collection of snippets to determine trigger strings.
    ],
    # SNIPPET       == 1
    # This sub-list is at this writing unsupported because there appears to
    # be no way to determine the state of the Snippet State Machine.
    [
    ],
    # WINDOW        == 2
    [
        'auto_complete_visible',
        'group_has_multiselect',
        'group_has_transient_sheet',
        'overlay_has_focus',
        'overlay_name',
        'overlay_visible',
        'panel',
        'panel_has_focus',
        'panel_visible',
        'panel_type',
        'popup_visible',
    ],
    # APPLICATION   == 3
    [
    ],
    # SETTINGS      == 4
    [
        'setting.',
    ],
    # UNIMPLEMENTED == 5
    [
        'has_next_field',          # Snippet
        'has_prev_field',          # Snippet
        'is_recording_macro',      # Application
        'last_command',            # Application
        'last_modifying_command',  # Application
    ],
]

# -------------------------------------------------------------------------
# Populate constants programmatically.
# -------------------------------------------------------------------------

# Generate ``_all_condition_names`` from ``_condition_name_groups``.
count = 0

for grp in _condition_name_groups:
    count += len(grp)

# Pre-allocate array instead of 103 ``append()`` calls (inefficient).
_all_condition_names = [None] * count
i = 0

for grp in _condition_name_groups:
    for cond_name in grp:
        _all_condition_names[i] = cond_name
        i += 1

# Clean up.
del i, count, grp, cond_name

# _on_query_context_list TODO

# _snippet_list TODO


# =========================================================================
# Data
# =========================================================================



# =========================================================================
# Utilities
# =========================================================================



# =========================================================================
# Function Definitions
# =========================================================================

def _check_value(value, operator, operand):
    try:
        if operator == "equal":
            return value == operand
        elif operator == "not_equal":
            return value != operand
        elif operator == "regex_match":
            return value != None and re.match(operand, value) != None
        elif operator == "not_regex_match":
            return value == None or re.match(operand, value) == None
        elif operator == "regex_contains":
            return value != None and re.search(operand, value) != None
        elif operator == "not_regex_contains":
            return value == None or re.search(operand, value) == None
        else:
            raise AssertionError(f'Operator not recognized:  {operator}.')
    except Exception as error:
        print("Failed to check context", operand, value, error)
        raise error


def _test_selections(test_func, view, operator, operand, match_all):
    """
    Run ``test_func()`` on all of ``view``'s selections.
    ``match_all`` = do all selections have to
    """
    debugging = is_debugging(DebugBits.FILTERING_ON_CONTEXT)
    if debugging:
        print(f'    In _test_selections()...')
        print(f'      test_func={test_func.__name__}')
        # print(f'      {view=}')
        # print(f'      {operator=}')
        # print(f'      {operand=}')
        # print(f'      {match_all=}')
    result = False
    live_sel_list = view.sel()

    if live_sel_list:
        if match_all:
            # Exit loop on first False result.
            for sel in live_sel_list:
                if debugging:
                    print(f'      {sel=}')
                value = test_func(view, sel)
                if debugging:
                    print(f'      Result: {value=}, {operator=}, {operand=}')
                result = _check_value(value, operator, operand)
                if not result:
                    if debugging:
                        print(f'      Exiting selection loop:  match_all=True, test failed.')
                    break;
        else:
            # Exit loop on first True result.
            for sel in live_sel_list:
                if debugging:
                    print(f'  {sel=}')
                value = test_func(view, sel)
                if debugging:
                    print(f'      Result: {value=}, {operator=}, {operand=}')
                result = _check_value(value, operator, operand)
                if result:
                    if debugging:
                        print(f'      Exiting selection loop:  match_all=False, test passed.')
                    break;

    if debugging:
        print(f'    {result=}')

    return result


def _test_num_selections(view, operator, operand, match_all):
    value = len(view.sel())
    return _check_value(value, operator, operand)


def _test_one_selection_empty(view, sel):
    return (( sel.a == sel.b ))


def _test_selection_empty(view, operator, operand, match_all):
    test_func = _test_one_selection_empty
    return _test_selections(test_func, view, operator, operand, match_all)


def _test_one_following_text(view, sel):
    left_edge_pt = sel.begin()
    line_rgn = view.line(left_edge_pt)
    following_text_rgn = Region(left_edge_pt, line_rgn.b)
    return view.substr(following_text_rgn)


def _test_following_text(view, operator, operand, match_all):
    test_func = _test_one_following_text
    return _test_selections(test_func, view, operator, operand, match_all)


def _test_one_preceding_text(view, sel):
    left_edge_pt = sel.begin()
    line_rgn = view.line(left_edge_pt)
    preceding_text_rgn = Region(line_rgn.a, left_edge_pt)
    return view.substr(preceding_text_rgn)


def _test_preceding_text(view, operator, operand, match_all):
    test_func = _test_one_preceding_text
    return _test_selections(test_func, view, operator, operand, match_all)


def _test_one_text(view, sel):
    return view.substr(sel)


def _test_text(view, operator, operand, match_all):
    test_func = _test_one_text
    return _test_selections(test_func, view, operator, operand, match_all)


def _test_one_indented_block(view, sel):
    line_rgn = view.line(sel)
    return (( line_rgn.size() > 0) and (view.substr(line_rgn)[0] in ' \t' ))


def _test_indented_block(view, operator, operand, match_all):
    test_func = _test_one_indented_block
    return _test_selections(test_func, view, operator, operand, match_all)


def _test_unimplemented(view, operator, operand, match_all):
    debugging = is_debugging(DebugBits.FILTERING_ON_CONTEXT)
    if debugging:
        print('    >>>> UNIMPLEMENTED.')
    return False


_context_tests = {
    # VIEW          == 0
    # Includes logic related to View, selections, scope and text.
    'num_selections'           : _test_num_selections,
    'selection_empty'          : _test_selection_empty,
    'eol_selector'             : _test_unimplemented,
    'is_javadoc'               : _test_unimplemented,
    'selector'                 : _test_unimplemented,
    'following_text'           : _test_following_text,
    'has_snippet'              : _test_unimplemented,
    'indented_block'           : _test_indented_block,
    'preceding_text'           : _test_preceding_text,
    'read_only'                : _test_unimplemented,
    'text'                     : _test_text,
    # SNIPPET       == 1
    'has_snippet'              : _test_unimplemented,
    # WINDOW        == 2
    'auto_complete_visible'    : _test_unimplemented,
    'group_has_multiselect'    : _test_unimplemented,
    'group_has_transient_sheet': _test_unimplemented,
    'overlay_has_focus'        : _test_unimplemented,
    'overlay_name'             : _test_unimplemented,
    'overlay_visible'          : _test_unimplemented,
    'panel'                    : _test_unimplemented,
    'panel_has_focus'          : _test_unimplemented,
    'panel_visible'            : _test_unimplemented,
    'panel_type'               : _test_unimplemented,
    'popup_visible'            : _test_unimplemented,
    # APPLICATION   == 3
    'last_command'             : _test_unimplemented,
    'last_modifying_command'   : _test_unimplemented,
    # SETTINGS      == 4
    # Implemented in `_condition_test()` due to exact string match not possible.
    # Setting queries all start with "setting.", but their ending supplies
    # the setting name to test, so no listing for "setting.xxxx" here.
    # UNIMPLEMENTED == 5
    'has_next_field'           : _test_unimplemented,
    'has_prev_field'           : _test_unimplemented,
    'is_recording_macro'       : _test_unimplemented,
}


# =========================================================================
# Classes
# =========================================================================

class ConditionGroup(IntEnum):
    """ These values index into ``condition_name_groups``. """
    VIEW          = 0
    SNIPPET       = 1
    WINDOW        = 2
    APPLICATION   = 3
    SETTING       = 4
    UNIMPLEMENTED = 5


class ContextCondition(dict):
    """
    Sublime Text Key-Binding Context Conditions

    Examples:
    { "key": "setting.auto_match_enabled", "operator": "equal", "operand": true },
    { "key": "selection_empty", "operator": "equal", "operand": true, "match_all": true },
    { "key": "following_text", "operator": "regex_contains", "operand": "^(?:\t| |\\)|]|\\}|>|$)", "match_all": true },
    { "key": "preceding_text", "operator": "not_regex_contains", "operand": "[\"a-zA-Z0-9_]$", "match_all": true },
    { "key": "eol_selector", "operator": "not_equal", "operand": "string.quoted.double - punctuation.definition.string.end", "match_all": true }
    """
    def __init__(self, condition_dict: dict):
        self.update(condition_dict)

    def __str__(self):
        return self.format_condition()

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.format_condition()}>'

    def format_condition(self,
            longest_key_len: int = 0,
            longest_op_len: int = 0,
            indent_level: int = 0
            ) -> str:
        """
        Python representation of ``json_binding`` context conditions (same structure as
        in .sublime-keymap files) such that the keys and values are in logical order.

        Each condition presented on 1 line.

        Representation (just one of these, but 2 shown to show meaning of args):
        ------------------------------------------------------------------------
        { "key": "selection_empty"           , "operator": "equal", "operand": False, "match_all": True }
        { "key": "setting.auto_match_enabled", "operator": "equal", "operand": True }
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^                ^^^^^
                      +-- longest_key_len                     +-- longest_op_len
        }
        """
        cond_name = self['key']
        field = f'"{cond_name}"'
        indent = '  ' * indent_level
        result = f'{indent}{{ "key": {field:{longest_key_len + 2}}'

        if 'operator' in self:
            op_name = self["operator"]
            field = f'"{op_name}"'
            result += f', "operator": {field:{longest_op_len + 2}}'
        if 'operand' in self:
            # This value can be str, bool or int, so we use `repr()`.
            result += f', "operand": {repr(self["operand"])}'
        if 'match_all' in self:
            result += f', "match_all": {repr(self["match_all"])}'

        result += ' }'

        return result


class Context(list):
    """
    Sublime Text Key-Binding Contexts --- lists of conditions required
    for Sublime Text to select a key binding.

    It has:
        +   list of ContextCondition objects
    It can be asked:
        +   query(self, view, path: str)
        +   str(self)
        +   repr(self)
    3.  It can be requested to change context objects as follows:
        +   ...
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...
    """
    __slots__ = [
        'conditions',
        'binding',    # For better debugging output.
    ]

    def __init__(self, binding: key_binding.KeyBinding):
        """
        Precondition:  ``binding`` must have a "context" entry.

        :param binding:  for better debug output
        :param path:     for better debug output
        """
        condition_list = binding.context()
        if condition_list is None:
            raise AssertionError('`binding` "context" entry not present.')

        self.extend(condition_list)

        conditions = None
        if len(condition_list) > 0:
            conditions = []
            for condition_dict in condition_list:
                conditions.append(ContextCondition(condition_dict))

        self.conditions = conditions
        self.binding    = binding

    def __str__(self):
        """
        <Context [setting.auto_match_enabled, selection_empty, following_text, selector, eol_selector]>
        """
        cond_name_list = []

        for cond in self.conditions:
            cond_name_list.append(cond["key"])

        short_test_name_list = ', '.join(cond_name_list)
        return f'<{self.__class__.__name__} [{short_test_name_list}]>'

    def __repr__(self):
        """
        "context": [
          { "key": "setting.auto_match_enabled", "operator": "equal"         , "operand": True }
          { "key": "selection_empty"           , "operator": "equal"         , "operand": True, "match_all": True }
          { "key": "following_text"            , "operator": "regex_contains", "operand": '^"', "match_all": True }
          { "key": "selector"                  , "operator": "not_equal"     , "operand": 'punctuation.definition.string.begin', "match_all": True }
          { "key": "eol_selector"              , "operator": "not_equal"     , "operand": 'string.quoted.double - punctuation.definition.string.end', "match_all": True }
        ]
        """
        return f'<{self.__class__.__name__} {self.format_context()}>'

    def format_context(self, indent_level: int = 0) -> str:
        """
        Python representation of ``self`` (same structure as in
        .sublime-keymap files) such that the keys and values are in logical order.

        Representation:
        ---------------
        "context": [
          { "key": "setting.auto_match_enabled", "operator": "equal"         , "operand": True }
          { "key": "selection_empty"           , "operator": "equal"         , "operand": True, "match_all": True }
          { "key": "following_text"            , "operator": "regex_contains", "operand": '^"', "match_all": True }
          { "key": "selector"                  , "operator": "not_equal"     , "operand": 'punctuation.definition.string.begin', "match_all": True }
          { "key": "eol_selector"              , "operator": "not_equal"     , "operand": 'string.quoted.double - punctuation.definition.string.end', "match_all": True }
        ]
        """
        indent = '  ' * indent_level
        lines = [f'{indent}"context": [']

        if self.conditions and len(self.conditions) > 0:
            longest_key_len = 0
            longest_op_len = 5   # Length of 'equal'

            # Compute length of widest `key` and `operator` fields.
            for condition in self.conditions:
                key_len = len(condition['key'])
                if key_len > longest_key_len:
                    longest_key_len = key_len
                if 'operator' in condition:
                    op_len  = len(condition['operator'])
                    if op_len > longest_op_len:
                        longest_op_len = op_len

            # Now generate indented formatted strings.
            for condition in self.conditions:
                lines.append(
                        condition.format_condition(
                                longest_key_len,
                                longest_op_len,
                                indent_level + 1
                                )
                        )

            lines.append(f'{indent}]')
        else:
            lines[0] += ']'

        return '\n'.join(lines)

    def _condition_test(self, view, condition: ContextCondition, debugging: bool):
        """
        :param view:            Current View (used to test if key context is applicable)
        :param keypress_list:  Tuple containing keypress/keypress sequence
        :param condition:      Single condition dictionary from key-binding context.
        :param debugging:      Produce debugging output?
        """
        if debugging:
            print(f'  In {self.__class__.__name__}._condition_test()...')
            print(f'    {repr(condition)}')

        result    = False
        key       = condition['key']
        operator  = condition['operator']  if 'operator'  in condition else 'equal'
        operand   = condition['operand']   if 'operand'   in condition else True
        match_all = condition['match_all'] if 'match_all' in condition else False

        if key.startswith('setting.'):
            setting_name = key[8:]
            view_stgs = view.settings()
            if setting_name in view_stgs:
                value = view_stgs.get(setting_name)
                result = _check_value(value, operator, operand)
                if debugging:
                    print(f'    Setting name {setting_name}:')
                    print(f'      {value=}, {operator=}, {operand=}')
                    print(f'    {result=}')
        elif key in _context_tests:
            test_func = _context_tests[key]
            result = test_func(view, operator, operand, match_all)
        else:
            # TODO  This is where `_on_query_context_list` comes into play.
            msg = (
                    f'{self._class__.__name__}:  context key [{key}] not recognized.\n'
                    f'  {self.keypress_list=}'
                  )
            raise AssertionError(msg)

        return result

    def query(self, view):
        """
        Do all conditions in "context" match current circumstances with
        ``view``, window, application, etc.?

        :param view:  Active View (used to test if key context is applicable)
        """
        debugging = is_debugging(DebugBits.FILTERING_ON_CONTEXT)
        if debugging:
            print(f'In {self.__class__.__name__}.query()...')
            print(f'{self.binding.format_binding(1, include_extra = True)}')

        all_tests_passed = True

        # Do all conditions pass?
        for condition in self.conditions:
            if not self._condition_test(view, condition, debugging):
                all_tests_passed = False
                if debugging:
                    print(f'  Excluding this binding:', end='')
                break

        if debugging:
            print(f'  {all_tests_passed=}')

        return all_tests_passed

