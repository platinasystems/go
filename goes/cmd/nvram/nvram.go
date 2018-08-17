// Copyright © 2017 Platina Systems, Inc. All rights reserved.
// Use of this source code is governed by the GPL-2 license described in the
// LICENSE file.

package nvram

import (
	"fmt"
	"syscall"

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

func (c Command) scan(d []byte, start, end uint64) {
	for i := start; i < end; i = i + 16 {
		if (d[0] == 'L' && d[1] == 'B' && d[2] == 'I' && d[3] == 'O') ||
			(d[3] == 'L' && d[2] == 'B' && d[1] == 'I' && d[0] == 'O') {
			fmt.Printf("%v\n", i)
		}
	}
}

func (c Command) Main(args ...string) error {
	fd, err := syscall.Open("/dev/mem", syscall.O_RDONLY, 0)
	if err != nil {
		return err
	}
	d, err := syscall.Mmap(fd, 0, 0x100000, syscall.PROT_READ, syscall.MAP_SHARED)
	if err != nil {
		return err
	}
	c.scan(d, 0x0, 0x1000)
	c.scan(d, 0xf0000, 0x100000)
	return nil
}
