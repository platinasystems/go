// Copyright 2017 Platina Systems, Inc. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package udp

import (
	"github.com/platinasystems/go/elib/parse"
	"github.com/platinasystems/go/vnet"

	"fmt"
	"unsafe"
)

type Header struct {
	// Source and destination port.
	SrcPort, DstPort vnet.Uint16

	// Length of UDP header plus payload.
	Length vnet.Uint16

	Checksum vnet.Uint16
}

func (h *Header) String() (s string) {
	s = fmt.Sprintf("0x%x -> 0x%x", h.SrcPort.ToHost(), h.DstPort.ToHost())
	return
}

func (h *Header) Parse(in *parse.Input) {
	var ports [2]vnet.Uint16
	if !in.Parse("%v -> %v", &ports[0], &ports[1]) {
		in.ParseError()
	}
	h.SrcPort = ports[0].FromHost()
	h.DstPort = ports[1].FromHost()
}

const SizeofHeader = 8

func (h *Header) Len() uint { return SizeofHeader }
func (h *Header) Write(b []byte) {
	h.Length.Set(uint(len(b)))
	h.Checksum = 0
	type t struct{ data [SizeofHeader]byte }
	i := (*t)(unsafe.Pointer(h))
	copy(b[:], i.data[:])
}
func (h *Header) Read(b []byte) vnet.PacketHeader { return (*Header)(vnet.Pointer(b)) }

func ParseHeader(b []byte) (h *Header, payload []byte) {
	i := 0
	h = (*Header)(unsafe.Pointer(&b[i]))
	i += SizeofHeader
	payload = b[i:]
	return
}
