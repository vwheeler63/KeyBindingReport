# KeyBindingReport

**KeyBindingReport** is a Sublime Text Package that produces a wide variety of reports about the current state of Sublime Text key bindings on the system it is running on, with a choice of output formats.



## Reports Available

As of this writing, there are 59 reports that this package can generate, plus an unlimited number of reports that can be created using custom calls to the "key_binding_report_keys_available" command (or the other commands), which you can set up:

- via any available key binding,
- by calling `view.run_command("key_binding_report_keys_available", custom_args)` in any Plugin,
- by creating your own custom version of `KeyBindingReport/resources/commands/KeyBindingReport.sublime-command` in an Override Package,
- or any other way Commands can be run in Sublime Text.

All of the reports built into this with this package are accessed via the Command Palette and start with "KeyBindingReport:".

Additionally:

- you can open this file directly via `Preferences > Package Settings > KeyBindingReport > README`, and
- you can change the settings for this package via `Preferences > Package Settings > KeyBindingReport > Settings`.

The settings are documented individually in the default settings file.



### Simple Reports

- **KeyBindingReport: Keys Used Report (Current Platform)**, generates Key-Binding Keys-Used Report:

  Modifier Keys Used with how many times each.
  Main Keys Used with how many times each.

  Optional argument (if you call it from your own Plugin):

  platform_code:  "windows", "linux" or "osx" to simulate the specified platform.

- **KeyBindingReport: Keys Available Report (Current Platform)**, generates report of which generates a large table showing ONLY keypresses (key combinations) that do not have any key bindings associated with them, considering all installed Packages.  It is the equivalent of doing this from your own Plugin:

  ```py
        flags = (
                  output.FlagBits.INCLUDE_UNBOUND_KEYPRESSES_ONLY
                | output.FlagBits.INCLUDE_WINDOWS_KEY
                )

        # Note:  passing "key_groups": [data.KeyGroup.ALL] does not work
        # because that causes multi-keypress bindings to be included as well,
        # and that domain is not relevant to the "Keys Available Report".
        key_group_list = []
        for i in range(data.KeyGroup.FIRST, data.KeyGroup.LAST + 1):
            key_group_list.append(i)

        args = {
            "key_groups"       : key_group_list,
            "fmt"              : ascii_table.Format.OUTLINED,
            "flags"            : flags
        }

        self.view.run_command('key_binding_report', args)

  ```

- **KeyBindingReport: Which Binding?**, generates a Key-Binding Report for a specified keypress or keypress sequence, based on the context in current View.  This command may be run when keyboard focus is in any View, including input Views in any Panels (e.g. Find) or Overlays (e.g. Command Palette).  (For release v1.0 you will need to run this command yourself and pass the desired keypresses to inspect in its `keypress_list` argument, and optionally which platform to simulate in its optional `platform_code` argument.  The command for this included with this package shows an example of calling this Command with no arguments, which uses the default keypress list:  `["ctrl+k", "ctrl+u"]`.)

- **KeyBindingReport: Key-Binding Overrides**, reports Key Bindings that, considering their "context" entries, override other key bindings, considering all shipped, installed and custom Packages present on the current system.

- **KeyBindingReport: Key-Binding Overrides in Current Context**, is the same as the above, with the addition that the current context in the current View is also taken into consideration.



### KeyBindingReport: The Main Report

This report is implemented via the **KeyBindingReportCommand** (key_binding_report) Command.  While it is the most complex report to call in this Package, it is simultaneously the most powerful.  54 of the built-in reports shipped with this Package call this command with different arguments.

This command reports about current key bindings present in your Sublime Text installation.  The report may be limited to:

- a specified list of key names,
- a specified list of key groups (e.g. F_KEYS, see below for full list),
- a specified list of specific keypresses (key combinations),
- a specified list of Packages, or
- any combination of the above.

The arguments passed to the command also allow options for output format, what to include in the report, and what OTHER platform to simulate, if any.



#### Available Output Formats

The output format must be an integer having one of these values:

- BARE = 0
- OUTLINED = 1
- OUTLINED_COLUMNS = 2
- RESTRUCTUREDTEXT = 3



#### What to Show in the Report

The following are among options you can select from to include in the report, and these options can be combined in any number of ways.  Each is a flag bit in a `flags` argument.

- include unbound key combinations (useful if you're looking for unbound key combinations you can use to bind to Commands of your choosing);
- whether to include the raw (untranslated) contexts with each binding that has a "context" entry (formatted so they are nicely readable);
- whether to include a natural-language translation of the contexts with each binding that has a "context" entry (English is currently the only supported language);
- the key binding's source (i.e. Package and filename the binding came from);
- whether to include a comments column (useful if you intend to copy the report into a document and manually edit it by adding comments for a purpose of your choosing, or print the report and hand-write comments in the comments column);
- whether to include the [⊞] (Windows) key for Windows and Linux platforms (the [⌘ Command] key is always included on OSX because it is always heavily used);
- whether to include the Table Key *after* the table instead of *before* (the default, see note below);
- whether to group keys by key group, generating 1 table and 1 set of footnotes for each key group (numbers, letters, function keys, symbol keys, named keys, keypad keys);
- whether to send output to a set of files in addition to a read-only report View on the screen (destination directory is configurable for each platform via Package settings.  The directory must already exist.  **Caution:** Same-named files within that directory are silently overwritten with each call to the command, so starting with an empty directory is recommended);
- whether to include all platforms in the report.

Note:  the Table Key shows the meaning of abbreviated column names in the table.  It looks like this for the Windows platform when the Windows key is included in the report:

```
Key:
     W = ⊞ Windows
     A = Alt
     C = Ctrl
     S = Shift
  Ctxt = Context
```


### Columns Always Included

- Key:  main key name
- C:  command key (always included on OSX platform, optional as [⊞] key by flag on Windows and Linux)
- A:  alt-key modifier ([⌥ Option] key on OSX platform)
- C:  control-key modifier
- S:  shift-key modifier
- Context:  A footnote reference for details when the key binding contains a "context" entry
- Command:  Sublime Text Command bound to that keypress or keypress sequence
- Args:  Optional arguments passed to the command


### Optional Columns Available via Flags Argument

- Source (Package and filename of keymap file the binding came from)
- Comments (useful if you intend to copy the report into a document and/or print it, adding your own comments for a purpose of your choosing)



## Running **KeyBindingReportCommand** on Your Own

See `class KeyBindingReportCommand` in `KeyBindingReport/src/commands/report.py`.  Each argument is documented in detail there.

Have a look at this table to get the "gist" of how you can vary the arguments you pass to the command to generate different report content.  (The default for all of these arguments is `None` so if the report is run without passing any of these, the report will be empty.)

```
+-------------------------------+-----------+-------------+----------+------------------------+
| Description                   |packages   |key_groups   |key_names | keypress_list          |
+===============================+===========+=============+==========+========================+
| By Package:  output all key   |["pkgname"]|    None     |   None   |    None                |
| bindings contained in Package |           |             |          |                        |
| (e.g. Default or a 3rd-party  |           |             |          |                        |
| Package)                      |           |             |          |                        |
+-------------------------------+-----------+-------------+----------+------------------------+
| By specified key limited      |["pkgname"]|    None     |["a", ...]|    None                |
| to a Package:  output all     |           |             |          |                        |
| of key's binding(s)           |           |             |          |                        |
+-------------------------------+-----------+-------------+----------+------------------------+
| By specified key:  output     |   None    |    None     |["a", ...]|    None                |
| that key's bindings in all    |           |             |          |                        |
| Packages that contain         |           |             |          |                        |
| bindings for that key         |           |             |          |                        |
+-------------------------------+-----------+-------------+----------+------------------------+
| By specified ``KeyGroup``     |   None    |[F_KEYS, ...]|   None   |    None                |
| using bindings from all       |           |             |          |                        |
| Packages.                     |           |             |          |                        |
+-------------------------------+-----------+-------------+----------+------------------------+
| By specified ``KeyGroup``     |["pkgname"]|[F_KEYS, ...]|   None   |    None                |
| limited to a Package.         |           |             |          |                        |
+-------------------------------+-----------+-------------+----------+------------------------+
| By specified ``keypress_list``|   None    |    None     |   None   |[["ctrl+u"], ["ctrl+p"]]|
| for all Packages.             |           |             |          |                        |
+-------------------------------+-----------+-------------+----------+------------------------+
```