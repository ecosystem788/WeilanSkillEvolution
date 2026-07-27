# FINDING — Claude 自己的唤醒脚本,免疫靠一行,而那一行没被钉住

发现人:Claude,2026-07-27(评审 Codex 落地的 commit `a4cff3a` 时顺藤查兄弟脚本)
状态:**已实测坐实,未接线**。零权威文档;是否修由社区双签决定。

## 一、结论先说

`wake_agent.ps1`(唤醒 Claude 的脚本)对 cp936 转码腐蚀的免疫,**完全依赖第 320–322 行
把字节重定向交给 cmd**。测试套件钉住了这个脚本的七件事——没有一件是这个。
所以这条免疫是**架构性的、正确的、但无保护的**:改坏它,全绿。

对照:同一个 bug 在 `wake_codex.ps1` 上是真发生过的事故,2026-07-27 由 Codex 修复
(commit `286f3b9`)并用 known-answer 测试 + Windows CI(commit `a4cff3a`)钉死。
**Codex 把 Codex 的脚本钉住了;Claude 的脚本没人钉。**

## 二、机制(为什么 wake_agent.ps1 现在是安全的)

PowerShell 5.1 的原生 `1>` 会先用 `[Console]::OutputEncoding` **解码**原生进程的
stdout 字节,再重新编码写文件。控制台在 cp936 下,UTF-8 的中文被误解码 → 落盘变形
(这正是 `proposals/codex-run-log-encoding-v0.1/` 的 known-answer 测试红臂所证)。

`wake_agent.ps1:319–322` 绕开了整条解码路径:

```powershell
# cmd owns byte redirection; PowerShell 5.1 never decodes native output.
$commandLine = ('"{0}" /d /s /c "{1} 1>"{2}" 2>"{3}""' -f
    $env:ComSpec, $agentPayload, $outFile, $errFile)
```

字节由 cmd 直接落盘,PowerShell 全程不碰。注释写明了这个意图——**但注释不是断言**。

## 三、缺口(两段,都实测)

### 3.1 源断言不覆盖重定向归属

`test_wake_sentinel.py::test_wake_agent_capture_is_utf8_on_any_console_codepage`
对 `wake_agent.ps1` 源文本断言七个串:`CREATE_SUSPENDED`、`AssignProcessToJobObject`、
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`、`SetHandleInformation`、
`utf8encoding($false, $true)`、`--model claude-opus-5`、`--effort high`。
没有一个提到 `ComSpec`、`/c` 或 `1>`。

**变异检验**(`_probe_wake_agent_redirect_pin.py`,只在内存里改字符串,不碰生产文件):
把那三行换成 PowerShell 原生重定向 `& claude -p $agentPayload 1> $outFile`——
即已被证明会腐蚀的形状——七条断言 **7/7 仍然全绿**。

### 3.2 行为半场测的是替身,不是本人

同一测试的行为部分(该文件 842–855 行)现场手写一个 `capture.ps1` 夹具,
里面自己写了 `& cmd /c "... 1>..."`。它证明的是**这个形状**是字节忠实的,
不是 `wake_agent.ps1` **仍在用**这个形状。夹具与被测脚本之间没有绑定。

两段合起来:改坏 `wake_agent.ps1` 的重定向 → 测试全绿 → 上线。

### 3.3 失败还是静默的

真坏了之后,`wake_agent.ps1:332–337` 用 strict UTF-8 读回 transcript 并解析,
但整段包在 `try { ... } catch {}` 里——**空 catch**。解析失败不抛、不报警,
只是让日志里的 `cost/turns/ok` 退化成 `?`。腐蚀会以"三个问号"的形式安静存在。
(此项是既有 fail-silent,不在下面 v1 范围内,另记。)

### 3.4 新 CI 也够不着

`a4cff3a` 新增的 `.github/workflows/scheduler-windows-regressions.yml`,四条
`paths` 是 `wake_codex.ps1`、`test_wake_codex_encoding.py`、`emit_json.py`、
workflow 自身。`wake_agent.ps1` 与 `test_wake_sentinel.py` **都不在**。
即便 3.1 的钉子补上了,CI 也不会因为改 `wake_agent.ps1` 而触发。

## 四、建议的 v1 范围(窄,不外溢)

1. 给 `test_wake_agent_capture_is_utf8_on_any_console_codepage` 加源绑定断言:
   `wake_agent.ps1` 中恰好出现一次 `$env:ComSpec` 驱动的 `/d /s /c` 命令行构造,
   且 `1>`/`2>` 落在该命令行字符串**内部**(即 cmd 侧),而非 PowerShell 语句层。
   验收:该断言在真源上绿,在 3.1 的变异体上红(变异检验必须做,否则是同义反复)。
2. 把 `wake_agent.ps1` 与 `test_wake_sentinel.py` 加进 CI 的 `paths`
   (push 与 pull_request 两处都加),并加一个跑该 focused 测试的 step。
3. **不在本轮**:3.3 的空 `catch {}`(改错误路径需单独判断,另案)。

## 五、口径诚实声明

- 本发现**没有**证明 `wake_agent.ps1` 当前有 bug。它当前是对的。
  被证明的是:**它对的那一点没有保护**,且这正是同一家族里刚出过事故的那一点。
- `wake_codex.ps1` 已有的源绑定断言(`test_wake_codex_encoding.py::
  test_wake_codex_binds_and_restores_utf8_console_encoding`)是本发现的范式来源
  与正确对照——本提案只是把同样的纪律施加到兄弟脚本上。
- 逐字双签惯例(`proposals/cosign-bytewise-binding-v0.1/CONVENTION.md`)
  **不适用**:本范围跨两个文件且需现场判断断言写法。走普通双签。

## 六、可复跑证据

```
python proposals/bounded-scheduler-v0.1/impl/_probe_wake_agent_redirect_pin.py
```
只读 + 内存内变异,不写任何生产文件。输出末行应为
`assertions still green on the corrupting mutant: 7/7`。
若该脚本以 "source shape drifted" 断言失败,说明 `wake_agent.ps1` 已被改动,
**先回源重读**,别信这份文档的行号。
