"""************************************************************************
Sublime Text Key-Binding Contexts
=================================

About to:

- represent contexts as a part of KeyBinding objects, and

- do system-wide context queries to determine if a particular
  key binding applies to the current context (circumstances).


How Context Works:
==================

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

A.  Context module.

    1.  It has:
        +   a full live collection of `on_query_context()` listeners
            +   Called when one of the "key" values (condition names) is not
                among the recognized set.  This list is called until a
                ``True`` or ``False`` is returned (value not ``None``)
                and that result is the valid test result.

                These are loaded when this module is loaded.  Avg time:  0.09 sec.

        +   a full live collection of Snippets triggers in a dictionary
            +   There are 3 "key" (condition) names that have to do with
                Snippets and 1 of them (has_snippet) requires parsing the
                actual snippet files and collecting triggers to determine
                whether the condition tests TRUE or not.  This collection
                is used when that context key (condition name) shows up.

                These are loaded when this module is loaded.  Avg time:  0.11 sec.

    2.  It can be asked:
        +   Are we debugging?                (bool)
        +   _on_query_context_listener_list  (list)
        +   _on_query_context_file_list      (list)
        +   _snippets_by_trigger             (dict)
        +   _context_tests_by_key            (dict)
        +   _operator_codes_by_name          (dict)

B.  ContextCondition Object.

    1.  It has:
        +   condition-definition dictionary directly from key binding

    2.  It can be asked:
        +   str(self)
            +   String representation
        +   repr(self)
            +   Debug representation

C.  Context Object.

    1.  It has:
        +   list of ContextCondition objects
    2.  It can be asked:
        +   query(self, view)
            +   Does context match current circumstances with `view`, window, etc.?
        +   str(self)
            +   String representation
        +   repr(self)
            +   Debug representation
    3.  It can be requested to change context objects as follows:
        +   Change only happens at instantiation when the newly-created
            Context object extracts its condition list from the
            passed-in binding.


Data Flow
=========

When this module is loaded, it loads up the required reference data
from the Sublime Text environment (on_query_context() listeners and
Snippet triggers and scopes).

Various parts of this package (e.g. reporting) build data structures of key
bindings used to do their job.  As these are built, ``Context`` objects are
created from the content of the key bindings, and can later be asked
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
import importlib
import pprint
from datetime import datetime
from enum import IntFlag, IntEnum
from typing import Tuple, List
from xml.etree import ElementTree as ET
import sublime
from sublime import QueryOperator
import sublime_plugin
from ..lib.debug import IntFlag, DebugBits, is_debugging
from ..lib import key_binding


# =========================================================================
# Constants
# =========================================================================

class Snippet:
    """
    Carriers of snippet data
    """
    __slots__ = ['path', 'tabTrigger', 'content', 'scope', 'description']

    def __init__(self, path: str, content: str, tabTrigger: str, scope: str, desc: str):
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
_context_tests_by_key = {}

# Regex to extract setting name from a "settings.xxxx" condition.
_setting_name_from_condition = re.compile(r'^setting\.(.+)$')

# on_query_context() operator code look-up dictionary.
_operator_codes_by_name = {
    "equal"             : QueryOperator.EQUAL,
    "not_equal"         : QueryOperator.NOT_EQUAL,
    "regex_match"       : QueryOperator.REGEX_MATCH,
    "not_regex_match"   : QueryOperator.NOT_REGEX_MATCH,
    "regex_contains"    : QueryOperator.REGEX_CONTAINS,
    "not_regex_contains": QueryOperator.NOT_REGEX_CONTAINS,
}

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
    debugging = is_debugging(DebugBits.LOADING_CONTEXT_ENV)
    if debugging:
        print('In context._on_qry_context_listeners()...:')

    skip_packages = ["Default.", "Package Control.", "SublimeLinter."]
    st_modules = [".sublime", ".sublime_plugin", ".sublime_types"]
    funcs = []
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
        except:
            # if debugging:
            #     print(f'  Exception   :  {resource}')
            modules_skipped_due_to_loading_exception_count += 1
            continue

        for attribute_name in dir(module):
            attributes_examined_count += 1
            attribute = getattr(module, attribute_name)

            is_event_listener = False
            is_event_listener_subclass = False
            is_view_event_listener_subclass = False

            is_class_w_on_query_context = ((
                        isinstance(attribute, type)  # class
                    and hasattr(attribute, "on_query_context")
                    ))

            if is_class_w_on_query_context:
                is_view_event_listener_subclass = \
                        issubclass(attribute, sublime_plugin.ViewEventListener)

                is_event_listener = ((
                           issubclass(attribute, sublime_plugin.EventListener)
                        or is_view_event_listener_subclass
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
            if is_view_event_listener_subclass:
                # These have to be re-instantiated with the current view
                # before each Key-Binding Report so that they are looking
                # at the correct context.
                view_event_listener_count += 1
                listener = attribute(curr_view)
            else:
                event_listener_count += 1
                listener = attribute()

            funcs.append(listener)  # Append instantiated EventListener class.
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
        print(f'  listeners_instantiated_and_kept         :  {listeners_instantiated_and_kept_count:5}')
        print(f'  event_listeners                         :  {event_listener_count:5}')
        print(f'  view_event_listeners                    :  {view_event_listener_count:5}')

    return funcs, files


def _snippet_triggers_dictionary():
    """
    Generate and return a dictionary of snippet triggers to be used
    by the ``has_snippet`` context query logic.
    """
    if debugging:
        print('In context._snippet_triggers_dictionary()...:')

    result_dict = {}
    skip_packages = ["Default.", "Package Control.", "SublimeLinter."]
    st_modules = [".sublime", ".sublime_plugin", ".sublime_types"]

    resources = sublime.find_resources("*.sublime-snippet")
    pkgs_path = sublime.packages_path()
    curr_view = sublime.active_window().active_view()
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
            trigger = trigger_elem.text if hasattr(trigger_elem, 'text') else None
            scope_elem = snippet_tree.find('scope')
            scope = scope_elem.text if hasattr(scope_elem, 'text') else None
            # desc_elem = snippet_tree.find('description')
            # desc = desc_elem.text if hasattr(desc_elem, 'text') else None
            desc    = None
            # No need to keep `content` and `desc`, but `trigger` and
            # `scope` are important to the `has_snippet` test.
            snippet = Snippet(path, content, trigger, scope, desc)

            if content is not None:  has_content_count += 1
            if trigger is not None:  has_trigger_count += 1
            if scope   is not None:  has_scope_count   += 1
            if desc    is not None:  has_desc_count    += 1

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

if debugging:  t0 = datetime.now()
_on_query_context_listener_list, _on_query_context_file_list = _on_qry_context_listeners()
if debugging:  t1 = datetime.now()
_snippets_by_trigger = _snippet_triggers_dictionary()

if debugging:
    t2 = datetime.now()
    print(f'Time to load `on_query_context()` listeners: {t1 - t0}.')
    print(f'Time to load Snippet triggers and scopes   : {t2 - t1}.')
    print(f'Total                                      : {t2 - t0}.')


# =========================================================================
# Utilities
# =========================================================================

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


# =========================================================================
# Standard Context Test Functions
# =========================================================================

def _evaluate_test(value, operator, operand):
    if debugging:
        print(f'        Evaluating:  {value=}, {operator=}, {operand=}')

    result = False

    try:
        if operator == "equal":
            result = value == operand
        elif operator == "not_equal":
            result = value != operand
        elif operator == "regex_match":
            result = value != None and re.match(operand, value)  != None
        elif operator == "not_regex_match":
            result = value == None or  re.match(operand, value)  == None
        elif operator == "regex_contains":
            result = value != None and re.search(operand, value) != None
        elif operator == "not_regex_contains":
            result = value == None or  re.search(operand, value) == None
        else:
            raise AssertionError(f'Operator not recognized:  {operator}.')
    except Exception as e:
        print("        Failed to evaluate context", operand, value, e)
        result = False

    if debugging:
        print(f'        Result    :  {result}')

    return result


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
    sel_list = view.sel()

    if sel_list:
        # Exit loop on first False result.
        for rgn in sel_list:
            if debugging:
                print(f'      {rgn=}')

            value = test_func(view, rgn)
            result = _evaluate_test(value, operator, operand)

            # Exit loop early?
            if result:
                if not match_all:
                    if debugging:
                        print('      Exiting sel loop early:  test passed and match_all == False.')
                    break;
            else:
                if match_all:
                    if debugging:
                        print('      Exiting sel loop early:  test failed and match_all == True.')
                    break;

    if debugging:
        print(f'    {result=}')

    return result


# -------------------------------------------------------------------------
# Selections
# -------------------------------------------------------------------------

def _test_num_selections(view, operator, operand, match_all):
    value = len(view.sel())
    return _evaluate_test(value, operator, operand)


def _test_one_selection_empty(view, rgn):
    return (( rgn.a == rgn.b ))


def _test_selection_empty(view, operator, operand, match_all):
    test_func = _test_one_selection_empty
    return _test_selections(test_func, view, operator, operand, match_all)


# -------------------------------------------------------------------------
# Scope
# -------------------------------------------------------------------------

def _test_one_eol_selector(view, rgn):
    # Get scope at EOL.
    line_rgn = view.line(rgn.end())
    eol_scope = view.scope_name(line_rgn.b)
    left_edge_pt = rgn.begin()
    line_rgn = view.line(left_edge_pt)
    following_text_rgn = sublime.Region(left_edge_pt, line_rgn.b)
    return view.substr(following_text_rgn)


def _test_eol_selector(view, operator, operand, match_all):
    test_func = _test_one_eol_selector
    return _test_selections(test_func, view, operator, operand, match_all)


# -------------------------------------------------------------------------
# Text
# -------------------------------------------------------------------------

def _test_one_following_text(view, rgn):
    left_edge_pt = rgn.begin()
    line_rgn = view.line(left_edge_pt)
    following_text_rgn = sublime.Region(left_edge_pt, line_rgn.b)
    return view.substr(following_text_rgn)


def _test_following_text(view, operator, operand, match_all):
    test_func = _test_one_following_text
    return _test_selections(test_func, view, operator, operand, match_all)


def _test_one_indented_block(view, rgn):
    line_rgn = view.line(rgn)
    return (( line_rgn.size() > 0) and (view.substr(line_rgn)[0] in ' \t' ))


def _test_indented_block(view, operator, operand, match_all):
    test_func = _test_one_indented_block
    return _test_selections(test_func, view, operator, operand, match_all)


def _test_one_preceding_text(view, rgn):
    left_edge_pt = rgn.begin()
    line_rgn = view.line(left_edge_pt)
    preceding_text_rgn = sublime.Region(line_rgn.a, left_edge_pt)
    return view.substr(preceding_text_rgn)


def _test_preceding_text(view, operator, operand, match_all):
    test_func = _test_one_preceding_text
    return _test_selections(test_func, view, operator, operand, match_all)


def _test_one_text(view, rgn):
    return view.substr(rgn)


def _test_text(view, operator, operand, match_all):
    test_func = _test_one_text
    return _test_selections(test_func, view, operator, operand, match_all)


# -------------------------------------------------------------------------
# View
# -------------------------------------------------------------------------

def _test_last_command(view, operator, operand, match_all):
    value = view.command_history(0)[0]
    if debugging:
        print(f'    last_command = [{cmd_name}]')
    return _evaluate_test(value, operator, operand)


def _test_last_modifying_command(view, operator, operand, match_all):
    value = view.command_history(0, modifying_only = True)[0]
    if debugging:
        print(f'    last_modifying_command = [{cmd_name}]')
    return _evaluate_test(value, operator, operand)


def _test_read_only(view, operator, operand, match_all):
    value = view.is_read_only()
    return _evaluate_test(value, operator, operand)


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
    test_func = _test_one_has_snippet
    return _test_selections(test_func, view, operator, operand, match_all)


# -------------------------------------------------------------------------
# Window Logic
# -------------------------------------------------------------------------

# -------------------------------------------------------------------------
# Unimplemented / Infeasible
# -------------------------------------------------------------------------

def _test_unimplemented(view, operator, operand, match_all):
    debugging = is_debugging(DebugBits.FILTERING_ON_CONTEXT)
    if debugging:
        print('    >>>> UNIMPLEMENTED.')
    return False


# -------------------------------------------------------------------------
# Populate ``_context_tests_by_key``.  This is done here because at module
# load time, the function definitions are first available at this point.
# This is somewhat more efficient than 27 assignments.
# -------------------------------------------------------------------------
_context_tests_by_key = {
    # Selections
    'num_selections'           : _test_num_selections,
    'selection_empty'          : _test_selection_empty,

    # Scope
    'eol_selector'             : _test_unimplemented,
    'is_javadoc'               : _test_unimplemented,
    'selector'                 : _test_unimplemented,

    # Text
    'following_text'           : _test_following_text,
    'indented_block'           : _test_indented_block,
    'preceding_text'           : _test_preceding_text,
    'text'                     : _test_text,

    # View
    'last_command'             : _test_last_command,
    'last_modifying_command'   : _test_last_modifying_command,
    'read_only'                : _test_read_only,

    # Snippet (examines text around caret)
    'has_snippet'              : _test_has_snippet,

    # Window
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

    # Settings
    # Implemented in `_condition_test()` due to exact string match not possible.
    # Setting queries all start with "setting.", but their ending supplies
    # the setting name to test, so no listing for "setting.xxxx" here.

    # Unimplemented
    'has_next_field'           : _test_unimplemented,
    'has_prev_field'           : _test_unimplemented,
    'is_recording_macro'       : _test_unimplemented,
}


# =========================================================================
# Context Classes
# =========================================================================

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
        <Context "context": [
          { "key": "setting.auto_match_enabled", "operator": "equal"         , "operand": True }
          { "key": "selection_empty"           , "operator": "equal"         , "operand": True, "match_all": True }
          { "key": "following_text"            , "operator": "regex_contains", "operand": '^"', "match_all": True }
          { "key": "selector"                  , "operator": "not_equal"     , "operand": 'punctuation.definition.string.begin', "match_all": True }
          { "key": "eol_selector"              , "operator": "not_equal"     , "operand": 'string.quoted.double - punctuation.definition.string.end', "match_all": True }
        ]>
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
        :param condition:      Single condition dictionary from key-binding context.
        :param debugging:      Produce debugging output?
        """
        if debugging:
            print(f'  In {self.__class__.__name__}._condition_test()...')
            print(f'    {repr(condition)}')

        result    = False
        key       = condition['key']
        operator  = condition.get('operator', 'equal')
        operand   = condition.get('operand', True)
        match_all = condition.get('match_all', False)

        if key.startswith('setting.'):
            # Query on setting.
            setting_name = key[8:]
            value = view.settings().get(setting_name, None)
            if debugging:
                print(f'    Setting name {setting_name}:')
            result = _evaluate_test(value, operator, operand)
        elif key in _context_tests_by_key:
            # Is one of the standard standard context tests.
            test_func = _context_tests_by_key[key]
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

                if query_result == None:
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
                        f'  keymap={self.binding.pkg_name}/{self.binding.file_name}\n'
                        f'{self.binding.format_binding(1, include_extra = True)}'
                      )
                print(msg)

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
                break

        if debugging:
            indent = ' '
            msg = f'{self.__class__.__name__}.query() result:  {all_tests_passed}'
            underline = '-' * len(msg)
            print(indent, msg)
            print(indent, underline)

        return all_tests_passed

