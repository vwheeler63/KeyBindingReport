# KeyBindingReport

**KeyBindingReport** is a Sublime Text package that builds a beautiful `.rst` document that shows how most of the keyboard keys are mapped and where.

The concept is to programmatically re-generate the source file that generates this [Default Key Bindings](http://crystal-clear-research.com/docs/quickrefs/sublime_text/default_key_bindings.html) web page.

Before this was developed, the author built the original source document by hand using ``grep`` on the `<install_path>/Packages/Default ($platform).sublime-keymap` Keymap in order to isolate all the different bindings to individual keys on the keyboard, since this is the way the author thinks about it when planning on where keys should be mapped for an application -- in this case Sublime Text.

Needless to say, all doing justice to just one lengthy `.sublime-keymap` file took almost an entire day to document, and since then, the author has come to the conclusion that this task could be better served programmatically, especially since Sublime Text as well as Package updates happen periodically.


## Original Set of Columns

:Key:      key name
:S:        shift-key modifier
:C:        control-key modifier
:A:        alt-key modifier
:Command:  Sublime Text Command with some English clarifications in parentheses

![F-Key Table from Original Document](docs/src/_static/images/orig_doc_f-key_table.png "F-Key Table from Original Document")

Exceptional or complex Contexts were handled by placing a footnote link next to the Command and describing the Context details (in clear English) in the footnote.


![Symbol-Key Table from Original Document](docs/src/_static/images/orig_doc_symbol-key_table.png "Symbol-Key Table from Original Document")


But there are many more variables at work, and in some cases, those variables can be important, and deserve their own column.  They are:

- English comments in Command column should have their own "Comments" column,
- Package name containing Key Binding,
- possibly the `.sublime-keymap` filename containing the Key Binding, though all Packages I am aware of only have 1 (either `Default....` or `Default ($platform)....`).

It might also be useful to have the Context syntax from the Key Binding object translated into clear English for most cases.
