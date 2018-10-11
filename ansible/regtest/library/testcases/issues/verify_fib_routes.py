#!/usr/bin/python
""" Verify Fib Routes """

#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible. If not, see <http://www.gnu.org/licenses/>.
#

import shlex

from collections import OrderedDict

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: verify_fib_routes
author: Platina Systems
short_description: Module to verify fib routes
description:
    Module to verify if given number of routes are available on the fib table.
options:
    switch_name:
      description:
        - Name of the switch on which goes health will be checked.
      required: False
      type: str
    routes_count:
      description:
        - Number of routes statically added.
      required: False
      type: int
    hash_name:
      description:
        - Name of the hash in which to store the result in redis.
      required: False
      type: str
    log_dir_path:
      description:
        - Path to log directory where logs will be stored.
      required: False
      type: str
"""

EXAMPLES = """
- name: Verify if routes are available on fib table
  verify_fib_routes:
    switch_name: "{{ inventory_hostname }}"
    routes_count: 1550
    hash_name: "{{ hostvars['server_emulator']['hash_name'] }}"
    log_dir_path: "{{ log_dir_path }}"
"""

RETURN = """
changed:
  description: Boolean flag to indicate if any changes were made by this module.
  returned: always
  type: bool
hash_dict:
  description: Dictionary containing key value pairs to store in hash.
  returned: always
  type: dict
log_file_path:
  description: Path to the log file on this switch.
  returned: always
  type: str
"""

RESULT_STATUS = True
HASH_DICT = OrderedDict()


def run_cli(module, cli):
    """
    Method to execute the cli command on the target node(s) and
    returns the output.
    :param module: The Ansible module to fetch input parameters.
    :param cli: The complete cli string to be executed on the target node(s).
    :return: Output/Error or None depending upon the response from cli.
    """
    cli = shlex.split(cli)
    rc, out, err = module.run_command(cli)

    if out:
        return out.rstrip()
    elif err:
        return err.rstrip()
    else:
        return None


def execute_commands(module, cmd):
    """
    Method to execute given commands and return the output.
    :param module: The Ansible module to fetch input parameters.
    :param cmd: Command to execute.
    :return: Output of the commands.
    """
    global HASH_DICT

    out = run_cli(module, cmd)

    # Store command prefixed with exec time as key and
    # command output as value in the hash dictionary
    exec_time = run_cli(module, 'date +%Y%m%d%T')
    key = '{0} {1} {2}'.format(module.params['switch_name'], exec_time, cmd)

    if out:
        HASH_DICT[key] = out[:512] if len(out.encode('utf-8')) > 512 else out
    else:
        HASH_DICT[key] = out

    return out


def main():
    """ This section is for arguments parsing """
    module = AnsibleModule(
        argument_spec=dict(
            switch_name=dict(required=False, type='str'),
            routes_count=dict(required=False, type='int'),
            hash_name=dict(required=False, type='str'),
            log_dir_path=dict(required=False, type='str'),
        )
    )

    global HASH_DICT, RESULT_STATUS
    failure_summary = ''
    switch_name = module.params['switch_name']

    # Get all ip routes
    ip_routes = execute_commands(module, 'ip route show')
    ip_routes = ip_routes.splitlines()

    # Get all routes from fib table
    fib_routes = execute_commands(module, 'goes vnet show ip fib')
    fib_routes = fib_routes.splitlines()

    # Verify if there are at least given number of routes available
    if len(ip_routes) < 1550 or len(fib_routes) < 1550:
        RESULT_STATUS = False
        failure_summary += 'On switch {} '.format(switch_name)
        failure_summary += 'there are less than 1550 routes available'

    # Calculate the entire test result
    HASH_DICT['result.status'] = 'Passed' if RESULT_STATUS else 'Failed'
    HASH_DICT['result.detail'] = failure_summary

    # Create a log file
    log_file_path = module.params['log_dir_path']
    log_file_path += '/{}.log'.format(module.params['hash_name'])
    log_file = open(log_file_path, 'w')
    for key, value in HASH_DICT.iteritems():
        log_file.write(key)
        log_file.write('\n')
        log_file.write(str(value))
        log_file.write('\n')
        log_file.write('\n')

    log_file.close()

    # Exit the module and return the required JSON.
    module.exit_json(
        hash_dict=HASH_DICT,
        log_file_path=log_file_path,
        changed=False
    )

if __name__ == '__main__':
    main()

