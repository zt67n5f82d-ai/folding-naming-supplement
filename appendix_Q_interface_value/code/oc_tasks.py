#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Task set for the OpenCode A/B/C/D experiment.

Four arms, same underlying task:
  A  bare      : minimal "vibe" spec (no signature precision, no examples, no structure)
  C  prose     : complete spec + visible examples, flattened prose, no pi/alpha/I labels
  B  layered   : identical information to C, but explicitly split into
                 pi (upward contract) / alpha (downward primitives) / I (invariant, rollback)
  D  B-minus-I : layered pi/alpha, no invariant clause, no visible examples

Two oracles per task:
  visible : the assertions quoted in the prompt (contract definition)
  hidden  : held-out assertions, never shown to the model -> guards against
            overfitting to the visible examples
"""
import math

TASKS = [
    dict(
        id="chunk",
        goal="把一个序列按固定长度切成连续的若干块。",
        sig="def chunk(seq, n):",
        ret="返回 list[list]，按原顺序连续切分；最后一块可以更短；"
            "即使输入是 tuple 或 str，切出的每一块也必须是 list；n<=0 时抛 ValueError。",
        alpha="仅使用 Python 标准库；不得修改传入的容器。",
        visible=[
            "chunk([], 3) == []",
            "chunk([1,2,3,4,5], 2) == [[1,2],[3,4],[5]]",
            "chunk([1,2], 5) == [[1,2]]",
        ],
        hidden=[
            "chunk([1,2,3,4], 4) == [[1,2,3,4]]",
            "chunk([1,2,3,4,5,6], 3) == [[1,2,3],[4,5,6]]",
            "chunk((7,8,9), 2) == [[7,8],[9]]",
            "chunk('abcde', 2) == [['a','b'],['c','d'],['e']]",
            "_raises(ValueError, lambda: chunk([1,2,3], 0))",
            "_raises(ValueError, lambda: chunk([1,2,3], -1))",
            "_unchanged()",
        ],
        prep="src = [1,2,3,4,5]; _before = list(src)",
        post_check="src == _before",
    ),
    dict(
        id="parse_duration",
        goal="把时长字符串解析成整数秒。",
        sig="def parse_duration(s):",
        ret="返回 int 秒数。支持单位 d(天)/h(小时)/m(分钟)/s(秒)，必须按 d>h>m>s 的降序出现；"
            "纯数字字符串按秒处理。空串、未知单位、重复单位、乱序单位均抛 ValueError。",
        alpha="仅使用 Python 标准库。",
        visible=[
            'parse_duration("90s") == 90',
            'parse_duration("1h30m") == 5400',
            'parse_duration("45") == 45',
        ],
        hidden=[
            'parse_duration("2d") == 172800',
            'parse_duration("1d2h3m4s") == 93784',
            'parse_duration("10m") == 600',
            '_raises(ValueError, lambda: parse_duration(""))',
            '_raises(ValueError, lambda: parse_duration("1x"))',
            '_raises(ValueError, lambda: parse_duration("1h1h"))',
            '_raises(ValueError, lambda: parse_duration("30m1h"))',
        ],
    ),
    dict(
        id="merge_intervals",
        goal="合并整数闭区间。",
        sig="def merge_intervals(intervals):",
        ret="输入 [(start,end),...]（start<=end），返回合并后的 list[tuple]；"
            "**重叠或相接**的区间都要合并（[1,3] 与 [4,5] 相接，应合并为 [1,5]）；结果按起点升序。",
        alpha="仅使用 Python 标准库；不得修改传入的列表。",
        visible=[
            "merge_intervals([]) == []",
            "merge_intervals([(1,3),(2,6),(8,10),(15,18)]) == [(1,6),(8,10),(15,18)]",
            "merge_intervals([(1,4),(4,5)]) == [(1,5)]",
        ],
        hidden=[
            "merge_intervals([(1,2)]) == [(1,2)]",
            "merge_intervals([(5,6),(1,2)]) == [(1,2),(5,6)]",
            "merge_intervals([(1,10),(2,3)]) == [(1,10)]",
            "merge_intervals([(1,2),(3,4),(5,6)]) == [(1,6)]",
            "_unchanged()",
        ],
        prep="src = [(1,4),(4,5)]; _before = list(src)",
        post_check="src == _before",
    ),
    dict(
        id="to_roman",
        goal="整数转罗马数字。",
        sig="def to_roman(n):",
        ret="1<=n<=3999 返回大写标准减法形式罗马数字；n 非 int 或越界抛 ValueError。",
        alpha="仅使用 Python 标准库。",
        visible=["to_roman(1) == 'I'", "to_roman(4) == 'IV'", "to_roman(1994) == 'MCMXCIV'"],
        hidden=[
            "to_roman(9) == 'IX'",
            "to_roman(40) == 'XL'",
            "to_roman(90) == 'XC'",
            "to_roman(400) == 'CD'",
            "to_roman(900) == 'CM'",
            "to_roman(3999) == 'MMMCMXCIX'",
            "_raises(ValueError, lambda: to_roman(0))",
            "_raises(ValueError, lambda: to_roman(4000))",
        ],
    ),
    dict(
        id="rle",
        goal="游程编码及其逆运算。",
        sig="def rle_encode(s):\n    def rle_decode(t):",
        ret="rle_encode: 每个连续字符段编码为 <字符><十进制次数>，次数总是写出（即使为 1）；空串返回空串。"
            "rle_decode 是其严格逆运算。",
        alpha="仅使用 Python 标准库。",
        visible=[
            "rle_encode('aaabbc') == 'a3b2c1'",
            "rle_encode('') == ''",
            "rle_decode('a3b2c1') == 'aaabbc'",
        ],
        hidden=[
            "rle_encode('a') == 'a1'",
            "rle_encode('wwwwwwwwwwwwbbbcccccddddda') == 'w12b3c5d5a1'",
            "rle_decode(rle_encode('xyz')) == 'xyz'",
            "rle_decode(rle_encode('aaaaaaaaaa')) == 'aaaaaaaaaa'",
            "rle_decode('z1') == 'z'",
        ],
    ),
    dict(
        id="top_k_frequent",
        goal="统计词频并取前 k 个。",
        sig="def top_k_frequent(words, k):",
        ret="返回 list[str]：按出现次数降序；次数相同时按字典序升序；k<=0 返回 []；"
            "不同词少于 k 时返回全部不同词。",
        alpha="仅使用 Python 标准库。",
        visible=[
            "top_k_frequent(['i','love','leetcode','i','love','coding'], 2) == ['i','love']",
            "top_k_frequent([], 3) == []",
            "top_k_frequent(['a'], 0) == []",
        ],
        hidden=[
            "top_k_frequent(['the','day','is','sunny','the','the','the','sunny','is','is'], 4) "
            "== ['the','is','sunny','day']",
            "top_k_frequent(['b','a'], 5) == ['a','b']",
            "top_k_frequent(['x','y','x'], 1) == ['x']",
            "top_k_frequent(['c','c','b','b','a'], 2) == ['b','c']",
        ],
    ),
    dict(
        id="crc8",
        goal="实现 CRC-8 校验。",
        sig="def crc8(data):",
        ret="参数固定为：多项式 0x07，初值 0x00，输入不反转，输出不反转，结果不异或。"
            "data 为 bytes，返回 0..255 的 int。",
        alpha="仅使用 Python 标准库；不得调用任何现成的 crc 库。",
        visible=[
            "crc8(b'') == 0",
            "crc8(b'123456789') == 0xF4",
            "crc8(b'\\x00') == 0",
        ],
        hidden=[
            "crc8(b'\\xff') == 0xF3",
            "crc8(b'A') == 0xC0",
            "crc8(b'abc') == 0x5F",
            "crc8(b'hello world') == 0xA8",
            "crc8(bytes(range(256))) == 0x14",
        ],
    ),
    dict(
        id="fixed_point",
        goal="不动点迭代。",
        sig="def fixed_point(g, x0, tol=1e-9, max_iter=100):",
        ret="反复计算 x_{k+1}=g(x_k)，当 |x_{k+1}-x_k| < tol 时停止，返回 (x_{k+1}, 迭代次数)；"
            "每次调用 g 记一次迭代；超过 max_iter 仍未收敛抛 ValueError。",
        alpha="仅使用 Python 标准库。",
        visible=[
            "fixed_point(lambda x: x, 5.0) == (5.0, 1)",
            "abs(fixed_point(lambda x: math.cos(x), 1.0)[0] - 0.7390851332151607) < 1e-6",
        ],
        hidden=[
            "abs(fixed_point(lambda x: 0.5*x + 1.0, 0.0)[0] - 2.0) < 1e-8",
            "fixed_point(lambda x: 0.5*x + 1.0, 0.0)[1] >= 1",
            "_raises(ValueError, lambda: fixed_point(lambda x: x+1, 0.0, max_iter=5))",
            "fixed_point(lambda x: x, 5.0, tol=1e-9)[1] == 1",
        ],
    ),
]

# ---- helpers injected into the test namespace -------------------------------

HELPERS = '''
import math

def _raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False

def _ref(data):
    """Independent reference CRC-8: poly 0x07, init 0x00, no reflect, no xorout."""
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if (crc & 0x80) else (crc << 1) & 0xFF
    return crc

def _unchanged():
    return src == _before

def _defined(name):
    return name in globals() or name in locals()
'''

# ---- prompt builders --------------------------------------------------------

_TAIL = "只输出一个 Python 代码块，不要任何解释文字，不要创建或修改任何文件，不要使用任何工具。"


def _bullets(items):
    return "\n".join("- " + x for x in items)


def build_prompt(task, arm):
    if arm == "A":
        return ("请用 Python 实现下面的需求，%s\n\n需求：%s\n函数名与签名：%s\n"
                % (_TAIL, task["goal"], task["sig"]))
    if arm == "C":
        return ("请用 Python 实现下面的需求，%s\n\n需求：%s\n\n"
                "函数签名：%s 返回值约定：%s\n"
                "约束：%s\n"
                "实现必须满足下列断言：\n%s\n"
                % (_TAIL, task["goal"], task["sig"], task["ret"],
                   task["alpha"], _bullets(task["visible"])))
    if arm == "B":
        return ("请用 Python 实现下面的需求，%s\n\n需求：%s\n\n"
                "【上行契约 π｜调用方据此依赖你】\n函数签名：%s\n返回值约定：%s\n\n"
                "【下行原语 α｜你被允许做什么】\n%s\n\n"
                "【不变量 I｜违反即视为未完成，必须回退重写】\n%s\n"
                % (_TAIL, task["goal"], task["sig"], task["ret"],
                   task["alpha"], _bullets(task["visible"])))
    if arm == "D":
        return ("请用 Python 实现下面的需求，%s\n\n需求：%s\n\n"
                "【上行契约 π｜调用方据此依赖你】\n函数签名：%s\n返回值约定：%s\n\n"
                "【下行原语 α｜你被允许做什么】\n%s\n"
                % (_TAIL, task["goal"], task["sig"], task["ret"], task["alpha"]))
    # R45 新增：α 消融对照臂。与 D 的唯一差别是没有【下行原语 α】那一段。
    # 因此 Δ(D − D0) 就是 α 的净价值（信息量完全相同，只差"允许你做什么"这一句约束）。
    if arm == "D0":
        return ("请用 Python 实现下面的需求，%s\n\n需求：%s\n\n"
                "【上行契约 π｜调用方据此依赖你】\n函数签名：%s\n返回值约定：%s\n"
                % (_TAIL, task["goal"], task["sig"], task["ret"]))
    raise ValueError(arm)


ARMS = ["A", "B", "C", "D"]
