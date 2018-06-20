#!/usr/bin/python
""" Test/Verify Port Links """

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
module: set_reset_configs_25g_fec_none_autoneg_off
author: Platina Systems
short_description: Module to execute and verify port links.
description:
    Module to execute and verify port links.
options:
    switch_name:
      description:
        - Name of the switch on which tests will be performed.
      required: False
      type: str
    leaf_list:
      description:
        - List of all leaf switches.
      required: False
      type: list
      default: []
    spine_list:
      description:
        - List of all spine switches.
      required: False
      type: list
      default: []
    eth_list:
      description:
        - List of eth interfaces described as string.
      required: False
      type: str
      default: ''
    speed:
      description:
        - Speed of the eth interface port.
      required: False
      type: str
    media:
      description:
        - Media of the eth interface port.
      required: False
      type: str
    fec:
      description:
        - Fec of the eth interface port.
      required: False
      type: str
    autoneg:
      description:
        - autoneg of the eth interface port.
      required: False
      type: str
    leaf_eth_ips_last_octet:
      description:
        - Last octets of IP address of interfaces of leaf switch.
      required: False
      type: str
      default: ''
    spine_eth_ips_last_octet:
      description:
        - Last octets of IP address of interfaces of spine switch.
      required: False
      type: str
      default: ''
    platina_redis_channel:
      description:
        - Name of the platina redis channel.
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
- name: Execute and verify port links
  test_port_links:
    switch_name: "{{ inventory_hostname }}"
    eth_list: "2,4,6,8,10,12,14,16"
    speed: "100g"
    media: "copper"
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
    if out:
        HASH_DICT[key] = out[:512] if len(out.encode('utf-8')) > 512 else out
    else:
        HASH_DICT[key] = out

    return out


def set_switch(module):
    """
    Method to update configs.
    :param module: The Ansible module to fetch input parameters.
    """
    global RESULT_STATUS, HASH_DICT
    failure_summary = ''
    switch_name = module.params['switch_name']
    spine_list = module.params['spine_list']
    leaf_list = module.params['leaf_list']
    speed = module.params['speed']
    fec = module.params['fec']
    autoneg = module.params['autoneg']
    platina_redis_channel = module.params['platina_redis_channel']
    is_subports = module.params['is_subports']
    is_lane2_count2 = module.params['is_lane2_count2']
    eth_list = module.params['eth_list'].split(',')
    leaf_eth_ips_last_octet = module.params['leaf_eth_ips_last_octet'].split(',')
    spine_eth_ips_last_octet = module.params['spine_eth_ips_last_octet'].split(',')

    if switch_name in spine_list:
        indx = spine_list.index(switch_name)
        last_octet = spine_eth_ips_last_octet[indx]
    else:
        indx = leaf_list.index(switch_name)
        last_octet = leaf_eth_ips_last_octet[indx]

    if is_subports:
        if not is_lane2_count2:
            subport = ['1', '2', '3', '4']
        else:
            subport = ['1', '3']
    else:
        subport = '1'

    execute_commands(module, 'goes stop')
    execute_commands(module, 'rmmod platina-mk1')
    execute_commands(module, 'modprobe platina-mk1')

    for eth in eth_list:
        for port in subport:
            cmd = 'ip link add eth-{}-{} type {}'.format(eth, port, platina_redis_channel)
            run_cli(module, cmd)

            cmd = 'ip link set eth-{}-{} up'.format(eth, port)
            run_cli(module, cmd)

            cmd = 'ethtool -s eth-{}-{} speed {}000 autoneg {}'.format(eth, port, speed[:-1], autoneg)
            run_cli(module, cmd)

            cmd = 'ifconfig eth-{}-{} 10.{}.{}.{}/24'.format(eth, port, eth, port, last_octet)
            run_cli(module, cmd)

    execute_commands(module, 'goes start')

    for eth in eth_list:
        for port in subport:
            time.sleep(1)
            cmd = 'goes hset {} vnet.eth-{}-{}.fec {}'.format(platina_redis_channel, eth, port, fec)
            run_cli(module, cmd)

    # Verify port link
    failure_summary += verify_port_links(module)

    HASH_DICT['result.detail'] = failure_summary

    # Get the GOES status info
    execute_commands(module, 'goes status')


def verify_port_links(module):
    """
    Method to execute and verify port links.
    :param module: The Ansible module to fetch input parameters.
    """
    global RESULT_STATUS, HASH_DICT
    failure_summary = ''
    switch_name = module.params['switch_name']
    speed = module.params['speed']
    media = module.params['media']
    fec = module.params['fec']
    autoneg = module.params['autoneg']
    platina_redis_channel = module.params['platina_redis_channel']
    is_subports = module.params['is_subports']
    is_lane2_count2 = module.params['is_lane2_count2']
    eth_list = module.params['eth_list'].split(',')

    if is_subports:
        if not is_lane2_count2:
            subport = ['1', '2', '3', '4']
        else:
            subport = ['1', '3']
    else:
        subport = '1'

    # Verify link
    for eth in eth_list:
        for port in subport:
            cmd = 'goes hget {} vnet.eth-{}-{}.link'.format(platina_redis_channel, eth, port)
            out = execute_commands(module, cmd)
            if 'true' not in out:
                RESULT_STATUS = False
                failure_summary += 'On switch {} '.format(switch_name)
                failure_summary += 'port link is not up '
                failure_summary += 'for the interface eth-{}-{}\n'.format(eth, port)

    # Verify media
    for eth in eth_list:
        for port in subport:
            cmd = 'goes hget {} vnet.eth-{}-{}.media'.format(platina_redis_channel, eth, port)
            out = execute_commands(module, cmd)
            if media not in out:
                RESULT_STATUS = False
                failure_summary += 'On switch {} '.format(switch_name)
                failure_summary += 'interface media is not set to {} '.format(media)
                failure_summary += 'for the interface eth-{}-{}\n'.format(eth, port)

    # Verify fec
    for eth in eth_list:
        for port in subport:
            cmd = 'goes hget {} vnet.eth-{}-{}.fec'.format(platina_redis_channel, eth, port)
            out = execute_commands(module, cmd)
            if fec not in out:
                RESULT_STATUS = False
                failure_summary += 'On switch {} '.format(switch_name)
                failure_summary += 'fec is not set to {} for '.format(fec)
                failure_summary += 'the interface eth-{}-{}\n'.format(eth, port)

    # Verify speed
    if autoneg == 'on':
        speed = 'autoneg'

    for eth in eth_list:
        for port in subport:
            cmd = 'goes hget {} vnet.eth-{}-{}.speed'.format(platina_redis_channel, eth, port)
            out = execute_commands(module, cmd)
            if speed not in out:
                RESULT_STATUS = False
                failure_summary += 'On switch {} '.format(switch_name)
                failure_summary += 'speed of the interface '
                failure_summary += 'is not set to {} for '.format(speed)
                failure_summary += 'the interface eth-{}-{}\n'.format(eth, port)

    time.sleep(40)
    return failure_summary


def main():
    """ This section is for arguments parsing """
    module = AnsibleModule(
        argument_spec=dict(
            switch_name=dict(required=False, type='str'),
            spine_list=dict(required=False, type='list', default=[]),
            leaf_list=dict(required=False, type='list', default=[]),
            eth_list=dict(required=False, type='str', default=''),
            speed=dict(required=False, type='str'),
            media=dict(required=False, type='str'),
            fec=dict(required=False, type='str', default=''),
            autoneg=dict(required=False, type='str', default=''),
            leaf_eth_ips_last_octet=dict(required=False, type='str', default=''),
            spine_eth_ips_last_octet=dict(required=False, type='str', default=''),
            platina_redis_channel=dict(required=False, type='str'),
            is_subports=dict(required=False, type='bool', default=False),
            is_lane2_count2=dict(required=False, type='bool', default=False),
            hash_name=dict(required=False, type='str'),
            log_dir_path=dict(required=False, type='str'),
        )
    )

    global HASH_DICT, RESULT_STATUS

    # Set/Reset the switch
    set_switch(module)

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

