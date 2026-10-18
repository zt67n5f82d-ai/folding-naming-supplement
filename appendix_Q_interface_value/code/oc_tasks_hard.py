#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HARD tier tasks.

Motivation: on the easy tier, arms C and B both sit at ~100%, so the
C-vs-B contrast (the marginal value of the LAYERED FORM at equal
information) is destroyed by a ceiling effect. These tasks keep many
interacting clauses so that a full prose contract still leaves room to fail.

Same 4-arm structure and same visible/hidden split as the easy tier.
"""

HARD = [
    dict(
        id="h_varint",
        goal="实现无符号 LEB128 变长整数编码与其解码。",
        sig="def encode_varint(n):\n    def decode_varint(b):",
        ret="encode_varint(n): n>=0 的 int → bytes（小端 7 位分组，最高位表示是否续读）；n<0 抛 ValueError。\n"
            "decode_varint(b): bytes → (value, consumed)，consumed 是实际消费的字节数；"
            "允许尾部有多余字节（只消费够用的部分）；输入在读完一个数之前就结束则抛 ValueError。",
        alpha="仅使用 Python 标准库；不得调用任何现成的 varint 库。",
        visible=[
            "encode_varint(0) == b'\\x00'",
            "encode_varint(127) == b'\\x7f'",
            "encode_varint(128) == b'\\x80\\x01'",
            "decode_varint(b'\\x80\\x01') == (128, 2)",
        ],
        hidden=[
            "encode_varint(300) == b'\\xac\\x02'",
            "encode_varint(2**32) == b'\\x80\\x80\\x80\\x80\\x10'",
            "decode_varint(b'\\x00') == (0, 1)",
            "decode_varint(b'\\xac\\x02') == (300, 2)",
            "decode_varint(b'\\xac\\x02\\xff') == (300, 2)",
            "_raises(ValueError, lambda: decode_varint(b'\\x80'))",
            "_raises(ValueError, lambda: decode_varint(b''))",
            "_raises(ValueError, lambda: encode_varint(-1))",
            "all(decode_varint(encode_varint(x)) == (x, len(encode_varint(x))) "
            "for x in [0,1,127,128,255,300,16383,16384,2**32,2**53])",
        ],
    ),
    dict(
        id="h_evaluate",
        goal="实现一个只含 + - * 与括号的整数表达式求值器。",
        sig="def evaluate(expr):",
        ret="支持整数常量、二元 + - *、一元负号、任意层括号与任意空白。* 优先级高于 + -，同级左结合。"
            "结果必须是 int。空串、括号不配平、缺操作数、多余操作数（如 '1 2'）、非法字符一律抛 ValueError。",
        alpha="仅使用 Python 标准库；不得使用 eval/exec/ast.literal_eval。",
        visible=[
            "evaluate('1+2*3') == 7",
            "evaluate('(1+2)*3') == 9",
            "evaluate('2*(3+4)-5') == 9",
        ],
        hidden=[
            "evaluate('10') == 10",
            "evaluate('-5+3') == -2",
            "evaluate('-(2+3)') == -5",
            "evaluate('1 - -2') == 3",
            "evaluate('2*3*4') == 24",
            "evaluate(' 1 + 2 ') == 3",
            "_raises(ValueError, lambda: evaluate('((1)))'))",
            "_raises(ValueError, lambda: evaluate(''))",
            "_raises(ValueError, lambda: evaluate('1+'))",
            "_raises(ValueError, lambda: evaluate('1 2'))",
        ],
    ),
    dict(
        id="h_schedule",
        goal="加权区间调度：选出总价值最大的互不重叠任务集合。",
        sig="def interval_schedule(tasks):",
        ret="tasks 为 [(start, end, value), ...]，区间是左闭右开 [start, end)，"
            "因此 end==start 的另一区间不算重叠。返回所选任务的索引列表（升序），使总 value 最大；"
            "存在多个并列最优时，返回**索引列表字典序最小**的那一个（先比第一个元素，再比第二个，依次类推）。"
            "空输入返回 []。",
        alpha="仅使用 Python 标准库；不得修改传入的列表。",
        visible=[
            "interval_schedule([]) == []",
            "interval_schedule([(0,3,3),(1,4,2)]) == [0]",
            "interval_schedule([(0,2,1),(2,4,1)]) == [0,1]",
        ],
        hidden=[
            "interval_schedule([(0,3,3),(3,6,4)]) == [0,1]",
            "interval_schedule([(0,10,5),(0,3,3),(3,10,3)]) == [1,2]",
            "interval_schedule([(0,1,1),(0,1,1)]) == [0]",
            "interval_schedule([(0,5,10),(1,2,3),(3,4,3)]) == [0]",
            "interval_schedule([(0,2,2),(1,3,4),(2,4,2)]) == [0,2]",
        ],
    ),
    dict(
        id="h_compose",
        goal="在既有接口之上做组合：把游程编码结果再转成十六进制文本。",
        sig="def pack(s):\n    def unpack(h):",
        ret="环境里已有一个可用的 rle_encode(s) -> str（每个字符段编码成 <字符><次数>，次数总是写出）"
            "与 rle_decode(t) -> str。请实现：\n"
            "pack(s)   = rle_encode(s) 的 UTF-8 字节的大写十六进制字符串\n"
            "unpack(h) = pack 的严格逆运算（h 为十六进制字符串）\n"
            "空串对应空串。必须复用既有的 rle_encode / rle_decode，不要重新实现游程编码。",
        alpha="仅使用 Python 标准库；只能调用上面给定的 rle_encode / rle_decode，不得自己重写它们。",
        visible=[
            "pack('aaabbc') == '613362326331'",
            "unpack('613362326331') == 'aaabbc'",
            "pack('') == ''",
        ],
        hidden=[
            "unpack(pack('xyz')) == 'xyz'",
            "unpack(pack('wwwwwwwwwwwwbbbcccccddddda')) == 'wwwwwwwwwwwwbbbcccccddddda'",
            "unpack('') == ''",
            "pack('a') == '6131'",
            "unpack(pack('Hello, World!')) == 'Hello, World!'",
        ],
    ),
]

# injected before the model's code for h_compose
COMPOSE_PRELUDE = '''
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
    import re as _re
    return "".join(ch * int(n) for ch, n in _re.findall(r"(.)(\\d+)", t))
'''

for _t in HARD:
    if _t["id"] == "h_compose":
        _t["prep"] = COMPOSE_PRELUDE
