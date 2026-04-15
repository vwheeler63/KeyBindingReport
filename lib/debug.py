""" ***********************************************************************
@copyright  Copyright (c) 2025-2026 WGA Crystal Research, Inc.
            All rights reserved.  Duplication and distribution prohibited
            except with explicit written permission.

Sublime Text Package Debug Module
*********************************

This module allows Sublime Text Packages or Plugins to implement an
elaborate, multi-part debugging scheme, selectively, programmatically,
turning on and off parts of debugging output in the Console Panel.

It allows flexible, user-configurable Package settings to determine what
parts of the Package are being debugged, typically via a ``debugging``
Package setting.

Valid values for a ``debugging`` Package setting:

- JSON bare true or false, implying "DebugBits.ALL" and "DebugBits.NONE" respectively;
- JSON integer containing necessary bits, e.g. 32 = 0x0020;
- JSON string expressions of bit-wise OR-ed constants from the DebugBits class.
  (See below for examples.)

Examples of valid ``debugging`` JSON Package setting strings:

- "DebugBits.NONE"
- "DebugBits.INITIALIZATION"
- "DebugBits.ALL"
- "DebugBits.CONTEXT_QUERY | DebugBits.PARAMETERS | DebugBits.PRECONDITIONS"
- "DebugBits.INITIALIZATION | DebugBits.HEADER_COMMENT_BLOCKS"

Note:  the spaces surrounding the '|' operator are optional,
    but are recommended for readability.

See also docstring with DebugBits class below for details about how to
set up the DebugBits class for your Sublime Text Package or Plugin.

See below for how to use this module in your Plugin code:


Usage
=====

.. code-block:: py

    from .lib.debug import IntFlag, DebugBits, is_debugging, set_debugging_bits

    def pc_setting():
        # ...function used to store and retrieve cached Package settings.
        # ...

    def plugin_loaded():
        pc_setting.obj = sublime.load_settings('my_package.sublime-settings')
        temp = pc_setting('debugging')
        set_debugging_bits(temp)
        # Other Plugin initialization here.

    # Then later in Plugin code:

    def any_plugin_function():
        # ...
        # This example illustrates calling ``is_debugging()``
        # just once per function for efficiency.
        debugging = is_debugging(DebugBits.QUERY_CONTEXT_EVENT)

        # Later...
        if debugging:
            if result:
                print('  OK.  Num selections == 1.')
            else:
                print('  FAIL.  Num selections != 1.')

        # Later...
        if debugging:
            if result:
                print(f'  OK.  Matches selector "{_my_selector}".')
            else:
                print(f'  FAIL.  DOES NOT match selector "{_my_selector}".')


Public API
==========

    def set_debugging_bits(setting_value: Union[int, str, bool]):
        # Set Debug Module setting to ``selection_bits``.

    def add_debugging_bits(setting_value: Union[int, str, bool]):
        # Add 1 bits in ``selection_bits`` to Debug Module setting.

    def subtract_debugging_bits(setting_value: Union[int, str, bool]):
        # Subtract 1 bits in ``selection_bits`` from Debug Module setting.

    def is_debugging(selection_bits: DebugBits = DebugBits.ANY) -> int:
        # Do any 1 bits in `selection_bits` also exist in
        # the Debug Module setting?
        #
        # Use Truth value of returned integer for Boolean uses.
        #
        # :returns:  Bitwise-AND-ed Debug Module flags and `selection_bits`.
        #            Allows caller to query about whether a specific topic in
        #            the Package has its debugging output turned on.
        #
        #            If ``bool(result)`` is ``False``, none of the specified bits
        #            were found.
        #
        #            If ``True``, at least one of the bits was found.
*************************************************************************** """
# Accept forward references as is done in the default assignment
# to ``_debugging`` below.
# from __future__ import annotations
from enum import IntFlag
from typing import Union
import re


class DebugBits(IntFlag):
    """
    Named bits used in debugging Packages.

    Maintenance Note:  when this class changes, update the documentation
    about it in the ``.sublime-settings`` file.

    The actual bit names in the ``DebugBits`` class will change, Package to
    Package, based on what is applicable to the Package using it.  It is,
    however, recommended to keep the NONE, DEBUGGING, ALL and ANY bits as
    all 4 of these values are used directly in this module, and are meant to:

    - show the user both how it works, and
    - announce in the Console Panel which debug bits are set, by both name
      and value (only when at least 1 bit is set).

    Here is an example of the ``DebugBits`` set of values from the ProComment
    Package:

    .. code-block:: py

        # ---------------------------------------------------------------------
        # Core Bits
        # ---------------------------------------------------------------------
        NONE                   = 0x0000
        DEBUGGING              = 0x0001
        LOAD_UNLOAD            = 0x0002
        INITIALIZATION         = 0x0004
        SETTINGS_CHANGED_EVENT = 0x0008
        QUERY_CONTEXT_EVENT    = 0x0010
        COMMENT_SPECIFIER      = 0x0020
        BASIC_COMMENT_BLOCKS   = 0x0040
        HEADER_COMMENT_BLOCKS  = 0x0080

        # ---------------------------------------------------------------------
        # Snippet (Header) Postprocessing (SPP) Bits
        # ---------------------------------------------------------------------
        POSTPROCESSING         = 0x0100
        BLOCK_COMMENTS         = 0x0200
        PARAMETERS             = 0x0400
        PRECONDITIONS          = 0x0800
        POSTCONDITIONS         = 0x1000

        # ---------------------------------------------------------------------
        # Importing Bits
        # ---------------------------------------------------------------------
        # Note: because the Debug Module normally does not get initialized
        # until after the Plugin is fully loaded and `plugin_loaded()` event
        # gets fired, in order to use the Debug Module with the IMPORTING
        # bit, the bit has to be set directly into the `_debugging` attribute
        # in THIS module's module-level code, since execution of THAT code is
        # when all the IMPORTING debug code gets executed.  Otherwise, the bit
        # won't be set yet, and all the importing code will have executed by
        # the time the bit gets set.  This is the only bit that is like that.
        # All the other ones get set after the cached Package settings have
        # been brought in.
        IMPORTING              = 0X2000

        # ---------------------------------------------------------------------
        # Utility Bits
        # ---------------------------------------------------------------------
        ALL                    = 0xFFFF
        ANY                    = 0xFFFF

    The number of bits used shown above is 16, but it can be raised or
    lowered in the range [1-32] (the limit of the ``IntFlag`` class and
    Python integers).  Example of a 32-bit bit constant:  0x00000001.  If
    you change the number of bits used higher than 16, you will also need
    to change the configured ``_cfg_debugging_print_format`` value above so
    that the debugging output will be formatted to include all the bits.
    """

    # ---------------------------------------------------------------------
    # Core Bits
    # ---------------------------------------------------------------------
    DEBUGGING              = 0x0001
    LOAD_UNLOAD            = 0x0002
    SETTINGS_CHANGED_EVENT = 0x0004
    KEY_BINDING_REPORT     = 0x0008
    WHICH_BINDING_REPORT   = 0x0010
    FILTERING_STAGE_I      = 0x0020
    FILTERING_STAGE_II     = 0x0040
    FILTERING_ON_SCOPE     = 0x0080
    BUILDING_MAIN_KEY_DICT = 0x0100
    BUILDING_KEY_SEQ_DICT  = 0x0200

    # ---------------------------------------------------------------------
    # Importing Bits
    # ---------------------------------------------------------------------
    # Note: because the Debug Module normally does not get initialized
    # until after the Plugin is fully loaded and `plugin_loaded()` event
    # gets fired, in order to use the Debug Module with the IMPORTING
    # bit, the bit has to be set directly into the `_debugging` attribute
    # in THIS module's module-level code, since execution of THAT code is
    # when all the IMPORTING debug code gets executed.  Otherwise, the bit
    # won't be set yet, and all the importing code will have executed by
    # the time the bit gets set.  This is the only bit that is like that.
    # All the other ones get set after the cached Package settings have
    # been brought in.
    IMPORTING              = 0x8000

    # ---------------------------------------------------------------------
    # Utility Bits
    # ---------------------------------------------------------------------
    NONE                   = 0x0000
    ALL                    = 0xFFFF
    ANY                    = 0xFFFF


# =========================================================================
# Data
#
# `_debugging` is a bit vector (int) used to do fast bit tests.
# This allows us to selectively turn on and off parts of debugging
# output, getting away from the profuse "all at once" debug output.
# =========================================================================

_debugging: DebugBits = DebugBits.NONE
_valid_debugging_string_re = None
_cfg_debugging_print_format = '04X'


# =========================================================================
# Module Definitions
# =========================================================================

def _debugging_string_validator_regex():
    r"""
    Only valid string expressions look like this:
    'DebugBits.INITIALIZATION' or
    'DebugBits.INITIALIZATION | DebugBits.QUERY_CONTEXT_EVENT | ...'

    Build this out of whatever is current in the DebugBits class:

        ^\s*DebugBits\.(?:NONE|ALL|INITIALIZATION|...)
          (?:\s*\|\s*DebugBits\.(?:NONE|ALL|INITIALIZATION|...))*\s*$

    """
    bit_class = DebugBits
    attr_list = dir(bit_class)
    bit_names = []

    for attr in attr_list:
        if attr[0] == '_':
            break
        bit_names.append(attr)

    attributes_or_ed_list = '|'.join(bit_names)
    class_name = bit_class.__name__
    bit_attr_re = fr'{class_name}\.(?:{attributes_or_ed_list})'
    optional_additional_or_ed_ones_re = fr'(?:\s*\|\s*{bit_attr_re})*'
    final_re = fr'^\s*{bit_attr_re}{optional_additional_or_ed_ones_re}\s*$'
    return re.compile(final_re)


def _securely_computed_bits_from_setting_input(
        selection_bits: Union[int, str, bool, DebugBits]
        ) -> DebugBits:
    """
    Accept any of int | str | bool | DebugBits, and securely compute the
    applicable Debug Module bits in an int:  ``result``.
    """
    global _valid_debugging_string_re
    result = DebugBits.NONE

    # ---------------------------------------------------------------------
    # DebugBits
    # ---------------------------------------------------------------------
    if isinstance(selection_bits, DebugBits):
        result = selection_bits

    # ---------------------------------------------------------------------
    # String -- only use if valid.
    # ---------------------------------------------------------------------
    elif isinstance(selection_bits, str):
        # Only use if validated.
        if not _valid_debugging_string_re:
            _valid_debugging_string_re = _debugging_string_validator_regex()
        match = _valid_debugging_string_re.search(selection_bits)
        if match:
            result = eval(selection_bits)
        else:
            raise ValueError(
                    f'Debug Module:  Error:  invalid string:  [{selection_bits}]\n'
                    f'  did not match [{_valid_debugging_string_re.pattern}].'
                    )
    # ---------------------------------------------------------------------
    # Boolean
    # ---------------------------------------------------------------------
    elif isinstance(selection_bits, bool):
        if selection_bits:
            result = DebugBits.ALL
        else:
            result = DebugBits.NONE
    # ---------------------------------------------------------------------
    # Integer
    # ---------------------------------------------------------------------
    elif isinstance(selection_bits, int):
        result = selection_bits
    # ---------------------------------------------------------------------
    # Unknown
    # ---------------------------------------------------------------------
    else:
        raise ValueError('Debug Module:  Error:  unrecognized type.')

    return result


def _report_debugging_setting():
    if is_debugging(DebugBits.DEBUGGING):
        print('Debugging:')
        if _valid_debugging_string_re:
            print(f'  Validating regex: [{_valid_debugging_string_re.pattern}]')
        else:
            print(f'  Validating regex: [{_valid_debugging_string_re}]')

    if is_debugging(DebugBits.ANY):
        print(f'Debugging: [0x{_debugging:{_cfg_debugging_print_format}}]')
        # Compute length of longest enumeration name with bit set.
        longest_name_len = 0
        for enum_bit in DebugBits:
            if enum_bit != DebugBits.ALL and enum_bit != DebugBits.ANY:
                if _debugging & enum_bit._value_:
                    name_len = len(enum_bit._name_)
                    if name_len > longest_name_len:
                        longest_name_len = name_len

        # Report.
        for enum_bit in DebugBits:
            if enum_bit != DebugBits.ALL and enum_bit != DebugBits.ANY:
                if _debugging & enum_bit._value_:
                    print(
                            f'  - {enum_bit._name_:{longest_name_len}}:  '
                            f'0x{enum_bit._value_:{_cfg_debugging_print_format}}'
                            )


def _set_debugging_bits(selection_bits: int):
    global _debugging
    _debugging = selection_bits
    _report_debugging_setting()


def _add_debugging_bits(selection_bits: int):
    global _debugging
    _debugging |= selection_bits
    _report_debugging_setting()


def _subtract_debugging_bits(selection_bits: int):
    global _debugging
    _debugging &= ~(selection_bits)
    _report_debugging_setting()


def set_debugging_bits(setting_value: Union[int, str, bool, DebugBits]):
    """ Set Debug Module setting to ``selection_bits``. """
    bits = _securely_computed_bits_from_setting_input(setting_value)
    _set_debugging_bits(bits)


def add_debugging_bits(setting_value: Union[int, str, bool, DebugBits]):
    """ Add '1' bits in ``selection_bits`` to Debug Module setting.  """
    bits = _securely_computed_bits_from_setting_input(setting_value)
    _add_debugging_bits(bits)


def subtract_debugging_bits(setting_value: Union[int, str, bool, DebugBits]):
    """ Subtract '1' bits in ``selection_bits`` from Debug Module setting.  """
    bits = _securely_computed_bits_from_setting_input(setting_value)
    _subtract_debugging_bits(bits)


def is_debugging(selection_bits: DebugBits = DebugBits.ANY) -> int:
    """ Do any '1' bits in `selection_bits` also exist in
        the Debug Module  setting?

    Use Truth value of returned integer for Boolean uses.

    :returns:  Bitwise-AND-ed Debug Module flags and `selection_bits`.
               Allows caller to query about whether a specific topic in
               the Package has its debugging output turned on.

               If ``bool(result)`` is ``False``, none of the specified bits
               were found.

               If ``True``, at least one of the bits was found.
    """
    return _debugging & selection_bits
