// Copyright © 2015-2017 Platina Systems, Inc. All rights reserved.
// Use of this source code is governed by the GPL-2 license described in the
// LICENSE file.

package main

import (
	"bytes"
	"flag"
	"testing"
	"text/template"
	"time"

	"github.com/platinasystems/go/internal/test"
	"github.com/platinasystems/go/internal/test/docker"
	"github.com/platinasystems/go/main/goes-platina-mk1/test/frr/bgp"
	"github.com/platinasystems/go/main/goes-platina-mk1/test/frr/isis"
	"github.com/platinasystems/go/main/goes-platina-mk1/test/frr/ospf"
	"github.com/platinasystems/go/main/goes-platina-mk1/test/net/dhcp"
	"github.com/platinasystems/go/main/goes-platina-mk1/test/net/slice"
	"github.com/platinasystems/go/main/goes-platina-mk1/test/net/static"
	"github.com/platinasystems/go/main/goes-platina-mk1/test/port2port"
)

var testPause = flag.Bool("test.pause", false, "pause before and after suite")

func Test(t *testing.T) {
	test.Main(main)

	assert := test.Assert{t}
	assert.YoureRoot()
	assert.GoesNotRunning()

	assert.Nil(docker.Check(t))

	defer assert.Background(test.Self{}, "redisd").Quit()
	assert.Program(12*time.Second, test.Self{}, "hwait", "platina",
		"redis.ready", "true", "10")

	vnetd := assert.Background(30*time.Second, test.Self{}, "vnetd")
	defer vnetd.Quit()
	assert.Program(32*time.Second, test.Self{}, "hwait", "platina",
		"vnet.ready", "true", "30")

	if *testPause {
		test.Pause("Attach vnet debugger to pid(", vnetd.Pid(), ");\n",
			"then press enter to continue...")
		defer test.Pause("complete, press enter to continue...")
	}

	test.Suite{
		{"vnet.ready", func(*testing.T) {}},
		{"net", test.Suite{
			{"slice", test.Suite{
				{"vlan", func(t *testing.T) {
					slice.Test(t, conf(t, "net-slice-vlan",
						slice.ConfVlan))
				}},
			}.Run},
			{"dhcp", test.Suite{
				{"eth", func(t *testing.T) {
					dhcp.Test(t, conf(t, "net-dhcp-eth",
						dhcp.Conf))
				}},
				{"vlan", func(t *testing.T) {
					dhcp.Test(t, conf(t, "net-dhcp-vlan",
						dhcp.ConfVlan))
				}},
			}.Run},
			{"static", test.Suite{
				{"eth", func(t *testing.T) {
					static.Test(t, conf(t, "net-static-eth",
						static.Conf))
				}},
				{"vlan", func(t *testing.T) {
					static.Test(t, conf(t, "net-static-vlan",
						static.ConfVlan))
				}},
			}.Run},
		}.Run},
		{"ospf", test.Suite{
			{"eth", func(t *testing.T) {
				ospf.Test(t, conf(t, "ospf", ospf.Conf))
			}},
			{"vlan", func(t *testing.T) {
				ospf.Test(t, conf(t, "ospf-vlan",
					ospf.ConfVlan))
			}},
		}.Run},
		{"isis", test.Suite{
			{"eth", func(t *testing.T) {
				isis.Test(t, conf(t, "isis", isis.Conf))
			}},
			{"vlan", func(t *testing.T) {
				isis.Test(t, conf(t, "isis-vlan",
					isis.ConfVlan))
			}},
		}.Run},
		{"bgp", test.Suite{
			{"eth", func(t *testing.T) {
				bgp.Test(t, conf(t, "bgp", bgp.Conf))
			}},
			{"vlan", func(t *testing.T) {
				bgp.Test(t, conf(t, "bgp-vlan", bgp.ConfVlan))
			}},
		}.Run},
	}.Run(t)
}

func conf(t *testing.T, name, text string) []byte {
	assert := test.Assert{t}
	assert.Helper()
	tmpl, err := template.New(name).Parse(text)
	assert.Nil(err)
	buf := new(bytes.Buffer)
	assert.Nil(tmpl.Execute(buf, port2port.Conf))
	return buf.Bytes()
}