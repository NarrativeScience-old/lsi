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
import os
import shlex
import subprocess
import sys

from threading import Thread

from term import random_color, get_color_hash

DEFAULT_COLOR = None

def stream_command(command, formatter=None, write_stdin=None, ignore_empty=False):
    """
    Starts `command` in a subprocess. Prints every line the command prints,
    prefaced with `description`.

    :param command: The bash command to run. Must use fully-qualified paths.
    :type command: ``str``
    :param formatter: An optional formatting function to apply to each line.
    :type formatter: ``function`` or ``NoneType``
    :param write_stdin: An optional string to write to the process' stdin.
    :type write_stdin: ``str`` or ``NoneType``
    :param ignore_empty: If true, empty or whitespace-only lines will be skipped.
    :type ignore_empty: ``bool``
    """
    command_list = shlex.split(command)
    try:
        proc = subprocess.Popen(command_list, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    except Exception as e:
        raise IOError('Encountered error: {0} when running command {1}'
                      .format(e.message, ' '.join(command_list)))
    if write_stdin is not None:
        proc.stdin.write(write_stdin)
        proc.stdin.flush()

    while proc.poll() is None:
        try:
            line = proc.stdout.readline()
        except KeyboardInterrupt:
            sys.exit('Keyboard interrupt while running {}'.format(command))
        if len(line.strip()) == 0 and ignore_empty is True:
            continue
        elif 'killed by signal 1' in line.lower():
            continue
        elif 'to the list of known hosts' in line.lower():
            continue
        if formatter is not None:
            line = formatter(line)
        sys.stdout.write(line)
    result = proc.poll()
    return result


def stream_command_dicts(commands, parallel=False):
    """
    Takes a list of dictionaries with keys corresponding to ``stream_command``
    arguments, and runs all concurrently.

    :param commands: A list of dictionaries, the keys of which should line up
                     with the arguments to ``stream_command`` function.
    :type commands: ``list`` of ``dict``
    :param parallel: If true, commands will be run in parallel.
    :type parallel: ``bool``
    """
    if parallel is True:
        threads = []
        for command in commands:
            target = lambda: stream_command(**command)
            thread = Thread(target=target)
            thread.start()
            threads.append(thread)
        for t in threads:
            t.join()
    else:
        for command in commands:
            stream_command(**command)


def _format_with_description(description):
    def _fmat(line):
        return '[{0}]: {1}'.format(description, line)
    return _fmat


def stream_commands(commands, hash_colors=True, parallel=False):
    """
    Runs multiple commands, optionally in parallel. Each command should be
    a dictionary with a 'command' key and optionally 'description' and
    'write_stdin' keys.
    """
    def _get_color(string):
        if hash_colors is True:
            return get_color_hash(string)
        else:
            return DEFAULT_COLOR
    fixed_commands = []
    for command in commands:
        cmd_text = command['command']
        description = command.get('description')
        color = _get_color(description or '')
        write_stdin = command.get('write_stdin')
        description = color(description) if color is not None else description
        formatter = _format_with_description(description)
        fixed_commands.append({
            'command': cmd_text,
            'formatter': formatter,
            'write_stdin': write_stdin,
            'ignore_empty': True
        })
    stream_command_dicts(fixed_commands, parallel=parallel)
