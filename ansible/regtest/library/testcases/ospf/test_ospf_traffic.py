#!/usr/bin/python
""" Test/Verify OSPF Traffic """

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
module: test_ospf_traffic
author: Platina Systems
short_description: Module to test and verify ospf traffic.
description:
    Module to test and verify ospf configurations and log the same.
options:
    switch_name:
      description:
        - Name of the switch on which tests will be performed.
      required: False
      type: str
    config_file:
      description:
        - OSPF configurations added.
      required: False
      type: str
    leaf_list:
      description:
        - List of all leaf switches.
      required: False
      type: list
      default: []
    package_name:
      description:
        - Name of the package installed (e.g. quagga/frr/bird).
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
- name: Verify ospf traffic
  test_ospf_traffic:
    switch_name: "{{ inventory_hostname }}"
    hash_name: "{{ hostvars['server_emulator']['hash_name'] }}"
    log_dir_path: "{{ ospf_log_dir }}"
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


def verify_ospf_traffic(module):
    """
    Method to verify ospf traffic.
    :param module: The Ansible module to fetch input parameters.
    """
    global RESULT_STATUS, HASH_DICT
    failure_summary = ''
    routes_to_check = []
    netmask = 'netmask 255.255.255.0'
    switch_name = module.params['switch_name']
    leaf_list = module.params['leaf_list']
    package_name = module.params['package_name']
    config_file = module.params['config_file'].splitlines()

    # Get the current/running configurations
    execute_commands(module, "vtysh -c 'sh running-config'")

    # Update eth network interfaces
    for line in config_file:
        line = line.strip()
        if line.startswith('network'):
            switch_id = switch_name[-2::]
            address = line.split()[1]
            address = address.split('/')[0]
            octets = address.split('.')
            if octets[2] == switch_id:
                # Add dummy0 interface
                execute_commands(module, 'ip link add dummy0 type dummy')

                # Assign ip to this created dummy0 interface
                cmd = 'ifconfig dummy0 192.168.{}.1 netmask 255.255.255.255'.format(
                    switch_name[-2::]
                )
                execute_commands(module, cmd)
            else:
                octets[3] = switch_id
                ip = '.'.join(octets)
                eth = 'eth-{}-1'.format(octets[2])
                cmd = 'ifconfig {} {} {}'.format(eth, ip, netmask)

            # Run ifconfig command
            execute_commands(module, cmd)

    # Restart and check package status
    execute_commands(module, 'service {} restart'.format(package_name))
    time.sleep(60)
    execute_commands(module, 'service {} status'.format(package_name))

    if switch_name in leaf_list:
        third_octet = [leaf[-2::] for leaf in leaf_list]

        for octet in third_octet:
            routes_to_check.append('192.168.{}.1'.format(octet))

        # Get all ospf ip routes
        cmd = "vtysh -c 'sh ip route ospf'"
        ospf_routes = execute_commands(module, cmd)

        if ospf_routes:
            for route in routes_to_check:
                if route not in ospf_routes:
                    RESULT_STATUS = False
                    failure_summary += 'On switch {} '.format(switch_name)
                    failure_summary += 'ospf route {} '.format(route)
                    failure_summary += 'is not present in the output '
                    failure_summary += 'of command {}\n'.format(cmd)
        else:
            RESULT_STATUS = False
            failure_summary += 'On switch {} '.format(switch_name)
            failure_summary += 'ospf route cannot be verified since '
            failure_summary += 'output of command {} is None'.format(cmd)

        leaf_list.remove(switch_name)
        neighbor_switch = leaf_list[0]

        self_ip = '192.168.{}.1'.format(switch_name[-2::])
        neighbor_ip = '192.168.{}.1'.format(neighbor_switch[-2::])

        # Verify ping
        packet_count = '3'
        ping_cmd = 'ping -w 3 -c {} -I {} {}'.format(packet_count,
                                                     self_ip, neighbor_ip)
        ping_out = execute_commands(module, ping_cmd)
        if '{} received'.format(packet_count) not in ping_out:
            RESULT_STATUS = False
            failure_summary += 'From switch {}, '.format(switch_name)
            failure_summary += '{} is not getting pinged\n'.format(neighbor_switch)

    HASH_DICT['result.detail'] = failure_summary

    # Get the GOES status info
    execute_commands(module, 'goes status')


def main():
    """ This section is for arguments parsing """
    module = AnsibleModule(
        argument_spec=dict(
            switch_name=dict(required=False, type='str'),
            config_file=dict(required=False, type='str', default=''),
            leaf_list=dict(required=False, type='list', default=[]),
            package_name=dict(required=False, type='str'),
            hash_name=dict(required=False, type='str'),
            log_dir_path=dict(required=False, type='str'),
        )
    )

    global HASH_DICT, RESULT_STATUS

    verify_ospf_traffic(module)

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

