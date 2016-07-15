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
import inspect
import json
import os
from os.path import dirname, join, expanduser, exists
import re
from datetime import datetime, timedelta
import time

import boto

from term import (green, yellow, cyan, red, blue, get_input, get_color_hash,
                  get_current_terminal_width, MIN_COLOR_BRIGHT,
                  MAX_COLOR_BRIGHT)
from table import render_table, get_table_width

# Location to read results from/write results to.
CACHE_LOCATION = expanduser(os.environ.get('LSI_CACHE', '~/.lsi_cache.json'))

# Interval after which cache is considered invalid.
_CACHE_DAYS = int(os.environ.get('LSI_CACHE_DAYS', 1))
CACHE_EXPIRATION_INTERVAL = timedelta(days=_CACHE_DAYS)


DEFAULT_ATTRIBUTES = os.environ.get("LSI_DEFAULT_ATTRIBUTES", "").lower()

class HostEntry(object):
    """A selection of information about a host."""
    # Default columns to show in a representation.
    if "LSI_DEFAULT_ATTRIBUTES" in os.environ:
        DEFAULT_COLUMNS = (os.environ["LSI_DEFAULT_ATTRIBUTES"].lower()
                           .split(","))
    else:
        DEFAULT_COLUMNS = ['name', 'hostname', 'public_ip']


    # Maps attribute names to their "pretty" names for use in display.
    COLUMN_NAMES = {
        'name': 'Instance Name',
        'hostname': 'Hostname',
        'private_ip': 'Private IP',
        'public_ip': 'Public IP',
        'instance_type': 'Instance Type',
        'launch_time': 'Launch Time',
        'instance_id': 'Instance ID'
    }

    def __init__(self, name, instance_type, hostname, private_ip, public_ip,
                 stack_name, logical_id, stack_id, security_groups, tags,
                 ami_id, launch_time, instance_id):
        #: The instance name of the host.
        self.name = name
        #: The instance type of the host.
        self.instance_type = instance_type
        #: The DNS name of the host.
        self.hostname = hostname
        #: The private (within the AWS network) IP of the host.
        self.private_ip = private_ip
        #: The public (internet) IP of the host.
        self.public_ip = public_ip
        #: The AWS ID for this instance.
        self.instance_id = instance_id
        #: The name of the stack this instance is part of.
        self.stack_name = stack_name
        #: The ID of that stack.
        self.stack_id = stack_id
        #: The logical ID (relative to its stack) of the instance.
        self.logical_id = logical_id
        #: The names of any security groups the instance is part of.
        self.security_groups = security_groups
        #: The ID of the AMI used to build the machine.
        self.ami_id = ami_id
        #: The date the image was launched.
        self.launch_time = launch_time
        #: Miscellaneous other tags associated with this instance.
        self.tags = tags

    def __repr__(self):
        return repr({k: self._get_attrib(k, convert_nones=True)
                     for k in self.DEFAULT_COLUMNS})

    def to_dict(self):
        """Serialize the host entry into a dictionary, for caching.

        :return: A dictionary serialization of ``self``.
        :rtype: ``dict``
        """
        return vars(self)

    @classmethod
    def from_dict(cls, entry_dict):
        """Deserialize a HostEntry from a dictionary.

        This is more or less the same as calling
        HostEntry(**entry_dict), but is clearer if something is
        missing.

        :param entry_dict: A dictionary in the format outputted by to_dict().
        :type entry_dict: ``dict``

        :return: A HostEntry object.
        :rtype: ``cls``
        """
        return cls(
            name=entry_dict["name"],
            instance_type=entry_dict["instance_type"],
            hostname=entry_dict["hostname"],
            private_ip=entry_dict["private_ip"],
            public_ip=entry_dict["public_ip"],
            stack_name=entry_dict["stack_name"],
            stack_id=entry_dict["stack_id"],
            logical_id=entry_dict["logical_id"],
            security_groups=entry_dict["security_groups"],
            tags=entry_dict["tags"],
            ami_id=entry_dict["ami_id"],
            launch_time=entry_dict["launch_time"],
            instance_id=entry_dict["instance_id"]
        )

    def _get_attrib(self, attr, convert_to_str=False):
        """
        Given an attribute name, looks it up on the entry. Names that
        start with ``tags.`` are looked up in the ``tags`` dictionary.

        :param attr: Name of attribute to look up.
        :type attr: ``str``
        :param convert_to_str: Convert result to a string.
        :type convert_to_str: ``bool``

        :rtype: ``object``
        """
        if attr.startswith('tags.'):
            tag = attr[len('tags.'):]
            if tag in self.tags and self.tags[tag] != '':
                return self.tags[tag]
            elif convert_to_str is True:
                return '<not set>'
            else:
                return self.tags.get(tag)
        elif not hasattr(self, attr):
            raise AttributeError('Invalid attribute: {0}. Perhaps you meant '
                                 '{1}?'.format(red(attr),
                                               green('tags.' + attr)))
        else:
            result = getattr(self, attr)
            if convert_to_str is True and not result:
                return '<none>'
            elif convert_to_str is True and isinstance(result, list):
                return ', '.join(result)
            elif convert_to_str is True:
                return str(result)
            else:
                return result

    @property
    def tagnames(self):
        """Get all available tagnames, separated by commas."""
        return ', '.join(self.tags.keys())

    @property
    def attributes(self):
        """All available attribute names for an instance of this class."""
        return self.list_attributes()

    @classmethod
    def list_attributes(cls):
        """
        Lists all of the attributes to be found on an instance of this class.
        It creates a "fake instance" by passing in `None` to all of the
        ``__init__`` arguments, then returns all of the attributes of that
        instance.

        :return: A list of instance attributes of this class.
        :rtype: ``list`` of ``str``
        """
        fake_args = [None for _ in inspect.getargspec(cls.__init__).args[1:]]
        fake_instance = cls(*fake_args)
        return vars(fake_instance).keys()

    @classmethod
    def sort_by(cls, entries, attribute):
        """
        Sorts a list of entries by the given attribute.
        """
        return sorted(entries, key=lambda e: e._get_attrib(attribute))


    def repr_as_line(self, additional_columns=None, only_show=None, sep=','):
        """
        Returns a representation of the host as a single line, with columns
        joined by ``sep``.

        :param additional_columns: Columns to show in addition to defaults.
        :type additional_columns: ``list`` of ``str``
        :param only_show: A specific list of columns to show.
        :type only_show: ``NoneType`` or ``list`` of ``str``
        :param sep: The column separator to use.
        :type sep: ``str``

        :rtype: ``str``
        """
        additional_columns = additional_columns or []
        if only_show is not None:
            columns = _uniquify(only_show)
        else:
            columns = _uniquify(self.DEFAULT_COLUMNS + additional_columns)
        to_display = [self._get_attrib(c, convert_to_str=True) for c in columns]
        return sep.join(to_display)

    @classmethod
    def from_boto_instance(cls, instance):
        """
        Loads a ``HostEntry`` from a boto instance.

        :param instance: A boto instance object.
        :type instance: :py:class:`boto.ec2.instanceInstance`

        :rtype: :py:class:`HostEntry`
        """
        return cls(
            name=instance.tags.get('Name'),
            private_ip=instance.private_ip_address,
            public_ip=instance.ip_address,
            instance_type=instance.instance_type,
            instance_id=instance.id,
            hostname=instance.dns_name,
            stack_id=instance.tags.get('aws:cloudformation:stack-id'),
            stack_name=instance.tags.get('aws:cloudformation:stack-name'),
            logical_id=instance.tags.get('aws:cloudformation:logical-id'),
            security_groups=[g.name for g in instance.groups],
            launch_time=instance.launch_time,
            ami_id=instance.image_id,
            tags={k.lower(): v for k, v in instance.tags.iteritems()}
        )

    def matches(self, _filter):
        """
        Returns whether the instance matches the given filter text.

        :param _filter: A regex filter. If it starts with `<identifier>:`, then
                        the part before the colon will be used as an attribute
                        and the part after will be applied to that attribute.
        :type _filter: ``basestring``

        :return: True if the entry matches the filter.
        :rtype: ``bool``
        """
        within_attrib = re.match(r'^([a-z_.]+):(.*)', _filter)
        having_attrib = re.match(r'^([a-z_.]+)\?$', _filter)
        if within_attrib is not None:
            # Then we're matching against a specific attribute.
            val = self._get_attrib(within_attrib.group(1))
            sub_regex = within_attrib.group(2)
            if len(sub_regex) > 0:
                sub_regex = re.compile(sub_regex, re.IGNORECASE)
                return _match_regex(sub_regex, val)
            else:
                # Then we are matching on the value being empty.
                return val == '' or val is None or val == []
        elif having_attrib is not None:
            # Then we're searching for anything that has a specific attribute.
            val = self._get_attrib(having_attrib.group(1))
            return val != '' and val is not None and val != []
        else:
            regex = re.compile(_filter, re.IGNORECASE)
            return _match_regex(regex, vars(self))

    def display(self):
        """
        Returns the best name to display for this host. Uses the instance
        name if available; else just the public IP.

        :rtype: ``str``
        """
        if isinstance(self.name, basestring) and len(self.name) > 0:
            return '{0} ({1})'.format(self.name, self.public_ip)
        else:
            return self.public_ip

    @classmethod
    def prettyname(cls, attrib_name):
        """
        Returns the "pretty name" (capitalized, etc) of an attribute, by
        looking it up in ``cls.COLUMN_NAMES`` if it exists there.

        :param attrib_name: An attribute name.
        :type attrib_name: ``str``

        :rtype: ``str``
        """
        if attrib_name.startswith('tags.'):
            tagname = attrib_name[len('tags.'):]
            return '{} (tag)'.format(tagname)
        elif attrib_name in cls.COLUMN_NAMES:
            return cls.COLUMN_NAMES[attrib_name]
        else:
            return attrib_name

    def format_string(self, fmat_string):
        """
        Takes a string containing 0 or more {variables} and formats it
        according to this instance's attributes.

        :param fmat_string: A string, e.g. '{name}-foo.txt'
        :type fmat_string: ``str``

        :return: The string formatted according to this instance. E.g.
                 'production-runtime-foo.txt'
        :rtype: ``str``
        """
        try:
            return fmat_string.format(**vars(self))
        except KeyError as e:
            raise ValueError('Invalid format string: {0}. Instance has no '
                             'attribute {1}.'.format(repr(fmat_string),
                                                     repr(e)))

    @classmethod
    def render_entries(cls, entries, additional_columns=None,
                       only_show=None, numbers=False):
        """
        Pretty-prints a list of entries. If the window is wide enough to
        support printing as a table, runs the `print_table.render_table`
        function on the table. Otherwise, constructs a line-by-line
        representation..

        :param entries: A list of entries.
        :type entries: [:py:class:`HostEntry`]
        :param additional_columns: Columns to show in addition to defaults.
        :type additional_columns: ``list`` of ``str``
        :param only_show: A specific list of columns to show.
        :type only_show: ``NoneType`` or ``list`` of ``str``
        :param numbers: Whether to include a number column.
        :type numbers: ``bool``

        :return: A pretty-printed string.
        :rtype: ``str``
        """
        additional_columns = additional_columns or []
        if only_show is not None:
            columns = _uniquify(only_show)
        else:
            columns = _uniquify(cls.DEFAULT_COLUMNS + additional_columns)
        top_row = map(cls.prettyname, columns)
        table = [top_row] if numbers is False else [[''] + top_row]
        for i, entry in enumerate(entries):
            row = [entry._get_attrib(c, convert_to_str=True) for c in columns]
            table.append(row if numbers is False else [i] + row)
        cur_width = get_current_terminal_width()
        colors = [get_color_hash(c, MIN_COLOR_BRIGHT, MAX_COLOR_BRIGHT)
                  for c in columns]
        if cur_width >= get_table_width(table):
            return render_table(table,
                                column_colors=colors if numbers is False
                                              else [green] + colors)
        else:
            result = []
            first_index = 1 if numbers is True else 0
            for row in table[1:]:
                rep = [green('%s:' % row[0] if numbers is True else '-----')]
                for i, val in enumerate(row[first_index:]):
                    color = colors[i-1 if numbers is True else i]
                    name = columns[i]
                    rep.append('  %s: %s' % (name, color(val)))
                result.append('\n'.join(rep))
            return '\n'.join(result)


def _uniquify(_list):
    """Remove duplicates in a list."""
    seen = set()
    result = []
    for x in _list:
        if x not in seen:
            result.append(x)
            seen.add(x)
    return result


def _match_regex(regex, obj):
    """
    Returns true if the regex matches the object, or a string in the object
    if it is some sort of container.

    :param regex: A regex.
    :type regex: ``regex``
    :param obj: An arbitrary object.
    :type object: ``object``

    :rtype: ``bool``
    """
    if isinstance(obj, basestring):
        return len(regex.findall(obj)) > 0
    elif isinstance(obj, dict):
        return _match_regex(regex, obj.values())
    elif hasattr(obj, '__iter__'):
        # Object is a list or some other iterable.
        return any(_match_regex(regex, s)
                   for s in obj if isinstance(s, basestring))
    else:
        return False


def get_entries(latest, filters, exclude, limit=None):
    """
    Lists all available instances.

    :param latest: If true, ignores the cache and grabs the latest list.
    :type latest: ``bool``
    :param filters: Filters to apply to results. A result will only be shown
                    if it includes all text in all filters.
    :type filters: [``str``]
    :param exclude: The opposite of filters. Results will be rejected if they
                    include any of these strings.
    :type exclude: [``str``]
    :param limit: Maximum number of entries to show (default no maximum).
    :type limit: ``int`` or ``NoneType``

    :return: A list of host entries.
    :rtype: ``list`` of :py:class:`HostEntry`
    """
    entry_list = _list_all_latest() if latest is True or not _is_valid_cache()\
                 else _list_all_cached()
    filtered = filter_entries(entry_list, filters, exclude)
    if limit is not None:
        return filtered[:limit]
    else:
        return filtered


def _is_valid_cache():
    """
    Returns if the cache is valid (exists and modified within the interval).

    :return: Whether the cache is valid.
    :rtype: ``bool``
    """
    if not os.path.exists(CACHE_LOCATION):
        return False
    modified = os.path.getmtime(CACHE_LOCATION)
    modified = time.ctime(modified)
    modified = datetime.strptime(modified, '%a %b %d %H:%M:%S %Y')
    return datetime.now() - modified <= CACHE_EXPIRATION_INTERVAL


def _list_all_latest():
    """
    Gets the latest list from AWS, and writes to the cache.

    :return: A list of host entries.
    :rtype: [:py:class:`HostEntry`]
    """
    entries = []
    ec2 = boto.connect_ec2()
    rs = ec2.get_all_instances(filters={'instance-state-name': 'running'})
    for r in rs:
        for inst in r.instances:
            entries.append(HostEntry.from_boto_instance(inst))
    with open(CACHE_LOCATION, 'w') as f:
        entry_objs = [vars(e) for e in entries]
        f.write(json.dumps(entry_objs))
    return entries


def _list_all_cached():
    """
    Reads the description cache, returning each instance's information.

    :return: A list of host entries.
    :rtype: [:py:class:`HostEntry`]
    """
    with open(CACHE_LOCATION) as f:
        contents = f.read()
        objects = json.loads(contents)
        return [HostEntry.from_dict(obj) for obj in objects]


def filter_entries(entries, filters, exclude):
    """
    Filters a list of host entries according to the given filters.

    :param entries: A list of host entries.
    :type entries: [:py:class:`HostEntry`]
    :param filters: Regexes that must match a `HostEntry`.
    :type filters: [``str``]
    :param exclude: Regexes that must NOT match a `HostEntry`.
    :type exclude: [``str``]

    :return: The filtered list of host entries.
    :rtype: [:py:class:`HostEntry`]
    """
    filtered = [entry
                for entry in entries
                if all(entry.matches(f) for f in filters)
                and not any(entry.matches(e) for e in exclude)]
    return filtered


def get_host(name):
    """
    Prints the public dns name of `name`, if it exists.

    :param name: The instance name.
    :type name: ``str``
    """
    f = {'instance-state-name': 'running', 'tag:Name': name}
    ec2 = boto.connect_ec2()
    rs = ec2.get_all_instances(filters=f)
    if len(rs) == 0:
        raise Exception('Host "%s" not found' % name)
    print rs[0].instances[0].public_dns_name
