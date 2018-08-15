// Copyright © 2017 Platina Systems, Inc. All rights reserved.
// Use of this source code is governed by the GPL-2 license described in the
// LICENSE file.

package nvram

import (
	"github.com/platinasystems/go/goes/lang"
)

const (
	Name    = "nvram"
	Apropos = "nvram"
	Usage   = "nvram"
	Man     = `
DESCRIPTION
	Manipulates the PC CMOS (nvram)
`
)

var (
	apropos = lang.Alt{
		lang.EnUS: Apropos,
	}
	man = lang.Alt{
		lang.EnUS: Man,
	}
)

type Command struct{}

func (Command) Apropos() lang.Alt { return apropos }
func (*Command) Man() lang.Alt    { return man }
func (Command) String() string    { return Name }
func (Command) Usage() string     { return Usage }

func (c Command) Main(args ...string) error {
	return nil
}
