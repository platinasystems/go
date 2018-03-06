# ANSIBLE REGRESSION SUITE

To run any playbook, please follow below guidelines:

Make sure you are in `go/ansible/regtest` directory.

Once you are in this path, all playbooks can be found inside `playbooks/` directory. 

Before executing the playbook, make sure the required package (quagga/bird/frr/gobgp) is installed in the testbed, on which you are trying to execute the playbook. All package installation playbooks can be found in `playbooks/installation` directory.

Suppose, you want to execute `bird_bgp_peering_ebgp_route_advertise.yml` playbook on testbed2, then first run package uninstallation playbook to make sure no protocol stack is present in the testbed, by executing this command:

```
    ansible-playbook -i hosts_testbed2 playbooks/installation/uninstall_packages.yml -K
```

And then run the bird installation playbook using this command:

```
    ansible-playbook -i hosts_testbed2 playbooks/installation/bird_install.yml -K
```

And then run the bird_bgp_peering_ebgp_route_advertise.yml playbook by executing this command:

```
    ansible-playbook -i hosts_testbed2 playbooks/bgp/bird_bgp_peering_ebgp_route_advertise.yml -K
```


NOTES:
-----

Each playbook run generate logs that gets stored in redis db on invader28 and on all invaders at location /var/log/regression/.

To access redis on invader28, use this command: `redis-cli -p 9090`

Log file on an invader consists of configuration done, verification commands executed on that invader followed by verification/result details and goes status.

If you want to reproduce any issue or debug the config then set reset_config flag to False while running the playbook (by default it's set to True). This will execute the playbook without resetting the config/setup. You can then ssh into any invaders and see the actual config present in respective package directory. For example:
```
    ansible-playbook -i hosts_testbed2 playbooks/bgp/frr_bgp_peering_ibgp.yml -K -e reset_config=False
```

Once you are done with debugging and wants to reset the config/setup then just run reset playbook. For example:
```
    ansible-playbook -i hosts_testbed2 playbooks/bgp/frr_bgp_peering_ibgp_reset.yml -K
```

Each playbook has it's own reset playbook which is appended with '_reset.yml', except for port provision playbooks. For example, `playbooks/ospf/quagga_ospf_basic.yml` playbook has it's own reset playbook (which by default get's executed) named `playbooks/ospf/quagga_ospf_basic_reset.yml`

There is only one `port_provision_reset.yml` playbook for all port provision playbooks in `playbooks/port_provision`
