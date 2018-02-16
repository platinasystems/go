// Copyright © 2015-2016 Platina Systems, Inc. All rights reserved.
// Use of this source code is governed by the GPL-2 license described in the
// LICENSE file.

// Package rpc provides remote calls to a redis server.
package rpc

import (
	"github.com/platinasystems/go/internal/redis/rpc/args"
	"github.com/platinasystems/go/internal/redis/rpc/reply"
	"github.com/platinasystems/go/internal/sockfile"
	"strings"
	"strconv"
	"fmt"
)

var empty = struct{}{}

type Rpc struct{ File, Name string }

func New(file, name string) *Rpc { return &Rpc{file, name} }

func (rpc *Rpc) Del(key string, keys ...string) (int, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return 0, err
	}
	defer cl.Close()
	var r reply.Del
	err = cl.Call(rpc.Name+".Del", args.Del{key, keys}, &r)
	if err != nil {
		return 0, err
	}
	return r.Redis(), nil
}

func (rpc *Rpc) Get(key string) ([]byte, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return nil, err
	}
	defer cl.Close()
	var r reply.Get
	err = cl.Call(rpc.Name+".Get", args.Get{key}, &r)
	if err != nil {
		return nil, err
	}
	return r.Redis(), nil
}

func (rpc *Rpc) Set(key string, value []byte) error {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return err
	}
	defer cl.Close()
	return cl.Call(rpc.Name+".Set", args.Set{key, value}, &empty)
}

func (rpc *Rpc) Hdel(key, field string, fields ...string) (int, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return 0, err
	}
	defer cl.Close()
	var r reply.Hdel
	err = cl.Call(rpc.Name+".Hdel", args.Hdel{key, field, fields}, &r)
	if err != nil {
		return 0, err
	}
	return r.Redis(), nil
}

func (rpc *Rpc) Hexists(key, field string) (int, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return 0, err
	}
	defer cl.Close()
	var r reply.Hexists
	err = cl.Call(rpc.Name+".Hexists", args.Hexists{key, field}, &r)
	if err != nil {
		return 0, err
	}
	return r.Redis(), nil
}

func (rpc *Rpc) Hget(key, field string) ([]byte, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return nil, err
	}
	defer cl.Close()
	var r reply.Hget
	err = cl.Call(rpc.Name+".Hget", args.Hget{key, field}, &r)
	if err != nil {
		return nil, err
	}
	return r.Redis(), nil
}

func (rpc *Rpc) Hgetall(key string) ([][]byte, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return nil, err
	}
	defer cl.Close()
	var r reply.Hgetall
	err = cl.Call(rpc.Name+".Hgetall", args.Hgetall{key}, &r)
	if err != nil {
		return nil, err
	}
	return r.Redis(), nil
}

func (rpc *Rpc) Hkeys(key string) ([][]byte, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return nil, err
	}
	defer cl.Close()
	var r reply.Hkeys
	err = cl.Call(rpc.Name+".Hkeys", args.Hkeys{key}, &r)
	if err != nil {
		return nil, err
	}
	return r.Redis(), nil
}

func (rpc *Rpc) Hset(key, id string, value []byte) (int, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return 0, err
	}
	defer cl.Close()
	var r reply.Hset
	id_arr:=strings.Split(id, ".")
	if len(id_arr)==3 && id_arr[2]=="speed" {
		sub_id_arr := strings.Split(id_arr[1], "-")
		val, err := strconv.Atoi(sub_id_arr[2])
		if err != nil{
			return 0,err
		}
		if val > 1 {
			speed := string(value[:])
			if speed == "auto" {
				return 0, fmt.Errorf("hset: ERROR invalid speed")
			}
		}
	}

	err = cl.Call(rpc.Name+".Hset", args.Hset{key, id, value}, &r)
	if err != nil {
		return 0, err
	}
	return r.Redis(), nil
}

func (rpc *Rpc) Lrange(key string, start, stop int) ([][]byte, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return nil, err
	}
	defer cl.Close()
	var r reply.Lrange
	err = cl.Call(rpc.Name+".Lrange", args.Lrange{key, start, stop}, &r)
	if err != nil {
		return nil, err
	}
	return r.Redis(), nil
}

func (rpc *Rpc) Lindex(key string, index int) ([]byte, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return nil, err
	}
	defer cl.Close()
	var r reply.Lindex
	err = cl.Call(rpc.Name+".Lindex", args.Lindex{key, index}, &r)
	if err != nil {
		return nil, err
	}
	return r.Redis(), nil
}

func (rpc *Rpc) Blpop(key string, keys ...string) ([][]byte, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return nil, err
	}
	defer cl.Close()
	var r reply.Blpop
	err = cl.Call(rpc.Name+".Blpop", args.Blpop{key, keys}, &r)
	if err != nil {
		return nil, err
	}
	return r.Redis(), nil
}

func (rpc *Rpc) Brpop(key string, keys ...string) ([][]byte, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return nil, err
	}
	defer cl.Close()
	var r reply.Brpop
	err = cl.Call(rpc.Name+".Brpop", args.Brpop{key, keys}, &r)
	if err != nil {
		return nil, err
	}
	return r.Redis(), nil
}

func (rpc *Rpc) Lpush(key string, value []byte, values ...[]byte) (int, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return 0, err
	}
	defer cl.Close()
	var r reply.Lpush
	err = cl.Call(rpc.Name+".Lpush", args.Lpush{key, value, values}, &r)
	if err != nil {
		return 0, err
	}
	return r.Redis(), nil
}

func (rpc *Rpc) Rpush(key string, value []byte, values ...[]byte) (int, error) {
	cl, err := sockfile.NewRpcClient(rpc.File)
	if err != nil {
		return 0, err
	}
	defer cl.Close()
	var r reply.Rpush
	err = cl.Call(rpc.Name+".Rpush", args.Rpush{key, value, values}, &r)
	if err != nil {
		return 0, err
	}
	return r.Redis(), nil
}
