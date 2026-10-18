#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Oracle self-test: run every task's hidden assertions against a
hand-written GOLDEN implementation. If the golden impl fails any hidden
assert, the oracle is wrong -- not the model.
"""
import sys

from oc_tasks import TASKS, HELPERS
from oc_tasks_hard import HARD

GOLDEN = {
"chunk": '''
def chunk(seq, n):
    if n <= 0:
        raise ValueError("n must be positive")
    seq = list(seq)
    return [seq[i:i+n] for i in range(0, len(seq), n)]
''',
"parse_duration": '''
import re as _re
def parse_duration(s):
    if not isinstance(s, str) or s == "":
        raise ValueError("empty")
    if s.isdigit():
        return int(s)
    order = {"d":0,"h":1,"m":2,"s":3}
    mult = {"d":86400,"h":3600,"m":60,"s":1}
    total, last, seen = 0, -1, set()
    for num, unit in _re.findall(r"(\\d+)([dhms])", s):
        if unit in seen:
            raise ValueError("repeated unit")
        if order[unit] <= last:
            raise ValueError("bad order")
        seen.add(unit); last = order[unit]
        total += int(num) * mult[unit]
    if sum(len(a) for a in _re.findall(r"\\d+[dhms]", s)) != len(s):
        raise ValueError("garbage")
    return total
''',
"merge_intervals": '''
def merge_intervals(intervals):
    xs = sorted((tuple(x) for x in intervals), key=lambda p: (p[0], p[1]))
    out = []
    for a, b in xs:
        if out and a <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out
''',
"to_roman": '''
def to_roman(n):
    if not isinstance(n, int) or isinstance(n, bool) or not (1 <= n <= 3999):
        raise ValueError("out of range")
    vals = [(1000,"M"),(900,"CM"),(500,"D"),(400,"CD"),(100,"C"),(90,"XC"),
            (50,"L"),(40,"XL"),(10,"X"),(9,"IX"),(5,"V"),(4,"IV"),(1,"I")]
    out = []
    for v, s in vals:
        while n >= v:
            out.append(s); n -= v
    return "".join(out)
''',
"rle": '''
def rle_encode(s):
    if s == "":
        return ""
    out, prev, cnt = [], s[0], 1
    for ch in s[1:]:
        if ch == prev:
            cnt += 1
        else:
            out.append("%s%d" % (prev, cnt)); prev, cnt = ch, 1
    out.append("%s%d" % (prev, cnt))
    return "".join(out)

def rle_decode(t):
    import re
    return "".join(ch * int(n) for ch, n in re.findall(r"(.)(\\d+)", t))
''',
"top_k_frequent": '''
from collections import Counter
def top_k_frequent(words, k):
    if k <= 0:
        return []
    c = Counter(words)
    return [w for w, _ in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))][:k]
''',
"crc8": '''
def crc8(data):
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if (crc & 0x80) else (crc << 1) & 0xFF
    return crc
''',
"fixed_point": '''
def fixed_point(g, x0, tol=1e-9, max_iter=100):
    x = x0
    for i in range(1, max_iter + 1):
        xn = g(x)
        if abs(xn - x) < tol:
            return (xn, i)
        x = xn
    raise ValueError("did not converge")
''',
"h_varint": '''
def encode_varint(n):
    if not isinstance(n, int) or n < 0:
        raise ValueError("negative")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)

def decode_varint(b):
    val, shift, i = 0, 0, 0
    while True:
        if i >= len(b):
            raise ValueError("truncated")
        byte = b[i]; i += 1
        val |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return (val, i)
        shift += 7
''',
"h_evaluate": '''
import re as _re
def evaluate(expr):
    if not isinstance(expr, str) or expr.strip() == "":
        raise ValueError("empty")
    toks = _re.findall(r"\\d+|[-+*()]", expr)
    if "".join(toks) != _re.sub(r"\\s+", "", expr):
        raise ValueError("bad char")
    pos = [0]
    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None
    def eat():
        t = peek(); pos[0] += 1; return t
    def primary():
        t = peek()
        if t is None:
            raise ValueError("missing operand")
        if t == "(":
            eat(); v = addsub()
            if peek() != ")":
                raise ValueError("unbalanced")
            eat(); return v
        if t == "-":
            eat(); return -primary()
        if t.isdigit():
            return int(eat())
        raise ValueError("unexpected")
    def muldiv():
        v = primary()
        while peek() == "*":
            eat(); v *= primary()
        return v
    def addsub():
        v = muldiv()
        while peek() in ("+", "-"):
            op = eat(); r = muldiv()
            v = v + r if op == "+" else v - r
        return v
    val = addsub()
    if pos[0] != len(toks):
        raise ValueError("trailing")
    return val
''',
"h_schedule": '''
from itertools import combinations as _comb
def interval_schedule(tasks):
    n = len(tasks)
    best_val, bests = -1, []
    for r in range(n + 1):
        for combo in _comb(range(n), r):
            ok = True
            for i in range(len(combo)):
                for j in range(i + 1, len(combo)):
                    a, b = tasks[combo[i]], tasks[combo[j]]
                    if a[0] < b[1] and b[0] < a[1]:
                        ok = False
            if not ok:
                continue
            v = sum(tasks[i][2] for i in combo)
            if v > best_val:
                best_val, bests = v, [list(combo)]
            elif v == best_val:
                bests.append(list(combo))
    if not bests:
        return []
    return min(bests)
''',
"h_compose": '''
def pack(s):
    return rle_encode(s).encode("utf-8").hex().upper()

def unpack(h):
    if h == "":
        return ""
    return rle_decode(bytes.fromhex(h).decode("utf-8"))
''',
}

fails = 0
for t in TASKS + HARD:
    code = GOLDEN[t["id"]]
    ns = {}
    exec(HELPERS, ns)
    if t.get("prep"):
        exec(t["prep"], ns)
    try:
        exec(code, ns)
    except Exception as e:
        print("GOLDEN EXEC FAIL", t["id"], e); fails += 1; continue
    for label, asserts in (("visible", t["visible"]), ("hidden", t["hidden"])):
        for a in asserts:
            try:
                r = bool(eval(a, ns))
            except Exception as e:
                r = "ERR " + type(e).__name__ + " " + str(e)[:60]
            if r is not True:
                print("  FAIL [%s/%s] %s  -> %s" % (t["id"], label, a, r))
                fails += 1
print("oracle self-test:", "ALL PASS" if fails == 0 else "%d FAILURES" % fails)
sys.exit(1 if fails else 0)
