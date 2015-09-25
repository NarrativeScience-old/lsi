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

import ansible.playbook
import ansible.runner
import ansible.inventory
from ansible import callbacks
from ansible import utils
import json
import os

utils.VERBOSITY = 0
stats = callbacks.AggregateStats()
playbook_cb = callbacks.PlaybookCallbacks(verbose=utils.VERBOSITY)
runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=utils.VERBOSITY)

def build_inventory(inventory_dict, query_group):
    '''
    Builds dynamic inventory list for use with ansible commands

    :param inventory_dict: The dictionary to create inventory
    :type inventory_dict: ``dict``
    :param query_group: Subset group created from lsi filters
    :type query_group: ``str``
    
    :return: Inventory file name
    :rtype: ``str``
    '''
    _INVENTORY_FILE = os.path.expanduser('~/.lsi-ansible-inventory')
    inventory_file = _INVENTORY_FILE
    with open(inventory_file, 'w+') as f:
        for key in inventory_dict.iterkeys():
            f.write('['+key+']\n')
        for val in inventory_dict.itervalues():
            f.write('\n'.join(val))
            #print('\n'.join(inventory_dict[query_group]))
        f.write('\n')
    return inventory_file

def run_playbook(inventory_file,playbook_file,subset):
    '''
    Runs specified playbook on provided inventory

    :param inventory_file: The inventory to use
    :type inventory_file: ``str``
    :param playbook_file: The playbook to use
    :type playbook_file: ``str``
    :param subset: The group subset to run against
    :type subset: ``str``
    
    :return: Output from ansible playbook runner
    :rtype: ``str``
    '''
    inv = ansible.inventory.Inventory(inventory_file)
    inv.subset(subset)
    inv.set_playbook_basedir(os.path.dirname(playbook_file))
    hosts = inv.list_hosts(subset)
    failed_hosts = list()
    
    pb = ansible.playbook.PlayBook(
        inventory = inv,
        playbook = playbook_file,
        callbacks = playbook_cb,
        runner_callbacks = runner_cb,
        stats = stats,
    )
    results = pb.run()
    playbook_cb.on_stats(pb.stats)
    return results

def run_module(inventory_file, subset, module, module_params=None):
    '''
    Run specific ansible module with optional parameters

    :param inventory_file: The inventory to use
    :type inventory_file: ``str``
    :param subset: The group subset to run against
    :type subset: ``str``
    :param module: The ansible module to use
    :type module: ``str``
    :param module_params: Optional parameters to pass to module
    :type module_params: ``list``

    :return: JSON formatted output
    :rtype: ``dict``
    '''
    inv = ansible.inventory.Inventory(inventory_file)
    inv.subset(subset)
    hosts = inv.list_hosts(subset)
    failed_hosts = list()

    if module_params is not None:
        runner = ansible.runner.Runner(
            inventory = inv,
            module_name = module,
            module_args = ' '.join(module_params),
            forks = 10
        )
    else:
        runner = ansible.runner.Runner(
            inventory = inv,
            module_name = module,
            forks = 10
        )
    results = runner.run()
    out = json.dumps(results, sort_keys=True, indent=4, separators=(',', ': '))
    return out
