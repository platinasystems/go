#!/usr/bin/python
""" Verify Interface Speed """

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
module: verify_interface_speed
author: Platina Systems
short_description: Module to verify interface speed in redis.
description:
    Module to verify if interface speed value in redis is set correctly.
options:
    switch_name:
      description:
        - Name of the switch on which goes health will be checked.
      required: False
      type: str
    start_file:
      description:
        - Start file configured on the invader.
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
    platina_redis_channel:
      description:
        - Name of the platina redis channel.
      required: False
      type: str
"""

EXAMPLES = """
- name: Verify if speed is set correctly in redis
  verify_interface_speed:
    switch_name: "{{ inventory_hostname }}"
    start_file: "{{ lookup('file', '../../templates/issue_10_start_file') }}"
    platina_redis_channel: "platina-mk1"
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
            start_file=dict(required=False, type='str'),
            platina_redis_channel=dict(required=False, type='str'),
            hash_name=dict(required=False, type='str'),
            log_dir_path=dict(required=False, type='str'),
        )
    )

    global HASH_DICT, RESULT_STATUS
    failure_summary = ''
    switch_name = module.params['switch_name']
    platina_redis_channel = module.params['platina_redis_channel']
    start_file = module.params['start_file'].splitlines()

    # Get speed values of interfaces from redis
    redis_speed = execute_commands(module, 'goes hget {} speed'.format(
        platina_redis_channel
    ))

    # Get speed values of interfaces from start file
    for line in start_file:
        line = line.strip()
        if 'speed' in line:
            speed = line.split('speed ')[1]
            eth = line.split('{} '.format(platina_redis_channel))[1].split()[0]

            speed = 'autoneg' if speed == 'auto' else speed
            interface_speed = '{}: {}'.format(eth, speed)

            # Verify if speed is correctly set in redis against the start file
            if interface_speed not in redis_speed:
                RESULT_STATUS = False
                failure_summary += 'On switch {} '.format(switch_name)
                failure_summary += '{} '.format(eth)
                failure_summary += 'in redis is not set to {}\n'.format(speed)

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

