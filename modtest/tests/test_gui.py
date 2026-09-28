#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gui_app 自测：不依赖外部窗口枚举，用 winfo + 行数断言。

用伪造的小 result 字典注入 App（不跑真实扫描），覆盖：
  页签结构、文件树挂载、本地化页签、详情操作条、删除清单增删、
  删除取消路径（不碰真实 mod），以及夹具上的真实删除+备份+还原全流程。
跑法：python tests\\test_gui.py，结束后自清理夹具与本次备份。

IDE 已知误报：下方对 fs_ops / i18n / gui_app 的 import 依赖第 21 行的
sys.path 注入（tests 引 src 的跨目录导入），WebStorm 静态分析解析不到，
实跑正常，用 noinspection 压掉。
"""

import io
import json
import os
import shutil
import sys

# noinspection PyUnresolvedReferences
import tkinter.messagebox as mb

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, SRC)

TOOL_ROOT = os.path.dirname(SRC)
FIX = os.path.join(HERE, "fixture_gui")
BACKUPS = os.path.join(TOOL_ROOT, "backups")

PASS = FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] " + name)
    else:
        FAIL += 1
        print("  [FAIL] " + name)


def make_fixture():
    fa = os.path.join(FIX, "modA")
    fb = os.path.join(FIX, "modB")
    for root in (fa, fb):
        os.makedirs(os.path.join(root, "common"), exist_ok=True)
        os.makedirs(os.path.join(root, "localisation"), exist_ok=True)
    pa = os.path.join(fa, "common", "stuff.txt")
    pb = os.path.join(fb, "common", "stuff.txt")
    io.open(pa, "w", encoding="utf-8").write("A version\n")
    io.open(pb, "w", encoding="utf-8").write("B version\n")
    la = os.path.join(fa, "localisation", "x_l_simp_chinese.yml")
    lb = os.path.join(fb, "localisation", "x_l_simp_chinese.yml")
    io.open(la, "w", encoding="utf-8").write(
        "l_simp_chinese:\n HELLO_KEY:0 \"A text\"\n")
    io.open(lb, "w", encoding="utf-8").write(
        "l_simp_chinese:\n HELLO_KEY:0 \"B text\"\n")
    return {"A": {"root": fa, "common": pa, "loc": la},
            "B": {"root": fb, "common": pb, "loc": lb}}


def fake_result(fx):
    ma = {"idx": 0, "name": "Alpha", "root": fx["A"]["root"], "files": 2,
          "vover": 0, "ovr": 0, "beaten": 1, "redund": 0, "errors": [],
          "desc": "", "ver": "", "deps": [], "rp": [], "entry": "",
          "stem": "alpha"}
    mb_ = {"idx": 1, "name": "Beta", "root": fx["B"]["root"], "files": 2,
           "vover": 0, "ovr": 1, "beaten": 0, "redund": 0, "errors": [],
           "desc": "", "ver": "", "deps": [], "rp": [], "entry": "",
           "stem": "beta"}
    diff = {"rel": "common/stuff.txt",
            "entries": [
                {"idx": 0, "name": "Alpha", "full": fx["A"]["common"],
                 "size": 9, "mtime": 0, "md5": "aaaaaaaaaaaaaaaa"},
                {"idx": 1, "name": "Beta", "full": fx["B"]["common"],
                 "size": 9, "mtime": 0, "md5": "bbbbbbbbbbbbbbbb"}],
            "in_vanilla": False, "winner": 1, "winner_name": "Beta"}
    loc = {"key": "HELLO_KEY", "lang": "l_simp_chinese",
           "entries": [
               {"rel": "localisation/x_l_simp_chinese.yml", "mod": 0,
                "full": fx["A"]["loc"]},
               {"rel": "localisation/x_l_simp_chinese.yml", "mod": 1,
                "full": fx["B"]["loc"]}],
           "winner": 1, "winner_label": "2:Beta", "loser_mods": [0],
           "mods": [0, 1], "has_vanilla": False, "mod_vs_mod": True}
    return {
        "playlist": "", "mods": [ma, mb_], "diff": [diff], "same": [],
        "vanilla": [], "keys": [], "l3_files": 0, "iface": [], "l4_files": 0,
        "problems": [], "replace_paths": [], "vanilla_count": 0,
        "elapsed": 0.0, "vanilla_root": "",
        "loc": [loc], "loc_stats": {0: {"defined": 1, "lost": 1,
                                        "beaten_by": ["Beta"]},
                                    1: {"defined": 1, "lost": 0,
                                        "beaten_by": []}},
        "loc_files": 2, "loc_keys": 1, "loc_elapsed": 0.0,
    }


def main():
    # 防跨运行残留：上次测试若在语言切换中途崩溃，config 里会留下别的语言，
    # 先归位到 zh-CN，保证断言与环境无关。
    # noinspection PyUnresolvedReferences
    import i18n
    i18n.set_language("zh-CN")
    # noinspection PyUnresolvedReferences
    from fs_ops import restore_backups
    # noinspection PyUnresolvedReferences
    from i18n import t as _t
    t = _t
    # noinspection PyUnresolvedReferences
    import gui_app
    # 隔离 config：config.json 在 %APPDATA%，跨运行残留（语言、路径）会让
    # 断言时好时坏；这里把两侧的 load/save 换成进程内字典，测试彻底确定性。
    # noinspection PyUnresolvedReferences
    import mod_conflict_check as _mcc
    _mem_cfg = {"lang": "zh-CN"}
    _mcc.load_config = lambda: dict(_mem_cfg)
    _mcc.save_config = lambda cfg: (_mem_cfg.clear(), _mem_cfg.update(cfg), True)[2]
    gui_app.load_config = _mcc.load_config
    gui_app.save_config = _mcc.save_config
    fx = make_fixture()
    res = fake_result(fx)
    backups_before = os.path.isdir(BACKUPS)

    app = gui_app.App(include_dlc=False)
    try:
        app.update_idletasks()
        app.update()
        app.result = res
        app._fill()
        app.update()

        print("== 结构 ==")
        check("主页签=文件树+高级",
              app.nb_main.tabs() and
              app.nb_main.tab(0, "text") == t("gui.143") and
              app.nb_main.tab(1, "text") == t("gui.145"))
        check("mod 列表 2 行", len(app.tv_mods.get_children()) == 2)
        check("总表含 diff+loc 行",
              len(app.tv_ov.get_children()) == 2)
        check("本地化页签 1 行", len(app.tv_loc.get_children()) == 1)
        check("文件树文件节点",
              app.tv_tree.exists("f|common/stuff.txt"))
        kids = app.tv_tree.get_children("f|common/stuff.txt")
        check("文件树 mod 链 2 层", len(kids) == 2)
        check("生效者在下(后加载)",
              app.tv_tree.item(kids[1], "text") == "2:Beta" and
              "win" in app.tv_tree.item(kids[1], "tags"))
        check("文件树第二列=生效者",
              app.tv_tree.set("f|common/stuff.txt", "winner") ==
              t("gui.180") % "2:Beta")

        print("== 文件树选中 → 操作条 ==")
        app.tv_tree.selection_set("f|common/stuff.txt")
        app._on_tree_select()
        check("保留方下拉有链上全部 mod",
              list(app.cb_keep["values"]) == ["1:Alpha", "2:Beta"])
        check("默认保留方=生效者", app.var_keep.get() == "2:Beta")
        check("删除按钮可用",
              "disabled" not in app.btn_del_keep.state())

        print("== 删除清单 ==")
        app.var_keep.set("1:Alpha")        # 保留输家 → 删生效方的文件
        app._add_pending()
        check("清单 1 条", len(app.pending) == 1 and
              len(app.tv_pend.get_children()) == 1)
        check("目标=Beta 的文件",
              app.pending[0]["targets"] and
              app.pending[0]["targets"][0]["full"] == fx["B"]["common"])
        app.tv_pend.selection_set(app.tv_pend.get_children()[0])
        app._remove_pending()
        check("移除后清空", not app.pending)

        print("== 删除：取消路径 ==")
        app.var_keep.set("1:Alpha")
        orig = mb.askyesno
        mb.askyesno = lambda *a, **k: False
        try:
            app._delete_keep_version()
        finally:
            mb.askyesno = orig
        check("取消后文件仍在", os.path.isfile(fx["B"]["common"]))
        check("详情显示已取消",
              t("gui.178") in app.txt.get("1.0", "end"))

        print("== 删除：真实执行（夹具）+ 备份 + 还原 ==")
        mb.askyesno = lambda *a, **k: True
        real_rescan = app.rescan
        app.rescan = lambda: None      # 隔离真实重扫，保持假数据状态可断言
        try:
            app._delete_keep_version()
        finally:
            mb.askyesno = orig
            app.rescan = real_rescan
        check("Beta 的文件已删除", not os.path.exists(fx["B"]["common"]))
        stamps = os.listdir(BACKUPS) if os.path.isdir(BACKUPS) else []
        bak = None
        for st in stamps:
            p = os.path.join(BACKUPS, st, "Beta", "common", "stuff.txt")
            if os.path.isfile(p):
                bak = os.path.join(BACKUPS, st)
        check("备份落在 modtest\\backups", bak is not None)
        if bak:
            man = json.load(io.open(os.path.join(bak, "manifest.json"),
                                    encoding="utf-8"))
            check("manifest 记录了目标",
                  any(r["target"].lower() == fx["B"]["common"].lower()
                      for r in man))
            rs = restore_backups(bak)
            check("还原回原位", rs and rs[0]["ok"] and
                  os.path.isfile(fx["B"]["common"]) and
                  io.open(fx["B"]["common"], encoding="utf-8").read() ==
                  "B version\n")

        print("== 增量功能：过滤 / 横幅跳转 / 还原入口 ==")
        app.var_tree_filter.set("stuff.txt")
        app._apply_tree_filter()
        app.update()
        check("过滤后仅剩匹配文件",
              len(app.tv_tree.get_children("")) >= 1 and
              app.tv_tree.exists("f|common/stuff.txt"))
        check("过滤视图展开", app.tv_tree.item("d|common", "open"))
        app._clear_tree_filter()
        app.update()
        check("清空过滤恢复全树", app.tv_tree.exists("f|common/stuff.txt"))
        app._banner_jump()
        sel = app.tv_tree.selection()
        check("横幅跳转选中首个冲突文件",
              sel and sel[0].startswith("f|"))
        check("跳转后详情有内容",
              bool(app.txt.get("1.0", "end").strip()))
        shown = []
        mb.showinfo = lambda *a, **k: shown.append(a)
        bdir = os.path.join(TOOL_ROOT, "backups")
        moved = False
        if os.path.isdir(bdir):
            shutil.move(bdir, bdir + "_t")
            moved = True
        try:
            app._restore_dialog()      # 无备份 → 提示分支
        finally:
            if moved:
                shutil.move(bdir + "_t", bdir)
            del mb.showinfo
        check("无备份时还原入口弹提示", len(shown) == 1)
        mb.showinfo = lambda *a, **k: shown.append(a)
        try:
            app._restore_dialog()      # 有备份 → 打开选择对话框
        finally:
            del mb.showinfo
        toplevels = [w for w in app.winfo_children()
                     if isinstance(w, __import__("tkinter").Toplevel)]
        for w in toplevels:
            w.destroy()
        check("有备份时打开还原对话框", len(toplevels) >= 1)

        print("== 语言切换 ==")
        old = app.var_lang.get()
        other = next(n for c, n in
                     __import__("i18n").languages() if n != old)
        app.var_lang.set(other)
        app._on_lang_change()
        app.update()
        # _rebuild 会重建控件：操作条引用随旧界面销毁，指向 None 收起
        app._set_action(None)
        check("重建后页签为新语言",
              app.nb_main.tab(0, "text") == t("gui.143"))
        back = next(n for c, n in
                    __import__("i18n").languages() if c == "zh-CN")
        app.var_lang.set(back)
        app._on_lang_change()
        app.update()
        check("切回中文", app.nb_main.tab(0, "text") == t("gui.143"))
    finally:
        app.destroy()
        shutil.rmtree(FIX, ignore_errors=True)
        # 本次测试若新建了 backups 且只含本次产物，清掉；原本就有则不动
        if not backups_before and os.path.isdir(BACKUPS):
            leftovers = []
            for dp, dn, fn in os.walk(BACKUPS):
                leftovers.extend(os.path.join(dp, f) for f in fn)
            if all("manifest.json" in f or "stuff.txt" in f or
                   f.endswith(".yml") for f in leftovers):
                shutil.rmtree(BACKUPS, ignore_errors=True)

    print("PASS=%d FAIL=%d" % (PASS, FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
