#!/usr/bin/python
""" Docker Up Down Vlan """

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
module: docker_updown_vlan
author: Platina Systems
short_description: Module to bring up and bring down docker containers for vlan.
description:
    Module to bring up and bring down docker containers for vlan.
options:
    switch_name:
      description:
        - Name of the switch on which tests will be performed.
      required: False
      type: str
    config_file:
      description:
        - Config details of docker container.
      required: False
      type: str
    state:
      description:
        - String describing if docker container has to be brought up or down.
      required: False
      type: str
      choices: ['up', 'down']
"""

EXAMPLES = """
- name: Bring up docker container
  docker_updown_vlan:
    config_file: "{{ lookup('file', '../../group_vars/{{ inventory_hostname }}/{{ item }}') }}"
    state: 'up'
"""

RETURN = """
msg:
  description: String describing docker container state.
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
        return out
    elif err:
        return err
    else:
        return None


def main():
    """ This section is for arguments parsing """
    module = AnsibleModule(
        argument_spec=dict(
            switch_name=dict(required=False, type='str'),
            config_file=dict(required=False, type='str'),
            state=dict(required=False, type='str', choices=['up', 'down']),
        )
    )

    d_move = '~/./docker_move.sh'
    switch_name = module.params['switch_name']
    container_name = None
    eth_list = []
    subport = 1
    vlan_id = []
    eth_second_octet, eth_third_octet = [], 0
    config_file = module.params['config_file'].splitlines()

    for line in config_file:
        if 'container_name' in line:
            container_name = line.split()[1]
        elif 'interface' in line:
            eth = line.split()[1]
            eth_list.append(eth)
        elif 'vlan_id' in line:
            vlan = line.split()[1]
            vlan_id.append(vlan)
        elif 'Second_Octet' in line:
            second = line.split()[1]
            eth_second_octet.append(second)
        elif 'Third_Octet' in line:
            eth_third_octet = line.split()[1]
        elif 'subport' in line:
            subport = line.split()[1]

    container_id = container_name[1::]
    dummy_id = int(container_id)
    dummy_third_octet = int(container_name[1::])/10
    dummy_forth_octet = int(container_name[-1])

    if module.params['state'] == 'up':
        # Add dummy interface and bring it up
        cmd = 'ip link add dummy{} type dummy 2> /dev/null'.format(dummy_id)
        run_cli(module, cmd)

        # Bring up dummy interface
        cmd = '{} up {} dummy{} 192.168.{}.{}/32'.format(
            d_move, container_name, dummy_id, dummy_third_octet, dummy_forth_octet)
        run_cli(module, cmd)

        # Bring up given interfaces in the docker container
        for i in range(len(eth_list)):
            cmd = 'ip link add link eth-{}-1 name eth-{}-1.{} type vlan id {}'.format(
                eth_list[i], eth_list[i], vlan_id[i], vlan_id[i])
            run_cli(module, cmd)

            cmd = 'ip link set up eth-{}-1.{}'.format(eth_list[i], vlan_id[i])
            run_cli(module, cmd)

            cmd = '{} up {} eth-{}-{}.{} {}.{}.{}.{}/24'.format(
                d_move, container_name, eth_list[i], subport, vlan_id[i], eth_list[i],
                eth_second_octet[i], eth_third_octet, switch_name[-2::])
            run_cli(module, cmd)
    else:
        # Bring down all interfaces in the docker container
        for i in range(len(eth_list)):
            cmd = '{} down {} eth-{}-{}.{}'.format(
                d_move, container_name, eth_list[i], subport, vlan_id[i])
            run_cli(module, cmd)

            cmd = 'ip link set down eth-{}-1.{}'.format(eth_list[i], vlan_id[i])
            run_cli(module, cmd)

            cmd = 'ip link del eth-{}-1.{}'.format(eth_list[i], vlan_id[i])
            run_cli(module, cmd)

        # Bring down dummy interface
        cmd = '{} down {} dummy{}'.format(d_move, container_name, dummy_id)
        run_cli(module, cmd)

    # Exit the module and return the required JSON.
    module.exit_json(
        msg='Module executed successfully'
    )

if __name__ == '__main__':
    main()

