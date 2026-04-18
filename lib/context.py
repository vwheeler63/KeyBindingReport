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
from .json_key_binding import *


# =========================================================================
# Constants
# =========================================================================

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



# =========================================================================
# Data
# =========================================================================



# =========================================================================
# Utilities
# =========================================================================



# =========================================================================
# Function Definitions
# =========================================================================



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


class Context():
    """
    Testers of key-binding "context" entries (i.e. list of conditions).
    """
    __slots__ = [
        '_on_query_context_list',
        '_snippet_list',
        '_debugging_context',
        '_requires_view_sel_set',
        '_context_tests',
    ]

    def __init__(self):
        self._on_query_context_list = None
        self._snippet_list = None
        self._debugging_context = is_debugging(DebugBits.FILTERING_ON_CONTEXT)
        self. _requires_view_sel_set = {}

        self._context_tests = {
            # VIEW          == 0
            # Includes logic related to View, selections, scope and text.
            'num_selections'           : self._test_num_selections,
            'selection_empty'          : self._test_selection_empty,
            'eol_selector'             : self._test_unimplemented,
            'is_javadoc'               : self._test_unimplemented,
            'selector'                 : self._test_unimplemented,
            'following_text'           : self._test_following_text,
            'has_snippet'              : self._test_unimplemented,
            'indented_block'           : self._test_indented_block,
            'preceding_text'           : self._test_preceding_text,
            'read_only'                : self._test_unimplemented,
            'text'                     : self._test_text,
            # SNIPPET       == 1
            'has_snippet'              : self._test_unimplemented,
            # WINDOW        == 2
            'auto_complete_visible'    : self._test_unimplemented,
            'group_has_multiselect'    : self._test_unimplemented,
            'group_has_transient_sheet': self._test_unimplemented,
            'overlay_has_focus'        : self._test_unimplemented,
            'overlay_name'             : self._test_unimplemented,
            'overlay_visible'          : self._test_unimplemented,
            'panel'                    : self._test_unimplemented,
            'panel_has_focus'          : self._test_unimplemented,
            'panel_visible'            : self._test_unimplemented,
            'panel_type'               : self._test_unimplemented,
            'popup_visible'            : self._test_unimplemented,
            # APPLICATION   == 3
            'last_command'             : self._test_unimplemented,
            'last_modifying_command'   : self._test_unimplemented,
            # SETTINGS      == 4
            # Implemented in `_condition_test()` due to exact string match not possible.
            # Setting queries all start with "setting.", but their ending supplies
            # the setting name to test, so no listing for "setting.xxxx" here.
            # UNIMPLEMENTED == 5
            'has_next_field'           : self._test_unimplemented,
            'has_prev_field'           : self._test_unimplemented,
            'is_recording_macro'       : self._test_unimplemented,
        }

        # Get `on_query_context()` collection.
        # Get Snippet collection.

    def _test_num_selections(self, view, operator, operand, match_all):
        value = len(view.sel())
        return self._check_value(value, operator, operand)

    def _test_selection_empty(self, view, operator, operand, match_all):
        test_func = lambda view, sel: sel.a == sel.b
        return self._test_selections(test_func, view, operator, operand, match_all)

    def _test_one_following_text(self, view, sel):
        left_edge_pt = sel.begin()
        line_rgn = view.line(left_edge_pt)
        following_text_rgn = Region(left_edge_pt, line_rgn.b)
        return view.substr(following_text_rgn)

    def _test_following_text(self, view, operator, operand, match_all):
        test_func = self._test_one_following_text
        return self._test_selections(test_func, view, operator, operand, match_all)

    def _test_one_preceding_text(self, view, sel):
        left_edge_pt = sel.begin()
        line_rgn = view.line(left_edge_pt)
        preceding_text_rgn = Region(line_rgn.a, left_edge_pt)
        return view.substr(preceding_text_rgn)

    def _test_preceding_text(self, view, operator, operand, match_all):
        test_func = self._test_one_preceding_text
        return self._test_selections(test_func, view, operator, operand, match_all)

    def _test_text(self, view, operator, operand, match_all):
        test_func = lambda view, sel: view.substr(sel)
        return self._test_selections(test_func, view, operator, operand, match_all)

    def _test_indented_block(self, view, operator, operand, match_all):
        test_func = lambda view, sel: ((view.line(sel).size() > 0) and (view.substr(view.line(sel))[0] in ' \t'))
        return self._test_selections(test_func, view, operator, operand, match_all)

    def _test_setting(self, view, operator, operand, match_all):
        test_func = lambda view, sel: sel.a == sel.b
        return self._test_selections(test_func, view, operator, operand, match_all)

    def _test_unimplemented(self, view, operator, operand, match_all):
        debugging = self._debugging_context
        if debugging:
            # print('    >>>> In context._test_unimplemented()...')
            print('    >>>> UNIMPLEMENTED.')
        return False

    def _check_value(self, value, operator, operand):
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

    def _test_selections(self, test_func, view, operator, operand, match_all):
        """
        Run ``test_func()`` on all of ``view``'s selections.
        ``match_all`` = do all selections have to
        """
        debugging = self._debugging_context
        if debugging:
            print(f'    In _test_selections()...')
            print(f'      {test_func.__name__=}')
            print(f'      {view=}')
            print(f'      {operator=}')
            print(f'      {operand=}')
            print(f'      {match_all=}')
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
                        print(f'      after calling test_func: {value=}, {operator=}, {operand=}')
                    result = self._check_value(value, operator, operand)
                    if not result:
                        if debugging:
                            print(f'      Exiting selection loop.')
                        break;
            else:
                # Exit loop on first True result.
                for sel in live_sel_list:
                    if debugging:
                        print(f'  {sel=}')
                    value = test_func(view, sel)
                    if debugging:
                        print(f'      after calling test_func: {value=}')
                    result = self._check_value(value, operator, operand)
                    if result:
                        if debugging:
                            print(f'      Exiting selection loop.')
                        break;

        if debugging:
            print(f'    {result=}')

        return result

    def _condition_test(self, view, condition: dict, keypress_list: tuple, path: str):
        """
        :param view:            Current View (used to test if key context is applicable)
        :param keypress_list:  Tuple containing keypress/keypress sequence
        :param condition:       Single condition dictionary from key-binding context.
        """
        debugging = self._debugging_context
        if debugging:
            print('  In context._condition_test()...')
            print(f'    {path=}')
            print(f'    {keypress_list=}')
            print(f'    condition={condition_repr(condition, 0, 0)}')
        result    = False
        key       = condition['key']
        operator  = condition['operator']  if 'operator'  in condition else 'equal'
        operand   = condition['operand']   if 'operand'   in condition else True
        match_all = condition['match_all'] if 'match_all' in condition else False

        if key in self._context_tests:
            test_func = self._context_tests[key]
            result = test_func(view, operator, operand, match_all)
        elif key.startswith('setting.'):
            setting_name = key[8:]
            view_stgs = view.settings()
            if setting_name in view_stgs:
                value = view_stgs.get(setting_name)
                result = self._check_value(value, operator, operand)
                if debugging:
                    print(f'    Setting name {setting_name}:')
                    print(f'      {value=}, {operator=}, {operand=}')
                    print(f'      {result=}')
        else:
            msg = (
                    f'{self.__class__.__name__}:  context key [{key}] not recognized.\n'
                    f'  {path=}  {keypress_list=}'
                  )
            raise AssertionError(msg)

        if not result:
            if debugging:
                print(f'    Excluding {keypress_list} because context query failed:\n      {condition_repr(condition, 0, 0)}')

        return result

    def query(self, view, json_binding: dict, path: str):
        """
        Do all conditions in ``json_binding's`` "context" entry match current
        circumstances with ``view``, etc.?

        Precondition:  json_binding must have a "context" entry.

        :param view:          Active View (used to test if key context is applicable)
        :param json_binding:  Info for error messages
        :param path:          Path to .sublime-keymap file for error messages.
        """
        debugging = self._debugging_context
        if debugging:
            print('In context.query()...')
            print(f'{binding_repr(json_binding, 1)}')
            print(f'  {path=}')
        all_tests_passed = True
        keypress_list    = json_binding['keys']
        conditions       = json_binding['context']

        # Do all conditions pass?
        for condition in conditions:
            if not self._condition_test(view, condition, keypress_list, path):
                all_tests_passed = False
                if debugging:
                    print(f'  Excluding {keypress_list}:  context.query() == False.')
                break

        return all_tests_passed

