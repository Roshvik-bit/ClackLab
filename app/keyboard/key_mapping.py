"""
macOS Virtual Keycode to Character Mapping Utility for ClackLab.
Translates macOS virtual scan codes into text characters and typing operations.
"""

from typing import Optional, Tuple, Dict

# Standard macOS scan code mappings: keycode -> (lower_char, upper_char)
MAC_KEY_CHAR_MAP: Dict[int, Tuple[str, str]] = {
    # Letters
    0: ("a", "A"), 1: ("s", "S"), 2: ("d", "D"), 3: ("f", "F"),
    4: ("h", "H"), 5: ("g", "G"), 6: ("z", "Z"), 7: ("x", "X"),
    8: ("c", "C"), 9: ("v", "V"), 11: ("b", "B"), 12: ("q", "Q"),
    13: ("w", "W"), 14: ("e", "E"), 15: ("r", "R"), 16: ("y", "Y"),
    17: ("t", "T"), 31: ("o", "O"), 32: ("u", "U"), 34: ("i", "I"),
    35: ("p", "P"), 37: ("l", "L"), 38: ("j", "J"), 40: ("k", "K"),
    45: ("n", "N"), 46: ("m", "M"),

    # Numbers and symbols row
    18: ("1", "!"), 19: ("2", "@"), 20: ("3", "#"), 21: ("4", "$"),
    23: ("5", "%"), 22: ("6", "^"), 26: ("7", "&"), 28: ("8", "*"),
    25: ("9", "("), 29: ("0", ")"), 27: ("-", "_"), 24: ("=", "+"),

    # Punctuation & Brackets
    33: ("[", "{"), 30: ("]", "}"), 42: ("\\", "|"),
    41: (";", ":"), 39: ("'", '"'),
    43: (",", "<"), 47: (".", ">"), 44: ("/", "?"),

    # Whitespace & Control
    49: (" ", " "),
    36: ("\n", "\n"),
    48: ("\t", "\t"),
}

BACKSPACE_KEYCODES = {51}
SHIFT_KEYCODES = {56, 60}
CAPS_LOCK_KEYCODES = {57}
COMMAND_KEYCODES = {54, 55}
OPTION_KEYCODES = {58, 61}
CONTROL_KEYCODES = {59}
FN_KEYCODES = {63}
ARROW_KEYCODES = {123, 124, 125, 126}


def keycode_to_char(keycode: int, is_shift: bool = False, is_caps: bool = False) -> Optional[str]:
    """
    Returns the character produced by the given macOS virtual keycode.
    Takes shift and caps lock modifier states into account.
    """
    if keycode in MAC_KEY_CHAR_MAP:
        lower, upper = MAC_KEY_CHAR_MAP[keycode]
        if lower.isalpha():
            # Letters are uppercase if shift XOR caps lock is active
            use_upper = is_shift ^ is_caps
            return upper if use_upper else lower
        else:
            # Symbols and numbers use shifted variant only if shift is active
            return upper if is_shift else lower

    return None


def is_backspace(keycode: int) -> bool:
    return keycode in BACKSPACE_KEYCODES


def is_shift(keycode: int) -> bool:
    return keycode in SHIFT_KEYCODES


def is_caps_lock(keycode: int) -> bool:
    return keycode in CAPS_LOCK_KEYCODES
