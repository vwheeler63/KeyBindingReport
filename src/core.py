r"""***********************************************************************
KeyBindingReport
****************

This module provides package utilities and event catching, such as:

- response to plugin_loaded(),
- response to plugin_unloaded(),
- Package settings + response to when those settings change,
"""

from datetime import datetime
import sublime
# Importing ``IntFlag`` in the below is to remain compatible with Python 3.8,
# which requires it.  Python 3.14 does not.
from ..lib.debug import IntFlag, DebugBits, is_debugging, set_debugging_bits  # noqa: F401
from ..keybindingreport import package_name
from . import platform
from . import output



# *************************************************************************
# Configuration
# *************************************************************************

# Use name of parent directory as `package_name`.
_cfg_pkg_settings_file                       = package_name + '.sublime-settings'

# Track on-settings-changed listener.
_cfg_on_settings_chgd_listener_id            = '_kbr_settings_changed_tag'

# Package Settings Names (most are used multiple times throughout this Plugin)
_cfg_stg_name__output_directory_for_windows  = 'output_directory_for_windows'
_cfg_stg_name__output_directory_for_linux    = 'output_directory_for_linux'
_cfg_stg_name__output_directory_for_osx      = 'output_directory_for_osx'
_cfg_stg_name__default_comments_column_width = 'default_comments_column_width'
_cfg_stg_name__rst_table_container_class     = 'rst_table_container_class'
_cfg_stg_name__timestamp_strftime_format     = 'timestamp_strftime_format'
_cfg_stg_name__debugging                     = 'debugging'



# *************************************************************************
# Package Settings
# *************************************************************************

def kbr_setting(setting_name: str):
    """
    Get a setting from a cached settings object.
    This function expects the following objects to already exist:

    - ``kbr_setting.obj``      a ``sublime.Settings`` object (looks like a dictionary)
    - ``kbr_setting.default``  a dictionary object with named default values

    :param setting_name:  name of setting whose value will be returned
    """
    if not hasattr(kbr_setting, 'default') or kbr_setting.default is None:
        raise AssertionError('`kbr_setting.default` must exist before calling `kbr_setting()`.')
    if not hasattr(kbr_setting, 'obj') or kbr_setting.obj is None:
        raise AssertionError('`kbr_setting.obj` must exist before calling `kbr_setting()`.')
    default = kbr_setting.default.get(setting_name, None)
    return kbr_setting.obj.get(setting_name, default)



# *************************************************************************
# Load default settings once.
# *************************************************************************

kbr_setting.default = {
    _cfg_stg_name__output_directory_for_windows : "",
    _cfg_stg_name__output_directory_for_linux   : "",
    _cfg_stg_name__output_directory_for_osx     : "",
    _cfg_stg_name__default_comments_column_width: 35,
    _cfg_stg_name__rst_table_container_class    : "",
    _cfg_stg_name__timestamp_strftime_format    : "%Y-%m-%d %H:%M",
    _cfg_stg_name__debugging                    : False,
}

setting__output_directory_for_windows  = kbr_setting.default[_cfg_stg_name__output_directory_for_windows]
setting__output_directory_for_linux    = kbr_setting.default[_cfg_stg_name__output_directory_for_linux]
setting__output_directory_for_osx      = kbr_setting.default[_cfg_stg_name__output_directory_for_osx]
setting__default_comments_column_width = kbr_setting.default[_cfg_stg_name__default_comments_column_width]
setting__rst_table_container_class     = kbr_setting.default[_cfg_stg_name__rst_table_container_class]
setting__timestamp_strftime_format     = kbr_setting.default[_cfg_stg_name__timestamp_strftime_format]
setting__debugging                     = kbr_setting.default[_cfg_stg_name__debugging]


def show_settings():
    print(f'{setting__output_directory_for_windows  = }')
    print(f'{setting__output_directory_for_linux    = }')
    print(f'{setting__output_directory_for_osx      = }')
    print(f'{setting__default_comments_column_width = }')
    print(f'{setting__rst_table_container_class     = }')
    print(f'{setting__timestamp_strftime_format     = }')
    print(f'{setting__debugging                     = }')



# *************************************************************************
# Utilities
# *************************************************************************

def timestamp() -> str:
    """ Universal timestamp; used in some Package debug output. """
    now = datetime.now()
    fmt = kbr_setting(_cfg_stg_name__timestamp_strftime_format)
    return now.strftime(fmt)


def arg_type_error_message(arg, arg_name: str, required_type: str, after_matter: str = ''):
    c = required_type[0]
    article = 'a'
    if c in 'aeiou':
        article = 'an'

    return f'`{arg_name}` arg must be {article} {required_type}. Got {type(arg)} instead.{after_matter}'



# *************************************************************************
# Events
# *************************************************************************

def _on_pkg_settings_chgd():
    """
    Take action after Package settings have changed.
    """
    # Load overridable Package settings.
    # `kbr_setting()` cannot be called until this is done, and
    # `is_debugging()` will return an incorrect value until this is done.
    kbr_setting.obj = sublime.load_settings(_cfg_pkg_settings_file)

    # Initialize debugging subsystem.
    bit_val = kbr_setting(_cfg_stg_name__debugging)
    set_debugging_bits(bit_val)
    debugging = is_debugging(DebugBits.SETTINGS_CHANGED_EVENT)
    if debugging:
        print('In _on_pkg_settings_chgd()')

    global setting__output_directory_for_windows
    global setting__output_directory_for_linux
    global setting__output_directory_for_osx
    global setting__default_comments_column_width
    global setting__rst_table_container_class
    global setting__timestamp_strftime_format
    global setting__debugging
    setting__output_directory_for_windows  = kbr_setting(_cfg_stg_name__output_directory_for_windows)
    setting__output_directory_for_linux    = kbr_setting(_cfg_stg_name__output_directory_for_linux)
    setting__output_directory_for_osx      = kbr_setting(_cfg_stg_name__output_directory_for_osx)
    setting__default_comments_column_width = kbr_setting(_cfg_stg_name__default_comments_column_width)
    setting__rst_table_container_class     = kbr_setting(_cfg_stg_name__rst_table_container_class)
    setting__timestamp_strftime_format     = kbr_setting(_cfg_stg_name__timestamp_strftime_format)
    setting__debugging                     = kbr_setting(_cfg_stg_name__debugging)

    output.set_comments_column_width(setting__default_comments_column_width)

    if debugging:
        show_settings()


def on_plugin_loaded():
    """
    Initialize plugin; called by Sublime Text after plugin is loaded.
    """
    # Prepare cached Package settings.
    # Anything that relies on Package settings will not work before
    # ``_on_pkg_settings_chgd()`` is called, since it is what loads
    # the Package settings.
    _on_pkg_settings_chgd()
    debugging = is_debugging(DebugBits.LOAD_UNLOAD)
    if debugging:
        print(f'In {__package__}.core.on_plugin_loaded()')

    # Establish event hook for "settings changed" event. This allows the user
    # to change the lists that partake in the content of the RegEx that detects
    # Comment Specifier strings, and have updated behavior immediately after
    # saving the changed configuration. Note:  Callback must be unloaded in
    # `plugin_unloaded()` to prevent a callback leak.
    kbr_setting.obj.add_on_change(_cfg_on_settings_chgd_listener_id, _on_pkg_settings_chgd)

    # Tell output module to update its column headings and modifier-key
    # names based on platform.
    platform.set_current_platform()


    # Report.
    if debugging:
        print(f'{package_name}:  Initialized at {timestamp()}.')


def on_plugin_unloaded():
    if hasattr(kbr_setting, 'obj'):
        # That test is for when this Plugin is in a state where it generates
        # an exception upon attempting to be loaded by Sublime Text, then
        # the `obj` attribute may not exist.
        if kbr_setting.obj:
            kbr_setting.obj.clear_on_change(_cfg_on_settings_chgd_listener_id)

    if is_debugging(DebugBits.LOAD_UNLOAD):
        print(f'{package_name}:  Plugin unloaded at {timestamp()}')
