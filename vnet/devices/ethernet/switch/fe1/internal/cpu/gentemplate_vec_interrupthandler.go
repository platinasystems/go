// Copyright 2016 Platina Systems, Inc. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

// autogenerated: do not edit!
// generated from gentemplate [gentemplate -d Package=cpu.-id interruptHandler -d VecType=interruptHandlerVec -d Type=interruptHandler github.com/platinasystems/go/elib/vec.tmpl]

package cpu

import (
	"github.com/platinasystems/go/elib"
)

type interruptHandlerVec []interruptHandler

func (p *interruptHandlerVec) Resize(n uint) {
	c := elib.Index(cap(*p))
	l := elib.Index(len(*p)) + elib.Index(n)
	if l > c {
		c = elib.NextResizeCap(l)
		q := make([]interruptHandler, l, c)
		copy(q, *p)
		*p = q
	}
	*p = (*p)[:l]
}

func (p *interruptHandlerVec) validate(i uint, zero *interruptHandler) *interruptHandler {
	c := elib.Index(cap(*p))
	l := elib.Index(i) + 1
	if l > c {
		cNext := elib.NextResizeCap(l)
		q := make([]interruptHandler, cNext, cNext)
		copy(q, *p)
		if zero != nil {
			for i := c; i < cNext; i++ {
				q[i] = *zero
			}
		}
		*p = q[:l]
	}
	if l > elib.Index(len(*p)) {
		*p = (*p)[:l]
	}
	return &(*p)[i]
}
func (p *interruptHandlerVec) Validate(i uint) *interruptHandler {
	return p.validate(i, (*interruptHandler)(nil))
}
func (p *interruptHandlerVec) ValidateInit(i uint, zero interruptHandler) *interruptHandler {
	return p.validate(i, &zero)
}

func (p interruptHandlerVec) Len() uint { return uint(len(p)) }