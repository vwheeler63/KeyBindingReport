"""
Report Key Bindings that override other key bindings.
*****************************************************

Key Binding Conflicts
*********************

Terminology
===========

grok
    To fully and completely understand something in all of its details and
    intricacies.

    ---Wiktionary


Overview
========

Conflicts among key bindings are not only important, but are difficult to
detect by humans.  As an example of how tricky this area can be, on
17-Mar-2022 an enhancement for the `"` and `'` key bindings in the
shipped Python Package introduced a conflict against the bindings for those
keys from the Default Package.  The enhancement for `"` was to NOT
introduce a paired double-quote when the selection was inside a Python
double-quoted string.  The enhancement for `'` was to do the same for
single-quoted strings.  But a subtle oversight caused the sum of these key
bindings (from the Default Package with parts overridden by the Python
Package) to malfunction inside Python comments.

That conflict was discovered (by @vwheeler63 [this author, while the
KeyBindingsReport Package was being developed]) and fixed (by @deathaxe) on
3-May-2026.  To the team's credit, once it was reported in the `Python
Package Issue 4535`_, this conflict was fully handled within about 2 hours
and merged (after several approvals from other team members) a couple of
days later.

To make the point:  how tricky is the area of key-binding conflicts?
Answer:

    These conflicts remained undetected in a mainstream Sublime |nbsp| Text
    Package for 4 years.

Towards answering the need for tools in this area, Package author
Scott |nbsp| Kuroda wrote and released the ``FindKeyConflicts`` Package on
8-Nov-2012. Version 1, 2 and 3 were released in short succession over the
next 3 days.

The name itself tends to fill one with hope that it will find problems in
your key binding arrangement.  However, what it actually does is report
where there is more than one binding that involves a single keypress or
keypress sequence, which is quite common and normal.  Even an unmodified
new Sublime |nbsp| Text installation has well over 70 of these, and none of
them are actual binding conflicts.

Example, these are reported as Key Conflicts for the key bindings to the
double-quote keypress.  The complex contexts are not only nearly 700
characters wide, but are also presented in a form that is completely
un-grok-able by a human.

Scroll to the right to examine the context definitions and ask yourself this
question:  "How long would it take me to determine if any of these had
overlapping contexts?"  The real answer is:

    It's not doable with any level of reliability without a drastic change
    in format that would enable the reader to either grok each context
    easily, or do a text 'diff' that would show the differences between them.

.. code-block:: text

     ["]
       insert_snippet                           Default               [{"key": "setting.auto_match_enabled", "operand": true, "operator": "equal"}, {"key": "selection_empty", "operand": true, "operator": "equal", "match_all": true}, {"key": "following_text", "operand": "^(?:\t| |\\)|]|\\}|>|$)", "operator": "regex_contains", "match_all": true}, {"key": "preceding_text", "operand": "[\"a-zA-Z0-9_]$", "operator": "not_regex_contains", "match_all": true}, {"key": "eol_selector", "operand": "string.quoted.double - punctuation.definition.string.end", "operator": "not_equal", "match_all": true}]
       insert_snippet                           Default               [{"key": "setting.auto_match_enabled", "operand": true, "operator": "equal"}, {"key": "selection_empty", "operand": false, "operator": "equal", "match_all": true}]
       move                                     Default               [{"key": "setting.auto_match_enabled", "operand": true, "operator": "equal"}, {"key": "selection_empty", "operand": true, "operator": "equal", "match_all": true}, {"key": "following_text", "operand": "^\"", "operator": "regex_contains", "match_all": true}, {"key": "selector", "operand": "punctuation.definition.string.begin", "operator": "not_equal", "match_all": true}, {"key": "eol_selector", "operand": "string.quoted.double - punctuation.definition.string.end", "operator": "not_equal", "match_all": true}]
       insert_snippet                           CSS                   [{"key": "setting.auto_match_enabled", "operand": true, "operator": "equal"}, {"key": "selection_empty", "operand": true, "operator": "equal", "match_all": true}, {"key": "selector", "operand": "source.css - string", "operator": "equal", "match_all": true}, {"key": "following_text", "operand": "^(?:\t| |\\)|]|\\}|>|,|;|$)", "operator": "regex_contains", "match_all": true}, {"key": "preceding_text", "operand": "[\"a-zA-Z0-9_]$", "operator": "not_regex_contains", "match_all": true}, {"key": "eol_selector", "operand": "string.quoted.double - punctuation.definition.string.end", "operator": "not_equal", "match_all": true}]
       insert_snippet                           JSON                  [{"key": "setting.auto_match_enabled"}, {"key": "selector", "operand": "source.json"}, {"key": "selection_empty", "match_all": true}, {"key": "preceding_text", "operand": "[\"\\w]$", "operator": "not_regex_contains", "match_all": true}, {"key": "following_text", "operand": "^(?:\t| |]|,|:|\\}|$)", "operator": "regex_contains", "match_all": true}]
       insert_snippet                           Java                  [{"key": "setting.auto_match_enabled", "operand": true, "operator": "equal"}, {"key": "selection_empty", "operand": true, "operator": "equal", "match_all": true}, {"key": "selector", "operand": "source.java - string", "operator": "equal", "match_all": true}, {"key": "following_text", "operand": "^(?:\t| |\\)|]|\\}|>|,|:|;|\\+|$)", "operator": "regex_contains", "match_all": true}, {"key": "preceding_text", "operand": "[\"a-zA-Z0-9_]$", "operator": "not_regex_contains", "match_all": true}, {"key": "eol_selector", "operand": "string.quoted.double - punctuation.definition.string.end", "operator": "not_equal", "match_all": true}]
       lsp_json_auto_complete                   LSP-json              [{"key": "setting.auto_match_enabled", "operand": true, "operator": "equal"}, {"key": "selection_empty", "operand": true, "operator": "equal", "match_all": true}, {"key": "following_text", "operand": "^(?:\t| |\\)|]|\\}|>|$)", "operator": "regex_contains", "match_all": true}, {"key": "preceding_text", "operand": "[\"a-zA-Z0-9_]$", "operator": "not_regex_contains", "match_all": true}, {"key": "eol_selector", "operand": "string.quoted.double - punctuation.definition.string.end", "operator": "not_equal", "match_all": true}, {"key": "selector", "operand": "source.json", "operator": "equal", "match_all": true}]
       insert                                   Python                [{"key": "setting.auto_match_enabled"}, {"key": "selector", "operand": "source.python - string.quoted.double"}, {"key": "selection_empty", "match_all": true}]
       insert_snippet                           Python                [{"key": "setting.auto_match_enabled"}, {"key": "selector", "operand": "source.python - string.quoted.double"}, {"key": "selection_empty", "match_all": true}, {"key": "preceding_text", "operand": "(?i:^|[^\"\\w\\\\]|\\b[bfru]+)$", "operator": "regex_contains", "match_all": true}, {"key": "following_text", "operand": "^(?:\t| |\\)|]|\\}|\\.|,|:|;|$)", "operator": "regex_contains", "match_all": true}]
       insert_snippet                           Python                [{"key": "setting.auto_match_enabled"}, {"key": "selector", "operand": "source.python"}, {"key": "selection_empty", "operand": false, "match_all": true}]
       move                                     Python                [{"key": "setting.auto_match_enabled"}, {"key": "selector", "operand": "source.python"}, {"key": "selection_empty", "match_all": true}, {"key": "following_text", "operand": "^\"", "operator": "regex_contains", "match_all": true}, {"key": "selector", "operand": "punctuation.definition.string.begin", "operator": "not_equal", "match_all": true}, {"key": "eol_selector", "operand": "string.quoted.double - punctuation.definition.string.end", "operator": "not_equal", "match_all": true}]

Note that these are straight out of the Packages shipped with
Sublime |nbsp| Text.

These bindings are not, in fact, conflicted because they operate in
distinctly separate environments such that none of these bindings actually
interfere with any of the other bindings.  To state it another way:  there
is no overlap in their contexts.

What the ``FindKeyConflicts`` Package actually does then is report where there
are POTENTIAL conflicts (more than one binding for a keypress), and prints
the key bindings involved, leaving it to the reader to decipher if there
are really any problems.

Conclusion:  while interesting, the reports generated by
``FindKeyConflicts`` (based on a mere use of the same keypresses) are not very
likely to help users detect actual problems with key bindings.

.. note::

    It also goes to show how far a good Package name goes towards getting
    people to install a Package because, despite its lack of usefulness,
    1-3 users per week are installing it and keeping it on their systems,
    perhaps in hope some day it might be useful.


What Is a Key-Binding Conflict?
===============================

A key-binding conflict is when one key binding *unintentionally* overrides
another key binding that should be able to function, but cannot in some (or
all) contexts.  The trouble with this definition is that there is no way,
in software, to determine what was intentional and what was not.  If the
target of a report was just based on this, you would also get every place
where you had intentionally overridden key bindings in your local
environment.

This might not be a bad thing, but perhaps the more useful target to report
on is when a key binding OVERRIDES another in the same context.  Let us
consider some programmatically-detectable situations:

    1.  More than one binding exists for a keypress or keypress sequence.

    2.  Of bindings found in 1, more than one of them have "context" entry
        restrictions that are satisfied by a given editing context.

    3.  Of bindings found in 1, two or more have functionally-equivalent
        context definitions.

Note that to test 2, there are only 2 practical ways to specify what context
to test against (that this author can think of):

- use the context of an existing key binding, or
- use the editing context in the current View.

In both cases, two bindings for the same keypress that would both be selected
in the specified context could be quite interesting, and potentially be
unintended.

Also note that 1 and 2 by themselves do not necessarily indicate
a "problem", since partially-overlapping contexts does not mean the key
bindings earlier in the list (the one(s) that did not get selected)
would not function correctly in other contexts.  This could be caused by
an intentional override for one or more contexts that are more specific
than the binding earlier in the list.  In that same light, 1 and 3
could also be caused by an intentional override.

So the more useful Key-Binding Conflict Reports involve:

- conditions 1 and 2 for the current context,
- conditions 1 and 2 for the context of a specified key binding, or
- 1 and 3 (which, as a side effect would mean 2 is also true and would
  produce a report with a slightly narrower list than the combination of
  1 and 2).


Details
-------

Note that "functionally equivalent" also includes when 2 bindings for the
same keypress have NO "context" entries in their key-binding definition
(i.e. no restrictions on where they will be applied).

Detecting 3 is not trivial given that all of the following context
conditions function identically since they specify default values, which is
quite common in key-binding definitions:

.. code-block:: json

    { "key": "setting.auto_match_enabled", "operator": "equal", "operand": true }
    { "key": "setting.auto_match_enabled", "operator": "equal" }
    { "key": "setting.auto_match_enabled", "operand": true }
    { "key": "setting.auto_match_enabled", "match_all": false }
    { "key": "setting.auto_match_enabled" }

Thus the default values for "operator", "operand" and "match_all" would
have to be taken into account.

Adding to the complexity is that the conditions in a complex context
definition can be in a different order and still be functionally
equivalent.


Single- vs Multi-Keypress Bindings
==================================

This is one area where ``FindKeyConflicts`` does report something useful:  when
there are both single- and multi-keypress key bindings with the same
leading keypress.  Fortunately, this is easy to test for, and would, in
many cases, be unintentional.

However, Sublime |nbsp| Text mitigates this by doing something constructive
when this situation occurs.  In fact, there is such an example in the
`sublime-rst-completion` Package:  "ctrl+t" is used as a leading keypress
in 7 multi-keypress bindings, whereas Sublime |nbsp| Text Default Package
binds "ctrl+t" alone to the "transpose" command (swaps 2 characters on
either side of the selection).

Interestingly, this actually does not create a problem.  Here is why.  In
the environment where the multi-keypress bindings apply that use "ctrl+t"
as the leading keypress, simply repeating the keypress again causes
Sublime |nbsp| Text to discover:

- that there is not binding for ``["ctrl+t", "ctrl+t"]``, and
- there is a single-keypress binding for ``["ctrl+t"]``,

in which case it applies the latter.  So the user is only burdened with one
more keypress to make use of the single-keypress binding while editing ``.rst``
files.  Since the Package provided no binding for ``["ctrl+t", "ctrl+t"]``,
it did not in fact "mask" the binding for ``["ctrl+t"]``!

So the best that can be done in this case is report it as a POTENTIAL
conflict, to make the user aware of it, and show the bindings in
human-readable form and let the user decide if it is a problem or not.


Detecting Potentially-Conflicting Key Bindings
==============================================

Considering all of the above, now we can define a more useful way to detect
POTENTIAL key-binding conflicts:  to be potentially conflicting, 2 key
bindings must:

- involve the same keypress or keypress sequence, i.e.
  ``self.keypress_tuple() == other.keypress_tuple()``

  and

- have equivalent context conditions (which includes both having no context
  conditions).


User Experience Considerations
==============================

Upon invoking the report, the user gets a choice between:

- show key bindings where there are multiple bindings that use the
  same keypresses AND also have functionally-equivalent contexts.
- use current context,
- choose a specific existing key binding (more complex to implement,
  probably not part of v1.0),

Also, to be useful at all (since the reader must still grok the contexts),
the reported key bindings involved would need to have their contexts printed
in a form that would be easy for a human to quickly digest and thus tell
if there was an UNINTENDED override or not.


Detecting the Problem Presented in the Overview
===============================================

What would it take to detect the key-binding conflict discovered in the Python
Package?

.. todo:: fill in, and preferably ensure the KeyBindingReport Package
          has such a report, and prove it with THE actual example.

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

_cfg_report_title = 'Partial and Full Key-Binding Overrides in the Current Context'



# *************************************************************************
# Constants
# *************************************************************************



# *************************************************************************
# Classes
# *************************************************************************

class KeyBindingReportContextOverridesCommand(sublime_plugin.TextCommand):
    """ Report Key Bindings that override other key bindings. """
    def _heading(self, title: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        parts = ['']
        parts.append(title)
        parts.append('*' * len(title))
        parts.append('')
        parts.append('Bindings lower in each override bindings higher in the list.')
        parts.append('')
        parts.append(f'Report generated:  {timestamp}')

        return '\n'.join(parts)

    def run(self, edit):
        """
        Report Key Bindings that override other key bindings.
        """
        debugging = is_debugging(DebugBits.CONTEXT_OVERRIDES_REPORT)
        if debugging:
            print('>\n>\n>\n>')
            print('In KeyBindingReportContextOverridesCommand.run()...')

        t0 = datetime.now()
        key_data = data.KeyBindingData()
        # Generate ALL overrides minus bindings that
        # do not match current context.
        override_list = key_data.binding_overrides(self.view)
        # binding = key_data.which_binding(keypress_list, self.view)
        # keypress_list_json = json.dumps(keypress_list)
        # t1 = datetime.now()

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
