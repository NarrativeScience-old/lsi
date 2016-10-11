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
#!/usr/bin/env python

"""
A simple script for listing (sorted by tag:Name) all running instances
within ns's ec2 east set. It will also return the public dns name of
an instance if the `--host` argument is used. Writes results to a cache
(just a text file) to speed up repeated queries. However, if the latest
list is needed, you can pass `--latest` (`-l`) as an argument.

Any additional command-line arguments will act as regex filters on the list of
instances (similar to running `grep`). Excluding patterns can be provided with
the `-v` (or `--exclude`) argument.

This also provides the ability to SSH into an instance. Passing the argument
`-s` (or `--ssh`) will present the list of instances and let the user choose
which to SSH into. The user can choose to log in a specific user by passing
the argument `-u` (or `--username`), and can specify an identity file with
`-i` (or `--identity_file`).

::
    # Use cache, if it exists and is not too old.
    > list_instances.py

    # Pull latest results from AWS, regardless of the cache.
    > list_instances.py --latest

    # Returns the public DNS name of <host>.
    > list_instances.py --host <host>

    # Filters with `wkfl` and `stg`, and runs the SSH dialog.
    > list_instances.py wkfl stg -s

    # Filters with `wkfl` and `stg`, excludes `batch`, and runs the SSH
    # dialog. Will connect as user `ubuntu`.
    > list_instances.py wkfl stg -e batch -s -u ubuntu
"""

import argparse
from ConfigParser import ConfigParser
import os
from os.path import dirname, join, expanduser, exists
import subprocess
import sys

from utils.hosts import HostEntry, get_entries, filter_entries, get_host
from utils.term import (green, yellow, cyan, blue, get_input)
from utils.system import get_current_username
from utils.stream import stream_commands


# String displayed at the command prompt.
COMMANDS_STRING = \
'''{commands}:
  h: Show this message
  <number {n}>: Connect to the {n}th instance in the list
  p {profile}: Use profile {profile}
  u {username}: Change SSH username to {username} (currently {_username})
  i {idfile}: Change identity file to {idfile} (currently {_idfile})
  f <one or more {pattern}s>: Restrict results to those with {pattern}s
  e <one or more {pattern}s>: Restrict results to those without {pattern}s
  limit {n}: Limit output to first {n} lines
  sort <{attribute}>: Sort the list by {attribute}
  show <one or more {attribute}s>: Additionally show those {attribute}s
  c <{command}>: Set ssh command to run on matching hosts (currently {cur_cmd})
  x: Execute the above command on the above host(s)
  {q}: Quit
'''.format(commands=green('Commands'),
                          n=cyan('n'),
                          profile=cyan('profile'),
                          attribute=cyan('attribute'),
                          username=cyan('username'), _username='{username}',
                          idfile=cyan('idfile'), _idfile='{idfile}',
                          pattern=cyan('pattern'), command=cyan('command'),
                          cur_cmd='{cur_cmd}',
                          q=cyan('q'))



# Path to where the SSH known hosts will be stored.
_KNOWN_HOSTS_FILE = os.path.expanduser(os.environ.get('LSI_KNOWN_HOSTS',
                                                      '~/.lsi-known-hosts'))

# Maps bash commands to their fully qualified paths, e.g. 'ls' -> '/bin/ls'
_PATHS = {}

class LsiProfile(object):
    """Describes the arguments to be found in an LSI profile."""
    def __init__(self, username=None, identity_file=None, filters=None,
                 exclude=None, command=None, no_prompt=False):
        self.username = username
        self.identity_file = identity_file
        self.filters = filters or []
        self.exclude = exclude or []
        self.command = command
        self.no_prompt = no_prompt

    def override(self, attrib, value):
        """Overrides an attribute, unless the overriding value is None."""
        if value is not None:
            setattr(self, attrib, value)

    class LoadError(ValueError):
        """Thrown when a profile fails to load."""
        pass

    @classmethod
    def load(cls, profile_name=None):
        """Loads the user's LSI profile, or provides a default."""
        lsi_location = os.path.expanduser('~/.lsi')
        if not os.path.exists(lsi_location):
            return LsiProfile()
        cfg_parser = ConfigParser()
        cfg_parser.read(lsi_location)
        if profile_name is None:
            # Load the default profile if one exists; otherwise return empty.
            if cfg_parser.has_section('default'):
                profile_name = 'default'
            else:
                return cls()
        elif not cfg_parser.has_section(profile_name):
            raise cls.LoadError('No such profile {}'.format(profile_name))
        def _get(option, alt=None):
            """Gets an option if it exists; else returns `alt`."""
            if cfg_parser.has_option(profile_name, option):
                return cfg_parser.get(profile_name, option)
            else:
                return alt
        if cfg_parser.has_option(profile_name, 'inherit'):
            profile = cls.load(cfg_parser.get(profile_name, 'inherit'))
        else:
            profile = cls()
        profile.override('username', _get('username'))
        profile.override('identity_file', _get('identity file'))
        profile.override('command', _get('command'))
        filters = [s for s in _get('filters', '').split(',') if len(s) > 0]
        exclude = [s for s in _get('exclude', '').split(',') if len(s) > 0]
        profile.filters.extend(filters)
        profile.exclude.extend(exclude)
        return profile

    @staticmethod
    def from_args(args):
        """Takes arguments parsed from argparse and returns a profile."""
        # If the args specify a username explicitly, don't load from file.
        if args.username is not None or args.identity_file is not None:
            profile = LsiProfile()
        else:
            profile = LsiProfile.load(args.profile)
        profile.override('username', args.username)
        profile.override('identity_file', args.identity_file)
        profile.override('command', args.command)
        profile.no_prompt = args.no_prompt
        profile.filters.extend(args.filters)
        profile.exclude.extend(args.exclude)
        if profile.identity_file is not None:
            profile.identity_file = os.path.expanduser(profile.identity_file)
        return profile


def _run_ssh(entries, username, idfile, no_prompt=False, command=None,
             show=None, only=None, sort_by=None, limit=None, tunnel=None):
    """
    Lets the user choose which instance to SSH into.

    :param entries: The list of host entries.
    :type entries: [:py:class:`HostEntry`]
    :param username: The SSH username to use. Defaults to current user.
    :type username: ``str`` or ``NoneType``
    :param idfile: The identity file to use. Optional.
    :type idfile: ``str`` or ``NoneType``
    :param no_prompt: Whether to disable confirmation for SSH command.
    :type no_prompt: ``bool``
    :param command: SSH command to run on matching instances.
    :type command: ``str`` or ``NoneType``
    :param show: Instance attributes to show in addition to defaults.
    :type show: ``NoneType`` or ``list`` of ``str``
    :param only: If not ``None``, will *only* show these attributes.
    :type only: ``NoneType`` or ``list`` of ``str``
    :param sort_by: What to sort columns by. By default, sort by 'name'.
    :type sort_by: ``str``
    :param limit: At most how many results to show.
    :type limit: ``int`` or ``NoneType``
    """
    _print_entries = True
    _print_help = False
    if len(entries) == 0:
        exit('No entries matched the filters.')
    if no_prompt is True and command is not None:
        return _run_ssh_command(entries, username, idfile, command)
    elif len(entries) == 1:
        if command is None:
            return _connect_ssh(entries[0], username, idfile, tunnel)
        else:
            return _run_ssh_command(entries, username, idfile, command)
    elif command is not None:
        print(HostEntry.render_entries(entries,
                                       additional_columns=show,
                                       only_show=only, numbers=True))
        if no_prompt is False:
            get_input("Press enter to run command {} on the {} "
                      "above machines (Ctrl-C to cancel)"
                      .format(cyan(command), len(entries)))
        return _run_ssh_command(entries, username, idfile, command)
    else:
        while True:
            if sort_by is not None:
                entries = HostEntry.sort_by(entries, sort_by)
            if limit is not None:
                entries = entries[:limit]
            if _print_entries is True:
                print HostEntry.render_entries(entries,
                                               additional_columns=show,
                                               only_show=only, numbers=True)
                print '%s matching entries.' % len(entries)
                _print_entries = False
            if _print_help is True:
                cmd_str = green(command) if command is not None else 'none set'
                msg = COMMANDS_STRING.format(username=username or 'none set',
                                             idfile=idfile or 'none set',
                                             cur_cmd=cmd_str)
                print msg
                _print_help = False
            elif command is not None:
                print 'Set to run ssh command: %s' % cyan(command)
            msg = 'Enter command (%s for help, %s to quit): ' % (cyan('h'),
                                                                 cyan('q'))
            choice = get_input(msg)
            if isinstance(choice, int):
                if 0 <= choice <= len(entries):
                    break
                else:
                    msg = 'Invalid number: must be between 0 and %s'
                    print msg % (len(entries) - 1)
            elif choice == 'x':
                if command is None:
                    print 'No command has been set. Set command with `c`'
                else:
                    return _run_ssh_command(entries, username, idfile, command)
            elif choice == 'h':
                _print_help = True
            elif choice in ['q', 'quit', 'exit']:
                print 'bye!'
                return
            else:
                # All of these commands take one or more arguments, so the
                # split length must be at least 2.
                commands = choice.split()
                if len(commands) < 2:
                    print yellow('Unknown command "%s".' % choice)
                else:
                    cmd = commands[0]
                    if cmd in ['u', 'i', 'p']:
                        if cmd == 'u':
                            username = commands[1]
                        elif cmd == 'i':
                            _idfile = commands[1]
                            if not os.path.exists(_idfile):
                                print yellow('No such file: %s' % _idfile)
                                continue
                            idfile = _idfile
                        elif cmd == 'p':
                            p = commands[1]
                            try:
                                profile = LsiProfile.load(p)
                                _username = profile.username
                                _idfile = expanduser(profile.identity_file)
                            except LsiProfile.LoadError:
                                print yellow('No such profile: %s' % repr(p))
                                continue
                            username = _username
                            idfile = _idfile
                        print 'username: %s' % green(repr(username))
                        print 'identity file: %s' % green(repr(idfile))
                    elif cmd == 'f':
                        entries = filter_entries(entries, commands[1:], [])
                        _print_entries = True
                    elif cmd == 'e':
                        entries = filter_entries(entries, [], commands[1:])
                        _print_entries = True
                    elif cmd == 'c':
                        command = ' '.join(commands[1:])
                    elif cmd == 'limit':
                        try:
                            limit = int(commands[1])
                            _print_entries = True
                        except ValueError:
                            print yellow('Invalid limit (must be an integer)')
                    elif cmd == 'sort':
                        sort_by = commands[1]
                        if sort_by not in show:
                            show.append(sort_by)
                        _print_entries = True
                    elif cmd == 'show':
                        if show is None:
                            show = commands[1:]
                        else:
                            show.extend(commands[1:])
                        _print_entries = True
                    else:
                        print yellow('Unknown command "%s".' % cmd)
        return _connect_ssh(entries[choice], username, idfile)


def _get_path(cmd):
    """Queries bash to find the path to a commmand on the system."""
    if cmd in _PATHS:
        return _PATHS[cmd]
    proc = subprocess.Popen('which ' + cmd, shell=True, stdout=subprocess.PIPE)
    out, err = proc.communicate()
    if proc.wait() != 0:
        raise IOError('Lookup of path to command {0} failed{1}'
                      .format(repr(cmd), '' if err is None else ': ' + err))
    _PATHS[cmd] = out.strip()
    return _PATHS[cmd]


def _build_ssh_command(hostname, username, idfile, ssh_command, tunnel):
    """Uses hostname and other info to construct an SSH command."""
    command = [_get_path('ssh'),
               '-o', 'StrictHostKeyChecking=no',
               '-o', 'ConnectTimeout=5',
               '-o', 'UserKnownHostsFile={}'.format(_KNOWN_HOSTS_FILE)]
    if idfile is not None:
        command.extend(['-i', idfile])
    if tunnel is not None:
       # If there's a tunnel, run the ssh command on the tunneled host.
       command.extend(['-A', '-t', tunnel, 'ssh', '-A', '-t'])
    if username is not None:
        command.append('{}@{}'.format(username, hostname))
    else:
        command.append(hostname)
    if ssh_command is not None:
        command.append(repr(ssh_command))
    return ' '.join(command)

def _build_scp_command(hostname, username, idfile, is_get,
                       local_path, remote_path):
    """
    Uses hostname and other info to construct an SCP command.

    :param hostname: The hostname of the remote machine.
    :type hostname: ``str``
    :param username: The username to use on the remote machine.
    :type username: ``str``
    :param idfile: A path to the identity file to use.
    :type idfile: ``str``
    :param is_get: If true, we are getting a file rather than putting a file.
    :type is_get: ``bool``
    :param local_path: The path on the local file system.
    :type local_path: ``str``
    :param remote_path: The path on the remote file system.
    :type remote_path: ``str``
    """
    if hostname.strip() == '' or hostname is None:
        raise ValueError('Empty hostname')
    command = [_get_path('scp'),
               '-o', 'StrictHostKeyChecking=no',
               '-o', 'ConnectTimeout=5',
               '-o', 'UserKnownHostsFile={}'.format(_KNOWN_HOSTS_FILE)]
    if idfile is not None:
        command.extend(['-i', idfile])
    if username is not None:
        hostname = '%s@%s' % (username, hostname)
    remote_path = '{}:{}'.format(hostname, remote_path)
    if is_get:
        command.extend([remote_path, local_path])
    else:
        command.extend([local_path, remote_path])
    return ' '.join(command)


def _copy_to(entries, remote_path, local_path, profile):
    """
    Performs an SCP command where the remote_path is the target and the
    local_path is the source.

    :param entries: A list of entries.
    :type entries: ``list`` of :py:class:`HostEntry`
    :param remote_path: The target path on the remote machine(s).
    :type remote_path: ``str``
    :param local_path: The source path on the local machine.
    :type local_path: ``str``
    :param profile: The profile, holding username/idfile info, etc.
    :type profile: :py:class:`Profile`
    """
    commands = []
    for entry in entries:
        hname = entry.hostname or entry.public_ip
        cmd = _build_scp_command(hname, profile.username,
                                 profile.identity_file,
                                 is_get=False,
                                 local_path=local_path,
                                 remote_path=remote_path)
        print 'Command:',cmd
        commands.append({
            'command': cmd,
            'description': entry.display()
        })
    stream_commands(commands)
    print green('Finished copying')


def _copy_from(entries, remote_path, local_path, profile):
    """
    Performs an SCP command where the remote_path is the source and the
    local_path is a format string, formatted individually for each host
    being copied from so as to create one or more distinct paths on the
    local system.

    :param entries: A list of entries.
    :type entries: ``list`` of :py:class:`HostEntry`
    :param remote_path: The source path on the remote machine(s).
    :type remote_path: ``str``
    :param local_path: A format string for the path on the local machine.
    :type local_path: ``str``
    :param profile: The profile, holding username/idfile info, etc.
    :type profile: :py:class:`Profile`
    """
    commands = []
    paths = set()
    for entry in entries:
        hname = entry.hostname or entry.public_ip
        _local_path = entry.format_string(local_path)
        if _local_path in paths:
            raise ValueError('Duplicate local paths: one or more paths '
                             'had value {} after formatting.'
                             .format(local_path))
        paths.add(_local_path)
        # If the path references a folder, create the folder if it doesn't
        # exist.
        _folder = os.path.split(_local_path)[0]
        if len(_folder) > 0:
            if not os.path.exists(_folder):
                print('Creating directory ' + _folder)
                os.makedirs(_folder)
        cmd = _build_scp_command(hname, profile.username,
                                 profile.identity_file,
                                 is_get=True,
                                 local_path=_local_path,
                                 remote_path=remote_path)
        print 'Command:',cmd
        commands.append({
            'command': cmd,
            'description': entry.display()
        })
    stream_commands(commands)
    print green('Finished copying')


def _run_ssh_command(entries, username, idfile, command, parallel=False):
    """
    Runs the given command over SSH in parallel on all hosts in `entries`.

    :param entries: The host entries the hostnames from.
    :type entries: ``list`` of :py:class:`HostEntry`
    :param username: To use a specific username.
    :type username: ``str`` or ``NoneType``
    :param idfile: The SSH identity file to use, or none.
    :type idfile: ``str`` or ``NoneType``
    :param command: The command to run.
    :type command: ``str``
    :param parallel: If true, commands will be run in parallel.
    :type parallel: ``bool``
    """
    if len(entries) == 0:
        print('(No hosts to run command on)')
        return 1
    if command.strip() == '' or command is None:
        raise ValueError('No command given')
    print('Running command {0} on {1} matching hosts'
          .format(green(repr(command)), len(entries)))
    shell_cmds = []
    for entry in entries:
        hname = entry.hostname or entry.public_ip
        cmd = _build_ssh_command(hname, username, idfile, command)
        shell_cmds.append({
            'command': cmd,
            'description': entry.display()
        })
    stream_commands(shell_cmds, parallel=parallel)
    print(green('All commands finished'))


def _connect_ssh(entry, username, idfile, tunnel=None):
    """
    SSH into to a host.

    :param entry: The host entry to pull the hostname from.
    :type entry: :py:class:`HostEntry`
    :param username: To use a specific username.
    :type username: ``str`` or ``NoneType``
    :param idfile: The SSH identity file to use, if supplying a username.
    :type idfile: ``str`` or ``NoneType``
    :param tunnel: Host to tunnel SSH command through.
    :type tunnel: ``str`` or ``NoneType``

    :return: An exit status code.
    :rtype: ``int``
    """
    if entry.hostname != "" and entry.hostname is not None:
        _host = entry.hostname
    elif entry.public_ip != "" and entry.public_ip is not None:
        _host = entry.public_ip
    elif entry.private_ip != "" and entry.private_ip is not None:
        if tunnel is None:
            raise ValueError("Entry does not have a hostname or public IP. "
                             "You can connect via private IP if you use a "
                             "tunnel.")
        _host = entry.private_ip
    else:
        raise ValueError("No hostname, public IP or private IP information "
                         "found on host entry. I don't know how to connect.")
    command = _build_ssh_command(_host, username, idfile, None, tunnel)
    print 'Connecting to %s...' % cyan(entry.display())
    print 'SSH command: %s' % green(command)
    proc = subprocess.Popen(command, shell=True)
    return proc.wait()


def _print_version():
    """Print the version and exit."""
    from __init__ import __version__
    print __version__
    sys.exit(0)


def _get_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='List EC2 instances')
    parser.add_argument('-l', '--latest', action='store_true', default=False,
                        help='Query AWS for latest instances')
    parser.add_argument('--version', action='store_true', default=False,
                        help='Print version and exit')
    parser.add_argument('--refresh-only', action='store_true', default=False,
                        help='Refresh cache and exit')
    parser.add_argument('--host', help='Specific host to list',
                        default=None)
    parser.add_argument('-s', '--ssh', action='store_true',
                        help='SSH to instance', default=False)
    parser.add_argument('-i', '--identity-file', help='SSH identify file',
                        default=None)
    parser.add_argument('-u', '--username', default=None,
                        help='Log in as this user')
    parser.add_argument('filters', nargs='*',
                        help='Text filters for output lines')
    parser.add_argument('-v', '--exclude', nargs='+',
                        help='Exclude results that match these')
    parser.add_argument('-c', '--command', type=str,
                        help='Command to run on matching instance(s)')
    parser.add_argument('-y', '--no-prompt', action='store_true', default=False,
                        help="Don't ask for confirmation before running a command")
    parser.add_argument('-p', '--profile', type=str,
                        help='Profile to use (defined in ~/.lsi)')
    parser.add_argument('--show', nargs='+', default=None,
                        help='Instance attributes to show')
    parser.add_argument('--only', nargs='+', default=None,
                        help='Show ONLY these instance attributes')
    parser.add_argument('--sep', type=str, default=None,
                        help='Simple output with given separator')
    parser.add_argument('--sort-by', type=str, default=None,
                        help='What to sort list by')
    parser.add_argument('-L', '--limit', type=int, default=None,
                        help='Show at most this many entries')
    parser.add_argument('--attributes', action='store_true',
                        help='Show all available attributes')
    parser.add_argument('--get', nargs=2, default=None,
                        help='Get files from matching instances')
    parser.add_argument('--put', nargs=2, default=None,
                        help='Put a local file on matching instances')
    parser.add_argument('-t', '--tunnel', default=None,
                        help='Connect via the tunneled host.')
    args = parser.parse_args()
    if args.exclude is None:
        args.exclude = []
    # Presumably, if someone is sorting by something, they want to show that
    # thing...
    if args.sort_by is not None:
        args.show = (args.show or []) + [args.sort_by]
    return args


def main(progname=sys.argv[0]):
    args = _get_args()
    profile = LsiProfile.from_args(args)
    if args.host is not None:
        return get_host(args.host)
    # Either of these directives should force a refresh.
    latest = args.latest or args.refresh_only
    entries = get_entries(latest, profile.filters, profile.exclude)
    if args.version is True:
        _print_version()
    if args.refresh_only is True:
        print('Refreshed cache')
        return
    sort_by = args.sort_by or "name"
    if args.get is not None:
        _copy_from(entries, remote_path=args.get[0],
                   local_path=args.get[1],
                   profile=profile)
    elif args.put is not None:
        _copy_to(entries, local_path=args.put[0],
                 remote_path=args.put[1],
                 profile=profile)
    elif args.ssh is True or \
           args.username is not None or args.identity_file is not None or \
           args.profile is not None or profile.command is not None:
        _run_ssh(
            entries=entries,
            username=profile.username,
            idfile=profile.identity_file,
            no_prompt=profile.no_prompt,
            command=profile.command,
            show=args.show,
            only=args.only,
            sort_by=sort_by,
            limit=args.limit,
            tunnel=args.tunnel
        )
    elif args.sep is not None:
        for e in entries:
            print(e.repr_as_line(additional_columns=args.show,
                                 only_show=args.only,
                                 sep=args.sep))
    elif args.attributes is True:
        attribs = HostEntry.list_attributes()
        print('The following attributes are available: {}'
              .format(', '.join(attribs)))
    else:
        entries = HostEntry.sort_by(entries, sort_by)
        if args.limit is not None:
            entries = entries[:args.limit]
        print(HostEntry.render_entries(entries, additional_columns=args.show,
                                       only_show=args.only))
        print('%s matching entries.' % len(entries))

if __name__ == '__main__':
    main()
