# KeyBindingReport

**KeyBindingReport** is a Sublime Text Package that produces a wide variety of reports about the current state of Sublime Text key bindings on the system it is running on, with a choice of output formats.



## What You Can Do, and the Reports that Support It

- Find out what key conflicts that are in your installation that you didn't already know about.

  - Pre-Built Reports that Do This:

    - Key-Binding Overrides
    - Key-Binding Overrides (in Current Context)

- Find out what key combinations are available for your Plugin or other Sublime Text customization(s).
  - Pre-Built Reports that Do This:

    - <key group> for All Installed Packages
      (There are 7 key groups: numbers, letters, function keys, symbols, named keys, keypad keys, and key sequences [e.g. "ctrl+k", "ctrl+u"].)
    - All Key Combinations for All Installed Packages
    - All Key Combinations for All Installed Packages (Separate Tables)
      (Tables are separated by key groups.)

- Find out what key binding Sublime Text is choosing for a given key combination in a given editing context. Editing contexts can also include when the caret is in a Panel (e.g. one of the Find Panels, Console Panel, etc.) or in an Overlay (e.g. Command Palette, Input Overlay, etc.).

  - Pre-Built Reports that Do This:

    - Which Binding? Report

- Find out the names of all keys (including modifier keys) that currently having bindings in your Sublime Text installation, including how many times each key was used in a binding.

  - Pre-Built Reports that Do This:

    - Keys Used Report (Current Platform)

- Find out all key combinations that have no key bindings.

  - Pre-Built Reports that Do This:

    - Keys Available Report (Current Platform)

- If you're not already an expert at interpreting key binding "context" entries, the natural-language descriptions of key-binding "context" entries can speed your understanding of what they mean.

- Each report is headed by its specification so you can see what arguments generated it.  This is helpful for running your own custom versions of each report to focus on your specific needs.

- Run custom versions of each report from your own Plugins.  You can:

  - focus on specific key groups (`key_groups` argument);
  - focus on specific keys (`key_names` argument);
  - focus on specific key combinations (`keypress_list` argument);
  - limit search to a specified list of Packages (`limit_to_packages` argument);
  - limit search to take current editing context into account;
  - specify the output format you want from a list of 4 formats;
  - include or exclude columns in the report;
  - include or exclude pieces of information in the report, including raw (untranslated) and natural-language context descriptions;
  - simulate being on other platforms (e.g. testing OSX key bindings from a Windows system);
  - optionally send reports to text files (configurable).



## Overview

All reports that come with this Package are accessible through the Command Palette and begin with "KeyBindingReport: ...".  The menu option

```
  Tools > KeyBindingReport > All KeyBindingReport Commands
```
takes you to the Command Palette with that prefix already entered, filtering the list to just those Commands.

Also, most pre-built reports are available via menu:
```
  Tools > KeyBindingReport > <format> > <pkg filter> > ...

  or

  Tools > KeyBindingReport > Other Reports > ...
```



## Reports Available

As of this writing, there are 59 pre-built reports that this package can generate, plus an unlimited number of reports that can be created using custom calls to the "key_binding_report" Command (or the other commands), which you run from the Command Palette, or:

- bind to any available key combination,
- calling `view.run_command("key_binding_report", custom_args)` (or any of the other commands) from a Plugin,
- run via any other way Commands can be run in Sublime Text (menu, mouse binding, Command Palette, Plugins), or
- run by creating your own custom version of `KeyBindingReport/resources/commands/KeyBindingReport.sublime-commands` in an Override Package.



## Simple Reports

- **KeyBindingReport: Keys Used Report (Current Platform)**, generates Key-Binding Keys-Used Report, which lists:

  - Modifier Keys Used with how many times each;
  - Main Keys Used with how many times each;
  - Other Keys (with unexpected key names, if any, with how many times each).

  Optional argument (if you call it from your own Plugin):

    platform_code: "windows", "linux" or "osx" to simulate the specified platform.

- **KeyBindingReport: Keys Available Report (Current Platform)**, generates a report of showing ONLY keypresses (key combinations) that have no associated key bindings, considering all installed Packages.  It is the equivalent of doing this from your own Plugin:

  ```py
        # Note:  passing "key_groups": [data.KeyGroup.ALL] does not work
        # because that causes multi-keypress bindings to be included as well,
        # and that domain is not relevant to the "Keys Available Report".
        key_group_list = [
            data.KeyGroup.NUMBER_KEYS,
            data.KeyGroup.LETTER_KEYS,
            data.KeyGroup.F_KEYS,
            data.KeyGroup.SYMBOL_KEYS,
            data.KeyGroup.NAMED_KEYS,
            data.KeyGroup.KEYPAD_KEYS
        ]

        flags = (
                  output.FlagBits.INCLUDE_UNBOUND_KEYPRESSES_ONLY
                | output.FlagBits.INCLUDE_WINDOWS_KEY
                )

        args = {
            "key_groups"       : key_group_list,
            "fmt"              : ascii_table.Format.OUTLINED,
            "flags"            : flags
        }

        self.view.run_command('key_binding_report', args)
  ```

- **KeyBindingReport: Which Binding?**, generates a Key-Binding Report for a specified keypress or keypress sequence, based on the context in current View.  This command may be run when keyboard focus is in any View, including input Views in any Panels (e.g. Find) or Overlays (e.g. Command Palette).

- **KeyBindingReport: Key-Binding Overrides**, reports Key Bindings that, considering their "context" entries, override other key bindings, considering all shipped, installed and custom Packages present on your system.

- **KeyBindingReport: Key-Binding Overrides (in Current Context)**, is the same as the above, with the addition that the current context in the current View is also taken into account.  Bindings are excluded whose "context" entries do not match the current editing context.



## KeyBindingReport: The Main Report

This report is implemented via the **KeyBindingReportCommand** (key_binding_report) Command.  While it is the most complex report to call in this Package, it is simultaneously the most powerful.  54 of the built-in reports shipped with this Package call this command with different arguments.

This command reports about current key bindings present in your Sublime Text installation.  The report may include:

- a specified list of key groups (e.g. F_KEYS, see below for full list),
- a specified list of key names,
- a specified list of specific keypresses (key combinations),

and may be limited to:

- a specified list of Packages,

or any combination of the above.

The report may also exclude key bindings that do not match the current editing context.

Also specifiable:

- optional output format, default: OUTLINED
- optional `flags` to specify information and columns to include, and
- an optional name for an alternate platform to report on:  e.g. "windows", "linux", or "osx".



### Report Columns

#### Columns Always Included

- Key:  main key name
- ⌘ Command key (always included on OSX platform, optional as [⊞] key by flag on Windows and Linux)
- Alt-key modifier ([⌥ Option] key on OSX platform)
- Ctrl-key modifier
- Shift-key modifier
- Context:  A footnote reference for details when the key binding contains a "context" entry
- Command:  name of the Sublime Text Command bound to that keypress or keypress sequence
- Args:  Optional arguments passed to the Command

#### Optional Columns Available via `flags` Argument

- Source (Package and filename of `.sublime-keymap` file the binding came from)
- Comments (useful if you intend to copy the report into a document and/or print it, adding your own comments for any purpose).  The default width of this column is configurable.



### Overview of How to Use Command's Arguments

Have a look at this table to get the "gist" of how you can vary the arguments you pass to the command to generate different report content.  (The default for all of these arguments is `None` so if the report is run without passing any of these, the report will be empty.)

Description | packages | key_groups | key_names | keypress_list
----------- | :------: | :--------: | :-------: | :-----------:
By Package: output all key bindings contained in Package (e.g. Default or a 3rd-party Package) | `["pkgname"]` | `None` | `None` | `None`
By specified keys limited to a Package:  output all of key's binding(s) | `["pkgname"]` | `None` | `["a", ...]` | `None`
By specified keys: output bindings for those keys in all Packages that contain bindings for those keys | `None` | `None` | `["a", ...]` | `None`
By specified KeyGroup using bindings from all Packages | `None` | `[F_KEYS, ...]` | `None` | `None`
By specified KeyGroup limited to a Package | `["pkgname"]` | `[F_KEYS, ...]` | `None` | `None`
By specified `keypress_list` for all Packages | `None` | `None` | `None` | `[["ctrl+u"], ["ctrl+f"]]`



### `key_groups` Argument

Passing a value for this argument means to include those key groups in the report.  Example:  `[2,3]`.

#### Available Key Groups

The value for the `key_groups` argument is optional, and can be a possibly empty list of integers from the `KeyGroup` enumeration.  Keys from the specified groups will be added to the data gathered.  ``[KeyGroup.ALL]`` is equivalent to specifying all the other key groups.  Pass ``None`` or ``[]`` when not applicable.  Default:  ``None``.

    NUMBER_KEYS    =  0
    LETTER_KEYS    =  1
    F_KEYS         =  2
    SYMBOL_KEYS    =  3
    NAMED_KEYS     =  4
    KEYPAD_KEYS    =  5
    KEY_SEQUENCES  =  6  # Multiple-keypress sequences, e.g. ["ctrl+k", "ctrl+u"]
    ALL            =  7  # Equivalent to specifying all groups, e.g. [0,1,2,3,4,5,6]



### `key_names` Argument

Optional:  list of individual key names, e.g. ["space", "tab", "enter", "a", "b"].  Each key in this list will be included in the data gathered, including all possible key-modifier combinations with these keys.  Each key only has an impact on data gathered if it is found in `data.all_key_names` (which is a programmatically assembled list of all key names in `data.key_name_groups`).  `None` or `[]` when not applicable.  Default:  `None`.



### `keypress_list` Argument

Optional:  list of lists of "keypresses".  The inner lists have the same format as "keys" entries from JSON key bindings, and typically include modifier keys.  Example: `[["ctrl+k", "ctrl+u"], ["ctrl+shift+p"]]`.  Passing this argument means:  include specified keypress/keypress sequences in report.  `None` or `[]` when not applicable.  Default:  `None`.



### `limit_to_packages` Argument

Optional:  case-sensitive list of package names that the gathered key-binding data should be limited to, e.g. `["Default", "User"]`.  `None` or `[]` means to gather data from all installed packages.  Default: `None`.



### `limit_to_context` Argument

Optional (Boolean):  Default: `false`.  Passing `True` for this argument means:  exclude key bindings whose "context" entries do not match the current editing context in the View that was active when the `key_binding_report` command was run.  The active View can be any View, including input and output views that are involved in Panels (e.g. one of the Find Panels, Console Panel, etc.) as well as Overlays (e.g. Command Palette, Input Overlay, etc.).



### `fmt` Argument

Pass an integer for the `fmt` argument when you want to specify the output format for the report.  Example:  `0`.  Default:  `1`.

#### Available Output Formats

The output format must be an integer having one of these values:

- BARE = 0
- OUTLINED = 1
- OUTLINED_COLUMNS = 2
- RESTRUCTUREDTEXT = 3



### `flags` Argument:  What to Show in the Report

The following are among bits you can OR together to specify what to include in the report.  These bits can be combined in any combination.

- `INCLUDE_UNBOUND_KEYPRESSES` (0x0001):  include unbound key combinations (useful if you're looking for unbound key combinations you can use to bind to Commands of your choosing).
- `INCLUDE_UNBOUND_KEYPRESSES_ONLY` (0x0002):  include unbound key combinations, and *do not include* bound key combinations.
- `INCLUDE_UNTRANSLATED_CONTEXTS` (0x0004):  include the raw (untranslated) contexts with each binding that has a "context" entry (formatted so they are nicely readable).
- `INCLUDE_NATURAL_LANGUAGE_CONTEXTS` (0x0008):  include a natural-language translation of contexts with each binding that has a "context" entry (English is currently the only supported language).
- `ADD_SOURCE_COLUMN` (0x0010):  include each key binding's source (i.e. Package + `.sublime-keymap` filename the binding came from).
- `ADD_COMMENTS_COLUMN` (0x0020):  include a comments column of the configured width (useful if you intend to copy the report into a document and manually edit it by adding comments for a purpose of your choosing, or print the report and hand-write comments in the comments column).
- `TABLE_KEY_AFTER_TABLE` (0x0040):  include the Table Key *after* the table instead of *before* it (the default, see note below).
- `INCLUDE_WINDOWS_KEY` (0x0080):  include the [⊞] (Windows) key for Windows and Linux platforms (the [⌘ Command] key is always included on OSX because it is always heavily used).
- `SEPARATE_TABLES_BY_KEY_GROUPS` (0x0100):  whether to group keys by key group, generating 1 table and 1 set of footnotes for each key group (numbers, letters, function keys, symbol keys, named keys, keypad keys).
- `OUTPUT_TO_FILES` (0x0200):  whether to send output to a set of files in addition to a read-only report View(s) on the screen.  The destination directory is configurable for each platform.  The directory must already exist.  **Caution:** Same-named files within that directory are silently overwritten each time the Command is run, so using a directory *other than the live production versions of these files* is recommended.
- `ALL_PLATFORMS` (0x0400):  whether to include all platforms ("windows", "linux" and "osx") in the report.

Note:  the Table Key shows the meaning of abbreviated column names in the table.  It looks like this for the Windows platform when the Windows key is included in the report:

```
Key:
     W = ⊞ Windows
     A = Alt
     C = Ctrl
     S = Shift
  Ctxt = Context
```



### `platform_code` Argument

Pass a value for this argument when you want the report to be about a platform other than the one that is currently running.  Valid values:  "windows", "linux", or "osx" (all lower case).



### Example

This key binding

```jsx
  {
    "keys": ["super+f9"],
    "command": "key_binding_report",
    "args": {
      "limit_to_packages": ["Default"],
      "keypress_list": [["\""]],
      "fmt": 1,
      "flags":   13,  //   INCLUDE_UNBOUND_KEYPRESSES
                      // | INCLUDE_UNTRANSLATED_CONTEXTS
                      // | INCLUDE_NATURAL_LANGUAGE_CONTEXTS
    },
  },

````

generates this report:

```

***************************************************
KeyBindingReport:  Specified Key-Bindings (Windows)
***************************************************

As of   :  12-Jun-2026 15:33
Platform:  Windows

Note:
    Keypresses with empty Commands are not bound.

Specification:
    keypress_list     = [['"']]
    limit_to_packages = ['Default']
    limit_to_context  = False
    format            = <Format.OUTLINED: 1>
    flags             = 0x000D
      - INCLUDE_UNBOUND_KEYPRESSES       :  0x0001
      - INCLUDE_UNTRANSLATED_CONTEXTS    :  0x0004
      - INCLUDE_NATURAL_LANGUAGE_CONTEXTS:  0x0008



Single-Keypress Table
*********************

Key:
     A = Alt
     C = Ctrl
     S = Shift
  Ctxt = Context

+-------------------------------------------------------------------+
|Key A C S Ctxt Command        Args                                 |
| "        (1)  insert_snippet {"contents": "\"$0\""}               |
| "        (2)  insert_snippet {"contents": "\"${0:$SELECTION}\""}  |
| "        (3)  move           {"by": "characters", "forward": true}|
| "      x                                                          |
| "    x                                                            |
| "    x x                                                          |
| "  x                                                              |
| "  x   x                                                          |
| "  x x                                                            |
| "  x x x                                                          |
+-------------------------------------------------------------------+
```
```jsx
(1):
    "context": [
      { "key": "setting.auto_match_enabled" }
        // Is the View-setting [auto_match_enabled] == true?,
      { "key": "selection_empty"           , "match_all": true }
        // Is selection empty (for all selections)?,
      { "key": "following_text"            , "operator": "regex_contains"    , "operand": "^(?:\t| |\\)|]|\\}|>|$)", "match_all": true }
        // Does regex "^(?:\t| |\\)|]|\\}|>|$)" match any of the text between left edge of selection and EOL (for all selections)?,
      { "key": "preceding_text"            , "operator": "not_regex_contains", "operand": "[\"a-zA-Z0-9_]$", "match_all": true }
        // Does regex "[\"a-zA-Z0-9_]$" match none of the text between BOL and the left edge of selection (for all selections)?,
      { "key": "eol_selector"              , "operator": "not_equal"         , "operand": "string.quoted.double - punctuation.definition.string.end", "match_all": true }
        // Does selector [string.quoted.double - punctuation.definition.string.end] NOT match scope at EOL (for all selections)?
    ]
(2):
    "context": [
      { "key": "setting.auto_match_enabled" }
        // Is the View-setting [auto_match_enabled] == true?,
      { "key": "selection_empty"           , "operand": false, "match_all": true }
        // Is selection NOT empty (for all selections)?
    ]
(3):
    "context": [
      { "key": "setting.auto_match_enabled" }
        // Is the View-setting [auto_match_enabled] == true?,
      { "key": "selection_empty"           , "match_all": true }
        // Is selection empty (for all selections)?,
      { "key": "following_text"            , "operator": "regex_contains", "operand": "^\"", "match_all": true }
        // Does regex "^\"" match any of the text between left edge of selection and EOL (for all selections)?,
      { "key": "selector"                  , "operator": "not_equal"     , "operand": "punctuation.definition.string.begin", "match_all": true }
        // Does selector [punctuation.definition.string.begin] NOT match scope at selection (for all selections)?,
      { "key": "eol_selector"              , "operator": "not_equal"     , "operand": "string.quoted.double - punctuation.definition.string.end", "match_all": true }
        // Does selector [string.quoted.double - punctuation.definition.string.end] NOT match scope at EOL (for all selections)?
    ]
```



### See Also

See also:  `class KeyBindingReportCommand` in `KeyBindingReport/src/commands/report.py`.

