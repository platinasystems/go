// Copyright 2016 Platina Systems, Inc. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package ip4

import (
	"github.com/platinasystems/go/vnet"
	"github.com/platinasystems/go/vnet/icmp4"
	"github.com/platinasystems/go/vnet/ip"
	"github.com/platinasystems/go/vnet/ip/udp"

	"unsafe"
)

func GetHeader(r *vnet.Ref) *Header { return (*Header)(r.Data()) }
func (h *Header) GetPayload() unsafe.Pointer {
	return unsafe.Pointer(uintptr(unsafe.Pointer(h)) + uintptr(4*(0xf&h.Ip_version_and_header_length)))
}

type Flow struct {
	Protocol ip.Protocol
	// icmp type otherwise 0.
	Extra uint8
	// Src, Dst port for tcp/udp; otherwise 0.
	SrcPort, DstPort vnet.Uint16
	Src, Dst         Address
}

func GetFlow(r *vnet.Ref) Flow {
	h := GetHeader(r)
	p := h.GetPayload()
	return h.getFlow(p)
}
func (h *Header) GetFlow(payload []byte) Flow {
	p := (*byte)(nil)
	if payload != nil {
		p = &payload[0]
	}
	return h.getFlow(unsafe.Pointer(p))
}

func (h *Header) getFlow(p unsafe.Pointer) (f Flow) {
	f.Protocol = h.Protocol
	f.Src, f.Dst = h.Src, h.Dst
	switch f.Protocol {
	case ip.ICMP:
		h := (*icmp4.Header)(p)
		f.Extra = uint8(h.Type)
	case ip.TCP, ip.UDP:
		h := (*udp.Header)(p)
		f.SrcPort, f.DstPort = h.SrcPort, h.DstPort
	}
	return
}
func (f *Flow) Reverse() (r Flow) {
	r = *f
	r.Src, r.Dst = r.Dst, r.Src
	r.SrcPort, r.DstPort = r.DstPort, r.SrcPort
	return
}

type nodeMain struct {
	inputNode              inputNode
	inputValidChecksumNode inputValidChecksumNode
	rewriteNode            inputNode
	arpNode                inputNode
}

func (m *Main) nodeInit(v *vnet.Vnet) {
	m.inputNode.Next = []string{
		input_next_drop: "error",
		input_next_punt: "punt",
	}
	v.RegisterInOutNode(&m.inputNode, "ip4-input")
	m.inputValidChecksumNode.Next = m.inputNode.Next
	v.RegisterInOutNode(&m.inputValidChecksumNode, "ip4-input-valid-checksum")
	v.RegisterInOutNode(&m.arpNode, "ip4-arp")
	v.RegisterInOutNode(&m.rewriteNode, "ip4-rewrite")
}

const (
	input_next_drop = iota
	input_next_punt
)

type inputNode struct{ vnet.InOutNode }

func (node *inputNode) NodeInput(in *vnet.RefIn, out *vnet.RefOut) {
	node.Redirect(in, out, input_next_punt)
}

type inputValidChecksumNode struct{ vnet.InOutNode }

func (node *inputValidChecksumNode) NodeInput(in *vnet.RefIn, out *vnet.RefOut) {
	node.Redirect(in, out, input_next_punt)
}
