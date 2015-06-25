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

import colored

def color(number):
    """
    Returns a function that colors a string with a number from 0 to 256.
    """
    def _color(string):
        return '{0}{1}{2}'.format(colored.fg(number), string,
                                  colored.attr('reset'))
    return _color

# Some coloring functions...
red = color(1)
green = color(2)
yellow = color(3)
blue = color(4)
magenta = color(5)
cyan = color(6)

COLORS = [green, blue, red, yellow, cyan, magenta]

def get_color_hash(string, _min=0, _max=255):
    """
    Hashes a string and returns a number between ``min`` and ``max``.
    """
    hash_num = int(hashlib.sha1(string).hexdigest()[:6], 16)
    _range = _max - _min
    num_in_range = hash_num % _range
    return color(_min + num_in_range)    


def random_color(_min=0, _max=255):
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
        return 100

def get_input(prompt, exit_msg='bye!'):
    """
    Reads stdin, exits with a message if interrupted, EOF, or a quit message.

    :return: The entered input. Converts to an integer if possible.
    :rtype: ``str`` or ``int``
    """
    try:
        response = raw_input(prompt)
    except (KeyboardInterrupt, EOFError):
        print '\n%s' % exit_msg
        exit()
    try:
        return int(response)
    except ValueError:
        return response

