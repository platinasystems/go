// Copyright © 2015-2016 Platina Systems, Inc. All rights reserved.
// Use of this source code is governed by the GPL-2 license described in the
// LICENSE file.

package netlink

import (
	"github.com/platinasystems/go/vnet"
)

// FOU Foo over UDP support for netlink.
const (
	FOU_CMD_UNSPEC = iota
	FOU_CMD_ADD
	FOU_CMD_DEL
	FOU_CMD_GET
)

const (
	FOU_ATTR_UNSPEC            = iota
	FOU_ATTR_PORT              /* u16 */
	FOU_ATTR_AF                /* u8 */
	FOU_ATTR_IPPROTO           /* u8 */
	FOU_ATTR_TYPE              /* u8 */
	FOU_ATTR_REMCSUM_NOPARTIAL /* flag */
)

// FOU_ATTR_TYPE
const (
	FOU_ENCAP_UNSPEC = iota
	FOU_ENCAP_DIRECT
	FOU_ENCAP_GUE
)

type fouFamily struct {
	genericFamily
}

var FouFamily = &genericFamily{
	name: "fou",
	cmdNames: []string{
		FOU_CMD_UNSPEC: "UNSPEC",
		FOU_CMD_ADD:    "ADD",
		FOU_CMD_DEL:    "DEL",
		FOU_CMD_GET:    "GET",
	},
	attrNames: []string{
		FOU_ATTR_UNSPEC:            "UNSPEC",
		FOU_ATTR_PORT:              "PORT",
		FOU_ATTR_AF:                "AF",
		FOU_ATTR_IPPROTO:           "IPPROTO",
		FOU_ATTR_TYPE:              "TYPE",
		FOU_ATTR_REMCSUM_NOPARTIAL: "REMCSUM_NOPARTIAL",
	},
	attrTypes: []Attr{
		FOU_ATTR_UNSPEC:            EmptyAttr{},
		FOU_ATTR_PORT:              Uint16Attr(0),
		FOU_ATTR_AF:                Uint8Attr(0),
		FOU_ATTR_IPPROTO:           Uint8Attr(0),
		FOU_ATTR_TYPE:              Uint8Attr(0),
		FOU_ATTR_REMCSUM_NOPARTIAL: EmptyAttr{},
	},
}

type FouPort struct {
	AddressFamily    AddressFamily
	Encap            uint8
	IpProtocol       uint8
	RemCsumNopartial bool
	// UDP port in network byte order.
	UdpPort vnet.Uint16
}

// FOU state.
type FouMain struct {
	Ports map[FouPort]struct{}
}

// Get fetches initial FOU state.
func (m *FouMain) Get(s *Socket) (err error) {
	var msg *GenericMessage
	if msg, err = s.NewGenericRequest(FouFamily, FOU_CMD_GET); err != nil {
		return
	}
	msg.Flags = NLM_F_REQUEST | NLM_F_DUMP
	s.Tx <- msg
	for {
		repMsg := <-s.Rx
		if rep, ok := repMsg.(*GenericMessage); !ok {
			break
		} else {
			p := FouPort{
				Encap:         rep.Attrs[FOU_ATTR_TYPE].(Uint8Attr).Uint(),
				AddressFamily: AddressFamily(rep.Attrs[FOU_ATTR_AF].(Uint8Attr).Uint()),
				IpProtocol:    rep.Attrs[FOU_ATTR_IPPROTO].(Uint8Attr).Uint(),
				UdpPort:       vnet.Uint16(rep.Attrs[FOU_ATTR_PORT].(Uint16Attr).Uint()),
			}
			m.addDelPort(p, false)
		}
	}
	return
}

func (m *FouMain) addDelPort(p FouPort, isDel bool) {
	if isDel {
		delete(m.Ports, p)
	} else {
		if m.Ports == nil {
			m.Ports = make(map[FouPort]struct{})
		}
		m.Ports[p] = struct{}{}
	}
}

// AddDel adds/deletes FOU ports.
func (m *FouMain) AddDel(s *Socket, p FouPort, isDel bool) (err error) {
	var msg *GenericMessage
	cmd := FOU_CMD_ADD
	if isDel {
		cmd = FOU_CMD_DEL
	}
	if msg, err = s.NewGenericRequest(FouFamily, cmd); err != nil {
		return
	}
	msg.Attrs[FOU_ATTR_TYPE] = Uint8Attr(p.Encap)
	msg.Attrs[FOU_ATTR_AF] = Uint8Attr(p.AddressFamily)
	msg.Attrs[FOU_ATTR_IPPROTO] = Uint8Attr(p.IpProtocol)
	msg.Attrs[FOU_ATTR_PORT] = Uint16Attr(p.UdpPort)
	s.Tx <- msg
	m.addDelPort(p, isDel)
	return
}
