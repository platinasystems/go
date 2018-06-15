#!/usr/bin/python
""" Reset Invaders """

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

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: reset_invaders
author: Platina Systems
short_description: Module to reset invaders.
description:
    Module to reset invaders and add eth interfaces.
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
"""

EXAMPLES = """
- name: Reset invaders
  reset_invaders:
    switch_name: "{{ inventory_hostname }}"
    eth_list: "2,4,6,8,10,12,14,16"
    platina_redis_channel: 'platina-mk1'
"""

RETURN = """
msg:
  description: String describing if invader got reset
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
            spine_list=dict(required=False, type='list', default=[]),
            leaf_list=dict(required=False, type='list', default=[]),
            leaf_eth_ips_last_octet=dict(required=False, type='str', default=''),
            spine_eth_ips_last_octet=dict(required=False, type='str', default=''),
            platina_redis_channel=dict(required=False, type='str'),
        )
    )

    switch_name = module.params['switch_name']
    spine_list = module.params['spine_list']
    leaf_list = module.params['leaf_list']
    platina_redis_channel = module.params['platina_redis_channel']
    leaf_eth_ips_last_octet = module.params['leaf_eth_ips_last_octet'].split(',')
    spine_eth_ips_last_octet = module.params['spine_eth_ips_last_octet'].split(',')
    eth_list = range(1, 33)

    if switch_name in spine_list:
        indx = spine_list.index(switch_name)
        last_octet = spine_eth_ips_last_octet[indx]
    else:
        indx = leaf_list.index(switch_name)
        last_octet = leaf_eth_ips_last_octet[indx]

    run_cli(module, 'goes stop')
    run_cli(module, 'rmmod {}'.format(platina_redis_channel))
    run_cli(module, 'modprobe {}'.format(platina_redis_channel))

    for eth in eth_list:
        cmd = 'ip link add eth-{}-1 type {}'.format(eth, platina_redis_channel)
        run_cli(module, cmd)

        cmd = 'ip link set eth-{}-1 up'.format(eth)
        run_cli(module, cmd)

        cmd = 'ethtool -s eth-{}-1 speed 100000 autoneg off'.format(eth)
        run_cli(module, cmd)

        cmd = 'ifconfig eth-{}-1 10.0.{}.{}/24'.format(eth, eth, last_octet)
        run_cli(module, cmd)

    run_cli(module, 'goes start')

    module.exit_json(
        msg='Reset all invaders'
    )


if __name__ == '__main__':
    main()

