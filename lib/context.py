from typing import Tuple, List
import sublime

"""
group_has_transient_sheet
    window.transient_sheet_in_group(grp_index) is not None


"""
class Context():
    """
    Testers of key-binding "context" entries (i.e. list of conditions).
    """
    def __init__(self, view):
        self.view = view

    def _check_value(self, value, operator, operand):
        try:
            if operator == sublime.OP_EQUAL:
                return value == operand
            elif operator == sublime.OP_NOT_EQUAL:
                return value != operand
            elif operator == sublime.OP_REGEX_MATCH:
                return value != None and re.match(operand, value) != None
            elif operator == sublime.OP_NOT_REGEX_MATCH:
                return value == None or re.match(operand, value) == None
            elif operator == sublime.OP_REGEX_CONTAINS:
                return value != None and re.search(operand, value) != None
            elif operator == sublime.OP_NOT_REGEX_CONTAINS:
                return value == None or re.search(operand, value) == None
            else:
                raise Exception("Unsupported operator: " + str(operator))
        except Exception as error:
            print("Failed to check context", operand, value, error)
            raise error

    def _check_sel(self, name, callback, view, key, operator, operand, match_all):
        if key != name:
            return None

        result = True
        for sel in view.sel():
            value = callback(view, sel)
            result = self._check_value(value, operator, operand)
            if not match_all:
                return result

            if not result:
                return False

        return True

    def _check(self, name, callback, view, key, operator, operand, match_all):
        if key != name:
            return None

        result = True
        value = callback(view)
        return self._check_value(value, operator, operand)



def _condition_test(
        view          : sublime.View,
        keypress_tuple: Tuple[str],
        condition     : dict
        ):
    """
    :param view:            Current View (used to test if key context is applicable)
    :param keypress_tuple:  Tuple containing keypress/keypress sequence
    :param condition:       Single condition dictionary from key-binding context.
    """
    result = False

    if not result:
        if _debugging_scope:
            print(f'  Excluding {keypress_tuple_bep} because context condition failed:\n    {condition}')

    return result


def matches(
        view          : sublime.View,
        keypress_tuple: Tuple[str],
        context       : List[dict]
        ):
    """
    :param view:            Current View (used to test if key context is applicable)
    :param keypress_tuple:  Tuple containing keypress/keypress sequence
    :param context:         Context entry from key-binding
    """
    result = True

    # Do all conditions pass?
    all_conditions_passed = True
    for condition in context:
        if not _condition_test(view, keypress_tuple, condition):
            all_conditions_passed = False
            break

    if not all_conditions_passed:
        if _debugging_scope:
            print(f'  Excluding {keypress_tuple_bep} because context does not apply.')

    return result


