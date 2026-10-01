#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L3 MERGE 语义回归锁：on_actions 不属 key 互抢，同路径整文件替换照旧报。

依据 Stellaris 官方 wiki Modding 页 Common folder 总表 on_actions 行：
Overwrite Type = "NO/MERGE"，Notes = "Cannot modify existing entries; new entries
will be merged with the existing entry with the same NAME={}." —— 即同目录下不同
文件只是把各自条目追加合并到同名 on_action 上，不存在谁覆盖谁、没有胜者，
不该被当成 key 互抢统计。本测试锁定该行为，同时防两种误伤：把「同路径整文件
替换」也吞掉、或把所有 key 一刀切滤掉。

覆盖四组断言：
  1. 语义表自证：dir_semantics("common/on_actions") == "MERGE"，且全表 MERGE
     目录有且仅有 on_actions。
  2. L3 剔除：res["keys"] 里不得出现 sem=="MERGE" 或 dir 以 common/on_actions
     开头的记录（修复前会各出一条，故本测试在旧代码上必 FAIL）。
  3. 同路径照旧报：两个 mod 的同相对路径 on_actions 文件内容不同 → 仍进
     res["diff"]（MERGE 语义只作用于「不同文件名同 key」，不吞整文件替换）。
  4. 对照不误伤：common/buildings(LIOS) 下不同文件名同 key 仍进 res["keys"]
     且 sem=="LIOS"（防「一刀切滤掉所有 key」）。

夹具建在 tests/fixture_merge 下，跑完自清理（不写系统 TEMP，见 tests/test_fs_ops.py
的说明）；VANILLA_ROOT 指向夹具内的空目录，不索引真实游戏目录。另有一组夹具自检
断言（直接调 extract_keys 核对三个 on_actions 文件都析出同名 key），防止夹具没造出
冲突导致第 2 组断言空转。

跑法：
  正常（工作区 src 的新代码）：
      cd modtest && python tests\\test_merge_semantics.py
  变异验证（同一测试跑修复前代码，必须 FAIL）：
      git show HEAD:modtest/src/mod_conflict_check.py > build\\acct\\mod_conflict_check.py
      set MCC_SRC_DIR=C:\\StellarisMod\\modtest\\build\\acct
      python tests\\test_merge_semantics.py

IDE 已知误报：下方对 mod_conflict_check 的 import 依赖 sys.path 注入（tests 引 src
的跨目录导入），WebStorm 静态分析解析不到，实跑正常，用 noinspection 压掉。
"""

import hashlib
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL_ROOT = os.path.dirname(HERE)
SRC = os.path.join(TOOL_ROOT, "src")
FIX = os.path.join(HERE, "fixture_merge")

# 变异验证：MCC_SRC_DIR 指向暂存的「修复前」源码目录（如 modtest/build/acct），
# 插到 sys.path 最前，import 到的就是旧代码；不设则用工作区 src。
ALT_SRC = os.environ.get("MCC_SRC_DIR", "")
sys.path.insert(0, SRC)
if ALT_SRC:
    sys.path.insert(0, ALT_SRC)

if True:  # 顶层 import 前先挂好 sys.path（放在函数外 IDE 也能解析）
    # noinspection PyUnresolvedReferences
    import mod_conflict_check as mcc  # noqa: E402

ONACT_DIR = "common/on_actions"
BLD_DIR = "common/buildings"
ONACT_REL = "common/on_actions/shared_actions.txt"   # 两个 mod 的同相对路径文件
ONACT_KEY = "on_yearly_pulse"
BLD_KEY = "fixture_building"
# 实测 win_rel 形如 common/buildings/zzz_buildings.txt（L3 的 entries[].rel 取的是
# 完整相对路径，不是 basename）
BLD_WIN_REL = "common/buildings/zzz_buildings.txt"

PASS = 0
FAIL = 0


def check(name, cond, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] " + name)
    else:
        FAIL += 1
        print("  [FAIL] " + name + ("" if detail is None
                                    else "  -- " + str(detail)))


def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def has_merge_filter(text):
    """源码里是否已有「MERGE 直接 continue」的拦截分支。

    只用于变异验证的前提核对：旧代码必须没有这个分支，否则变异无意义。
    同时认 `==` 与 `in (...)` 两种写法（防止「一刀切式修复」被当成旧代码），
    并跳过注释行；continue 允许写在同一行或紧随的下一行。
    """
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("#"):
            continue
        if "sem" not in ln or "MERGE" not in ln:
            continue
        tested = ("==" in ln) or (" in " in ln)
        if not tested:
            continue
        if "continue" in ln.split(":", 1)[-1]:
            return True
        if i + 1 < len(lines) and "continue" in lines[i + 1]:
            return True
    return False


def make_fixture():
    """建夹具，返回 (doc_root, vanilla_root, playlist, fx)。

    fx 里带各文件的绝对路径，供夹具自检直接调 extract_keys（不靠拼路径猜）。

    两个 mod 各带三份 common 文件：
      on_actions/aaa_alpha.txt + on_actions/zzz_beta.txt  不同文件名、同 key
        （MERGE 目录的真冲突形状，修复后必须被剔除）
      on_actions/shared_actions.txt                        同相对路径、内容不同
        （L1 整文件替换，必须照旧进 diff）
      buildings/aaa_buildings.txt + zzz_buildings.txt      不同文件名、同 key
        （LIOS 对照，必须照旧进 keys）
    """
    if os.path.isdir(FIX):
        shutil.rmtree(FIX, ignore_errors=True)
    mods_dir = os.path.join(FIX, "mod")
    vanilla = os.path.join(FIX, "vanilla")     # 空目录：不索引真实游戏目录
    os.makedirs(vanilla)
    os.makedirs(mods_dir)

    # 同一个 on_action 上各追加一条事件：追加合并不产生胜者
    on_a = "on_yearly_pulse = {\n\tevents = { alpha.1 }\n}\n"
    on_b = "on_yearly_pulse = {\n\tevents = { beta.1 }\n}\n"
    # 同相对路径、内容不同（长度也不同，保证两侧 md5 必然不同）
    shared_a = "on_yearly_pulse = {\n\tevents = { alpha.9 }\n}\n"
    shared_b = "on_yearly_pulse = {\n\tevents = { beta.99 }\n}\n"
    # LIOS 对照：不同文件名、同 key，zzz_ 靠后者胜
    bld_a = "fixture_building = {\n\tcost = 1\n}\n"
    bld_b = "fixture_building = {\n\tcost = 2\n}\n"

    shared_rel = os.path.relpath(ONACT_REL, ONACT_DIR)
    specs = (
        ("alpha_fixture", "AlphaFixture", {
            "common/on_actions/aaa_alpha.txt": on_a,
            "common/on_actions/" + shared_rel: shared_a,
            "common/buildings/aaa_buildings.txt": bld_a,
        }),
        ("beta_fixture", "BetaFixture", {
            "common/on_actions/zzz_beta.txt": on_b,
            "common/on_actions/" + shared_rel: shared_b,
            "common/buildings/zzz_buildings.txt": bld_b,
        }),
    )
    fx = {}
    for stem, name, files in specs:
        for rel, text in files.items():
            full = os.path.join(mods_dir, stem, rel.replace("/", os.sep))
            write_file(full, text)
            fx.setdefault(rel, []).append(full)
        # 描述符：path 用相对 Documents 的写法，scan 会按 DOC_ROOT 解析
        write_file(os.path.join(mods_dir, stem + ".mod"),
                   'name="%s"\npath="mod/%s"\nsupported_version="3.14.*"\n'
                   % (name, stem))

    playlist = os.path.join(FIX, "dlc_load.json")
    write_file(playlist, json.dumps(
        {"enabled_mods": ["mod/alpha_fixture.mod", "mod/beta_fixture.mod"],
         "disabled_dlcs": []}, ensure_ascii=False))
    return FIX, vanilla, playlist, fx


def main():
    # noinspection PyUnresolvedReferences
    import i18n
    i18n.set_language("zh-CN")      # 只改内存，不写 config.json

    print("== 环境（%s）==" % ("变异：MCC_SRC_DIR" if ALT_SRC else "工作区 src"))
    expect_dir = os.path.normcase(os.path.abspath(ALT_SRC or SRC))
    loaded_dir = os.path.normcase(os.path.dirname(os.path.abspath(mcc.__file__)))
    check("import 到期望的源码目录", loaded_dir == expect_dir,
          "loaded=%s expect=%s" % (loaded_dir, expect_dir))

    src_txt = ""
    try:
        with io.open(mcc.__file__, "r", encoding="utf-8", errors="replace") as f:
            src_txt = f.read()
    except OSError:
        pass
    has_filter = has_merge_filter(src_txt)
    md5 = hashlib.md5(src_txt.encode("utf-8", "replace")).hexdigest()[:12]
    print("  (info) 被测源码: %s  md5:%s" % (mcc.__file__, md5))
    print("  (info) 源码含 MERGE 拦截分支: %s" % has_filter)
    if ALT_SRC:
        check("变异前提：旧源码无 MERGE 拦截分支", not has_filter,
              "旧代码已含拦截分支，变异无意义")

    doc_root, vanilla, playlist, fx = make_fixture()
    old_paths = (mcc.DOC_ROOT, mcc.VANILLA_ROOT, mcc.PLAYLIST)
    res = None
    scan_err = ""
    try:
        try:
            mcc.DOC_ROOT, mcc.VANILLA_ROOT, mcc.PLAYLIST = (doc_root, vanilla,
                                                           playlist)
            res = mcc.scan()
        except Exception as e:                       # noqa: BLE001
            scan_err = "%s: %s" % (type(e).__name__, e)
        finally:
            mcc.DOC_ROOT, mcc.VANILLA_ROOT, mcc.PLAYLIST = old_paths
        r = res or {}

        print("== 夹具与扫描 ==")
        check("scan() 正常返回", res is not None, scan_err)
        mods = r.get("mods") or []
        check("夹具 2 个 mod 均解析出真实根目录",
              len(mods) == 2 and all(m.get("root") and os.path.isdir(m["root"])
                                     for m in mods),
              [(m.get("name"), m.get("root"), m.get("errors")) for m in mods])
        check("夹具 mod 名与加载顺序 = AlphaFixture,BetaFixture",
              [m.get("name") for m in mods] == ["AlphaFixture", "BetaFixture"],
              [m.get("name") for m in mods])

        print("== 夹具自检：MERGE 冲突真实存在（防断言空转）==")
        # 直接调被测模块的 key 提取，独立于 scan() 的剔除逻辑：三个 on_actions
        # 文件都必须析出同名 key，且分布在 >=2 个文件名上 —— 这正是 L3 候选形状。
        # 路径取自 make_fixture 的实际落盘位置，不靠字符串拼接猜。
        onact_full = fx["common/on_actions/aaa_alpha.txt"] + \
            fx["common/on_actions/zzz_beta.txt"] + fx[ONACT_REL]
        got = {}
        for full in onact_full:
            rel = os.path.relpath(full, doc_root).replace(os.sep, "/")
            got[rel] = mcc.extract_keys(full, ONACT_DIR)
        check("三个 on_actions 文件都析出同 key",
              all(ONACT_KEY in got[rel] for rel in got), got)
        check("on_actions 同 key 分布在 >=2 个文件名上（具备 L3 候选形状）",
              len({os.path.basename(rel) for rel in got
                   if ONACT_KEY in got[rel]}) >= 2, got)

        print("== 1. 语义表自证 ==")
        check('dir_semantics("common/on_actions") == "MERGE"',
              mcc.dir_semantics(ONACT_DIR) == "MERGE",
              mcc.dir_semantics(ONACT_DIR))
        check('dir_semantics("common/buildings") == "LIOS"',
              mcc.dir_semantics(BLD_DIR) == "LIOS",
              mcc.dir_semantics(BLD_DIR))
        merge_dirs = sorted(k for k, v in mcc.WIKI_COMMON_OVERWRITE.items()
                            if v == "MERGE")
        check("wiki 表 MERGE 语义目录有且仅有 on_actions",
              merge_dirs == ["on_actions"], merge_dirs)

        print("== 2. L3 剔除 MERGE ==")
        keys = r.get("keys") or []
        merge_recs = [x for x in keys if x.get("sem") == "MERGE"]
        check("res['keys'] 无 sem==MERGE 的记录", not merge_recs,
              [(x.get("dir"), x.get("key"), x.get("sem")) for x in merge_recs])
        onact_recs = [x for x in keys
                      if str(x.get("dir", "")).startswith(ONACT_DIR)]
        check("res['keys'] 无 dir 以 common/on_actions 开头的记录",
              not onact_recs,
              [(x.get("dir"), x.get("key"), x.get("sem")) for x in onact_recs])

        print("== 3. 同路径整文件替换照旧报 ==")
        diff_map = {d.get("rel"): d for d in (r.get("diff") or [])}
        check("res['diff'] 含 " + ONACT_REL, ONACT_REL in diff_map,
              sorted(diff_map))
        d = diff_map.get(ONACT_REL) or {}
        check("该 diff 条目含两个 mod 各自的文件",
              sorted(e.get("idx") for e in (d.get("entries") or [])) == [0, 1],
              [(e.get("idx"), e.get("name")) for e in (d.get("entries") or [])])
        md5s = {e.get("md5") for e in (d.get("entries") or [])}
        check("该对文件内容确实不同（md5 两侧不等且非空）",
              len(md5s) == 2 and "" not in md5s, md5s)

        print("== 4. 对照：LIOS 不被误伤 ==")
        bld = [x for x in keys
               if x.get("key") == BLD_KEY and x.get("dir") == BLD_DIR]
        check("LIOS 目录同 key 仍在 res['keys']（未一刀切滤掉）",
              len(bld) == 1,
              [(x.get("dir"), x.get("key"), x.get("sem")) for x in keys])
        check("该记录 sem == LIOS", bool(bld) and bld[0].get("sem") == "LIOS",
              bld[0].get("sem") if bld else None)
        check("LIOS 仍判出胜者 = 文件名靠后的 zzz_buildings.txt",
              bool(bld) and
              bld[0].get("win_rel") == BLD_WIN_REL and
              bld[0].get("win_mod") == 1,
              (bld[0].get("win_rel"), bld[0].get("win_mod")) if bld else None)
        check("res['keys'] 恰为这一条 LIOS（既未多滤也未漏滤）",
              len(keys) == 1,
              [(x.get("dir"), x.get("key"), x.get("sem")) for x in keys])
    finally:
        shutil.rmtree(FIX, ignore_errors=True)

    print("PASS=%d FAIL=%d" % (PASS, FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
