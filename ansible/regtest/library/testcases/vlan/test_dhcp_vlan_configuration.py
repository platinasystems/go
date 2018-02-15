#!/usr/bin/python
""" Test DHCP Vlan Configurations """

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
module: test_dhcp_vlan_configuration
author: Platina Systems
short_description: Module to verify dhcp vlan configurations.
description:
    Module to test different vlan configurations.
options:
    switch_name:
      description:
        - Name of the switch on which tests will be performed.
      required: False
      type: str
    leaf_switch:
      description:
        - Name of leaf switch on which dhcp server is running.
      required: False
      type: str
    eth:
      description:
        - eth interface.
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
- name: Verify vlan configurations dhcp
  test_dhcp_vlan_configurations:
    switch_name: "{{ inventory_hostname }}"
    leaf_switch: "{{ groups['leaf'][0] }}"
    eth: "5"
    hash_name: "{{ hostvars['server_emulator']['hash_name'] }}"
    log_dir_path: "{{ port_provision_log_dir }}"
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


def verify_vlan_configurations(module):
    """
    Method to verify vlan configurations.
    :param module: The Ansible module to fetch input parameters.
    """
    global RESULT_STATUS, HASH_DICT
    failure_summary = ''
    switch_name = module.params['switch_name']
    leaf_switch = module.params['leaf_switch']
    eth = module.params['eth']
    third_octet = switch_name[-2::]

    # Bring down interfaces that are connected to packet generator
    if switch_name == leaf_switch:
        for interface in [x for x in range(1, 33) if x % 2 == 0]:
            execute_commands(module, 'ifconfig eth-{}-1 down'.format(interface))

    # Configure vlan interfaces
    cmd = 'ip link add link eth-{}-1 name eth-{}-1.1 type vlan id {}'.format(
        eth, eth, eth
    )
    execute_commands(module, cmd)

    # Assign ip to vlan only for leaf switch on which dhcp is running
    if switch_name == leaf_switch:
        execute_commands(module, 'ifconfig eth-{}-1.1 192.168.50.{}/24'.format(
            eth, third_octet
        ))

        # Verify vlan interfaces got created with ip assigned to them
        ip_out = execute_commands(module, 'ifconfig eth-{}-1.1'.format(eth))
        if ip_out:
            if '192.168.50.{}'.format(third_octet) not in ip_out:
                RESULT_STATUS = False
                failure_summary += 'On switch {} '.format(switch_name)
                failure_summary += 'failed to configure vlan on interface '
                failure_summary += 'eth-{}-1.1\n'.format(eth)

    # Restart DHCP server
    if switch_name == leaf_switch:
        execute_commands(module, 'service isc-dhcp-server restart')

    time.sleep(5)

    # Run dhclient on spine switch and perform tcpdump on leaf switch to check
    # if dhcp request/reply packets can be seen along with untagged packets.
    if switch_name == leaf_switch:
        cmd = 'tcpdump -c 7 -G 10 -net -i eth-{}-1 not arp and not icmp'.format(eth)
        cmd_out = execute_commands(module, cmd)

        if cmd_out:
            cmd_out = cmd_out.lower()
            if 'bootp/dhcp' not in cmd_out:
                RESULT_STATUS = False
                failure_summary += 'On switch {} '.format(switch_name)
                failure_summary += 'there are no dhcp packets and untagged packets '
                failure_summary += 'captured in tcpdump for eth-{}-1\n'.format(eth)
        else:
            RESULT_STATUS = False
            failure_summary += 'On switch {} '.format(switch_name)
            failure_summary += 'failed to capture tcpdump output\n'
    else:
        execute_commands(module, 'dhclient eth-{}-1'.format(eth))
        time.sleep(5)

        # Verify that eth interface has fetched an ip from dhcp server
        ip_out = execute_commands(module, 'ifconfig eth-{}-1'.format(eth))
        if ip_out:
            if '192.168.5' not in ip_out:
                RESULT_STATUS = False
                failure_summary += 'On switch {} '.format(switch_name)
                failure_summary += 'failed to assign an ip from dhcp server '
                failure_summary += 'for eth-{}-1\n'.format(eth)
        else:
            RESULT_STATUS = False
            failure_summary += 'On switch {} '.format(switch_name)
            failure_summary += 'failed to fetch an ip from dhcp server '
            failure_summary += 'for eth-{}-1\n'.format(eth)

    # Run dhclient on spine switch and perform tcpdump on leaf switch to check
    # if dhcp request/reply packets can be seen along with tagged packets.
    if switch_name == leaf_switch:
        cmd = 'tcpdump -c 7 -G 10 -net -i eth-{}-1 not arp and not icmp'.format(eth)
        cmd_out = execute_commands(module, cmd)

        if cmd_out:
            cmd_out = cmd_out.lower()
            if ('bootp/dhcp' not in cmd_out or '802.1q (0x8100)' not in cmd_out or
                    'vlan {}'.format(eth) not in cmd_out):
                RESULT_STATUS = False
                failure_summary += 'On switch {} '.format(switch_name)
                failure_summary += 'there are no dhcp packets and tagged packets '
                failure_summary += 'captured in tcpdump for eth-{}-1\n'.format(eth)
        else:
            RESULT_STATUS = False
            failure_summary += 'On switch {} '.format(switch_name)
            failure_summary += 'failed to capture tcpdump output\n'
    else:
        execute_commands(module, 'dhclient eth-{}-1.1'.format(eth))
        time.sleep(120)

        # Verify that eth interface has fetched an ip from dhcp server
        ip_out = execute_commands(module, 'ifconfig eth-{}-1.1'.format(eth))
        if ip_out:
            if '192.168.50' not in ip_out:
                RESULT_STATUS = False
                failure_summary += 'On switch {} '.format(switch_name)
                failure_summary += 'failed to assign an ip from dhcp server '
                failure_summary += 'for eth-{}-1.1\n'.format(eth)
        else:
            RESULT_STATUS = False
            failure_summary += 'On switch {} '.format(switch_name)
            failure_summary += 'failed to fetch an ip from dhcp server '
            failure_summary += 'for eth-{}-1.1\n'.format(eth)

    HASH_DICT['result.detail'] = failure_summary

    # Get the GOES status info
    execute_commands(module, 'goes status')


def main():
    """ This section is for arguments parsing """
    module = AnsibleModule(
        argument_spec=dict(
            switch_name=dict(required=False, type='str'),
            leaf_switch=dict(required=False, type='str'),
            eth=dict(required=False, type='str'),
            hash_name=dict(required=False, type='str'),
            log_dir_path=dict(required=False, type='str'),
        )
    )

    global HASH_DICT, RESULT_STATUS

    verify_vlan_configurations(module)

    # Calculate the entire test result
    HASH_DICT['result.status'] = 'Passed' if RESULT_STATUS else 'Failed'

    # Create a log file
    log_file_path = module.params['log_dir_path']
    log_file_path += '/{}.log'.format(module.params['hash_name'])
    log_file = open(log_file_path, 'a')
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

