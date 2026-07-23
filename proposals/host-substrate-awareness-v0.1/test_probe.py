#!/usr/bin/env python3
"""host-substrate-awareness probe 的承重测试。

核心断言(Codex 2026-07-23 19:53 承重裁断的落地):working_tree_clean 必须 fail-closed——
当 workspace 是非仓库/不存在目录时,git status 非零退出,探针须报 value=None(没读到),
绝不裁成 True(干净)。这条测试就是把"没读伪装成干净"钉死为回归失败。

运行: python test_probe.py
"""
import os
import tempfile

import probe


def test_non_repo_workspace_fails_closed():
    """非 git 目录:working_tree_clean 必须为 None,而不是 True。"""
    with tempfile.TemporaryDirectory() as tmp:
        fact = probe._git_porcelain(tmp)
        assert fact["name"] == "working_tree_clean"
        assert fact["value"] is None, (
            "非仓库目录下必须 fail-closed(value=None),读到的却是 %r" % fact["value"]
        )
        assert "returncode" in fact["detail"], "失败事实须带 returncode 供回源"
        assert fact["authority"] == "none"


def test_nonexistent_workspace_fails_closed():
    """路径根本不存在:同样 fail-closed,不得裁成 clean。"""
    missing = os.path.join(tempfile.gettempdir(), "weilan_no_such_dir_zzz_qwerty")
    assert not os.path.exists(missing)
    fact = probe._git_porcelain(missing)
    assert fact["value"] is None, "不存在路径必须 value=None,而非 True"
    assert fact["authority"] == "none"


def test_real_repo_reports_bool():
    """真实仓库(本项目根)下:value 应为具体 bool,不是 None。"""
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, os.pardir, os.pardir))
    fact = probe._git_porcelain(repo_root)
    assert isinstance(fact["value"], bool), (
        "真实仓库下应读到 bool,得到 %r" % fact["value"]
    )


def _repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, os.pardir, os.pardir))


def test_no_demand_collects_nothing():
    """无具名消费问题(demand=None)= 不采:facts 必须为空。

    这是 Codex 2026-07-23 19:45 守恒差异的落地——"没有当前判断消费者就不采",
    防固定面板悄悄把"可感知"变成"应持续感知"。
    """
    out = probe.collect(_repo_root(), demand=None)
    assert out["facts"] == [], "无 demand 时不得采任何事实"
    assert out["count"] == 0
    assert out["demand_scoped"] is True


def test_demand_collects_exactly_declared_subset():
    """一问一集:只采被具名问题声明的那些事实,不多不少,并留失效条件。"""
    demand = {
        "question": "本回合能否安全落一个 commit?",
        "facts": ["working_tree_clean"],
        "retires_when": "该 commit 决策做出即退",
    }
    out = probe.collect(_repo_root(), demand)
    names = [f["name"] for f in out["facts"]]
    assert names == ["working_tree_clean"], "只应采声明的那一枚,得到 %r" % names
    assert out["declared_by"] == demand["question"]
    assert out["retires_when"] == demand["retires_when"]


def test_unregistered_fact_fails_closed():
    """声明了登记表里没有的事实名:fail-closed 记 value=None,绝不静默丢弃。"""
    demand = {"question": "q", "facts": ["no_such_fact"], "retires_when": None}
    out = probe.collect(_repo_root(), demand)
    assert len(out["facts"]) == 1, "未登记事实也须留痕(不得静默丢弃)"
    assert out["facts"][0]["value"] is None
    assert out["facts"][0]["authority"] == "none"


def _with_codex_home(value):
    """临时设置/清除 CODEX_HOME,返回一个 restore 闭包。"""
    saved = os.environ.get("CODEX_HOME")
    if value is None:
        os.environ.pop("CODEX_HOME", None)
    else:
        os.environ["CODEX_HOME"] = value

    def restore():
        if saved is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = saved
    return restore


def test_ledger_unset_codex_home_is_undetermined():
    """CODEX_HOME 未配置:无从判定,须 value=None,绝不裁成 False(确认不可达)。"""
    restore = _with_codex_home(None)
    try:
        fact = probe._shared_ledger_reachable()
        assert fact["value"] is None, (
            "未配置 CODEX_HOME 应无从判定(None),得到 %r" % fact["value"]
        )
        assert fact["detail"]["codex_home_set"] is False
        assert fact["authority"] == "none"
    finally:
        restore()


def test_ledger_set_but_absent_is_false():
    """CODEX_HOME 指向真实读到的'不存在':这是诚实的 False,不是 None。"""
    with tempfile.TemporaryDirectory() as tmp:
        # tmp 存在但其下无 method-state 子目录 → 确认不存在 → 真读到"不在"。
        restore = _with_codex_home(tmp)
        try:
            fact = probe._shared_ledger_reachable()
            assert fact["value"] is False, (
                "确认不存在的 ledger 应为 False(真读到不在),得到 %r" % fact["value"]
            )
            assert fact["detail"]["exists"] is False
        finally:
            restore()


def test_ledger_present_is_true():
    """CODEX_HOME/method-state 真为目录:value=True。"""
    with tempfile.TemporaryDirectory() as tmp:
        os.mkdir(os.path.join(tmp, "method-state"))
        restore = _with_codex_home(tmp)
        try:
            fact = probe._shared_ledger_reachable()
            assert fact["value"] is True, (
                "真实存在的 ledger 目录应为 True,得到 %r" % fact["value"]
            )
            assert fact["detail"]["is_dir"] is True
        finally:
            restore()


if __name__ == "__main__":
    test_non_repo_workspace_fails_closed()
    test_nonexistent_workspace_fails_closed()
    test_real_repo_reports_bool()
    test_no_demand_collects_nothing()
    test_demand_collects_exactly_declared_subset()
    test_unregistered_fact_fails_closed()
    test_ledger_unset_codex_home_is_undetermined()
    test_ledger_set_but_absent_is_false()
    test_ledger_present_is_true()
    print("ok: 9 passed — fail-closed(git+ledger)+ demand-scoped(一问一集、问结集退)验证通过")
