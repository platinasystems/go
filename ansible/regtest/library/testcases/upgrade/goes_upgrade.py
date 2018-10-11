#!/usr/bin/python
""" GOES Upgrade """

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
module: goes_upgrade
author: Platina Systems
short_description: Module to upgrade goes.
description:
    Module to upgrade goes version to latest.
options:
    switch_name:
      description:
        - Name of the switch on which tests will be performed.
      required: False
      type: str
    installer_dir:
      description:
        - Directory path where GOES upgrade installer file is stored.
      required: False
      type: str
    installer_name:
      description:
        - Name of the GOES upgrade installer file.
      required: False
      type: str
    coreboot:
      description:
        - Flag to indicate if coreboot upgrade file to be used.
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
- name: Upgrade goes
  goes_upgrade:
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


def verify_goes_status(module, switch_name):
    """
    Method to verify if goes status is ok or not
    :param module: The Ansible module to fetch input parameters.
    :param switch_name: Name of the switch.
    :return: String describing if goes status is ok or not
    """
    global RESULT_STATUS
    failure_summary = ''

    # Get the GOES status info
    goes_status = execute_commands(module, 'goes status')

    if 'not ok' in goes_status.lower():
        RESULT_STATUS = False
        failure_summary += 'On switch {} '.format(switch_name)
        failure_summary += 'goes status is not ok\n'

    return failure_summary


def get_core_boot_version(module):
    """
    Method to get core boot version
    :param module: The Ansible module to fetch input parameters.
    :return: Core boot version
    """
    version_out = execute_commands(module, 'goes upgrade -r')
    version_out = version_out.splitlines()
    for line in version_out:
        line = line.strip()
        if 'version:' in line.lower():
            return line.split()[1]


def upgrade_goes(module):
    """
    Method to upgrade goes version.
    :param module: The Ansible module to fetch input parameters.
    """
    global RESULT_STATUS, HASH_DICT
    failure_summary = ''
    switch_name = module.params['switch_name']
    installer_dir = module.params['installer_dir']
    installer_name = module.params['installer_name']

    # Verify goes status before upgrade
    failure_summary += verify_goes_status(module, switch_name)

    # Get core boot version before upgrade
    before_upgrade_version = get_core_boot_version(module)

    # Upgrade goes
    if module.params['coreboot']:
        cmd = '/usr/local/sbin/flashrom -p internal '
        cmd += '-l /usr/local/share/flashrom/layouts/platina-mk1.xml -i bios '
        cmd += '-w {}./{} -A -V'.format(installer_dir, installer_name)
        upgrade_out = execute_commands(module, cmd)
    else:
        cmd = '{}./{}'.format(installer_dir, installer_name)
        upgrade_out = execute_commands(module, cmd)

    if upgrade_out is not None:
        if 'timeout' in upgrade_out or 'exit status 1' in upgrade_out:
            RESULT_STATUS = False
            failure_summary += 'On switch {} '.format(switch_name)
            failure_summary += 'goes upgrade failed\n'

    # Verify goes status after upgrade
    failure_summary += verify_goes_status(module, switch_name)

    # Get core boot version after upgrade
    after_upgrade_version = get_core_boot_version(module)

    failure_summary += 'On switch {}, upgraded core boot version from {} to {}'.format(
        switch_name, before_upgrade_version, after_upgrade_version
    )

    HASH_DICT['result.detail'] = failure_summary


def main():
    """ This section is for arguments parsing """
    module = AnsibleModule(
        argument_spec=dict(
            switch_name=dict(required=False, type='str'),
            installer_dir=dict(required=False, type='str'),
            installer_name=dict(required=False, type='str'),
            coreboot=dict(required=False, type='bool', default='False'),
            hash_name=dict(required=False, type='str'),
            log_dir_path=dict(required=False, type='str'),
        )
    )

    global HASH_DICT, RESULT_STATUS

    upgrade_goes(module)

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

