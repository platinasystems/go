#!/usr/bin/python
""" Verify Iperf Traffic """

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
module: verify_iperf_traffic
author: Platina Systems
short_description: Module to verify iperf traffic.
description:
    Module to verify iperf traffic at client.
options:
    switch_name:
      description:
        - Name of the switch on which tests will be performed.
      required: False
      type: str
    eth_ips_last_octet:
      description:
        - Last octets of IP address of interfaces of leaf switch.
      required: False
      type: str
      default: ''
    eth_list:
      description:
        - List of eth interfaces described as string.
      required: False
      type: str
    is_subports:
      description:
        - Flag to indicate if subports are provisioned or not.
      required: False
      type: bool
      default: False
    is_lane2_count2:
      description:
        - Flag to indicate if lane 2 count 2 configuration is used or not.
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
- name: Verify iperf traffic
  verify_iperf_traffic:
    switch_name: "{{ inventory_hostname }}"
    eth_list: "1,3,5,7,9,11,13,15"
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


def verify_traffic(module):
    """
    Method to verify iperf traffic
    :param module: The Ansible module to fetch input parameters.
    """
    global RESULT_STATUS, HASH_DICT
    failure_summary = ''
    switch_name = module.params['switch_name']
    eth_ips_last_octet = module.params['eth_ips_last_octet'].split(',')
    eth_list = module.params['eth_list'].split(',')
    is_subports = module.params['is_subports']
    is_lane2_count2 = module.params['is_lane2_count2']

    if is_subports:
        if not is_lane2_count2:
            subport = ['1', '2', '3', '4']
        else:
            subport = ['1', '3']
    else:
        subport = '1'

    for eth in eth_list:
        ind = eth_list.index(eth)
        last_octet = eth_ips_last_octet[ind]
        for port in subport:
            cmd = 'iperf -c 10.{}.{}.{} -t 2 -P 1'.format(eth, port, last_octet)
            traffic_out = execute_commands(module, cmd)

            if ('Transfer' not in traffic_out and 'Bandwidth' not in traffic_out and
                    'Bytes' not in traffic_out and 'bits/sec' not in traffic_out):
                RESULT_STATUS = False
                failure_summary += 'On switch {} '.format(switch_name)
                failure_summary += 'iperf traffic cannot be verified for '
                failure_summary += 'eth-{}-{} using command {}\n'.format(eth, port, cmd)

    for eth in eth_list:
        for port in subport:
            cmd = 'goes hget platina-mk1 eth-{}-{}'.format(eth, port)
            out = run_cli(module, cmd).splitlines()
            for line in out:
                if 'vnet.eth-{}-{}.port-rx-crc-error-packet'.format(eth, port) in line and '0' not in line:
                    RESULT_STATUS = False
                    failure_summary += 'On switch {} '.format(switch_name)
                    failure_summary += 'crc error count is not 0 for interface '
                    failure_summary += 'eth-{}-{} \n'.format(eth, port)

    HASH_DICT['result.detail'] = failure_summary

    # Get the GOES status info
    execute_commands(module, 'goes status')


def main():
    """ This section is for arguments parsing """
    module = AnsibleModule(
        argument_spec=dict(
            switch_name=dict(required=False, type='str'),
            eth_ips_last_octet=dict(required=False, type='str', default=''),
            eth_list=dict(required=False, type='str'),
            is_subports=dict(required=False, type='bool', default=False),
            is_lane2_count2=dict(required=False, type='bool', default=False),
            hash_name=dict(required=False, type='str'),
            log_dir_path=dict(required=False, type='str')
        )
    )

    global HASH_DICT, RESULT_STATUS

    # Verify iperf traffic
    verify_traffic(module)

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


