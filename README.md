# KeyBindingReport

**KeyBindingReport** is a Sublime Text Package that produces reports about the current state of Sublime Text key bindings, using any of a number of output formats.



## KeyBindingReport: Generate Report

This command reports about current key bindings present in your Sublime Text installation.  The report may be limited to:

- a specified list of key names,
- a specified list of key groups (e.g. F_KEYS, see below for full list),
- a specified list of Packages, or
- combinations of the above

and allows an option for output format and whether to show:

- unbound key combinations (useful if you're looking for unbound key combinations you can use)
- the Package name for each binding
- a comments column (useful if you intend to copy the report into a document and manually edit it by adding comments)
- untranslated contexts (conditions which limit when that key binding is chosen)
- those same contexts translated into English



## KeyBindingReport: Which Binding?

This command reports on the key bindings that Sublime Text would select given the current scope of the current View for a specified list of keypresses and/or keypress sequences.

This command allows you to input (or pass it) a list of key combinations, such as

  [["ctrl+p"]]
  [["ctrl+k", "ctrl+b"], ["ctrl+k", "ctrl+u"]]
  [["ctrl+p"], ["ctrl+shift+p"]]

and for each keypress/keypress-sequence in the list, it will do a search the same way Sublime Text does when you hit keys, and the report will include:

- details about the specific key binding was selected for each keypress/keypress-sequence given the current scope in the current View;

- which Package contained each key binding.



## Output Formats

All output formats are in the form of an ASCII table.  The current formats supported are:

- Bare
- Outlined (box around report with lines between columns)
- reStructuredText[^1]

[^1]: The concept is to programmatically re-generate the tables that live in the source file that generates this [Default Key Bindings](http://crystal-clear-research.com/docs/quickrefs/sublime_text/default_key_bindings.html) web page.

Before this was developed, the author built the original source document by hand using ``grep`` on the `<install_path>/Packages/Default ($platform).sublime-keymap` Keymap in order to isolate all the different bindings to individual keys on the keyboard, since this is the way the author thinks about it when planning on where keys should be mapped for an application---in this case Sublime Text.

Needless to say, all doing justice to just one lengthy `.sublime-keymap` file took almost an entire day to document, and since then, the author has come to the conclusion that this task could be better served programmatically, especially since Sublime Text as well as Package updates happen periodically, which can silently modify the current set of key bindings.



## Columns that Are Always Included

:Key:      key name
:S:        shift-key modifier
:C:        control-key modifier
:A:        alt-key modifier
:Command:  Sublime Text Command with some English clarifications in parentheses

![F-Key Table from Original Document](docs/src/_static/images/orig_doc_f-key_table.png "F-Key Table from Original Document")

Each `Command` has a footnote link when there is a key binding has a limiting context, and the footnote describes the possibly-complex condition that that context defines.

![Symbol-Key Table from Original Document](docs/src/_static/images/orig_doc_symbol-key_table.png "Symbol-Key Table from Original Document")



## Optional Additional Details

You can optionally, through a flags keyword argument, cause the report to additionally include:

- Package name containing each key binding,
- a "Comments" column (for possible manual editing later after moving the report into a document of some type),
- footnotes choices:

  - none (no mention of key contexts [conditions which restrict when Sublime Text chooses a particular key binding]),
  - untranslated key-binding contexts,
  - English translations of key-binding contexts (more readable),
  - both.
