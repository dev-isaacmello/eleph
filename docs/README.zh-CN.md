<h1 align="center">eleph</h1>

<p align="center">
  <strong>一门程序无法说谎的语言。</strong><br>
  言语行为、作为唯一状态的历史，以及从程序文本本身推导出来的
  正确性条件，而不是写在程序旁边的说明。
</p>

<p align="center">
  <a href="https://elephlanguage.vercel.app/zh-CN"><strong>文档</strong></a> ·
  <a href="#安装">安装</a> ·
  <a href="#在-python-中使用">Python API</a> ·
  <a href="#对照已发表的-benchmark-进行度量">Benchmark</a> ·
  <a href="#诚实的局限">局限</a> ·
  <a href="../README.md">English</a> ·
  <a href="README.pt-BR.md">Português</a> ·
  <a href="README.es.md">Español</a> ·
  中文
</p>

---

*Isaac Mello，2026。本项目实现并扩展了 **Elephant 2000**，这是一门基于言语行为的
编程语言，由 John McCarthy 规范设计（斯坦福，1998 年 11 月 6 日），他本人从未将其
实现。设计出自他之手。完备性阈值、承诺义务、增量运行时以及可嵌入的 API 则属于
本项目。*

## 为什么

一个智能体会对客户的记录作出断言，也会承诺去做某些事情。今天没有任何机制把这两者
与现实连接起来。输出过滤器检查的是文本。没有东西检查一个断言是否由真正发生过的事情
所蕴含，也没有东西追踪一个承诺究竟有没有被兑现。

McCarthy 的答案写在这个问题出现之前：让程序只说它自己的历史所支持的话，并让它的
承诺成为必须清偿的债务。两条义务，都是他提出的：

* **回答必须为真。** 每一个 `yes` 或 `no` 都必须由日志所蕴含。
* **承诺必须被兑现。** 程序不能承诺它的历史尚未确立的东西，也不能承诺任何一条经过它
  的路径都无法促成的东西。

这些条件不需要你来写。编译器直接从程序中读出它们。

```
$ eleph obligations examples/airline_buggy.eleph

  linha 17  question(Caller, has_reservation)
    resposta yes e verdadeira
      supondo   alguma vez make_reservation(P, F)
      entao     (make_reservation(P, F) e desde entao nenhum cancel_reservation(P, F))
```

然后它会试图推翻这些条件。

```
$ eleph check examples/airline_buggy.eleph

  X   question(Caller, has_reservation)  linha 17  -  resposta yes e verdadeira

      historico que quebra a obrigacao:
        1. make_reservation(P, F)
        2. cancel_reservation(P, F)

      o programa responde yes, a verdade do log e no
```

这个 bug 只差一个词。守卫条件问的是*他们是否订过座位*，而它本该问*他们现在是否持有
座位*。这是两个不同的问题，差别就在于取消。这正是 McCarthy 本人的例子，而整门语言的
存在，就是为了让这种差别不可能被忽略。

## 过去是唯一的状态

语法中没有赋值。这不是疏漏。根本没有可供赋值的对象，因为事实不是被存储的，它是对
已发生之事的一次查询：

```
fact has_reservation(P: Passenger, F: Flight) :=
    make_reservation(P, F) since_not cancel_reservation(P, F)
```

大象从不遗忘。没有任何东西被覆盖，因此也没有任何东西会与真相渐行渐远。程序自己说过
的话也进入同一份日志，所以可以问它已经说过什么：

```
if spoke accept to C about make_reservation(P, F):
    decline C
```

## 证明，而不是抽查

有界模型检查回答的是一个比我们想要的更弱的问题：不存在*长度不超过 N* 的历史能够破坏
该义务。对于这门语言的片段而言，这道缺口是可以合拢的，因为一个公式在历史末端的真值
只取决于**每个原子最后一次出现的先后顺序**。`a since_not b` 恰好等于「在最后一个 `b`
之后存在一个 `a`」。任何这样的配置都可以由一条每个原子占一个位置的历史来实现，因此
一个可计算的阈值

```
N = sum over distinct atoms of k(a),   k(a) = 1, or n+1 under a count
```

使得「未发现反例」意味着「不存在反例」。每条义务都在它自己的阈值上被检查：

```
PROVADO  -  6 obrigacoes valem para TODO historico, de qualquer tamanho
```

这不是装饰。`examples/fundo.eleph` 只有在第七个事件之后才会说谎，而固定取六的界限会
**判定它通过**：

```
$ eleph check examples/fundo.eleph --bound 6
SEM CONTRAEXEMPLO  -  dentro dos limites checados, que nao sao exaustivos aqui

$ eleph check examples/fundo.eleph
X   question(C, elite)  -  resposta yes e verdadeira
    1..7. make_reservation(P, F)
```

如果一个公式把复合表达式放在 `since_not` 之下，它就离开了线性片段。此时完备性来自
监视器的状态空间，对于 `k` 个时序子公式是 `2^k`，原理上是指数级的，实践中则很小。
当连这个代价都负担不起时，检查器会明说这次运行不是穷尽的，而不是假装它是。

## 三个主张，以及能够推翻它们的实验

**阈值。** 在计算出的阈值之上，任何判定结论都不得改变。验证方式是在高于该阈值的界限
和论域上，对每个示例的每条义务重新检查一遍。

**推导的可靠性。** 如果所有义务都被证明，运行时就永远不会拒绝。运行时恰好在某个言语
行为的真值条件不成立时才拒绝，而推导器会在同一份日志上，为每个这样的行为生成
`path condition implies truth condition`。验证方式是用随机的过去和随机的对话反复冲击
已证明的程序，并确认未被证明的程序确实会拒绝。

**索引算出的结果与日志算出的结果一致。** 见下文。

它们分别位于 `tests/test_soundness.py` 和 `tests/test_incremental.py`。

## 一份永不停止增长的历史

对于一门唯一状态就是其过去的语言，最显而易见的反对意见是：回答一个问题就意味着读取
过去。那是二次复杂度，而且确实暴露出来了：在四千次交互时，它只跑到每秒 46 个事件。

这里的每个算子都有一个单步递推式，
`(a since_not b)@t = a@t or ((a since_not b)@(t-1) and not b@t)`，这正是过去时态时序
逻辑的动态规划读法。有一条引理让它变得锋利：**一个不匹配某子公式任何原子的事件，
无法改变该子公式的值。** 因此折入一个事件时，只会触及该事件所指名的那些键。

```
$ python bench/scaling.py

interacoes      log   relendo   indice   ganho     ev/s  escala
       500     1134      1.62    0.058     28x    19482       -
      1000     2274      6.15    0.109     56x    20867   x1.87
                       (x3.8)
      2000     4554     24.97    0.208    120x    21890   x1.91
                       (x4.1)
      4000     9100         -    0.381      -    23912   x1.83
      8000    18192         -    0.830      -    21909   x2.18
```

工作量翻倍时时间翻倍，而重读日志的做法则是翻了四倍。实测在 145,564 个事件下耗时
6.1 s，吞吐保持平稳。

索引的每一个单元格都是日志的纯函数，与朴素求值器通过重读日志计算出的是同一个函数。
那是对一个真值主张的优化，因此绝不会被无条件信任。`Machine(audit=True)` 会用**两种**
方式回答每次查询，一旦结果不同就抛出异常，覆盖随机的过去和超过一千个事件的历史。

## 在 Python 中使用

完整示例位于 [`examples/langchain-agent`](../examples/langchain-agent)：同一个
LangChain 智能体在九个场景上运行两次，一次底层有 guard，一次没有，模型、提示词
和工具完全相同。

这门语言是研究成果本身。大多数系统需要的东西更小，而它以库的形式提供：

```python
from eleph import Policy

policy = Policy.from_file("booking.eleph")
assert policy.verify().proved          # the same file, proved statically

g = policy.guard(log="booking.jsonl")  # durable, reopening replays

g.record("make_reservation", "alice", "ba117")
g.holds("has_reservation", "alice", "ba117")                  # True
g.assert_answer("has_reservation", False, "alice", "ba117")   # raises

g.promise("alice", "has_seat", "alice", "ba117",
          before=("board", ("alice", "ba117")))
g.outstanding()        # what is still owed, to whom
```

三种形态，由轻到重。`python examples/agente.py` 会把三种都跑一遍。

| 形态 | 你需要改什么 | 你得到什么 |
|---|---|---|
| **observer** | 什么都不改，你只负责把事件喂给它 | 记录中什么为真，以及一份审计 |
| **guard** | 断言和工具调用都经由它路由 | 没有依据的主张会抛出异常，而不是被发出去 |
| **language** | 用 `.eleph` 编写处理器 | 静态证明 |

把规则放在策略文件里、而不是用 Python 写检查逻辑，理由就在上面第一行：
**你的守卫在凌晨三点执行的规则，和求解器证明过的是同一份产物。** 规则被证明过的守卫，
和规则只是被某人相信的守卫，是两回事。

写入磁盘的只有事件。索引和账本是通过重新经历一遍过去而重建的，因此一个崩溃后重启的
进程与一个从未崩溃的进程无从区分。末尾被截断的一行会被丢弃：一个还没写完的事件，
就是一个没有发生过的事件。

## 对照已发表的 benchmark 进行度量

[τ-bench](https://arxiv.org/abs/2406.12045)（ICLR 2025）给一个航空公司客服智能体
提供了一份成文的策略，其中两次声明**「API 不会替智能体检查这些」**，并通过对最终
数据库做哈希来为每次运行打分。这条义务被写了出来，却既未被强制执行，也未被度量。

其中两条规则在这里被写成 `.eleph` 事实，并在已发表的 200 条 gpt-4o 航空轨迹上重放：

```
$ python bench/taubench/check.py         # the confirmation rule
  gasta na acao                 85 escritas sem confirmacao,  8 em execucoes pontuadas como sucesso
  expira no turno               52 escritas sem confirmacao,  4 em execucoes pontuadas como sucesso

$ python bench/taubench/cancel_check.py  # cancellation eligibility
  seguro E motivo coberto       38 cancelamentos proibidos, 26 deles no gabarito anotado
  ter seguro basta              16 cancelamentos proibidos,  7 deles no gabarito anotado
```

把这些规则写下来，带来了比统计违规次数更有意思的结果：这两句话都**在会波及黄金标签
的层面上存在歧义**，而该 benchmark 的后续版本重写了其中一句。这次形式化落在了它上面，
而且没有任何人提示去那里看。

这并不是在主张 τ-bench 是错的。它的奖励函数有文档、也是刻意设计的，论文本身就直言
`r = 1`「可能是必要条件而非充分条件」。这里的主张更狭窄：一个智能体被要求遵守的承诺，
并没有被那个度量智能体的东西所度量，而度量它只需要一行。

完整的审计过程，包括两处歧义以及每个数字各自经受住了哪些检验，见
[`bench/README.md`](../bench/README.md)。`tests/test_taubench.py` 固定了上面的每一个数字。

## 语言

```
sort   Passenger
event  make_reservation(p: Passenger, f: Flight)
fact   has_reservation(P: Passenger, F: Flight) := <temporal expression>
on question(C, has_reservation(P, F)):  ...
on request(C, make_reservation(P, F)):  ...
```

| 形式 | 含义 |
|---|---|
| `e(a, b)` | 事件 `e` 在过去**至少发生过一次** |
| `a since_not b` | `a` 发生过，且此后没有发生过 `b` |
| `count e(a) >= n` | `e` 发生了多少次 |
| `exists P: Sort where φ` | 当前存在某个对象满足 φ |
| `count P: Sort where φ >= n` | 有多少个对象满足，这正是座位上限所需要的 |
| `spoke accept to C about e(...)` | 程序在那次交互中执行过该行为 |
| `e(a, amount > 100)` | 事件的一个数值字段，在它发生的当下被检验 |
| `not`、`and`、`or` | 一如通常 |

处理器可以以权限为前提来设卡，这是 McCarthy 的第八种言语行为，也是普通评审从来不会
去追问的那一种：

```
on question(Quem, saldo(C)) permitted pode_perguntar(Quem, C):
    answer Quem with saldo(C)
```

一个客服智能体，只要谁来问就如实报出任何客户的余额，它一句谎话都没说，而这里其他
所有义务都会放它过关。权限会并入路径条件，因此回答是*在权限之下*被证明的，而不是
在旁边被单独打勾，并且运行时是失败即关闭的：被扣下的回答还能补救，泄露出去的回答
不能。

裸写的 `e(a, b)` 表示*曾经发生过*，这个陷阱是故意留的：它读起来像「持有」，实际意思却是
「办理过」。能把两者分辨开的，正是验证器。

语句：`answer C yes` / `answer C no` / `answer C with φ`、`record e(...)`、
`accept C`、`decline C`、`release C from φ`，以及四种强度的承诺：
`offer C that φ`（有意愿，尚未负债）、`promise C that φ`（说出时即为真）、
`promise C eventually φ`，以及 `promise C that φ before e(...)`。

## 推导出的义务

| 义务 | 由什么检查 |
|---|---|
| 回答为真 | Z3，在完备性阈值处 |
| 回答确实回应了所提的问题 | Z3 |
| 即时承诺在说出时成立 | Z3，基于日志加上处理器刚刚记录的内容 |
| 未来承诺是某条路径能够促成的 | Z3，要求该路径把它从假变为真 |
| 参数的 sort 与声明一致 | 编译器，对每个 fact，无论是否被用到 |
| 提议是某条路径能够兑现的 | Z3 |
| 通往受保护主题的门没有一扇是未上锁的 | 结构性检查 |
| 每条路径恰好回答一次 | 结构性检查 |
| 每个请求恰好被接受或拒绝一次 | 结构性检查 |
| 未结清与已违背的承诺 | 运行时账本 |

## 诚实的局限

* **没有挂钟时间。** `since_not` 知道的是顺序，不是时间。「在订票后 24 小时内取消」
  无法直接表达。今天可行的模式，也是 `bench/taubench/cancel.eleph` 采用的模式，是让
  宿主把截止时刻作为一个事件发出。时钟活在逻辑之外，反正事件溯源系统本来就是这样
  处理时间的。
* **数值字段是在事件发生的那一瞬间被比较的。** 正是这一点让完备性论证保持完整，同时
  它也是限制所在：你可以问*这一笔扣款*是否超过 100，但不能问最近三笔的总和是否超过。
  对历史做聚合运算是无法表达的。
* **线性完备性阈值只覆盖一个片段。** 它在每个 `since_not` 都只接受原子时成立。超出这个
  范围，完备性来自监视器的状态空间；再超出去，检查器就会承认这次运行不是穷尽的。
  阈值还会随常量增长：要证明关于 180 这个容量的性质，就需要能容纳 180 个事件的历史。
* **未来承诺检查的是可兑现性，不是活性。** 编译器证明的是存在某条路径能够确立它。
  它无法证明调用方会走上那条路，因为没有任何程序能做到这一点。
* **索引需要局部性。** 一个子公式如果指名的变量比它的父公式更少，就会让一个事件扰动
  无界多个键。这样的程序仍然能跑，只是要靠重读日志，`Machine.index.usable` 会如实
  说明这一点。
* **`spoke` 指名的是交互，不是内容。** 「我是否已经承诺过这件一模一样的事？」无法表达。
  「我在这里是否已经承诺过什么？」可以。
* **权限是一个事实，不是角色系统。** `permitted` 让一个 handler 取决于日志能够支持的
  东西，也就是"这个调用方是否已在该账户上完成认证"。没有角色，没有层级，也没有委派。
* **fact 不能递归**，因此传递性性质是够不着的。
* **τ-bench 审计是用正则表达式读自然语言的。** 同意是从一份宽松的词表中匹配的，所以
  计数是少报而不是多报。样本违规在数字发表之前都经过了人工阅读。
* **这些定理是在纸上证明并经过测试的，没有机械化。** 为基础片段做一个 Lean 产物，是
  接下来最值得做的事。

## 安装

```bash
pip install eleph          # or:  uv pip install eleph
```

从源码安装：

```bash
git clone https://github.com/dev-isaacmello/eleph && cd eleph
uv venv && uv pip install -e ".[dev]"
```

## 运行

```bash
eleph obligations examples/airline_buggy.eleph   # what the text demands
eleph check       examples/companhia.eleph       # try to break it
eleph run         examples/companhia.eleph examples/voo.session --log /tmp/voo.jsonl
eleph ledger      examples/companhia.eleph /tmp/voo.jsonl   # what it still owes
eleph talk        examples/companhia.eleph examples/conversa.txt --roster alice,bruno,ba117

python examples/agente.py            # the three integration shapes
python bench/scaling.py              # constant time per event
python bench/taubench/check.py       # the benchmark audit
pytest -q                            # 164 tests
```

## 来源

McCarthy, John. *Elephant 2000: A Programming Language Based on Speech Acts.*
斯坦福，1998 年 11 月 6 日。

## 许可证

MIT。见 [LICENSE](../LICENSE)。
