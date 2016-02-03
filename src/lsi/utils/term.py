# Copyright (c) 2015, Narrative Science
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
import hashlib
import os
import random
import sys

# Codes for some terminal colors
COLORS = {
    'cyan': 36, 'green': 32, 'red': 31,
    'yellow': 33, 'blue': 34, 'magenta': 35,
}

def supports_256():
    """Returns true if this terminal supports 256 colors"""
    return "TERM" in os.environ and "256" in os.environ["TERM"]

def color(number):
    """
    Returns a function that colors a string with a number from 0 to 255.
    """
    if supports_256():
        template = "\033[38;5;{number}m{text}\033[0m"
    else:
        template = "\033[{number}m{text}\033[0m"
    def _color(text):
        if not all([sys.stdout.isatty(), sys.stderr.isatty()]):
            return text
        else:
            return template.format(number=number, text=text)
    return _color

# Some coloring functions...
red = color(COLORS['red'])
green = color(COLORS['green'])
yellow = color(COLORS['yellow'])
blue = color(COLORS['blue'])
magenta = color(COLORS['magenta'])
cyan = color(COLORS['blue'])

COLORS = [green, blue, red, yellow, cyan, magenta]

# In this case we only support 6 colors...
if supports_256():
    MIN_COLOR, MAX_COLOR = 0, 255
    MIN_COLOR_BRIGHT, MAX_COLOR_BRIGHT = 100, 150
else:
    MIN_COLOR = MIN_COLOR_BRIGHT = 31
    MAX_COLOR = MAX_COLOR_BRIGHT = 36


def get_color_hash(string, _min=MIN_COLOR_BRIGHT, _max=MAX_COLOR_BRIGHT):
    """
    Hashes a string and returns a number between ``min`` and ``max``.
    """
    hash_num = int(hashlib.sha1(string).hexdigest()[:6], 16)
    _range = _max - _min
    num_in_range = hash_num % _range
    return color(_min + num_in_range)


def random_color(_min=MIN_COLOR, _max=MAX_COLOR):
    """Returns a random color between min and max."""
    return color(random.randint(_min, _max))


def get_current_terminal_width():
    """
    Returns the current terminal size, in characters.
    :rtype: ``int``
    """
    try:
        return int(os.popen('stty size', 'r').read().split()[1])
    except Exception:
        return 80


def get_input(prompt, default=None, exit_msg='bye!'):
    """
    Reads stdin, exits with a message if interrupted, EOF, or a quit message.

    :return: The entered input. Converts to an integer if possible.
    :rtype: ``str`` or ``int``
    """
    try:
        response = raw_input(prompt)
    except (KeyboardInterrupt, EOFError):
        print()
        print(exit_msg)
        exit()
    try:
        return int(response)
    except ValueError:
        if response.strip() == "" and default is not None:
            return default
        else:
            return response
