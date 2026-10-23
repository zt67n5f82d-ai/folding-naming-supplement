/-
  折叠与命名 · 第 21 章「有界构造公理」的机器验证

  入口文件。五个部分：
    Basic         良基序与变式（公理①的定量版、公理②的规约、反例）
    Lexicographic 字典序变式（Ackermann 在类内）
    While         带变式的循环（公理①的直接形式化：无变式就写不出来）
    Certificate   把公理当判据用（准入门的可靠性：通过必停、上界可算、反例无证书）
    FSM           第 16–17 章两个状态机（完备性/安全性/活跃性/不变量）

  构建：lake build
-/
import BoundedConstruction.Basic
import BoundedConstruction.Lexicographic
import BoundedConstruction.While
import BoundedConstruction.Certificate
import BoundedConstruction.FSM
import BoundedConstruction.TCP
import BoundedConstruction.Gate
