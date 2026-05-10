"""************************************************************************
Sublime Text Key-Binding Contexts...
************************************

...that can:

- represent contexts as a part of KeyBinding objects, and

- do system-wide context queries to determine if a particular key
  binding applies to the current context (editing circumstances).


How SmartContext Works:
=======================

See http://crystal-clear-research.com/docs/quickrefs/sublime_text/key_bindings.html#context
for terminology and understandings required to use this module.


Summary
=======

In the below, from a high level, a `context` is a list of conditions
that all must be true for a key binding to be selected by Sublime Text.

From a lower level, a `context` is a list of dictionary objects with
a specific format:

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

A.  SmartContext module.

    1.  It has:
        +   a full live collection of `on_query_context()` listeners
            +   Called when one of the "key" values (condition names) is not
                among the recognized set.  This list is called until a
                ``True`` or ``False`` is returned (value not ``None``).
                That result is the test result.

                These are loaded when this module is loaded.  Avg time:  0.09 sec.

        +   a full live collection of Snippet triggers in a dictionary
            +   There are 3 context conditions that have to do with
                Snippets and 1 of them (has_snippet) requires parsing the
                actual snippet files and collecting triggers to determine
                whether the condition tests TRUE or not.  This collection
                is used when that context condition shows up.

                These are loaded when this module is loaded.  Avg time:  0.11 sec.

    2.  It can be asked:
        +   Are we debugging?                (bool)
        +   _on_query_context_listener_list  (list)
        +   _on_query_context_file_list      (list)
        +   _snippets_by_trigger             (dict)
        +   _context_tests_by_name           (dict)
        +   _operator_codes_by_name          (dict)

B.  ContextCondition Object.

    See ContextCondition docstring.

C.  SmartContext Object.

    1.  It has:
        +   list of ContextCondition objects
    2.  It can be asked:
        +   query(self, view)
            +   Does context match current circumstances with `view`, window, etc.?
        +   str(self)
            +   String representation
        +   repr(self)
            +   Debug representation
        +   equivalent(self, other)
            +   Whether the sum of all contained ContextCondition objects
                are functionally equivalent with the sum of `other`s
                contained ContextCondition objects.
    3.  It can be requested to change context objects as follows:
        +   Change only happens at instantiation when the newly-created
            SmartContext object extracts its condition list from the
            passed-in binding.


Data Flow
=========

When this module is loaded, it loads up the required reference data
from the Sublime Text environment (on_query_context() listeners and
Snippet triggers and scopes).

Various parts of this package (e.g. reporting) build data structures of key
bindings used to do their job.  As these are built, ``SmartContext`` objects
are created from the content of the key bindings, and can later be asked
whether they are a match for the current circumstances with the current
View, window, application, etc..  This is done by:

    binding.context.query(current_view):

If a condition name is not among the standard key (test) names, the
collection of live `on_query_context()` listeners is consulted to determine
the answer.  If no `on_query_context()` returns a value that is not
``None``, then the returned value is ``False``.  Otherwise, the returned
value is the Boolean value returned from the first `on_query_context()` to
return a Boolean value.



@version  Current revision:  @(#) v1.0  16-Apr-2026 15:35
@version  1.0  16-Apr-2026 15:35  vw  - Created.
***************************************************************************"""

import os
import re
import json
from enum import IntEnum
import importlib
from datetime import datetime
from xml.etree import ElementTree as ET
import sublime
from sublime import QueryOperator
import sublime_plugin
from ..lib.debug import DebugBits, is_debugging
from ..lib import key_binding



# *************************************************************************
# Constants
# *************************************************************************

_key_key       = 'key'
_operator_key  = 'operator'
_operand_key   = 'operand'
_match_all_key = 'match_all'

_default_operator  = 'equal'
_default_operand   = True
_default_match_all = False


class Snippet:
    """
    Carriers of snippet data
    """
    __slots__ = ['path', 'tabTrigger', 'content', 'scope', 'description']

    def __init__(
            self,
            path      : str,
            content   : str | None,
            tabTrigger: str | None,
            scope     : str | None,
            desc      : str | None):
        self.path        = path
        self.content     = content
        self.tabTrigger  = tabTrigger
        self.scope       = scope
        self.description = desc

# System-wide list of `on_query_context()` functions for when there
# is a key-binding context not among the standard list.  Populated
# by a call to `_on_qry_context_listeners()` below.
_on_query_context_listener_list = []
_on_query_context_file_list = []

# System-wide list of Snippets
_snippets_by_trigger = []

# Context test functions by key; populated after test functions below.
_context_tests_by_name = {}

# on_query_context() operator code look-up dictionary.
_operator_codes_by_name = {
    "equal"             : QueryOperator.EQUAL,
    "not_equal"         : QueryOperator.NOT_EQUAL,
    "regex_match"       : QueryOperator.REGEX_MATCH,
    "not_regex_match"   : QueryOperator.NOT_REGEX_MATCH,
    "regex_contains"    : QueryOperator.REGEX_CONTAINS,
    "not_regex_contains": QueryOperator.NOT_REGEX_CONTAINS,
}

# These lists of strings are used to compare against the current View's
# ``view.element()`` string, which is returned when the View is a member of
# a Panel or Overlay instead of a Sheet.  Specifically, it returns:
#
# ``None`` for normal views that are part of a `Sheet`.  For Views that
# are part of the UI, a string is returned from the following list:
#
# - "console:input"                - Console input.
# - "goto_anything:input"          - Input for the Goto Anything overlay.
# - "command_palette:input"        - Input for the Command Palette overlay.
# - "find:input"                   - Input for the Find panel.
# - "incremental_find:input"       - Input for the Incremental Find panel.
# - "replace:input:find"           - Find input for the Replace panel.
# - "replace:input:replace"        - Replace input for the Replace panel.
# - "find_in_files:input:find"     - Find input for the Find-in-Files panel.
# - "find_in_files:input:location" - Where input for the Find-in-Files panel.
# - "find_in_files:input:replace"  - Replace input for the Find-in-Files panel.
# - "find_in_files:output"         - Output for Find-in-Files (buffer or output panel).
# - "input:input"                  - Input for the Input panel.
# - "exec:output"                  - Output for the exec command.
# - "output:output"                - A general output panel.
#
# The console output, indexer status output and license input controls
# are not accessible via the API.
_panel_view_element_detection_list = [
    'console:',
    'find:',
    'incremental_find:',
    'replace:',
    'find_in_files:',
    'input:',
    'exec:',
    'output:',
]

_overlay_view_element_detection_list = [
    'goto_anything:',
    'command_palette:',
]

_find_panel_type_detection_list = [
    'find:',
    'incremental_find:',
    'replace:',
    'find_in_files:',
]

# Debugging?  This is one of the rare situations where debugging
# and validation/verification is done at module load time.
debugging = is_debugging(DebugBits.LOADING_CONTEXT_ENV)

# -------------------------------------------------------------------------
# Populate these constants programmatically:
# - _on_query_context_listener_list
# - _on_query_context_file_list
# - _snippet_data
# - _snippet_trigger_dict
# -------------------------------------------------------------------------


def _on_qry_context_listeners():
    """
    Generate and return a list of instantiated event-listener objects
    that have ``on_query_context()`` functions.
    """
    if debugging:
        print('In context._on_qry_context_listeners()...:')

    skip_packages = ["Default.", "Package Control.", "SublimeLinter."]
    st_modules = [".sublime", ".sublime_plugin", ".sublime_types"]
    listeners = []
    files = []

    resources = sublime.find_resources("*.py")
    pkgs_path = sublime.packages_path()
    curr_view = sublime.active_window().active_view()
    modules_skipped_due_to_package_count = 0
    modules_skipped_due_to_being_st_modules_count = 0
    modules_loaded_count = 0
    modules_skipped_due_to_loading_exception_count = 0
    attributes_examined_count = 0
    attr_skipped_due_to_not_having_listeners_count = 0
    duplicate_listeners_skipped_count = 0
    listeners_instantiated_and_kept_count = 0
    event_listener_count = 0
    view_event_listener_count = 0

    event_listener_class_name_dict = {}

    # ---------------------------------------------------------------------
    # For each *.py file within perception of Sublime Text....
    # ---------------------------------------------------------------------
    for resource in resources:
        full_path = os.path.join(pkgs_path, "..", resource)
        full_path = os.path.normpath(full_path)

        _, resource = resource.split("/", 1)  # remove Packages/ from path

        resource, _ = os.path.splitext(resource)
        resource = resource.replace("/", ".")

        # -----------------------------------------------------------------
        # Skip if Package in `skip_packages` list.
        # -----------------------------------------------------------------
        skip = False
        for skip_pkg in skip_packages:
            if resource.startswith(skip_pkg):
                # if debugging:
                #     print(f'  Skipping    :  {resource=}')
                modules_skipped_due_to_package_count += 1
                skip = True
                break

        if skip:
            continue

        # -----------------------------------------------------------------
        # Skip if module is a Sublime Text module.
        # -----------------------------------------------------------------
        skip = False
        for st_mod in st_modules:
            if resource.endswith(st_mod):
                modules_skipped_due_to_being_st_modules_count += 1
                skip = True
                break

        if skip:
            continue

        # -----------------------------------------------------------------
        # Skip module if:
        # - there is an exception loading it;
        # - if it does not contain any subclasses of:
        #   - sublime_plugin.EventListener,
        #   - sublime_plugin.ViewEventListener;
        # - if class encountered is a duplicate.
        #
        # Note:  multi-module Packages with event listeners in a module
        # below the top level have to "pass listener references up" so that
        # they reach 1 of the Package's top-level modules so that Sublime
        # Text will find and use it.  This fact causes more than one module
        # to contain references to the same class.  We detect this through
        # placing the class names in `event_listener_class_name_dict` and
        # checking for this before instantiating the listener object.
        # -----------------------------------------------------------------
        try:
            module = importlib.import_module(resource)
            modules_loaded_count += 1
            # if debugging:
            #     print(f'  Examining   :  {module.__name__}')
        except Exception:
            # if debugging:
            #     print(f'  Exception   :  {resource}')
            modules_skipped_due_to_loading_exception_count += 1
            continue

        for attribute_name in dir(module):
            attributes_examined_count += 1
            attribute = getattr(module, attribute_name)

            is_event_listener = False
            is_view_event_listener = False

            is_class_w_on_query_context = ((
                        isinstance(attribute, type)  # class
                    and hasattr(attribute, "on_query_context")
                    ))

            if is_class_w_on_query_context:
                is_view_event_listener = ((
                        issubclass(attribute, sublime_plugin.ViewEventListener)
                        ))

                is_event_listener = ((
                           issubclass(attribute, sublime_plugin.EventListener)
                        or is_view_event_listener
                        ))

            if not is_event_listener:
                # if debugging:
                #     print(f'  Not Listener:  {resource=}')
                attr_skipped_due_to_not_having_listeners_count += 1
                continue

            # Eliminate duplicate classes.  Multi-module Packages can have
            # a reference to an event listener in multiple modules, since these
            # have to be propagated upwards to at least 1 top-level module in
            # the package.  But we can detect duplicates observing their class
            # names, and only accepting the first one.
            if attribute.__name__ in event_listener_class_name_dict:
                # Is a duplicate.  Skip.
                # if debugging:
                #     print(f'  Skipping duplicate class: [{attribute.__name__}]')
                duplicate_listeners_skipped_count += 1
                continue
            else:
                # Not a duplicate.  Keep.
                event_listener_class_name_dict[attribute.__name__] = None

            # -------------------------------------------------------------
            # Finally, duplicates removed, it's okay to instantiate these
            # listeners for later use.
            # -------------------------------------------------------------
            listeners_instantiated_and_kept_count += 1
            if debugging:
                print(f'  Keeping >>>>:  {resource}')
            if is_view_event_listener:
                # These have to be instantiated with the current View.
                # However, these Views are replaced if the current View has
                # changed before running each Report so they have the
                # correct View when their `on_query_context()` functions
                # are being called.
                view_event_listener_count += 1
                listener = attribute(curr_view)
            else:
                event_listener_count += 1
                listener = attribute()

            listeners.append(listener)  # Append instantiated EventListener class.
            files.append(full_path)

    if debugging:
        print('_on_qry_context_listeners() stats:')
        print(f'  modules_considered                      :  {len(resources):5}')
        print(f'  modules_skipped_due_to_package          :  {modules_skipped_due_to_package_count:5}')
        print(f'  modules_skipped_due_to_loading_exception:  {modules_skipped_due_to_loading_exception_count:5}')
        print(f'  modules_skipped_due_to_being_st_modules :  {modules_skipped_due_to_being_st_modules_count:5}')
        print(f'  modules_loaded                          :  {modules_loaded_count:5}')
        print(f'  attributes_examined                     :  {attributes_examined_count:5}')
        print(f'  attr_skipped_due_to_not_having_listeners:  {attr_skipped_due_to_not_having_listeners_count:5}')
        print(f'  duplicate_listeners_skipped             :  {duplicate_listeners_skipped_count:5}')
        print(f'  listeners_instantiated_and_kept         :  {listeners_instantiated_and_kept_count:5}')
        print(f'  event_listeners                         :  {event_listener_count:5}')
        print(f'  view_event_listeners                    :  {view_event_listener_count:5}')

    return listeners, files


def _snippet_triggers_dictionary():
    """
    Generate and return a dictionary of snippet triggers to be used
    by the ``has_snippet`` context query logic.
    """
    if debugging:
        print('In context._snippet_triggers_dictionary()...:')

    result_dict = {}

    resources = sublime.find_resources("*.sublime-snippet")
    has_content_count = 0
    has_trigger_count = 0
    has_scope_count = 0
    has_desc_count = 0
    duplicate_trigger_count = 0
    unique_trigger_count = 0
    skipped_due_to_exception_parsing = 0
    dup_trigger_list = []

    # ---------------------------------------------------------------------
    # For each *.sublime-snippet file within perception of Sublime Text....
    # ---------------------------------------------------------------------
    for path in resources:
        # print(f'  {path}')
        snippet_xml_str = sublime.load_resource(path)

        try:
            snippet_tree = ET.fromstring(snippet_xml_str)
            # content_elem = snippet_tree.find('content')
            # content = content_elem.text if hasattr(content_elem, 'text') else None
            content = None

            trigger_elem = snippet_tree.find('tabTrigger')
            if trigger_elem and hasattr(trigger_elem, 'text'):
                trigger = trigger_elem.text
            else:
                trigger = None

            scope_elem = snippet_tree.find('scope')
            if scope_elem and hasattr(scope_elem, 'text'):
                scope = scope_elem.text
            else:
                scope = None

            # desc_elem = snippet_tree.find('description')
            # desc = desc_elem.text if hasattr(desc_elem, 'text') else None
            desc    = None
            # No need to keep `content` and `desc`, but `trigger` and
            # `scope` are important to the `has_snippet` test.
            snippet = Snippet(path, content, trigger, scope, desc)

            if content is not None:
                has_content_count += 1
            if trigger is not None:
                has_trigger_count += 1
            if scope   is not None:
                has_scope_count   += 1
            if desc    is not None:
                has_desc_count    += 1

            if trigger in result_dict:
                # Append to list.
                duplicate_trigger_count += 1
                result_dict[trigger].append(snippet)
                dup_trigger_list.append(trigger)
            else:
                unique_trigger_count += 1
                result_dict[trigger] = [snippet]
        except Exception as e:
            skipped_due_to_exception_parsing += 1
            if debugging:
                print(f'  >>>>>>>>>>>> Exception parsing [{path}]\n  [{e}].')

    if debugging:
        print('_snippet_triggers_dictionary() stats:')
        print(f'  snippet_files_examined      :  {len(resources):4}')
        print(f'  number that have content    :  {has_content_count:4}')
        print(f'  number that have triggers   :  {has_trigger_count:4}')
        print(f'  number that have scope      :  {has_scope_count:4}')
        print(f'  number that have description:  {has_desc_count:4}')
        print(f'  number of unique triggers   :  {unique_trigger_count:4}')
        print(f'  number of duplicate triggers:  {duplicate_trigger_count:4}')
        print(f'  number of exceptions parsing:  {skipped_due_to_exception_parsing:4}')
        # print(f'  duplicate triggers          :  {dup_trigger_list}')

    return result_dict

t0 = datetime.now()
_on_query_context_listener_list, _on_query_context_file_list = _on_qry_context_listeners()
t1 = datetime.now()
_snippets_by_trigger = _snippet_triggers_dictionary()

if debugging:
    t2 = datetime.now()
    print(f'Time to load `on_query_context()` listeners: {t1 - t0}.')
    print(f'Time to load Snippet triggers and scopes   : {t2 - t1}.')
    print(f'Total                                      : {t2 - t0}.')


# *************************************************************************
# Utilities
# *************************************************************************

def update_view_event_listeners(curr_view: sublime.View):
    """
    Conditionally update any ViewEventListeners so they are using the
    current view if consulted to evaluate a context.
    """
    if debugging:
        print('In context.update_view_event_listeners()...:')

    for i, listener in enumerate(_on_query_context_listener_list):
        class_obj = type(listener)
        if issubclass(class_obj, sublime_plugin.ViewEventListener):
            view_event_listener = _on_query_context_listener_list[i]
            if view_event_listener.view != curr_view:
                if debugging:
                    print(f'  {view_event_listener.view} != {curr_view}.')
                    print('  Updating.')
                view_event_listener.view = curr_view
            else:
                if debugging:
                    print(f'  {view_event_listener.view} == {curr_view}.')
                    print('  Already current.')


def _curr_word_for_snippet(view, rgn):
    r"""
    Current word in Snippet context.  What is special about Snippet context
    is that Snippet triggers can use symbols, so it is not limited by regex
    '\w+' nor is it limited by "word-separator" characters.  Specifically,
    these characters are also used in snippets, and these may not be the
    limit.

        $ / \ | _ - ( ^ ~ ! # = { : , . ?

    Symbols not used in Snippets on test system:

        ` @ % ) } ; ' " < >

    "Current word" is defined as:

    - characters to the left of carat until first space or BOL, concatenated
    - with characters to the right of caret until first space or EOL.

    Returns:  "current word" or ``None`` if there isn't one.

    """
    result = None
    blank_chars = ' \t'

    # No text is selected.  Gather characters surrounding caret.
    line_rgn = view.line(rgn.a)
    line = view.substr(line_rgn)
    idx_of_caret_in_line = rgn.b - line_rgn.a

    # BOL disqualifies.
    if idx_of_caret_in_line > 0:
        line_len = len(line)
        # if debugging:
        #     print(f'  {line_len=}')
        #     print(f'  {idx_of_caret_in_line=}')

        c = line[idx_of_caret_in_line - 1]

        # Blank char left of caret disqualifies.
        if c in blank_chars:
            pass
        else:
            # Walk backwards until BOL or blank char.
            # (range(idx_of_caret_in_line - 1, -1, -1) is a reversed sequence
            # of integers that ends after 0, like [5,4,3,2,1,0]
            i = 0
            for i in range(idx_of_caret_in_line - 1, -1, -1):
                c = line[i]
                if c in blank_chars:
                    break

            if c in blank_chars:
                begin_i = i + 1
            else:
                begin_i = i

            # if debugging:
            #     print(f'  {begin_i=}')
            #     print(f'  BEGIN: {begin_i} [{line[begin_i]}]')

            # Now walk forwards until EOL or blank char.
            # Note:  `end_i` should contain index AFTER last char.
            if idx_of_caret_in_line < line_len:
                for i in range(idx_of_caret_in_line, line_len):
                    c = line[i]
                    if c in blank_chars:
                        break

                if c in blank_chars:
                    end_i = i
                else:
                    end_i = i + 1
            else:
                # Caret at EOL.  No chars to the right.
                end_i = idx_of_caret_in_line

            # if debugging:
            #     print(f'  {end_i=}')
            #     print(f'  END  : {end_i} [{line[end_i - 1]}]')

            # Extract word.
            result = line[begin_i:end_i]
            if debugging:
                print(f'  Current word: [{result}]')

    return result


def _view_element_found_in_list(view, test_list: list[str]):
    """ Do any of ``test_list`` strings appear in ``view.element()``? """
    result   = False
    element  = view.element()
    if debugging:
        print('In _view_element_found_in_list()....')
        print(f'  {view=}')
        print(f'  {test_list=}')
        print(f'  {element=}')

    if element:
        for pdstr in test_list:
            if pdstr in element:
                result = True
                break

    return result


# *************************************************************************
# Standard Context Test Functions
# *************************************************************************

def _evaluate_test(test_val, operator, operand):
    if debugging:
        print(f'        Evaluating:  {test_val=}, {operator=}, {operand=}')

    result = False

    try:
        if operator == "equal":
            result = test_val == operand
        elif operator == "not_equal":
            result = test_val != operand
        elif operator == "regex_match":
            result = test_val is not None and re.fullmatch(operand, test_val) is not None
        elif operator == "not_regex_match":
            result = test_val is     None or  re.fullmatch(operand, test_val) is     None
        elif operator == "regex_contains":
            result = test_val is not None and re.search(operand, test_val)    is not None
        elif operator == "not_regex_contains":
            result = test_val is     None or  re.search(operand, test_val)    is     None
        else:
            raise AssertionError(f'Operator not recognized:  {operator}.')
    except Exception as e:
        print("        Failed to evaluate context", operand, test_val, e)
        result = False

    if debugging:
        print(f'        Result    :  {result}')

    return result


def _test_selections(test_val_func, view, operator, operand, match_all):
    """
    Run ``test_val_func()`` on all of ``view``'s selections.

    :param val_func:    Function used to fetch test value
    :param view:        Current view being used in testing
    :param operator:    String operator from context condition:
                          - "equal",
                          - "not_equal",
                          - "regex_match",
                          - "not_regex_match",
                          - "regex_contains",
                          - "not_regex_contains".
    :param operand:     (str | int | bool) value to compare with.
    :param match_all:   Do all selections have to evaluate TRUE?
    """
    if debugging:
        print('    In _test_selections()...')
        print(f'      test_val_func={test_val_func.__name__}')
    result = False
    sel_list = view.sel()

    if sel_list:
        for rgn in sel_list:
            if debugging:
                print(f'      {rgn=}')

            test_val = test_val_func(view, rgn)
            result = _evaluate_test(test_val, operator, operand)

            # Exit loop early?
            if result:
                if not match_all:
                    if debugging:
                        print('      Exiting sel loop early:  test passed and match_all == False.')
                    break
            else:
                if match_all:
                    if debugging:
                        print('      Exiting sel loop early:  test failed and match_all == True.')
                    break

    if debugging:
        print(f'    {result=}')

    return result


def _test_selections_scope(selector_pt_func, view, operator, selector, match_all):
    """
    Run ``selector_pt_func()`` on all of ``view``'s selections.

    :param val_func:    Function used to fetch test scope_name
    :param view:        Current view being used in testing
    :param operator:    String operator from context condition:
                          - "equal",
                          - "not_equal".
    :param selector:     (str | int | bool) scope_name to compare with.
    :param match_all:   Do all selections have to evaluate TRUE?
    """
    if debugging:
        print('    In _test_selections_scope()...')
        print(f'      selector_pt_func={selector_pt_func.__name__}')
    result = False
    sel_list = view.sel()

    if sel_list:
        for rgn in sel_list:
            if debugging:
                print(f'      {rgn=}')

            pt_to_test = selector_pt_func(view, rgn)
            is_selector_match = view.match_selector(pt_to_test, selector)

            if operator == "equal":
                result = is_selector_match
            elif operator == "not_equal":
                result = not is_selector_match
            else:
                print(f'      Selector operator [{operator}] not recognized!')
                result = False

            # Exit loop early?
            if result:
                if not match_all:
                    if debugging:
                        print('      Exiting sel loop early:  test passed and match_all == False.')
                    break
            else:
                # result == False
                if match_all:
                    if debugging:
                        print('      Exiting sel loop early:  test failed and match_all == True.')
                    break

    if debugging:
        print(f'    {result=}')

    return result


# -------------------------------------------------------------------------
# Selections
# -------------------------------------------------------------------------

def _test_num_selections(view, operator, operand, match_all):
    test_val = len(view.sel())
    return _evaluate_test(test_val, operator, operand)


def _test_one_selection_empty(view, rgn):
    return (( rgn.a == rgn.b ))


def _test_selection_empty(view, operator, operand, match_all):
    test_val_func = _test_one_selection_empty
    return _test_selections(test_val_func, view, operator, operand, match_all)


# -------------------------------------------------------------------------
# Scope
# -------------------------------------------------------------------------

def _eol_pt(view, rgn):
    # Return pt at EOL.
    return view.line(rgn.end()).b


def _curr_pt(view, rgn):
    # Return pt at current position.
    return rgn.b


def _test_eol_selector(view, operator, operand, match_all):
    scope_pt_func = _eol_pt
    return _test_selections_scope(scope_pt_func, view, operator, operand, match_all)


def _test_one_selector(view, rgn, selector):
    # Return scope at current position.
    return view.scope_name(rgn.b)


def _test_selector(view, operator, operand, match_all):
    scope_pt_func = _curr_pt
    return _test_selections_scope(scope_pt_func, view, operator, operand, match_all)


def _test_one_is_javadoc(view, rgn):
    """
    Does selector 'source comment.block.documentation' match current position?
    """
    selector = 'source comment.block.documentation'
    return view.match_selector(rgn.b, selector)


def _test_is_javadoc(view, operator, operand, match_all):
    """
    Does selector 'source comment.block.documentation' match current position
    for all selections?
    """
    test_val_func = _test_one_is_javadoc
    return _test_selections(test_val_func, view, operator, operand, match_all)


# -------------------------------------------------------------------------
# Text
# -------------------------------------------------------------------------

def _test_one_following_text(view, rgn):
    left_edge_pt = rgn.begin()
    line_rgn = view.line(left_edge_pt)
    following_text_rgn = sublime.Region(left_edge_pt, line_rgn.b)
    return view.substr(following_text_rgn)


def _test_following_text(view, operator, operand, match_all):
    test_val_func = _test_one_following_text
    return _test_selections(test_val_func, view, operator, operand, match_all)


def _test_one_indented_block(view, rgn):
    line_rgn = view.line(rgn)
    return (( line_rgn.size() > 0) and (view.substr(line_rgn)[0] in ' \t' ))


def _test_indented_block(view, operator, operand, match_all):
    test_val_func = _test_one_indented_block
    return _test_selections(test_val_func, view, operator, operand, match_all)


def _test_one_preceding_text(view, rgn):
    left_edge_pt = rgn.begin()
    line_rgn = view.line(left_edge_pt)
    preceding_text_rgn = sublime.Region(line_rgn.a, left_edge_pt)
    return view.substr(preceding_text_rgn)


def _test_preceding_text(view, operator, operand, match_all):
    test_val_func = _test_one_preceding_text
    return _test_selections(test_val_func, view, operator, operand, match_all)


def _test_one_text(view, rgn):
    return view.substr(rgn)


def _test_text(view, operator, operand, match_all):
    test_val_func = _test_one_text
    return _test_selections(test_val_func, view, operator, operand, match_all)


# -------------------------------------------------------------------------
# View
# -------------------------------------------------------------------------

def _test_auto_complete_visible(view, operator, operand, match_all):
    test_val = view.is_auto_complete_visible()
    return _evaluate_test(test_val, operator, operand)


def _test_last_command(view, operator, operand, match_all):
    test_val = view.command_history(0)[0]
    if debugging:
        print(f'    last_command = [{test_val}]')
    return _evaluate_test(test_val, operator, operand)


def _test_last_modifying_command(view, operator, operand, match_all):
    test_val = view.command_history(0, modifying_only = True)[0]
    if debugging:
        print(f'    last_modifying_command = [{test_val}]')
    return _evaluate_test(test_val, operator, operand)


def _test_overlay_has_focus(view, operator, operand, match_all):
    """ Does any panel have focus?

    Supports all of these possible context conditions:
    - {"key": "overlay_has_focus"}
    - {"key": "overlay_has_focus", "operator": "equal", "operand": true}
    - {"key": "overlay_has_focus", "operator": "equal", "operand": false}
    - {"key": "overlay_has_focus", "operator": "not_equal", "operand": true}
    - {"key": "overlay_has_focus", "operator": "not_equal", "operand": false}
    """
    test_val = _view_element_found_in_list(view, _overlay_view_element_detection_list)
    return _evaluate_test(test_val, operator, operand)


def _test_overlay_name(view, operator, operand, match_all):
    """
    Does name of Overlay with focus match ``operator`` and ``operand``?

    Supports context conditions like this:
    - { "key": "overlay_name", "operator": "equal", "operand" : "goto" }
    - { "key": "overlay_name", "operator": "not_equal", "operand" : "goto" }
    """
    result = False
    test_val = None
    element = view.element()

    if element:
        if 'goto_anything:' in element:
            test_val = 'goto'
        elif 'command_palette:' in element:
            test_val = 'command_palette'

        if test_val:
            result = _evaluate_test(test_val, operator, operand)

    return result


def _test_panel_has_focus(view, operator, operand, match_all):
    """ Does any panel have focus?

    Supports all of these possible context conditions:
    - {"key": "panel_has_focus"}
    - {"key": "panel_has_focus", "operator": "equal", "operand": true}
    - {"key": "panel_has_focus", "operator": "equal", "operand": false}
    - {"key": "panel_has_focus", "operator": "not_equal", "operand": true}
    - {"key": "panel_has_focus", "operator": "not_equal", "operand": false}
    """
    test_val = _view_element_found_in_list(view, _panel_view_element_detection_list)
    return _evaluate_test(test_val, operator, operand)



def _test_panel_type(view, operator, operand, match_all):
    """
    Is the type of the Panel with focus a match with ``operator`` and ``operand``?

    Used with key bindings like this:

    { "keys": ["alt+c"], "command": "toggle_case_sensitive", "context":
        [{"key": "panel_type", "operand": "find"}, {"key": "panel_has_focus"}],
    },
    { "keys": ["enter"], "command": "select", "context":
        [
            { "key": "panel_has_focus", "operator": "equal", "operand": true },
            { "key": "panel_type", "operand": "input"},
        ],
    },

    Possible choices:

    - "input" = any panel created by ``window.create_io_panel()``
    - "find"  = any input View on any of these Panels:

        Find
        Find-in-Files
        Replace
        Incremental Find

    - "output" = output of a Build System, but not of the console, likely
                 any panel created with ``window.create_output_panel()``
    """
    result = False

    if operand == 'input':
        found = _view_element_found_in_list(view, ['input:'])
        if found:
            result = _evaluate_test('input', operator, operand)
    elif operand == 'find':
        found = _view_element_found_in_list(view, _find_panel_type_detection_list)
        if found:
            result = _evaluate_test('find', operator, operand)
    elif operand == 'output':
        found = _view_element_found_in_list(view, [':output'])
        if found:
            result = _evaluate_test('output', operator, operand)

    return result


def _test_popup_visible(view, operator, operand, match_all):
    test_val = view.is_popup_visible()
    return _evaluate_test(test_val, operator, operand)


def _test_read_only(view, operator, operand, match_all):
    test_val = view.is_read_only()
    return _evaluate_test(test_val, operator, operand)


# -------------------------------------------------------------------------
# Snippet (examines text around caret)
# -------------------------------------------------------------------------

def _test_one_has_snippet(view, rgn):
    r"""
    Does current word match a Snippet trigger?  Only applies if:

    - no text is selected, and
    - there is at least one non-blank character to the left of caret.
    """
    curr_word = _curr_word_for_snippet(view, rgn)
    return (( curr_word and curr_word in _snippets_by_trigger ))


def _test_has_snippet(view, operator, operand, match_all):
    test_val_func = _test_one_has_snippet
    return _test_selections(test_val_func, view, operator, operand, match_all)


# -------------------------------------------------------------------------
# Window Logic
# -------------------------------------------------------------------------

def _group_for_view(view) -> int | None:
    """ Group number for view.

    :return:  None if view not in group.
    """
    result = None
    sheet = view.sheet()

    if sheet:
        result = sheet.group()

    return result


def _test_group_has_multiselect(view, operator, operand, match_all):
    result = False
    group_id = _group_for_view(view)

    if group_id is not None:
        win = view.window()
        test_val = len( win.selected_sheets_in_group(group_id) ) > 1
        result = _evaluate_test(test_val, operator, operand)

    return result


def _test_group_has_transient_sheet(view, operator, operand, match_all):
    result = False
    group_id = _group_for_view(view)

    if group_id is not None:
        win = view.window()
        test_val = (( win.transient_sheet_in_group(group_id) is not None ))
        result = _evaluate_test(test_val, operator, operand)

    return result


def _test_panel(view, operator, operand, match_all):
    """ Does name of active panel == `operand`? """
    result = False
    operand_type = type(operand)

    if operand_type is not str:
        print(f'_test_panel:  expected operand to be a string, got {operand_type} instead.')
    else:
        win = view.window()
        panel_name = win.active_panel()
        if panel_name:
            result = _evaluate_test(panel_name, operator, operand)
        else:
            # This branch handles things when no panel is visible, so tests like:
            # - { "key": "panel", "operator": "not_equal", "operand": 'console' }
            #   correctly tests TRUE , and
            # - { "key": "panel", "operator": "equal", "operand": 'console' }
            #   correctly tests FALSE.
            result = _evaluate_test('non-existent_panel', operator, operand)

    return result


def _test_panel_visible(view, operator, operand, match_all):
    """ Is any panel visible? """
    result = False

    win = view.window()
    panel_name = win.active_panel()
    test_val = (( panel_name is not None ))
    result = _evaluate_test(test_val, operator, operand)

    return result


# -------------------------------------------------------------------------
# Unimplemented / Infeasible
# -------------------------------------------------------------------------

def _test_unimplemented(view, operator, operand, match_all):
    if debugging:
        print('    >>>> UNIMPLEMENTED.')
    return False


# -------------------------------------------------------------------------
# Populate ``_context_tests_by_name``.  This is done here because at module
# load time, the function definitions are first available at this point.
# This is somewhat more efficient than 27 assignments.
# -------------------------------------------------------------------------
_context_tests_by_name = {                                          # Operator Group
    # Selections                                                    # --------------
    'num_selections'           : _test_num_selections,              # equality group
    'selection_empty'          : _test_selection_empty,             # equality group

    # Scope
    'eol_selector'             : _test_eol_selector,                # equality group
    'is_javadoc'               : _test_is_javadoc,                  # equality group
    'selector'                 : _test_selector,                    # equality group

    # Text
    'following_text'           : _test_following_text,              # regex group
    'indented_block'           : _test_indented_block,              # equality group
    'preceding_text'           : _test_preceding_text,              # regex group
    'text'                     : _test_text,                        # regex group

    # View
    'auto_complete_visible'    : _test_auto_complete_visible,       # equality group
    'last_command'             : _test_last_command,                # equality group
    'last_modifying_command'   : _test_last_modifying_command,      # equality group
    'overlay_has_focus'        : _test_overlay_has_focus,           # equality group
    'overlay_name'             : _test_overlay_name,                # equality group
    'overlay_visible'          : _test_overlay_has_focus,  # Kludge, but no other option appears possible.
    'panel_has_focus'          : _test_panel_has_focus,             # equality group
    'panel_type'               : _test_panel_type,                  # equality group
    'popup_visible'            : _test_popup_visible,               # equality group
    'read_only'                : _test_read_only,                   # equality group
    # setting.xxxx  is implemented in `_condition_test()` since     # equality group
    # its test pattern is different from all the other tests.

    # Snippet (examines text around caret)
    'has_next_field'           : _test_unimplemented,               # equality group
    'has_prev_field'           : _test_unimplemented,               # equality group
    'has_snippet'              : _test_has_snippet,                 # equality group

    # Window
    'group_has_multiselect'    : _test_group_has_multiselect,       # equality group
    'group_has_transient_sheet': _test_group_has_transient_sheet,   # equality group
    'panel'                    : _test_panel,                       # equality group
    'panel_visible'            : _test_panel_visible,               # equality group

    # Application
    'is_recording_macro'       : _test_unimplemented,               # equality group
}

_context_entry_numbers_by_name = {}
_context_entry_numbers_by_name['setting'] = 0

i = 0     # Make LSP-pyright happy.
key = ''  # Make LSP-pyright happy.

for i, key in enumerate(_context_tests_by_name, 1):
    _context_entry_numbers_by_name[key] = i

del i, key




# *************************************************************************
# Context Classes
# *************************************************************************

class OperandTypeCode(IntEnum):
    """
    An integer value for operand types;
    helps with detecting functionally-equivalent ContextCondition objects.
    """
    STR   = 0
    BOOL  = 1
    INT   = 2
    FLOAT = 3   # As of 07-May-2026 this type doesn't exist in an operand yet,
                # but this is here since it feels like it is only a matter of
                # time before this type is accepted.


class ContextCondition:
    """
    Sublime Text Key-Binding Context Conditions

    Each instantiated ContextCondition represents one Boolean condition of a
    Sublime Text key-binding context.

    1.  It has:
        +   "key" entry (test name); str value:  (no default value).
            One of the keys in `_context_tests_by_name`.
            The test indicates the value of the LHS (left-hand-side)
            of the Boolean expression this condition forms.

        +   operator; str:  (Default:  "equal").
            One of the Boolean operators in one of these groups:

            + equality-operator group:

                + "equal",
                + "not_equal"

            + regex-operator group:

                + "regex_match",
                + "not_regex_match",
                + "regex_contains",
                + "not_regex_contains"

            Hint:  all tests use operators from the quality-operator group
            except these 3:

            +   "text",
            +   "preceding_text", and
            +   "following_text".

        +   operand; str | bool | int:  (Default: true).
            This value provides the RHS (right-hand-side) of the Boolean
            expression formed by this condition.

        +   match_all; bool:  (Default: false).
            If specified with a `true` value, the context of ALL selections
            must satisfy this condition for it to evaluate TRUE.  If omitted
            or specified `false`, only ONE of the selections must satisfy
            this condition for it to result in a TRUE test result.

        +   language:  language code, e.g. 'en' (features that use this
            are not yet implemented).

    2.  It can be asked:
        +   str(self)   # String representation
        +   repr(self)  # Debug representation
        +   hash(self)  # Used in determining equivalency to other ContextConditions
        +   self.equivalent(other)?  # Is ``other`` equivalent to ``self``?
        +   self == other?           # Is ``other`` equivalent to ``self``?
        +   formatted(self, longest_key_len, longest_op_len, indent_level)
            +   The parameters assist with giving a table-like
                representation, to enhance readability.
        +   natural_language_repr(self)  (translation of Boolean condition)

    3.  It can be requested to change ContextConditions objects as follows:
        +   Creation passes the condition dictionary from the `.sublime-keymap`
            "context" entry, which parts are then extracted and stored.
        +   set_language(language_code)
            +   Default:  'en'
            +   Determines language used by `natural_language_repr()` method.

    Examples:
    { "key": "setting.auto_match_enabled", "operator": "equal"             , "operand": true },
    { "key": "selection_empty"           , "operator": "equal"             , "operand": true }, "match_all": true,
    { "key": "following_text"            , "operator": "regex_contains"    , "operand": "^(?:\t| |\\)|]|\\}|>|$)" }, "match_all": true,
    { "key": "preceding_text"            , "operator": "not_regex_contains", "operand": "[\"a-zA-Z0-9_]$" }, "match_all": true,
    { "key": "eol_selector"              , "operator": "not_equal"         , "operand": "string.quoted.double - punctuation.definition.string.end" }, "match_all": true,


    Although several attributes are exposed, it is expected that clients of
    this class ONLY read them.  Setting them is done at instantiation time.
    """
    hash_format_spec = '06x'

    __slots__ = [
        'key',
        'setting_name',
        'operator',
        'operand',
        'match_all',
        'language',
        '_orig_operator',
        '_orig_operand',
        '_orig_match_all',
        '_hashcode',
    ]

    def __init__(self, condition_dict: dict, language_code: str = 'en'):
        key = condition_dict[_key_key]
        if key.startswith('setting.'):
            self.key          = 'setting'
            self.setting_name = key[8:]
        else:
            self.key          = key
            self.setting_name = ''

        if _operator_key in condition_dict:
            self.operator = condition_dict[_operator_key]
            self._orig_operator = self.operator
        else:
            self.operator = _default_operator
            self._orig_operator = None

        if _operand_key in condition_dict:
            self.operand = condition_dict[_operand_key]
            self._orig_operand = self.operand
        else:
            self.operand = _default_operand
            self._orig_operand = None

        if _match_all_key in condition_dict:
            self.match_all = condition_dict[_match_all_key]
            self._orig_match_all = self.match_all
        else:
            self.match_all = _default_match_all
            self._orig_match_all = None

        self.language  = language_code
        self._hashcode = -1

        debugging = is_debugging(DebugBits.CONTEXT_CONDITION)
        if debugging:
            print(f'In {self.__class__.__name__}.__init__()....')
            print(f'  {self.key             = }')
            print(f'  {self.setting_name    = }')
            print(f'  {self.operator        = }')
            print(f'  {self._orig_operator  = }')
            print(f'  {self.operand         = }')
            print(f'  {self._orig_operand   = }')
            print(f'  {self.match_all       = }')
            print(f'  {self._orig_match_all = }')
            print(f'  {self.language        = }')
            print(f'  {hash(self)           = :{self.hash_format_spec}}')

    def __str__(self) -> str:
        return self.formatted()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.formatted()})'

    def __hash__(self) -> int:
        """
        To make it easy for humans to read in hex while debugging, the 4
        values above occupy bit space in the integer like this:

                 byte 2                  byte 1                  byte 0
        +-----------+-----------+-----------+-----------+-----------+-----------+
        |     test_name_code    |   0b0000    operator  |  operand    match_all |
        +-----------+-----------+-----------+-----------+-----------+-----------+
        """
        if self._hashcode == -1:
            # Lazy calculation; only once when the value is required.
            # key = self.key

            key = self.key
            if key in _context_entry_numbers_by_name:
                test_entry_num = _context_entry_numbers_by_name[key]
            else:
                test_entry_num = len(_context_entry_numbers_by_name) + 1

            operator_code  = _operator_codes_by_name[self.operator]
            match_all_val  = int(self.match_all)

            operand = self.operand
            if isinstance(operand, str):
                operand_type_code = OperandTypeCode.STR
            elif isinstance(operand, bool):
                operand_type_code = OperandTypeCode.BOOL
            elif isinstance(operand, int):
                operand_type_code = OperandTypeCode.INT
            elif isinstance(operand, float):
                operand_type_code = OperandTypeCode.FLOAT
            else:
                msg = f'{self.__class__.__name__}.__hash__():  operand type not recognized: {type(operand)}'
                raise AssertionError(msg)

            self._hashcode = (
                      (test_entry_num    << 16)
                    | (operator_code     <<  8)
                    | (operand_type_code <<  4)
                    | match_all_val
                    )

        return self._hashcode

    def __eq__(self, other) -> bool:
        return self.is_equivalent(other)

    def is_equivalent(self, other) -> bool:
        """
        Is ``other`` equivalent to ``self``?

        Testing for Functionally-Equivalent ContextCondition Objects
        ------------------------------------------------------------
        To detect 2 equivalent context conditions, the approach taken is to
        make each condition have a "hash value".  It encapsulates:

        +----------------------------------+------+-------------------------+
        | Description                      | Bits | Source                  |
        +==================================+======+=========================+
        | key (test_name) (28 tests with   | 5    | Condition's entry # in  |
        | "setting.xxx" counting as 1)     |      | _context_tests_by_name  |
        +----------------------------------+------+-------------------------+
        | operator (there are 6 operators) | 3    | _operator_codes_by_name |
        +----------------------------------+------+-------------------------+
        | operand type (str, bool, int)    | 2    | OperandTypeCode         |
        +----------------------------------+------+-------------------------+
        | match_all value                  | 1    | 0 == False, 1 == True   |
        +----------------------------------+------+-------------------------+

        See ``__hash__()`` docstring for bit layout.

        Each ContextCondition has a "setting_name" attribute which is an empty
        string by default.  If its test name begins with "setting.", then the
        condition name is copied into it.  Then two ContextCondition objects
        would be functionally equivalent if:

        - they have the same hash value (ensuring the operands are of the same type)
        - cond1.setting_name == cond2.setting_name.
        - cond1.operand == cond2.operand, and

        Note that this would also require the ContextCondition (at instantiation
        time) to assume the default values for operator, operand and match_all
        when they were not specified.
        """
        return (    (hash(other) == hash(self))
                and (other.setting_name == self.setting_name)
                and (other.operand == self.operand)
                )

    def set_language(self, language: str = 'en'):
        self.language = language

    def formatted(self,
            longest_key_len: int = 0,
            longest_op_len: int = 0,
            indent_level: int = 0
            ) -> str:
        """
        Python representation of ``json_binding`` context conditions (same structure as
        in .sublime-keymap files) such that the keys and values are in logical order.

        Each condition presented on 1 line in JSON-compatible representation.

        Representation (just one of these, but 2 shown to show meaning of args):
        ------------------------------------------------------------------------
        { "key": "selection_empty"           , "operator": "equal", "operand": False, "match_all": True }
        { "key": "setting.auto_match_enabled", "operator": "equal", "operand": True }
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^                ^^^^^
                      +-- longest_key_len                     +-- longest_op_len
        }
        """
        key = self.key
        if key == 'setting':
            cond_name = f'{key}.{self.setting_name}'
        else:
            cond_name = key
        field = f'"{cond_name}"'
        indent = '  ' * indent_level
        result = f'{indent}{{ "key": {field:{longest_key_len + 2}}'

        # operator
        field = json.dumps(self.operator)
        result += f', "operator": {field:{longest_op_len + 2}}'
        # operand
        # This value can be str, bool or int, so we use `json.dumps()`.
        val_repr = json.dumps(self.operand)
        result += f', "operand": {val_repr}'
        # match_all
        val_repr = json.dumps(self.match_all)
        result += f', "match_all": {val_repr}'

        result += ' }'

        return result

    def natural_language_repr(self, indent_level: int = 0) -> str:
        indent = '  ' * indent_level
        return f'{indent}English:  Description of ContextCondition'


class SmartContext:
    """
    Sublime Text Key-Binding Contexts --- lists of conditions required
    for Sublime Text to select a key binding.

    It has:
        +   list of ContextCondition objects
    It can be asked:
        +   query(self, view)
        +   str(self)
        +   repr(self)
        +   ...
    t can be requested to change context objects as follows:
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
        condition_list = binding.context_list()
        if condition_list is None:
            raise AssertionError('`binding` "context" entry not present.')

        conditions: list[ContextCondition] | None = None
        if len(condition_list) > 0:
            conditions = []
            for condition_dict in condition_list:
                conditions.append(ContextCondition(condition_dict))

        self.conditions = conditions
        self.binding    = binding

    def __str__(self):
        """
        SmartContext(setting.auto_match_enabled, selection_empty, following_text, selector, eol_selector)
        """
        cond_name_list = []

        if self.conditions is not None and len(self.conditions) > 0:
            for cond in self.conditions:
                cond_name_list.append(cond.key)

        short_test_name_list = ', '.join(cond_name_list)
        return f'{self.__class__.__name__}({short_test_name_list})'

    def __repr__(self):
        """
        SmartContext("context": [
          { "key": "setting.auto_match_enabled", "operator": "equal"         , "operand": true }
          { "key": "selection_empty"           , "operator": "equal"         , "operand": true, "match_all": true }
          { "key": "following_text"            , "operator": "regex_contains", "operand": '^"', "match_all": true }
          { "key": "selector"                  , "operator": "not_equal"     , "operand": 'punctuation.definition.string.begin', "match_all": true }
          { "key": "eol_selector"              , "operator": "not_equal"     , "operand": 'string.quoted.double - punctuation.definition.string.end', "match_all": true }
        ])
        """
        return f'{self.__class__.__name__}({self.formatted()})'

    def __eq__(self, other) -> bool:
        """ Is ``self`` equal to ``other``? """
        return self.is_equivalent(other)

    def _equivalent_to_any_condition(self, self_cond, other_cond_list) -> tuple[int, bool]:
        result = False
        i = -1

        for i, other_cond in enumerate(other_cond_list):
            if other_cond.is_equivalent(self_cond):
                result = True
                break

        return i, result

    def is_equivalent(self, other) -> bool:
        """
        Is ``other`` equivalent to ``self``?

        Testing for Equivalent Contexts
        -------------------------------
        Over and above having context conditions that are equivalent, the
        order they may appear in another context is random, so a SmartContext
        is considered the equivalent of another if and only if:

        - number of conditions in both contexts match;
        - each ``self.conditions`` item can be paired with an item in
          ``other.conditions`` that it is equivalent to, and
          thereafter both paired conditions no longer participate in any other
          equivalence tests.

        If each condition was paired up with an equivalent condition in the
        other, and no conditions were left over in either, then the two
        contexts are equivalent.
        """
        result = False

        if other.conditions is not None and self.conditions is not None:
            if len(other.conditions) == len(self.conditions):
                working_other_cond_list = other.conditions.copy()  # Shallow copy.

                for self_cond in self.conditions:
                    i, test_result = self._equivalent_to_any_condition(self_cond, working_other_cond_list)
                    if test_result:
                        # Okay so far.  Remove element 'i' from working list.
                        del working_other_cond_list[i]
                        if len(working_other_cond_list) == 0:
                            # Equivalent conditions in other were found for
                            # each condition in self.conditions.
                            result = True
                            break
                    else:
                        # result is already False, just break out of loop.
                        break

        return result

    def formatted(self, indent_level: int = 0, raw: bool = True, natural_language: bool = False) -> str:
        """
        Python representation of ``self`` (same structure as in
        .sublime-keymap files) such that the keys and values are in logical order.

        Representation:
        ===============

        raw:
        ----
        "context": [
          { "key": "setting.auto_match_enabled", "operator": "equal"         , "operand": true },
          { "key": "selection_empty"           , "operator": "equal"         , "operand": true, "match_all": true },
          { "key": "following_text"            , "operator": "regex_contains", "operand": '^"', "match_all": true },
          { "key": "selector"                  , "operator": "not_equal"     , "operand": 'punctuation.definition.string.begin', "match_all": true },
          { "key": "eol_selector"              , "operator": "not_equal"     , "operand": 'string.quoted.double - punctuation.definition.string.end', "match_all": true }
        ]

        natural_language:
        --------
        "context": [
          English:  Description of ContextCondition,
          English:  Description of ContextCondition,
          English:  Description of ContextCondition,
          English:  Description of ContextCondition,
          English:  Description of ContextCondition
        ]

        raw and natural_language:
        ----------------
        "context": [
          { "key": "setting.auto_match_enabled", "operator": "equal"         , "operand": true }
            English:  Description of ContextCondition,
          { "key": "selection_empty"           , "operator": "equal"         , "operand": true, "match_all": true }
            English:  Description of ContextCondition,
          { "key": "following_text"            , "operator": "regex_contains", "operand": '^"', "match_all": true }
            English:  Description of ContextCondition,
          { "key": "selector"                  , "operator": "not_equal"     , "operand": 'punctuation.definition.string.begin', "match_all": true }
            English:  Description of ContextCondition,
          { "key": "eol_selector"              , "operator": "not_equal"     , "operand": 'string.quoted.double - punctuation.definition.string.end', "match_all": true }
            English:  Description of ContextCondition
        ]

        :param indent_level:  Level of indentation for output
        :param natural_language:       Include English description with raw condition repr?
        """
        indent = '  ' * indent_level
        lines = [f'{indent}"context": [']

        if self.conditions and len(self.conditions) > 0:
            longest_key_len = 0
            longest_op_len = 5   # Length of 'equal'

            # Compute length of widest `key` and `operator` fields.
            for condition in self.conditions:
                key_len = len(condition.key)
                if key_len > longest_key_len:
                    longest_key_len = key_len

                op_len  = len(condition.operator)
                if op_len > longest_op_len:
                    longest_op_len = op_len

            # Now generate indented formatted strings.
            cond_lines = []

            for condition in self.conditions:
                if raw and natural_language:
                    # Raw and English
                    cond_str = condition.formatted(
                            longest_key_len,
                            longest_op_len,
                            indent_level + 1
                            )

                    cond_str += '\n' + condition.natural_language_repr(indent_level + 2)
                elif natural_language:
                    # English only
                    cond_str = condition.natural_language_repr(indent_level + 1)
                else:
                    # Raw only
                    cond_str = condition.formatted(
                            longest_key_len,
                            longest_op_len,
                            indent_level + 1
                            )

                cond_lines.append(cond_str)

            lines.append( ',\n'.join(cond_lines) )
            lines.append(f'{indent}]')
        else:
            lines[0] += ']'

        return '\n'.join(lines)

    def _condition_test(self, view, condition: ContextCondition, debugging: int) -> bool:
        """
        :param view:       Current View (used to test if key context is applicable)
        :param condition:  Single condition dictionary from key-binding context.
        :param debugging:  Produce debugging output?
        :return:  Result of test of specified ContextCondition.
        """
        if debugging:
            print(f'  In {self.__class__.__name__}._condition_test()...')
            print(f'    {repr(condition)}')

        result    = False
        key       = condition.key
        operator  = condition.operator
        operand   = condition.operand
        match_all = condition.match_all

        if key == 'setting':
            # Query on setting.
            value = view.settings().get(condition.setting_name, None)
            if debugging:
                print(f'    Setting name {condition.setting_name}:')
            result = _evaluate_test(value, operator, operand)
        elif key in _context_tests_by_name:
            # Is one of the standard standard context tests.
            test_func = _context_tests_by_name[key]
            result = test_func(view, operator, operand, match_all)
        else:
            # Is NOT one of the standard standard context tests.
            # Consult event listeners with `on_query_context()` functions.
            if debugging:
                print(f'  Non-standard test [{key}]; consulting event listeners...')

            found = False
            operator_code = _operator_codes_by_name[operator]

            for listener in _on_query_context_listener_list:
                if issubclass(type(listener), sublime_plugin.ViewEventListener):
                    # EventListener takes 5 arguments because it already has
                    # the current view.  (It was updated to the current view
                    # just moments ago if it was out of date.)
                    query_result = listener.on_query_context(
                            key, operator_code, operand, match_all
                            )
                else:
                    # EventListener takes 6 arguments with current view view.
                    query_result = listener.on_query_context(
                            view, key, operator_code, operand, match_all
                            )

                if query_result is None:
                    if debugging:
                        print(f'  No knowledge of [{key}] by {listener}.')
                    continue
                else:
                    # on_query_context() listener just consulted knows about
                    # this context test and reported, so we can break out
                    # of the loop.
                    if debugging:
                        print(f'  {query_result} reported by {listener}.')
                    found = True
                    result = query_result
                    break

            if not found:
                msg = (
                        f'  {self.__class__.__name__}:  key [{key}] not recognized.\n'
                        f'  keymap={self.binding.source()}\n'
                        f'{self.binding.formatted(1, include_source = True)}'
                      )
                print(msg)

        return result

    def query(self, view):
        """
        Do all conditions in "context" match current circumstances with
        ``view``, window, application, etc.?

        :param view:  Active View (used to test if key context is applicable)
        """
        global debugging
        debugging = is_debugging(DebugBits.FILTERING_ON_CONTEXT)
        if debugging:
            print(f'In {self.__class__.__name__}.query()...')
            print(f'{self.binding.formatted(1, include_source = True)}')

        all_tests_passed = True

        # Do all conditions pass?
        if self.conditions is not None and len(self.conditions) > 0:
            for condition in self.conditions:
                if not self._condition_test(view, condition, debugging):
                    all_tests_passed = False
                    break

        if debugging:
            indent = ' '
            msg = f'{self.__class__.__name__}.query():  {all_tests_passed}'
            underline = '-' * len(msg)
            print(indent, msg)
            print(indent, underline)

        return all_tests_passed

