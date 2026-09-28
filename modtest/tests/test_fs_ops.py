#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fs_ops 全流程夹具自测（tests/fixture 下建临时假 mod，测完自清理）。

覆盖验收点：
  1. plan_targets：dict 与 (label, full, is_win) 三元组两种入参；
     保留方不进清单；原版条目（idx=-1 / 「原版」标签）绝不进清单；
     缺 full 的被删方报 ValueError。
  2. execute_deletes：备份先于删除；备份落点结构正确且不在 mod 目录里；
     删除成功；空目录向上清理到 mod 根为止（根不删、非空即停）；
     manifest 逐项追加、JSON 合法。
  3. restore_backups：按 manifest 放回原路径，内容字节一致；
     目标已存在时跳过不覆盖。
  4. is_workshop：组件级大小写不敏感判定。

跑法：python tests\\test_fs_ops.py
"""

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "src"))
sys.path.insert(0, SRC)

if True:  # 顶层 import 前先把 src 挂进 sys.path（放在函数外 IDE 也能解析）
    import fs_ops  # noqa: E402

TOOL_ROOT = None   # 临时工具根（模拟 modtest 根，backups 落在这里）
MOD_A = None       # mod A 根
MOD_B = None       # mod B 根
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  [PASS] " if cond else "  [FAIL] ") + name +
          ("" if cond else "  -- " + str(detail)))


def make_yml(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def setup():
    global TOOL_ROOT, MOD_A, MOD_B
    # 注意：不放进系统 TEMP —— 本工具的沙箱允许写会话工作区，
    # TEMP 里建目录可能被拒。夹具放在 tests/ 下，测完自删，可复跑。
    TOOL_ROOT = os.path.join(HERE, "fixture", "_run")
    if os.path.isdir(TOOL_ROOT):
        shutil.rmtree(TOOL_ROOT, ignore_errors=True)
    MOD_A = os.path.join(TOOL_ROOT, "fakeMods", "AlphaMod")
    MOD_B = os.path.join(TOOL_ROOT, "fakeMods", "BetaMod")
    # Alpha：两个文件，其中一个在深层目录
    make_yml(os.path.join(MOD_A, "localisation", "english", "a_l_english.yml"),
             'l_english:\n KEY_A:0 "alpha"\n')
    make_yml(os.path.join(MOD_A, "gfx", "models", "deep", "ship.asset"), "asset A\n")
    # Beta：同路径覆盖其中之一，另一个独有
    make_yml(os.path.join(MOD_B, "localisation", "english", "a_l_english.yml"),
             'l_english:\n KEY_A:0 "beta"\n')
    make_yml(os.path.join(MOD_B, "events", "b_events.txt"), "event B\n")


def teardown():
    # 测试进程自己的文件，不会有只读残留；真有残留就留着目录让失败可见
    shutil.rmtree(TOOL_ROOT, ignore_errors=True)


def test_plan_targets():
    print("== plan_targets ==")
    mods = [
        {"idx": 0, "name": "AlphaMod", "root": MOD_A},
        {"idx": 1, "name": "BetaMod", "root": MOD_B},
    ]
    fa = os.path.join(MOD_A, "localisation", "english", "a_l_english.yml")
    fb = os.path.join(MOD_B, "localisation", "english", "a_l_english.yml")
    fv = os.path.join("G:", os.sep, "SteamLibrary", "steamapps", "common",
                      "Stellaris", "localisation", "english", "a_l_english.yml")

    # dict 形式：保留 1（Beta），Alpha 应进清单
    chain = [
        {"idx": 0, "name": "AlphaMod", "root": MOD_A, "full": fa},
        {"idx": 1, "name": "BetaMod", "root": MOD_B, "full": fb},
        {"idx": -1, "name": "vanilla", "root": "G:\\Steam", "full": fv},
    ]
    tg = fs_ops.plan_targets(chain, 1)
    check("keep Beta: only Alpha listed",
          len(tg) == 1 and tg[0]["idx"] == 0 and tg[0]["full"] == fa, tg)
    check("rel preserved",
          tg and tg[0]["rel"] == os.path.join("localisation", "english",
                                              "a_l_english.yml"), tg[0]["rel"])

    # 原版条目在 keep_idx=0 时也不得进入删除清单
    tg2 = fs_ops.plan_targets(chain, 0)
    check("vanilla never a target (keep Alpha)",
          len(tg2) == 1 and tg2[0]["idx"] == 1, tg2)

    # 三元组形式（GUI 详情链）：label "1:AlphaMod"；「原版」标签被跳过
    chain3 = [("1:AlphaMod", fa, False), ("2:BetaMod", fb, True),
              ("原版", fv, False)]
    tg3 = fs_ops.plan_targets(chain3, 1, mods=mods)
    check("tuple form: vanilla label skipped",
          len(tg3) == 1 and tg3[0]["idx"] == 0 and tg3[0]["mod"] == "AlphaMod", tg3)

    # 缺 full 的被删方必须报错
    try:
        fs_ops.plan_targets([{"idx": 0, "name": "AlphaMod", "full": ""}], 1)
        check("missing full raises", False, "no exception")
    except ValueError:
        check("missing full raises", True)


def test_execute_and_restore():
    print("== execute_deletes / restore_backups ==")
    fa = os.path.join(MOD_A, "localisation", "english", "a_l_english.yml")
    fd = os.path.join(MOD_A, "gfx", "models", "deep", "ship.asset")
    mods = [
        {"idx": 0, "name": "AlphaMod", "root": MOD_A},
        {"idx": 1, "name": "BetaMod", "root": MOD_B},
    ]
    chain = [
        {"idx": 0, "name": "AlphaMod", "root": MOD_A, "full": fa},
        {"idx": 0, "name": "AlphaMod", "root": MOD_A, "full": fd},
    ]
    targets = fs_ops.plan_targets(chain, 1, mods=mods)
    stamp = "20260929_010203"
    results = fs_ops.execute_deletes(targets, TOOL_ROOT, stamp=stamp)

    check("two deletes ok", all(r["ok"] for r in results), results)
    check("file really gone", not os.path.exists(fa) and not os.path.exists(fd))

    # 备份落点：tool_root/backups/stamp/AlphaMod/原相对路径
    b_root = os.path.join(TOOL_ROOT, "backups", stamp)
    ba = os.path.join(b_root, "AlphaMod", "localisation", "english",
                      "a_l_english.yml")
    bd = os.path.join(b_root, "AlphaMod", "gfx", "models", "deep", "ship.asset")
    check("backup at correct layout", os.path.isfile(ba) and os.path.isfile(bd))
    with open(ba, encoding="utf-8") as f:
        check("backup content matches", f.read() == 'l_english:\n KEY_A:0 "alpha"\n')
    check("backups never inside a mod root",
          not b_root.startswith(os.path.normcase(MOD_A)) and
          not b_root.startswith(os.path.normcase(MOD_B)))

    # 空目录清理：english/ 与 gfx/models/deep/ 及其空父级应消失；
    # localisation/ 因 Beta 也用？不，Beta 的同名文件在 BetaMod 根下，
    # Alpha 的 localisation/english 已空，localisation/ 本身也应消失。
    check("empty dirs cleaned up to mod root",
          not os.path.exists(os.path.join(MOD_A, "localisation")) and
          not os.path.exists(os.path.join(MOD_A, "gfx")), "dirs still there")

    # manifest：两笔记录，JSON 合法
    mp = os.path.join(b_root, "manifest.json")
    with open(mp, encoding="utf-8") as f:
        manifest = json.load(f)
    check("manifest has 2 records", len(manifest) == 2, manifest)
    check("manifest targets recorded",
          sorted(m["target"] for m in manifest) == sorted([fa, fd]), manifest)

    # restore：全部放回，内容一致
    rs = fs_ops.restore_backups(b_root)
    check("restore all ok", all(r["ok"] for r in rs), rs)
    with open(fa, encoding="utf-8") as f:
        check("restored content identical",
              f.read() == 'l_english:\n KEY_A:0 "alpha"\n')
    # 再还原一次：目标已存在 → 跳过不覆盖
    rs2 = fs_ops.restore_backups(b_root)
    check("second restore skips existing",
          len(rs2) == 2 and not any(r["ok"] for r in rs2), rs2)


def test_delete_failure_paths():
    print("== failure paths ==")
    # 目标不存在：跳过并如实记录，不炸
    ghost = {"mod": "GhostMod", "idx": 9, "root": MOD_B,
             "rel": "x.txt", "full": os.path.join(MOD_B, "x.txt")}
    r = fs_ops.execute_deletes([ghost], TOOL_ROOT, stamp="20260929_090909")
    check("missing target skipped with error",
          len(r) == 1 and not r[0]["ok"] and r[0]["error"], r[0]["error"])

    # 备份失败（把备份根造成文件，makedirs 必败）→ 该项不删
    victim = os.path.join(MOD_B, "events", "b_events.txt")
    stamp = "20260929_040404"
    b_root = os.path.join(TOOL_ROOT, "backups", stamp)
    os.makedirs(os.path.dirname(b_root), exist_ok=True)
    with open(b_root, "w") as f:      # 备份时间戳目录被文件占用
        f.write("blocker")
    t = fs_ops.plan_targets([{"idx": 1, "name": "BetaMod", "root": MOD_B,
                              "full": victim}], 0)
    r2 = fs_ops.execute_deletes(t, TOOL_ROOT, stamp=stamp)
    check("backup failure -> no delete",
          len(r2) == 1 and not r2[0]["ok"] and os.path.isfile(victim), r2)
    os.remove(b_root)                 # 拆掉路障，供后续用


def test_is_workshop():
    print("== is_workshop ==")
    ws = os.path.join("G:", os.sep, "SteamLibrary", "steamapps", "workshop",
                      "content", "281990", "123456", "localisation", "x.yml")
    check("workshop+281990 True", fs_ops.is_workshop(ws))
    check("case insensitive True", fs_ops.is_workshop(ws.upper()))
    doc = os.path.join("C:", os.sep, "Users", "hp", "Documents", "Paradox",
                       "Stellaris", "mod", "m1", "localisation", "x.yml")
    check("documents path False", not fs_ops.is_workshop(doc))
    ck = os.path.join("G:", os.sep, "SteamLibrary", "steamapps", "workshop",
                      "content", "1086940", "x.yml")
    check("other game id False", not fs_ops.is_workshop(ck))
    ck2 = os.path.join("G:", os.sep, "SteamLibrary", "steamapps", "common",
                       "281990", "x.yml")
    check("281990 without workshop False", not fs_ops.is_workshop(ck2))


def test_rmtree_boundary():
    print("== rmtree_empty_dirs boundary ==")
    # stop 本身即使为空也绝不删
    empty_root = os.path.join(TOOL_ROOT, "EmptyRoot")
    os.makedirs(empty_root)
    fs_ops.rmtree_empty_dirs(empty_root, empty_root)
    check("stop dir itself never deleted", os.path.isdir(empty_root))
    # start 在 stop 外：整个不做
    outside = os.path.join(TOOL_ROOT, "Outside")
    os.makedirs(outside)
    fs_ops.rmtree_empty_dirs(outside, empty_root)
    check("outside start untouched", os.path.isdir(outside))


def main():
    setup()
    try:
        test_plan_targets()
        test_execute_and_restore()
        test_delete_failure_paths()
        test_is_workshop()
        test_rmtree_boundary()
    finally:
        teardown()
    print("")
    print("PASS=%d FAIL=%d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", FAIL)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
