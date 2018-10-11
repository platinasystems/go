#!/usr/bin/python
""" Get failure summary """

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
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

import shlex

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: get_failure_summary
author: Platina Systems
short_description: Module to get failure summary from redis db.
description:
    Module to get failure summary of all failed test cases from redis db using hash on server emulator.
options:
    summary_report_file:
      description:
        - Summary report file containing executed test cases names along with Passed/Failed result.
      required: False
      type: str
"""

EXAMPLES = """
- name: Get failure summary of Failed test cases
  get_failure_summary:
    summary_report_file: "{{ lookup('file', '{{ regression_summary_report }}') }}"
"""

RETURN = """
result_detail:
  description: String describing failure summary details of the failed test cases.
  returned: always
  type: str
"""


def get_cli():
    """
    Method to get the initial cli string.
    :return: Initial cli string.
    """
    return 'redis-cli -p 9090 '


def run_cli(module, cli):
    """
    Method to execute the cli command on the target node(s) and returns the
    output.
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
            summary_report_file=dict(required=False, type='str'),
        )
    )

    summary = ''
    failure_summary = []

    for line in module.params['summary_report_file'].splitlines():
        if 'Failed' in line:
            hash_name = line.split()[0][:-1]
            cli = get_cli()
            cli += '--raw hget {0} {1}'.format(hash_name, 'result.detail')
            out = run_cli(module, cli)
            detail = 'None' if out.isspace() else out
            summary += '{}{}'.format(line, detail)

    if summary:
        summary = filter(bool, summary.splitlines())
        failure_summary = []
        for line in summary:
            if 'Failed' in line and summary.index(line) != 0:
                failure_summary.append('\n')
                failure_summary.append(line)
            else:
                failure_summary.append(line)

    # Exit the module and return the required JSON.
    module.exit_json(
        stdout_lines=failure_summary
    )


if __name__ == '__main__':
    main()

