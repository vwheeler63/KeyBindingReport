""" -----------------------------------------------------------------------
General Python utilities.
----------------------------------------------------------------------- """
import os
from typing import Iterable


def largest_string_length(items: Iterable[str]) -> int:
    """
    Length of longest string in `items`

    :param items:   Iterable of strings
    :return:  Longest length among all elements
    """
    longest_len = 0

    for s in items:
        s_len = len(s)
        if s_len > longest_len:
            longest_len = s_len

    return longest_len
