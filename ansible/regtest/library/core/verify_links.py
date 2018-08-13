#!/usr/bin/python
""" Verify Links """

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

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: verify_links
author: Platina Systems
short_description: Module to verify link status.
description:
    Module to verify link status and ping.
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
    eth_list:
      description:
        - List of eth interfaces described as string.
      required: False
      type: str
    platina_redis_channel:
      description:
        - Name of the platina redis channel.
      required: False
      type: str
"""

EXAMPLES = """
- name: Ping verification for directly connected interfaces
  verify_links:
    switch_name: "{{ inventory_hostname }}"
    leaf_list: "{{ groups['leaf'] }}"
    eth_list: "1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31"
    platina_redis_channel: "{{ platina_redis_channel }}"
"""

RETURN = """
msg:
  description: String describing the link status b/w invaders
  returned: always
  type: str
"""


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


def main():
    """ This section is for arguments parsing """
    module = AnsibleModule(
        argument_spec=dict(
            switch_name=dict(required=False, type='str'),
            leaf_list=dict(required=False, type='list', default=[]),
            eth_list=dict(required=False, type='str'),
            platina_redis_channel=dict(required=False, type='str')
        )
    )

    switch_name = module.params['switch_name']
    leaf_list = module.params['leaf_list']
    eth_list = module.params['eth_list'].split(',')
    platina_redis_channel = module.params['platina_redis_channel']

    is_leaf = True if switch_name in leaf_list else False
    msg = ''
    result_status = True

    for eth in eth_list:
        cmd = 'goes hget {} vnet.eth-{}-1.link'.format(platina_redis_channel, eth)
        link_status = run_cli(module, cmd)

        if 'true' not in link_status:
            result_status = False
            msg += 'On switch {} '.format(switch_name)
            msg += 'port link is not up for '
            msg += 'eth-{}-1 interface\n'.format(eth)

    if is_leaf and result_status:
        if leaf_list.index(switch_name) == 0:
            last_octet1 = '31'
            last_octet2 = '32'
        else:
            last_octet1 = '32'
            last_octet2 = '31'
#            time.sleep(50)

        for eth in range(1, 16, 2):
            ip = '10.0.{}.{}'.format(eth, last_octet1)
            cmd = 'ping -c 3 {}'.format(ip)
            ping_out = run_cli(module, cmd)
            if '100% packet loss' in ping_out:
                result_status = False
                msg += 'On switch {} '.format(switch_name)
                msg += 'unable to ping interface ip {}\n'.format(ip)
		msg += 'Ping Out:\n{}\n'.format(ping_out)
            time.sleep(1)

        for eth in range(17, 32, 2):
            ip = '10.0.{}.{}'.format(eth, last_octet2)
            cmd = 'ping -c 3 {}'.format(ip)
            ping_out = run_cli(module, cmd)
            if '100% packet loss' in ping_out:
                result_status = False
                msg += 'On switch {} '.format(switch_name)
                msg += 'unable to ping interface ip {}\n'.format(ip)
                msg += 'Ping Out:\n{}\n'.format(ping_out)
            time.sleep(1)

    if result_status:
        msg = 'Links b/w invaders are UP\n'

    module.exit_json(
        msg=msg
    )


if __name__ == '__main__':
    main()

