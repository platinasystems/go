#!/usr/bin/python
""" Test/Verify OSPF Config in Docker """

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
module: test_ospf
author: Platina Systems
short_description: Module to test and verify ospf configurations inside docker.
description:
    Module to test and verify ospf configurations inside docker container.
options:
    switch_name:
      description:
        - Name of the switch on which tests will be performed.
      required: False
      type: str
    container:
      description:
        - Name of the container.
      required: False
      type: str
    config_file:
      description:
        - ospfd.conf file added in the given container.
      required: False
      type: str
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
- name: Verify ospf config inside docker container
  test_ospf:
    switch_name: "{{ inventory_hostname }}"
    container: 'R1'
    hash_name: "{{ hostvars['server_emulator']['hash_name'] }}"
    log_dir_path: "{{ log_dir_path }}"
"""

RETURN = """
hash_dict:
  description: Dictionary containing key value pairs to store in hash.
  returned: always
  type: dict
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
    HASH_DICT[key] = out

    return out


def get_cli(module):
    """
    Method to get initial cli string.
    :param module: The Ansible module to fetch input parameters.
    :return: Initial cli/cmd string.
    """
    return "docker exec -i {} ".format(module.params['container'])


def verify_ospf_neighbors(module):
    """
    Method to verify if ospf neighbor relationship got established or not.
    :param module: The Ansible module to fetch input parameters.
    """
    global RESULT_STATUS, HASH_DICT
    failure_summary = ''
    switch_name = module.params['switch_name']
    config_file = module.params['config_file'].splitlines()

    # Get the current/running configurations
    cmd = get_cli(module) + "vtysh -c 'sh running-config'"
    execute_commands(module, cmd)

    # Get ospf routes
    cmd = get_cli(module) + "vtysh -c 'show ip route ospf'"
    ospf_routes = execute_commands(module, cmd)

    if ospf_routes:
        for line in config_file:
            line = line.strip()
            if 'network' in line and 'area' in line:
                route = line.split()[1]
                if route not in ospf_routes:
                    RESULT_STATUS = False
                    failure_summary += 'On switch {} '.format(switch_name)
                    failure_summary += 'ospf route {} is not showing up '.format(route)
                    failure_summary += 'in the output of command {} '.format(cmd)
    else:
        RESULT_STATUS = False
        failure_summary += 'On switch {} '.format(switch_name)
        failure_summary += 'ospf routes cannot be verified since '
        failure_summary += 'output of command {} is None'.format(cmd)

    # Get ospf neighbors relationships
    cmd = get_cli(module) + "vtysh -c 'show ip ospf neighbor'"
    out = execute_commands(module, cmd)

    # For errors, update the result status to False
    if out is None or 'error' in out:
        RESULT_STATUS = False
        failure_summary += 'On Switch {} '.format(switch_name)
        failure_summary += 'ospf neighbors cannot be verified since '
        failure_summary += 'output of command {} is None'.format(cmd)

    HASH_DICT['result.detail'] = failure_summary

    # Get the GOES status info
    execute_commands(module, 'goes status')


def main():
    """ This section is for arguments parsing """
    module = AnsibleModule(
        argument_spec=dict(
            switch_name=dict(required=False, type='str'),
            container=dict(required=False, type='str'),
            config_file=dict(required=False, type='str'),
            hash_name=dict(required=False, type='str'),
            log_dir_path=dict(required=False, type='str'),
        )
    )

    global HASH_DICT, RESULT_STATUS

    # Verify ospf neighbors
    verify_ospf_neighbors(module)

    # Calculate the entire test result
    HASH_DICT['result.status'] = 'Passed' if RESULT_STATUS else 'Failed'

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
        log_file_path=log_file_path
    )

if __name__ == '__main__':
    main()

