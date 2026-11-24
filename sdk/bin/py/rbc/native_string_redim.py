# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Native re-DIM of fixed-capacity string arrays with runtime row and width.

The maximum declaration reserves backing memory. Each executed DIM records
its actual row count and character width and resets the elements. Every
index uses that live shape, not the largest shape. No archived source changes.
"""
from __future__ import annotations
import re

_DIM = re.compile(rb'^\s*([A-Za-z])\$\s*\(\s*([0-9]+)(?:\x0e.{5})?\s*,\s*([0-9]+)(?:\x0e.{5})?\s*\)',re.S)


def _string_redims(lines):
    found={}
    for _, body in lines:
        quoted=data=False
        pos=0
        while pos<len(body):
            b=body[pos]
            if b==14 and not quoted:
                pos+=6;continue
            if b==34:quoted=not quoted
            elif not quoted and b==234:break
            elif not quoted and b==228:data=True
            elif not quoted and b==58:data=False
            elif not quoted and not data and b==233:
                m=_DIM.match(body[pos+1:])
                if m:
                    idx=(m[1][0]|0x20)-97
                    a,b=int(m[2]),int(m[3])
                    found.setdefault(idx,[]).append((a,b) if 1<=a<=65535 and 1<=b<=65535 else None)
            pos+=1
    return {i:tuple(v) for i,v in found.items() if len(v)>1 and None not in v
            and len(set(v))>1 and max(x[0] for x in v)*max(x[1] for x in v)<=65535}


def with_string_redims(base, *, string_type, memory_fill, element_rt):
    class StringRedim(base):
        def reset(self,prog):
            super().reset(prog)
            self._zxux_string_redims=_string_redims(self.lines)
            for i,shapes in self._zxux_string_redims.items():
                self.strvars[i]['zxux_string_shapes']=frozenset(shapes)
                self.strvars[i]['zxux_live_rows']=0

        def _dim_sizes_set(self,ent,last,first):
            if 'zxux_string_shapes' not in ent:
                return super()._dim_sizes_set(ent,last,first)
            if (first,last) not in ent['zxux_string_shapes']:
                self.not_supported('unproved string redimension')
            if self.pass0:
                ent['last']=max(ent['last'],max(v[1] for v in ent['zxux_string_shapes']))
                ent['first']=max(ent['first'],max(v[0] for v in ent['zxux_string_shapes']))
            self._zxux_current_string_shape=(first,last)

        def var_size(self,ent,t):
            size=super().var_size(ent,t)
            if 'zxux_string_shapes' in ent:
                ent['zxux_live_rows']=ent['addr']+2+size
                return size+2
            return size

        def st_dim(self):
            c=self.get_char()
            idx=(c|0x20)-97
            if self.peek_after()!=ord('$') or idx not in self._zxux_string_redims:
                return super().st_dim()
            self.next_char();self.next_char()
            sv=self.strvars[idx]
            self.dim_sizes(sv)
            rows,width=self._zxux_current_string_shape
            self.t=string_type
            # Width and row count are scalar constants, never addresses. ld_hl() emits a
            # RELOCATABLE address operand in HiSoft.
            self.emit('ld hl,{}', width)
            self.st_hl(sv['addr'])
            self.emit('ld hl,{}', rows)
            self.st_hl(sv['zxux_live_rows'])
            self.ld_hl(sv['addr']+2)
            self.ld_bc_abs(sv['first']*sv['last']-1)
            self.emit('ld a,32')
            self.call_rt(memory_fill)

        def string_var_value(self,sv):
            if 'zxux_string_shapes' not in sv:
                return super().string_var_value(sv)
            self.next_char()
            self.expr_int()
            self._guard_index(sv['zxux_live_rows'])
            self.ld_de(sv['addr'])
            self.call_rt(element_rt)
            self._strarr_tail()

    return StringRedim
