#!/usr/bin/python
""" Test/Verify BGP Peering Interface Down """

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
import time

from collections import OrderedDict

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: test_bgp_peering_if_down
author: Platina Systems
short_description: Module to test and verify bgp peering when interfaces are down.
description:
    Module to test and verify bgp configurations and log the same.
options:
    switch_name:
      description:
        - Name of the switch on which tests will be performed.
      required: False
      type: str
    config_file:
      description:
        - BGP configuration added.
      required: False
      type: str
    leaf_list:
      description:
        - List of all leaf switches.
      required: False
      type: list
      default: []
    eth_list:
      description:
        - Comma separated string of eth interfaces to bring down/up.
      required: False
      type: str
    package_name:
      description:
        - Name of the package installed (e.g. quagga/frr/bird).
      required: False
      type: str
    check_ping:
      description:
        - Flag to indicate if ping should be tested or not.
      required: False
      type: bool
      default: False
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
- name: Verify bgp peering interface down
  test_bgp_peering_if_down:
    switch_name: "{{ inventory_hostname }}"
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

    if 'dummy' in cmd or 'restart' in cmd:
        out = None
    else:
        out = run_cli(module, cmd)

    # Store command prefixed with exec time as key and
    # command output as value in the hash dictionary
    exec_time = run_cli(module, 'date +%Y%m%d%T')
    key = '{0} {1} {2}'.format(module.params['switch_name'], exec_time, cmd)
    HASH_DICT[key] = out

    return out


def check_bgp_neighbors(module):
    """
    Method to check if bgp neighbor relationship got established or not.
    :param module: The Ansible module to fetch input parameters.
    """
    global RESULT_STATUS, HASH_DICT
    neighbor_count = 0
    failure_summary = HASH_DICT.get('result.detail', '')
    switch_name = module.params['switch_name']
    config_file = module.params['config_file'].splitlines()

    # Get all bgp routes
    cmd = "vtysh -c 'sh ip bgp neighbors'"
    bgp_out = execute_commands(module, cmd)

    if bgp_out:
        for line in config_file:
            line = line.strip()
            if 'neighbor' in line and 'remote-as' in line:
                neighbor_count += 1
                config = line.split()
                neighbor_ip = config[1]
                remote_as = config[3]
                if neighbor_ip not in bgp_out or remote_as not in bgp_out:
                    RESULT_STATUS = False
                    failure_summary += 'On switch {} '.format(switch_name)
                    failure_summary += 'bgp neighbor {} '.format(neighbor_ip)
                    failure_summary += 'is not present in the output of '
                    failure_summary += 'command {}\n'.format(cmd)

        if bgp_out.count('BGP state = Established') != neighbor_count:
            RESULT_STATUS = False
            failure_summary += 'On switch {} '.format(switch_name)
            failure_summary += 'bgp state of all/some neighbors '
            failure_summary += 'are not Established in the output of '
            failure_summary += 'command {}\n'.format(cmd)
    else:
        RESULT_STATUS = False
        failure_summary += 'On switch {} '.format(switch_name)
        failure_summary += 'bgp neighbor relationship cannot be verified '
        failure_summary += 'because output of command {} '.format(cmd)
        failure_summary += 'is None'

    HASH_DICT['result.detail'] = failure_summary


def verify_ping(module, self_ip, neighbor_ip):
    """
    Method to verify ping between two switches.
    :param module: The Ansible module to fetch input parameters.
    :param self_ip: Switch IP from where ping will be initiated.
    :param neighbor_ip: Destination ip to ping.
    """
    global RESULT_STATUS, HASH_DICT
    failure_summary = HASH_DICT.get('result.detail', '')
    switch_name = module.params['switch_name']
    packet_count = '3'

    ping_cmd = 'ping -w 3 -c {} -I {} {}'.format(packet_count,
                                                 self_ip, neighbor_ip)
    ping_out = execute_commands(module, ping_cmd)
    if '{} received'.format(packet_count) not in ping_out:
        RESULT_STATUS = False
        failure_summary += 'From switch {} '.format(switch_name)
        failure_summary += 'neighbor ip {} '.format(neighbor_ip)
        failure_summary += 'is not getting pinged\n'

    HASH_DICT['result.detail'] = failure_summary


def verify_bgp_peering_interface_down(module):
    """
    Method to verify bgp peering when interfaces are down.
    :param module: The Ansible module to fetch input parameters.
    """
    global RESULT_STATUS, HASH_DICT
    switch_name = module.params['switch_name']
    package_name = module.params['package_name']
    check_ping = module.params['check_ping']
    eth_list = module.params['eth_list'].split(',')
    leaf_list = module.params['leaf_list']
    is_leaf = True if switch_name in leaf_list else False

    if is_leaf:
        leaf_list.remove(switch_name)

    self_ip = '192.168.{}.1'.format(switch_name[-2::])
    neighbor_ip = '192.168.{}.1'.format(leaf_list[0][-2::])

    # Add dummy0 interface
    execute_commands(module, 'ip link add dummy0 type dummy')

    # Assign ip to this created dummy0 interface
    cmd = 'ifconfig dummy0 192.168.{}.1 netmask 255.255.255.255'.format(
        switch_name[-2::]
    )
    execute_commands(module, cmd)

    # Get the current/running configurations
    execute_commands(module, "vtysh -c 'sh running-config'")

    # Restart and check package status
    execute_commands(module, 'service {} restart'.format(package_name))
    execute_commands(module, 'service {} status'.format(package_name))

    # Check and verify BGP neighbor relationship
    check_bgp_neighbors(module)

    # Verify ping
    if check_ping and is_leaf:
        verify_ping(module, self_ip, neighbor_ip)

    # Wait for 3 seconds
    time.sleep(3)

    # Bring down few eth interfaces on only leaf switches
    if is_leaf:
        for eth in eth_list:
            eth = eth.strip()
            cmd = 'ifconfig eth-{}-1 down'.format(eth)
            execute_commands(module, cmd)

    # Wait for 5 seconds
    time.sleep(5)

    # Again check and verify BGP neighbor relationship
    check_bgp_neighbors(module)

    # Verify ping
    if check_ping and is_leaf:
        verify_ping(module, self_ip, neighbor_ip)

    # Bring up eth interfaces which were down
    if is_leaf:
        for eth in eth_list:
            eth = eth.strip()
            cmd = 'ifconfig eth-{}-1 up'.format(eth)
            execute_commands(module, cmd)

    # Wait for 5 seconds
    time.sleep(5)

    # Again check and verify BGP neighbor relationship
    check_bgp_neighbors(module)

    # Verify ping
    if check_ping and is_leaf:
        verify_ping(module, self_ip, neighbor_ip)

    # Get the GOES status info
    execute_commands(module, 'goes status')


def main():
    """ This section is for arguments parsing """
    module = AnsibleModule(
        argument_spec=dict(
            switch_name=dict(required=False, type='str'),
            config_file=dict(required=False, type='str', default=''),
            leaf_list=dict(required=False, type='list', default=[]),
            eth_list=dict(required=False, type='str'),
            check_ping=dict(required=False, type='bool', default=False),
            package_name=dict(required=False, type='str'),
            hash_name=dict(required=False, type='str'),
            log_dir_path=dict(required=False, type='str'),
        )
    )

    global HASH_DICT, RESULT_STATUS

    verify_bgp_peering_interface_down(module)

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

