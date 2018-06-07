// Copyright © 2015-2018 Platina Systems, Inc. All rights reserved.
// Use of this source code is governed by the GPL-2 license described in the
// LICENSE file.

// DESCRIPTION
// http server to be incorporated in to the master server
// include in goes only for debugging

package serverd

import (
	"fmt"
	"net/http"
	"strconv"
	"strings"

	"github.com/platinasystems/go/goes/cmd"
	"github.com/platinasystems/go/goes/lang"
	"github.com/platinasystems/go/internal/log"
)

type Command chan struct{}

func (Command) String() string { return "bootd" }

func (Command) Usage() string { return "bootd" }

func (Command) Apropos() lang.Alt {
	return lang.Alt{
		lang.EnUS: "http boot controller daemon",
	}
}

func (c Command) Close() error {
	close(c)
	return nil
}

func (Command) Kind() cmd.Kind { return cmd.Daemon }

func (c Command) Main(...string) error {
	if err := startHandler(); err != nil {
		return err
	}
	return nil
}

func startHandler() (err error) {
	ClientCfg = make(map[string]*Client)
	ClientBootCfg = make(map[string]*BootcConfig)
	if err = readClientCfgDB(); err != nil {
		return
	}

	http.HandleFunc("/", serve)
	if err = http.ListenAndServe(":9090", nil); err != nil {
		log.Print("HTTP Server failed.")
		return
	}
	return
}

func serve(w http.ResponseWriter, r *http.Request) {
	var b = ""
	var err error

	r.ParseForm()
	t := strings.Replace(r.URL.Path, "/", "", -1)
	u := strings.Split(t, " ")

	switch u[0] {
	case Register:
		if b, err = register(&u); err != nil {
			b = "error registering\n"
		}
	case DumpVars:
		if b, err = dumpvars(); err != nil {
			b = "error dumping server variables\n"
		}
		b += r.URL.Path + "\n"
		b += t + "\n"
	case NumClients:
		if b, err = numclients(); err != nil {
			b = "error getting number of clients\n"
		}
	case ClientData:
		if len(u) < 2 {
			b = "error client number missing\n"
			return
		}
		i, _ := strconv.Atoi(u[1])
		if b, err = clientdata(i); err != nil {
			b = "error getting client data\n"
		}
	case ClientBootData:
		if len(u) < 2 {
			b = "error client number missing\n"
			return
		}
		i, _ := strconv.Atoi(u[1])
		if b, err = clientbootdata(i); err != nil {
			b = "error getting client boot data\n"
		}
	default:
		b = "404\n"
	}

	fmt.Println("scheme", r.URL.Scheme)
	fmt.Println(r.Form["url_long"])
	for k, v := range r.Form {
		fmt.Println("key:", k)
		fmt.Println("val:", strings.Join(v, ""))
	}
	log.Print("serve exit ", b)
	fmt.Fprintf(w, b)
}