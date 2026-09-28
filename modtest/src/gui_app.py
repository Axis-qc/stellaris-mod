#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stellaris mod 冲突检查器 —— GUI 界面（v2，自 mod_conflict_check.py 迁出）。

界面骨架与交互逻辑与 v1 完全一致；后续在骨架上按 tests/contract.md 第五节改造：
  右区改为 Notebook[文件树, 高级]，高级里嵌套收纳原全部页签，
  新增本地化页签（res["loc"]）与删除清单页签，详情窗格加保留方下拉与
  打开文件位置 / 打开 mod 根目录 / 删除并保留此版本 / 加入删除清单按钮组。

扫描核心仍在 mod_conflict_check.py，这里只做界面；
文件删除与备份走 fs_ops.py，本地化扫描走 loc_scan.py（缺失时优雅降级）。
main() 由 mod_conflict_check.py 接线，本模块不提供入口。
"""

import os
import queue
import re
import subprocess
import threading
import tkinter as tk
from tkinter import ttk

from i18n import t  # 所有面向玩家的文字都在 lang/*.json，不硬编码
import i18n

# 扫描核心与工具函数来自 mod_conflict_check（main() 由该文件接线）。
# 注意：不要 import 模块级路径变量（VANILLA_ROOT / DOC_ROOT / PLAYLIST）——
# init_paths 会重写那些全局量，import 进来的绑定会停在旧值；一律走 DETECT。
from mod_conflict_check import (scan, build_overview, build_report, overview_stats,
                                focus_stats, speak_row, sem_label, fmt_size, fmt_time,
                                md5_of, read_text, load_config, save_config, config_path,
                                init_paths, DETECT, WIKI_RAW_TYPE, WIKI_NOTES,
                                CONTESTED, _known_folder)

# 契约一、三：本地化数据已随主扫描产出（mod_conflict_check.scan() 内嵌
# loc_scan，结果在 res["loc"]），界面不再单独起扫描线程，避免重复扫一遍。
# 文件删除与备份走 fs_ops；fs_ops 缺失时删除按钮组置灰，其余功能不受影响。
try:
    import fs_ops
    from fs_ops import plan_targets, execute_deletes, is_workshop, backup_dir_for \
        as fs_backup_dir
except ImportError:
    fs_ops = None
    plan_targets = execute_deletes = is_workshop = None

    def fs_backup_dir(tool_root, stamp=None):
        """fs_ops 缺失时的兜底：只给个路径字符串，避免界面代码崩掉。"""
        import time as _time
        return os.path.join(tool_root, "backups",
                            _time.strftime("%Y%m%d_%H%M%S"))


class App(tk.Tk):
    def __init__(self, include_dlc=False):
        super().__init__()
        self.title(t("gui.001"))
        # 默认尺寸按屏幕实测再收，保证在 1366x768 这类小屏上也能完整显示。
        # 之前固定 1440 宽，在 1536 宽的屏上右侧列被切掉，「改排序有用吗」
        # 这一列整个看不到，界面等于白做。
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = max(1080, min(1340, sw - 60))
        h = max(640, min(800, sh - 80))
        self.geometry("%dx%d" % (w, h))
        self.minsize(1080, 640)
        self.result = None
        self.filter_idx = None
        self.rows = []
        self.focus_only = None
        self.q = queue.Queue()
        # v2 新增状态：删除清单、详情操作条、文件树节点元数据、页签 frame 表
        self.pending = []          # 删除清单条目 {rel, keep_label, keep_idx, targets}
        self._act = None           # 详情操作条当前指向的冲突
        self.tree_meta = {}        # 文件树文件节点 iid -> 元数据
        self._fr_map = {}          # 页签 key -> frame（删除清单按钮条挂这里）
        self.loc_ready = False     # res["loc"] 本地化数据已填充
        self.loc_items = []        # res["loc"] 的冲突行（供文件树与页签共用）
        self._build(include_dlc)
        self.after(100, self._drain)
        self.after(250, self.rescan)

    # ---------- 界面 ----------
    def _build(self, include_dlc):
        sty = ttk.Style(self)
        for th in ("vista", "winnative", "clam"):
            try:
                sty.theme_use(th)
                break
            except Exception:
                continue
        base = ("Microsoft YaHei UI", 9)
        self.option_add("*Font", base)
        sty.configure(".", font=base)
        sty.configure("Treeview", rowheight=23)
        sty.configure("T.Treeview", rowheight=23)
        sty.configure("Banner.TLabel", font=("Microsoft YaHei UI", 11, "bold"))
        # v2：文件树与本地化页签的行色。绿=生效者，灰=被覆盖者；
        # 本地化页签行本身用 tag 表示所在语言段，不用行色。

        # ---- 第一行：路径与操作
        top = ttk.Frame(self, padding=(8, 6, 8, 2))
        top.pack(fill="x")
        ttk.Label(top, text=t("gui.002")).pack(side="left")
        self.lbl_vanilla = ttk.Label(top, text=t("gui.003"), foreground="#555")
        self.lbl_vanilla.pack(side="left", padx=(4, 6))
        ttk.Button(top, text=t("gui.004"), width=6,
                   command=lambda: self._edit_path("vanilla")).pack(side="left")
        ttk.Label(top, text=t("gui.005")).pack(side="left", padx=(12, 0))
        self.lbl_doc = ttk.Label(top, text=t("gui.003"), foreground="#555")
        self.lbl_doc.pack(side="left", padx=(4, 6))
        ttk.Button(top, text=t("gui.004"), width=6,
                   command=lambda: self._edit_path("documents")).pack(side="left")

        ttk.Button(top, text=t("gui.006"), command=self.rescan).pack(side="left", padx=(14, 0))

        # 语言切换：换完立刻重建界面，避免残留旧语言文字
        ttk.Label(top, text=t("gui.142")).pack(side="left", padx=(14, 0))
        langs = i18n.languages()
        avail = i18n.available()
        self.var_lang = tk.StringVar(
            value=dict(langs).get(i18n.current(), i18n.current()))
        cb = ttk.Combobox(top, textvariable=self.var_lang, width=12, state="readonly",
                          values=[name for code, name in langs if code in avail])
        cb.pack(side="left", padx=(4, 0))
        cb.bind("<<ComboboxSelected>>", self._on_lang_change)

        self.lbl_status = ttk.Label(top, text=t("gui.007"), foreground="#0a5")
        self.lbl_status.pack(side="right")

        # ---- 第二行：结论横幅（玩家第一眼看这句）
        bar = ttk.Frame(self, padding=(10, 6))
        bar.pack(fill="x")
        self.lbl_banner = ttk.Label(
            bar, text=t("gui.008"), style="Banner.TLabel",
            foreground="#0a5", wraplength=1290, justify="left")
        self.lbl_banner.pack(side="left", anchor="w")

        # ---- 第三行：操作与筛选
        act = ttk.Frame(self, padding=(8, 0, 8, 4))
        act.pack(fill="x")
        ttk.Button(act, text=t("gui.009"), command=self.export_report).pack(side="left")
        ttk.Button(act, text=t("gui.010"), command=self.copy_report).pack(side="left", padx=(6, 0))
        self.var_dlc = tk.BooleanVar(value=include_dlc)
        ttk.Checkbutton(act, text=t("gui.011"), variable=self.var_dlc).pack(side="left", padx=10)
        self.var_only_nosort = tk.BooleanVar(value=False)
        ttk.Checkbutton(act, text=t("gui.012"),
                        variable=self.var_only_nosort,
                        command=self._refill_overview).pack(side="left", padx=(0, 10))
        self.var_mod_vs_mod = tk.BooleanVar(value=True)
        ttk.Checkbutton(act, text=t("gui.013"),
                        variable=self.var_mod_vs_mod,
                        command=self._refill_overview).pack(side="left", padx=(0, 10))
        self.var_focus = tk.BooleanVar(value=False)
        ttk.Checkbutton(act, text=t("gui.014"),
                        variable=self.var_focus,
                        command=self._refill_overview).pack(side="left")
        ttk.Button(act, text=t("gui.015"), width=9,
                   command=self.clear_filter).pack(side="left", padx=(8, 0))
        self.lbl_filter = ttk.Label(act, text="", foreground="#a50")
        self.lbl_filter.pack(side="left", padx=8)

        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        # 左：mod 列表
        left = ttk.Frame(body)
        body.add(left, weight=2)
        hdr = ttk.Frame(left)
        hdr.pack(fill="x")
        ttk.Label(hdr, text=t("gui.016")).pack(side="left")

        lcols = ("no", "name", "files", "vover", "ovr", "beaten", "state")
        self.tv_mods = ttk.Treeview(left, columns=lcols, show="headings", height=22)
        heads = (("no", t("gui.017"), 40), ("name", t("gui.018"), 176), ("files", t("gui.019"), 46),
                 ("vover", t("gui.020"), 54), ("ovr", t("gui.021"), 46), ("beaten", t("gui.022"), 56),
                 ("state", t("gui.023"), 78))
        for c, label, w in heads:
            self.tv_mods.heading(c, text=label)
            self.tv_mods.column(c, width=w, anchor="center" if c != "name" else "w",
                                stretch=(c == "name"))
        lsb = ttk.Scrollbar(left, orient="vertical", command=self.tv_mods.yview)
        self.tv_mods.configure(yscrollcommand=lsb.set)
        self.tv_mods.pack(side="left", fill="both", expand=True)
        lsb.pack(side="right", fill="y")
        self.tv_mods.tag_configure("bad", foreground="#c00")
        self.tv_mods.tag_configure("multi", foreground="#06c")
        self.tv_mods.bind("<<TreeviewSelect>>", self._on_mod_select)
        self.tv_mods.bind("<Double-1>", lambda e: self.clear_filter())

        # 右：v2 结构 —— Notebook[文件树, 高级]
        # 「高级」是嵌套 Notebook，收纳 v1 的全部页签（顺序与契约第五节一致）；
        # 文件树是给玩家的第一入口，所以放在第一位。
        right = ttk.Frame(body)
        body.add(right, weight=5)
        self.nb_main = ttk.Notebook(right)
        self.nb_main.pack(fill="both", expand=True)

        # ---- 页签一：文件树（只挂 mod 互抢路径：同路径 diff + 本地化 yml）
        fr_tree = ttk.Frame(self.nb_main)
        self.nb_main.add(fr_tree, text=t("gui.143"))
        self.tv_tree = ttk.Treeview(fr_tree, columns=("winner",), show="tree headings")
        self.tv_tree.heading("#0", text=t("gui.144"))
        self.tv_tree.heading("winner", text=t("gui.030"))
        self.tv_tree.column("#0", width=430, anchor="w", stretch=True)
        self.tv_tree.column("winner", width=230, anchor="w", stretch=True)
        tsb = ttk.Scrollbar(fr_tree, orient="vertical", command=self.tv_tree.yview)
        self.tv_tree.configure(yscrollcommand=tsb.set)
        self.tv_tree.pack(side="left", fill="both", expand=True)
        tsb.pack(side="right", fill="y")
        self.tv_tree.tag_configure("win", foreground="#070")
        # 绿=生效者；灰=被覆盖者
        self.tv_tree.tag_configure("lose", foreground="#777")
        self.tv_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # ---- 页签二：高级（嵌套 Notebook，v1 全部页签 + 本地化 + 删除清单）
        fr_adv = ttk.Frame(self.nb_main)
        self.nb_main.add(fr_adv, text=t("gui.145"))
        self.nb = ttk.Notebook(fr_adv)
        self.nb.pack(fill="both", expand=True)

        # 主视图：谁覆盖了谁（默认页签）
        # 只保留四列。玩家的行动依据是「改排序有用吗」和「依据」，
        # 列多了会被挤出可视区，反而看不到关键信息。
        self.tv_ov = self._tab(
            t("gui.024"),
            (("who", t("gui.025"), 430), ("fix", t("gui.026"), 90),
             ("obj", t("gui.027"), 170), ("sem", t("gui.028"), 120)),
            "ov")

        self.tv_diff = self._tab(t("speak.004"),
                                 (("rel", t("gui.029"), 430), ("winner", t("gui.030"), 190),
                                  ("losers", t("gui.031"), 300), ("van", t("gui.032"), 70)),
                                 "diff")
        self.tv_same = self._tab(t("gui.033"),
                                 (("rel", t("gui.029"), 430), ("mods", t("gui.034"), 380),
                                  ("van", t("gui.032"), 70)),
                                 "same")
        self.tv_van = self._tab(t("gui.035"),
                                (("rel", t("gui.029"), 500), ("mods", t("gui.034"), 380)),
                                "van")
        self.tv_keys = self._tab(t("gui.036"),
                                 (("key", t("gui.037"), 250), ("dir", t("gui.038"), 210),
                                  ("win", t("gui.030"), 210), ("sem", t("gui.039"), 110),
                                  ("upset", t("gui.040"), 100), ("n", t("gui.041"), 52)),
                                 "keys")
        self.tv_iface = self._tab(t("ov.009"),
                                  (("key", t("gui.042"), 300), ("kind", t("gui.043"), 60),
                                   ("win", t("gui.030"), 220), ("file", t("gui.044"), 300),
                                   ("upset", t("gui.040"), 100), ("n", t("gui.041"), 52)),
                                  "iface")

        # 本地化页签（v2 新增）：数据来自 res["loc"]（主扫描内嵌 loc_scan 产出）
        self.tv_loc = self._tab(t("gui.146"),
                                (("key", t("gui.161"), 230), ("lang", t("gui.148"), 110),
                                 ("winner", t("gui.030"), 200), ("losers", t("gui.150"), 240),
                                 ("file", t("gui.044"), 200)),
                                "loc")
        self.tv_prob = self._tab(t("gui.045"),
                                 (("mod", "Mod", 200), ("kind", t("gui.043"), 140),
                                  ("detail", t("gui.046"), 560)),
                                 "prob")

        # 删除清单页签（v2 新增）：待删条目 + 执行/移除/清空按钮条
        fr_pend = ttk.Frame(self.nb)
        self._fr_map["pending"] = fr_pend
        self.nb.add(fr_pend, text=t("gui.153"))
        pcols = ("rel", "keep", "del")
        self.tv_pend = ttk.Treeview(fr_pend, columns=pcols, show="headings")
        for c, label, w in (("rel", t("gui.154"), 300), ("keep", t("gui.155"), 160),
                            ("del", t("gui.156"), 340)):
            self.tv_pend.heading(c, text=label)
            self.tv_pend.column(c, width=w, anchor="w", stretch=(c == "del"))
        psb = ttk.Scrollbar(fr_pend, orient="vertical", command=self.tv_pend.yview)
        self.tv_pend.configure(yscrollcommand=psb.set)
        self.tv_pend.pack(side="left", fill="both", expand=True)
        psb.pack(side="right", fill="y")
        pbtn = ttk.Frame(fr_pend)
        pbtn.pack(side="bottom", fill="x")
        self.btn_pend_run = ttk.Button(pbtn, text=t("gui.157"), command=self._run_pending)
        self.btn_pend_run.pack(side="left", padx=(2, 4), pady=2)
        self.btn_pend_rm = ttk.Button(pbtn, text=t("gui.158"), command=self._remove_pending)
        self.btn_pend_rm.pack(side="left", padx=(0, 4), pady=2)
        self.btn_pend_clr = ttk.Button(pbtn, text=t("gui.159"), command=self._clear_pending)
        self.btn_pend_clr.pack(side="left", padx=(0, 4), pady=2)
        self.lbl_pend_empty = ttk.Label(fr_pend, text=t("gui.160"), foreground="#777",
                                        padding=(6, 3))
        self.lbl_pend_empty.pack(side="bottom", anchor="w")   # 有条目时由 _sync_pending 收起
        self._sync_pending()
        self.nb.select(0)

        det = ttk.LabelFrame(right, text=t("gui.047"),
                             padding=4)
        det.pack(fill="both", expand=False, pady=(4, 0))
        self.txt = tk.Text(det, height=8, wrap="word", font=("Consolas", 9),
                           background="#fbfbfb", relief="flat")
        dsb = ttk.Scrollbar(det, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=dsb.set, state="disabled")
        self.txt.pack(side="left", fill="both", expand=True)
        dsb.pack(side="right", fill="y")

        # v2：详情操作条（对 diff / loc 冲突生效；按钮组来自契约第五节）
        abar = ttk.Frame(det)
        abar.pack(side="bottom", fill="x", pady=(3, 0))
        self.lbl_keep = ttk.Label(abar, text=t("gui.163"))
        self.lbl_keep.pack(side="left")
        self.var_keep = tk.StringVar()
        self.cb_keep = ttk.Combobox(abar, textvariable=self.var_keep, width=24,
                                    state="readonly", values=[])
        self.cb_keep.pack(side="left", padx=(4, 8))
        self.btn_open_file = ttk.Button(abar, text=t("gui.164"),
                                        command=self._open_file_location)
        self.btn_open_file.pack(side="left", padx=(0, 4))
        self.btn_open_root = ttk.Button(abar, text=t("gui.165"),
                                        command=self._open_mod_root)
        self.btn_open_root.pack(side="left", padx=(0, 4))
        self.btn_del_keep = ttk.Button(abar, text=t("gui.166"),
                                       command=self._delete_keep_version)
        self.btn_del_keep.pack(side="left", padx=(0, 4))
        self.btn_add_pend = ttk.Button(abar, text=t("gui.167"),
                                       command=self._add_pending)
        self.btn_add_pend.pack(side="left", padx=(0, 4))
        for b in (self.btn_open_file, self.btn_open_root, self.btn_del_keep,
                  self.btn_add_pend):
            b.state(["disabled"])

        self.lbl_bottom = ttk.Label(self, text="", padding=(10, 2), foreground="#333")
        self.lbl_bottom.pack(fill="x")

    # ---------- 路径展示与手动指定 ----------
    def _show_paths(self, det):
        v = det.get("vanilla") or ""
        self.lbl_vanilla.configure(
            text=(v if v else t("gui.048")),
            foreground=("#555" if v else "#c00"))
        self.lbl_doc.configure(text=det.get("documents") or "?", foreground="#555")
        if det.get("notes"):
            self._set_detail("\n".join(det["notes"]))

    def _edit_path(self, which):
        from tkinter import filedialog, messagebox
        cur = DETECT.get(which) or ""
        title = t("gui.049") if which == "vanilla" \
            else t("gui.050")
        p = filedialog.askdirectory(title=title, initialdir=cur or os.path.expanduser("~"))
        if not p:
            return
        p = os.path.normpath(p)
        if which == "vanilla":
            if not os.path.isdir(os.path.join(p, "common")):
                if not messagebox.askyesno(
                        t("gui.051"),
                        t("gui.052")):
                    return
        else:
            if not os.path.isfile(os.path.join(p, "dlc_load.json")):
                if not messagebox.askyesno(
                        t("gui.051"),
                        t("gui.053")):
                    return
        cfg = load_config()
        cfg[which] = p
        ok = save_config(cfg)
        init_paths()
        self._show_paths(DETECT)
        if not ok:
            self._set_detail(t("gui.054")
                             % config_path())
        self.rescan()

    def _tab(self, title, cols, key):
        fr = ttk.Frame(self.nb)
        self.nb.add(fr, text=title)
        self._fr_map[key] = fr        # v2：记下页签 frame，供提示条 / 按钮条挂载
        names = tuple(c[0] for c in cols)
        tv = ttk.Treeview(fr, columns=names, show="headings")
        for c, label, w in cols:
            tv.heading(c, text=label)
            tv.column(c, width=w, anchor="w",
                      stretch=(c in ("rel", "detail", "losers", "who", "obj")))
        sb = ttk.Scrollbar(fr, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        tv.tag_configure("hard", foreground="#c00")
        tv.tag_configure("multi", foreground="#06c")
        tv.bind("<<TreeviewSelect>>", lambda e, k=key, w=tv: self._on_row_select(k, w))
        return tv

    # ---------- 扫描 ----------
    def rescan(self):
        init_paths()
        self._show_paths(DETECT)
        self.lbl_status.configure(text=t("gui.055"), foreground="#a50")
        self.tv_mods.delete(*self.tv_mods.get_children())
        for tv in (self.tv_ov, self.tv_diff, self.tv_same, self.tv_van, self.tv_keys,
                   self.tv_iface, self.tv_prob):
            tv.delete(*tv.get_children())
        # v2：本地化页签、文件树、详情操作条一并复位
        self.tv_loc.delete(*self.tv_loc.get_children())
        self.tv_tree.delete(*self.tv_tree.get_children())
        self.tree_meta = {}
        self.loc_items = []
        self.loc_ready = False
        self._set_action(None)
        self._set_detail(t("gui.008"))
        dlc = bool(self.var_dlc.get())
        # 本地化数据随主扫描一起返回（res["loc"]），不再单独起线程。
        th = threading.Thread(target=self._worker, args=(dlc,), daemon=True)
        th.start()

    def _worker(self, dlc):
        try:
            res = scan(include_dlc=dlc, progress=lambda m: self.q.put(("msg", m)))
            self.q.put(("done", res))
        except Exception as e:
            import traceback
            self.q.put(("err", traceback.format_exc()))

    def _drain(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "msg":
                    self.lbl_status.configure(text=payload, foreground="#a50")
                elif kind == "done":
                    self.result = payload
                    self._fill()
                elif kind == "err":
                    self.lbl_status.configure(text=t("gui.056"), foreground="#c00")
                    self._set_detail(payload)
        except queue.Empty:
            pass
        self.after(120, self._drain)

    # ---------- 填表 ----------
    def _fill(self):
        res = self.result
        if not res:
            return
        self.filter_idx = None
        self.lbl_filter.configure(text="")
        self.rows = build_overview(res)
        self._fill_mods()
        self._fill_overview()
        self._fill_right()
        self._fill_loc_rows()
        self._fill_tree()
        self._update_banner()
        self.lbl_status.configure(text=t("gui.057") % res["elapsed"], foreground="#0a5")
        self._restore_bottom()

    def _fill_mods(self):
        """填左侧 mod 列表。语言切换后重建界面也走这里。"""
        res = self.result
        if not res:
            return
        self.tv_mods.delete(*self.tv_mods.get_children())
        for m in res["mods"]:
            state = t("report.067")
            tag = ()
            if m["errors"]:
                state = "/".join(m["errors"])[:22]
                tag = ("bad",)
            elif m["vover"] or m["ovr"]:
                tag = ("multi",)
            self.tv_mods.insert("", "end", iid=str(m["idx"]), tags=tag, values=(
                m["idx"] + 1, m["name"], m["files"], m["vover"], m["ovr"],
                m["beaten"], state))

    def _update_banner(self):
        """顶部横幅：一句话说清这套播放集的冲突状况。"""
        st = overview_stats(self.result, self.rows)
        focus = self.filter_idx
        if focus is not None:
            fs = focus_stats(self.rows, focus)
            m = self.result["mods"][focus]
            txt = (t("gui.059")
                   % (focus + 1, m["name"], len(fs["beats"]), len(fs["beaten"]),
                      len(fs["beaten_fixable"]), len(fs["beaten_nosort"])))
            self.lbl_banner.configure(text=txt, foreground="#06c")
            return
        if not st["rows"] and not st["vs_vanilla"]:
            self.lbl_banner.configure(
                text=t("gui.060"), foreground="#0a5")
            return
        txt = (t("gui.061")
               % (st["rows"], st["nosort"], st["vs_vanilla"]))
        if st["nosort"]:
            txt += t("gui.062")
        self.lbl_banner.configure(
            text=txt, foreground=("#c60" if st["nosort"] else "#0a5"))

    def _visible_rows(self):
        rows = self.rows
        if self.var_mod_vs_mod.get():
            rows = [r for r in rows if r.get("mod_vs_mod")]
        if self.var_only_nosort.get():
            rows = [r for r in rows if not r["sortable"]]
        if self.var_focus.get() and self.filter_idx is not None:
            rows = [r for r in rows
                    if r["winner_mod"] == self.filter_idx
                    or self.filter_idx in r["loser_mods"]]
        return rows

    def _fill_overview(self):
        """总表：一行一条冲突，主列直接写成「谁覆盖了谁」。"""
        for tv in (self.tv_ov,):
            tv.delete(*tv.get_children())
        for n, r in enumerate(self._visible_rows()):
            if r["winner_mod"] == self.filter_idx and self.filter_idx is not None:
                tag = ("hard",)
            elif r.get("upset"):
                tag = ("hard",)
            elif not r["sortable"]:
                tag = ("multi",)
            else:
                tag = ()
            self.tv_ov.insert("", "end", iid="ov%d" % n, tags=tag,
                              values=(speak_row(r),
                                      t("gui.063") if not r["sortable"] else t("report.012"),
                                      r["subject"], r["sem"]))

    def _refill_overview(self):
        if self.result:
            self._fill_overview()
            self._update_banner()

    def _keep(self, entries):
        if self.filter_idx is None:
            return True
        return any(e["idx"] == self.filter_idx for e in entries)

    # ---------- v2：文件树 ----------
    def _tree_sources(self):
        """文件树的数据源：mod 互抢的同路径冲突 + 本地化 yml 互抢。

        返回 {rel: {"chain": [(label, full, is_win)], "keep_idx", "winner_label",
                    "src": "diff"|"loc", "lang", "keys"}}。
        同一路径出现在 diff 与 loc 时只挂一次，diff 优先。
        """
        # 键一律小写：diff 的 rel 本就是小写，loc 的 rel 保留原大小写，
        # 不归一会让同一路径在树上出现大小写两个节点。
        out = {}
        res = self.result
        if not res:
            return out
        for it in res.get("diff") or []:
            if not self._keep(it["entries"]):
                continue
            chain = []
            for r in it["entries"]:
                chain.append(("%d:%s" % (r["idx"] + 1, r["name"]), r["full"],
                              r["idx"] == it["winner"]))
            out[it["rel"].lower()] = {"chain": chain, "keep_idx": it["winner"],
                                      "winner_label": "%d:%s" % (it["winner"] + 1,
                                                                 it["winner_name"]),
                                      "src": "diff", "lang": ""}
        # 本地化互抢：把同 (lang,key) 冲突按「文件相对路径」聚合后挂树；
        # 原版文件不进互抢树，链上只有真实 mod。
        agg = {}
        for c in self.loc_items:
            if not self._keep(c.get("entries") or []):
                continue
            for e in c["entries"]:
                if e["mod"] < 0 or not e.get("rel"):
                    continue
                rel = e["rel"].lower()
                slot = agg.setdefault(rel, {"rel": rel, "lang": c["lang"],
                                            "mods": {}, "winner": c["winner"]})
                slot["mods"].setdefault(e["mod"], e["full"])
        for rel, slot in agg.items():
            if rel in out or len(slot["mods"]) < 2:
                continue
            chain = [("%d:%s" % (m + 1, self._mod_name(m)), full,
                      m == slot["winner"])
                     for m, full in sorted(slot["mods"].items())]
            out[rel] = {"chain": chain, "keep_idx": slot["winner"],
                        "winner_label": "%d:%s" % (slot["winner"] + 1,
                                                   self._mod_name(slot["winner"])),
                        "src": "loc", "lang": slot["lang"]}
        return out

    def _mod_name(self, idx):
        res = self.result
        if res and 0 <= idx < len(res["mods"]):
            return res["mods"][idx]["name"]
        return "?"

    def _fill_tree(self):
        self.tv_tree.delete(*self.tv_tree.get_children())
        self.tree_meta = {}
        src = self._tree_sources()
        for rel in sorted(src, key=str.lower):
            meta = src[rel]
            parts = rel.split("/")
            parent = ""
            path_so_far = []
            for i, seg in enumerate(parts):
                path_so_far.append(seg)
                cur_rel = "/".join(path_so_far)
                if i == len(parts) - 1:
                    iid = "f|" + cur_rel          # 文件节点
                    vals = (t("gui.180") % meta["winner_label"],)
                else:
                    iid = "d|" + cur_rel          # 目录节点
                    vals = ("",)
                if not self.tv_tree.exists(iid):
                    node = self.tv_tree.insert(parent, "end", iid=iid,
                                               text=seg, open=False, values=vals)
                    if i == len(parts) - 1:
                        self.tree_meta[node] = {"rel": rel, "meta": meta}
                else:
                    node = iid
                    if i == len(parts) - 1:
                        # 同一路径被多条 loc 冲突共享时，补挂 chain
                        self.tv_tree.set(node, "winner", vals[0])
                parent = node
            # 文件节点下按加载顺序上→下插 mod 子节点（上=先加载=低优先级）
            for label_, _full, is_win in meta["chain"]:
                cid = "m|" + rel.lower() + "|" + label_
                if not self.tv_tree.exists(cid):
                    self.tv_tree.insert("f|" + rel, "end", iid=cid,
                                        text=label_,
                                        tags=("win" if is_win else "lose",))
        if not src:
            self.tv_tree.insert("", "end", iid="|empty",
                                text=t("gui.181"))

    def _tree_current(self):
        sel = self.tv_tree.selection()
        if not sel:
            return None
        return self.tree_meta.get(sel[0])

    def _on_tree_select(self, _e=None):
        cur = self._tree_current()
        if not cur:
            return
        meta = cur["meta"]
        rel = cur["rel"]
        res = self.result
        L = [t("gui.099") % rel]
        if meta["src"] == "diff":
            L.append(t("gui.100"))
        else:
            L.append(t("gui.182"))
            if meta.get("lang"):
                L.append(t("gui.183") % meta["lang"])
            n_keys = self._loc_keys_for_path(rel)
            if n_keys:
                L.append(t("gui.185") % n_keys)
        it = next((x for x in (res.get("diff") or []) if x["rel"] == rel), None) \
            if meta["src"] == "diff" else None
        if it is not None and it.get("in_vanilla"):
            L.append(t("gui.103") % os.path.join(res["vanilla_root"], it["rel"]))
        L.append("")
        for label_, full, is_win in meta["chain"]:
            mark = t("gui.098") if is_win else t("gui.104")
            L.append("[%s]%s" % (label_, mark))
            L.append("    %s" % full)
            size, mtime, md5 = self._file_info(full)
            L.append(t("gui.105")
                     % (fmt_size(size) if size >= 0 else "-", fmt_time(mtime),
                        (md5 or "-")[:12], "-"))
        self._set_detail("\n".join(L))
        self._set_action({"src": meta["src"], "rel": rel,
                          "lang": meta.get("lang", ""),
                          "chain": meta["chain"], "keep_idx": meta["keep_idx"],
                          "winner_label": meta["winner_label"]})

    def _file_info(self, full):
        try:
            st = os.stat(full)
            return st.st_size, st.st_mtime, md5_of(full)
        except OSError:
            return -1, 0, ""

    def _loc_keys_for_path(self, rel):
        """该 yml 相对路径上互抢的本地化 key 数（对详情窗格用）。"""
        n = 0
        rl = rel.lower()
        for c in self.loc_items:
            rels = {e["rel"].lower() for e in c["entries"] if e["mod"] >= 0}
            if rl in rels:
                n += 1
        return n

    # ---------- v2：本地化页签 ----------
    def _fill_loc_rows(self):
        """把 res["loc"] 填进本地化页签。主扫描完成（_fill）时调用。"""
        self.tv_loc.delete(*self.tv_loc.get_children())
        res = self.result
        self.loc_items = list((res or {}).get("loc") or [])
        self.loc_ready = bool(self.loc_items)
        for n, c in enumerate(self.loc_items):
            win = next((e for e in c["entries"] if e["mod"] == c["winner"]), None)
            losers = []
            seen = set()
            for e in c["entries"]:
                if e["mod"] == c["winner"] or e["mod"] in seen or e["mod"] < 0:
                    continue
                seen.add(e["mod"])
                losers.append("%d:%s" % (e["mod"] + 1, self._mod_name(e["mod"])))
            self.tv_loc.insert("", "end", iid="loc%d" % n, values=(
                c["key"], c["lang"],
                c["winner_label"],
                t("sep.list").join(losers),
                (win or {}).get("rel", "")))

    def _fill_right(self):
        res = self.result
        for tv in (self.tv_diff, self.tv_same, self.tv_van, self.tv_keys,
                   self.tv_iface, self.tv_prob):
            tv.delete(*tv.get_children())

        for it in res["diff"]:
            if not self._keep(it["entries"]):
                continue
            order = it["entries"]
            losers = ", ".join("%d:%s" % (r["idx"] + 1, r["name"]) for r in order[:-1])
            tag = ("hard",) if it["in_vanilla"] else ("multi",)
            self.tv_diff.insert("", "end", iid=it["rel"], tags=tag, values=(
                it["rel"], "%d:%s" % (it["winner"] + 1, it["winner_name"]),
                losers, t("gui.064") if it["in_vanilla"] else ""))

        for it in res["same"]:
            if not self._keep(it["entries"]):
                continue
            mods = ", ".join("%d:%s" % (r["idx"] + 1, r["name"]) for r in it["entries"])
            self.tv_same.insert("", "end", iid=it["rel"], values=(
                it["rel"], mods, t("gui.064") if it["in_vanilla"] else ""))

        for it in res["vanilla"]:
            if not self._keep(it["entries"]):
                continue
            mods = ", ".join("%d:%s" % (r["idx"] + 1, r["name"]) for r in it["entries"])
            tag = ("hard",) if it.get("multi") else ()
            self.tv_van.insert("", "end", iid=it["rel"], tags=tag, values=(it["rel"], mods))

        for n, it in enumerate(res["keys"]):
            if self.filter_idx is not None and self.filter_idx not in it["mods"]:
                continue
            tag = ()
            if it["upset"]:
                tag = ("hard",)
            elif it["sem"] in ("MERGE", "DUPL", "DUPL_LIOS", "DUPL_NO",
                               "NO_DUPL_FIOS", "DUPL_FIOS", "NO"):
                tag = ("multi",)
            self.tv_keys.insert("", "end", iid="key%d" % n, tags=tag, values=(
                it["key"], it["dir"], it["win_label"] or t("gui.065"),
                sem_label(it["sem"]),
                t("gui.064") if it["upset"] else "", len(it["entries"])))

        for n, it in enumerate(res["iface"]):
            if self.filter_idx is not None and self.filter_idx not in it["mods"]:
                continue
            tag = ("hard",) if it["upset"] else ()
            self.tv_iface.insert("", "end", iid="if%d" % n, tags=tag, values=(
                it["key"],
                "gui" if it["kind"] == "gui" else "gfx",
                it["win_label"], it["win_rel"],
                t("gui.064") if it["upset"] else "", len(it["entries"])))

        for n, p in enumerate(res["problems"]):
            tags = ("hard",) if p["kind"] == "replace_path" else ()
            self.tv_prob.insert("", "end", iid="pb%d" % n, tags=tags,
                                values=(p["mod"], p["kind"], p["detail"]))

    # ---------- 语言 ----------
    def _on_lang_change(self, _e=None):
        """切换语言：把配置写下来，然后整体重建界面。

        重建而不是逐个改控件文字，是因为界面上的文字散落在几十个控件里，
        逐个更新容易漏；重建一次代价不到一秒，且保证没有残留的旧语言。
        """
        name = self.var_lang.get()
        code = next((c for c, n in i18n.languages() if n == name), i18n.DEFAULT_LANG)
        if code == i18n.current():
            return
        i18n.set_language(code)
        cfg = load_config()
        cfg["lang"] = code
        save_config(cfg)
        self._rebuild()

    def _rebuild(self):
        """按当前语言重建整个界面，扫描结果原样保留。"""
        res = self.result
        focus = self.filter_idx
        pending = self.pending
        for child in self.winfo_children():
            child.destroy()
        self.title(t("gui.001"))          # 标题不归 _build 管，要单独重设
        self._fr_map = {}
        self.tree_meta = {}
        self._act = None
        self._build(self.var_dlc.get() if hasattr(self, "var_dlc") else False)
        self.result = res
        self.filter_idx = focus
        self.pending = pending
        self._sync_pending()
        if res:
            self.rows = build_overview(res)
            self._fill_mods()
            self._fill_overview()
            self._fill_right()
            self._fill_loc_rows()
            self._fill_tree()
            self._update_banner()
            self._restore_bottom()
        else:
            self._set_detail(t("gui.007"))

    def _restore_bottom(self):
        if not self.result:
            return
        st = overview_stats(self.result, self.rows)
        self.lbl_bottom.configure(text=(
            t("gui.058")
            % (st["mods"], st["files"], st["vanilla_files"], st["rows"],
               st["sortable"], st["nosort"], st["vs_vanilla"],
               st["redundant"], st["problems"])))

    # ---------- v2：详情操作条 ----------
    def _set_action(self, act):
        """操作条指向一条冲突（diff 或 loc 来源）。act=None 收起按钮组。

        act 结构：{"src": "diff"|"loc", "rel", "lang", "chain",
                   "keep_idx", "entries", "winner_label"}
        chain 为 [(label, full, is_win)]，label 形如 "2:mod名"，
        plan_targets 两种形式都认，这里直接传 entries 之外还要给 full，
        所以统一转成 [(label, full, is_win)] 交给 plan_targets。
        """
        self._act = act
        if not act:
            self.var_keep.set("")
            self.cb_keep.configure(values=[])
            for b in (self.btn_open_file, self.btn_open_root, self.btn_del_keep,
                      self.btn_add_pend):
                b.state(["disabled"])
            return
        chain = act.get("chain") or []
        vals = [c[0] for c in chain]
        self.cb_keep.configure(values=vals)
        self.var_keep.set(act.get("winner_label") or (vals[-1] if vals else ""))
        has_fs = execute_deletes is not None
        for b in (self.btn_open_file, self.btn_open_root):
            b.state(["!disabled"])
        for b in (self.btn_del_keep, self.btn_add_pend):
            b.state(["!disabled"] if (has_fs and vals) else ["disabled"])

    def _resolve_keep_idx(self):
        """当前保留方：从下拉框现值解析，单一真相，不存第二份状态。

        标签形如 "2:mod名"，序号即 res["mods"] 的 idx+1。
        原版标签（无序号）映射为 -1：保留原版 = 删除链上全部真实 mod
        的条目，fs_ops 对 -1 的处理正是这个语义（原版条目永不删除）。
        解析不出（下拉为空）时退回 act 记录的 keep_idx。
        """
        act = self._act or {}
        m = re.match(r"^\s*(\d+)\s*:", self.var_keep.get())
        if m:
            return int(m.group(1)) - 1
        return act.get("keep_idx")

    def _act_mod_root(self, idx):
        res = self.result
        if res and 0 <= idx < len(res["mods"]):
            return res["mods"][idx].get("root") or ""
        return ""

    def _open_full(self, p):
        """资源管理器里定位一个文件或目录；失败静默（写详情提示会误导）。"""
        if not p or not os.path.exists(p):
            return
        try:
            subprocess.Popen(["explorer", "/select,", os.path.normpath(p)])
        except OSError:
            pass

    def _open_dir(self, p):
        if not p or not os.path.isdir(p):
            return
        try:
            subprocess.Popen(["explorer", os.path.normpath(p)])
        except OSError:
            pass

    def _open_file_location(self):
        act = self._act
        if not act:
            return
        keep = act.get("keep_idx")
        for label_, full, _w in act.get("chain") or []:
            m = re.match(r"^\s*(\d+)\s*:", label_)
            if m and int(m.group(1)) - 1 == keep:
                self._open_full(full)
                return
        # 兜底：打开第一个候选的所在目录
        for _label_, full, _w in act.get("chain") or []:
            d = os.path.dirname(full)
            if d:
                self._open_dir(d)
                return

    def _open_mod_root(self):
        act = self._act
        if not act:
            return
        root = self._act_mod_root(act.get("keep_idx"))
        if not root:
            # 保留方未解析出根目录时，退而打开链上第一个 mod 的根
            for label_, _full, _w in act.get("chain") or []:
                m = re.match(r"^\s*(\d+)\s*:", label_)
                if m:
                    root = self._act_mod_root(int(m.group(1)) - 1)
                    if root:
                        break
        self._open_dir(root)

    def _tool_root(self):
        """备份根的基准：modtest 根 = fs_ops.py 所在 src 目录的上一级。"""
        if fs_ops is not None:
            return os.path.dirname(os.path.dirname(os.path.abspath(fs_ops.__file__)))
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _confirm_delete(self, targets, keep_label):
        """删除确认弹窗：逐条列出删与留；工坊文件追加 Steam 恢复提示。

        返回 True 表示玩家点了确认。
        """
        from tkinter import messagebox
        L = [t("gui.168") % (len(targets), keep_label), ""]
        for tg in targets:
            L.append(t("gui.169") % (tg.get("mod") or tg.get("idx", "?"), tg["rel"]))
        L.append("")
        L.append(t("fs.004") % fs_backup_dir(self._tool_root()))
        if any(is_workshop(tg["full"]) for tg in targets):
            L.append("")
            L.append(t("gui.171"))
        return messagebox.askyesno(t("gui.172"), "\n".join(L))

    def _delete_result_text(self, results, backup_root):
        """把 execute_deletes 的结果写成人话，回填详情窗格。"""
        ok = [r for r in results if r.get("ok")]
        bad = [r for r in results if not r.get("ok")]
        L = [t("gui.173") % (len(ok), len(bad))]
        if ok:
            bdir = backup_root
            L.append(t("gui.174") % bdir)
        for r in bad:
            L.append(t("gui.175") % (r.get("rel") or r.get("full"), r.get("error") or "?"))
        return "\n".join(L)

    def _delete_keep_version(self):
        """「删除并保留此版本」：立即执行删除，成功后自动重扫。"""
        act = self._act
        if not act or execute_deletes is None or plan_targets is None:
            return
        try:
            targets = plan_targets(act["chain"], self._resolve_keep_idx(),
                                   mods=self.result["mods"])
        except ValueError as e:
            self._set_detail(t("gui.176") % e)
            return
        if not targets:
            self._set_detail(t("gui.177"))
            return
        if not self._confirm_delete(targets, act.get("winner_label") or ""):
            self._set_detail(t("gui.178"))
            return
        results = execute_deletes(targets, self._tool_root())
        self._set_detail(self._delete_result_text(
            results, fs_backup_dir(self._tool_root())))
        self.rescan()

    def _add_pending(self):
        """「加入删除清单」：只登记不执行，等玩家在清单页签统一执行。"""
        act = self._act
        if not act or plan_targets is None:
            return
        try:
            targets = plan_targets(act["chain"], self._resolve_keep_idx(),
                                   mods=self.result["mods"])
        except ValueError as e:
            self._set_detail(t("gui.176") % e)
            return
        if not targets:
            self._set_detail(t("gui.177"))
            return
        rel = act.get("rel") or (targets[0]["rel"] if targets else "?")
        self.pending.append({"rel": rel, "keep_idx": act["keep_idx"],
                             "keep_label": act.get("winner_label") or "",
                             "targets": targets})
        self._sync_pending()

    def _sync_pending(self):
        """刷新删除清单页签与空提示、按钮状态。"""
        if not hasattr(self, "tv_pend"):
            return
        self.tv_pend.delete(*self.tv_pend.get_children())
        for n, e in enumerate(self.pending):
            dels = "; ".join("%s:%s" % (tg.get("mod") or "?", tg["rel"])
                             for tg in e["targets"])
            self.tv_pend.insert("", "end", iid="pd%d" % n, values=(
                e["rel"], e["keep_label"], dels))
        has = bool(self.pending)
        if has:
            self.lbl_pend_empty.pack_forget()
        else:
            self.lbl_pend_empty.pack(side="bottom", anchor="w")
        for b in (self.btn_pend_run, self.btn_pend_rm, self.btn_pend_clr):
            b.state(["!disabled"] if has else ["disabled"])

    def _remove_pending(self):
        sel = self.tv_pend.selection()
        if not sel:
            return
        keep_rows = []
        for iid in sel:
            try:
                keep_rows.append(int(iid[2:]))
            except (ValueError, TypeError):
                pass
        self.pending = [e for n, e in enumerate(self.pending) if n not in set(keep_rows)]
        self._sync_pending()

    def _clear_pending(self):
        if not self.pending:
            return
        self.pending = []
        self._sync_pending()

    def _run_pending(self):
        """执行整个删除清单：一次确认、一次执行，完成后清空并重扫。"""
        if not self.pending or execute_deletes is None:
            return
        all_targets = [tg for e in self.pending for tg in e["targets"]]
        keep_desc = t("sep.list").join(e["keep_label"] for e in self.pending)
        if not self._confirm_delete(all_targets, keep_desc):
            self._set_detail(t("gui.178"))
            return
        results = execute_deletes(all_targets, self._tool_root())
        self._set_detail(self._delete_result_text(
            results, fs_backup_dir(self._tool_root())))
        self.pending = []
        self._sync_pending()
        self.rescan()

    # ---------- 交互 ----------
    def clear_filter(self):
        self.filter_idx = None
        self.lbl_filter.configure(text="")
        self.tv_mods.selection_remove(*self.tv_mods.selection())
        if self.result:
            self._fill_overview()
            self._fill_right()
            self._update_banner()
            self._set_detail(t("gui.066"))

    def _on_mod_select(self, _e):
        sel = self.tv_mods.selection()
        if not sel:
            return
        idx = int(sel[0])
        if self.filter_idx == idx:
            return
        self.filter_idx = idx
        m = self.result["mods"][idx]
        self.lbl_filter.configure(text=t("gui.067") % (idx + 1, m["name"]))
        self._fill_overview()
        self._fill_right()
        self._update_banner()
        self._set_detail(self._mod_detail(m))

    def _mod_detail(self, m):
        L = []
        L.append("%d  %s" % (m["idx"] + 1, m["name"]))
        L.append(t("gui.068") % m["desc"])
        L.append(t("gui.069") % (m["root"] or t("gui.070")))
        if m["ver"]:
            L.append(t("gui.071") % m["ver"])
        if m["deps"]:
            L.append("dependencies: %s" % ", ".join(m["deps"]))
        L.append(t("gui.072")
                 % (m["files"], m["vover"], m["ovr"], m["beaten"], m["redund"]))
        nk = [k for k in self.result["keys"] if m["idx"] in k["mods"]]
        if nk:
            nupset = sum(1 for k in nk if any(m["idx"] in e["mods"] for e in k["upset"]))
            L.append(t("gui.073")
                     % (len(nk), nupset))
        if m["errors"]:
            L.append(t("gui.074") % t("sep.list").join(m["errors"]))
        if m["rp"]:
            L.append(t("gui.075")
                     % ", ".join(m["rp"]))
            for rp in self.result["replace_paths"]:
                if rp["idx"] != m["idx"]:
                    continue
                L.append(t("gui.076")
                         % (rp["victim_files"], rp["vanilla_files"]))
                if rp["victims"]:
                    for i, n, c in rp["victims"]:
                        L.append(t("cli.015") % (i + 1, n, c))
                else:
                    L.append(t("cli.016"))
        return "\n".join(L)

    def _overview_detail(self, r):
        """一条冲突的来龙去脉：结论、依据、候选链、证据、怎么办。"""
        L = []
        L.append(t("gui.077") % speak_row(r))
        L.append("")
        L.append(t("gui.078") % (r.get("subject") or r.get("key"), r["kind"]))
        L.append(t("gui.079") % r["winner_label"])
        L.append(t("gui.080") % r["winner_file"])
        if r["losers"]:
            L.append(t("gui.081") % t("sep.list").join(r["losers"]))
        L.append(t("gui.082") % (r["sem"], r["reason"]))
        L.append("")
        L.append(t("gui.083"))
        for label_, path, is_win in r["chain"]:
            L.append("  %-22s %s%s" % (label_, path, t("gui.084") if is_win else t("gui.085")))
        L.append("")
        L.append(t("gui.086") % r["evidence"])
        if r.get("upset"):
            L.append("")
            L.append(t("gui.087"))
            L.append(t("gui.088"))
            for who in r["upset"]:
                L.append("  %s" % who)
        L.append("")
        if r["sortable"]:
            L.append(t("gui.089"))
        else:
            L.append(t("gui.090"))
            L.append(t("gui.091"))
            L.append(t("gui.092"))
        if r["in_vanilla"]:
            L.append("")
            L.append(t("gui.093"))
            L.append(t("gui.094"))
        return "\n".join(L)

    def _on_row_select(self, key, tv):
        sel = tv.selection()
        if not sel:
            return
        iid = sel[0]
        res = self.result
        if not res:
            return
        if key == "ov":
            try:
                idx_o = int(iid[2:])
            except (ValueError, TypeError):
                return
            rows = self._visible_rows()
            if not (0 <= idx_o < len(rows)):
                return
            self._set_detail(self._overview_detail(rows[idx_o]))
            return
        if key in ("diff", "same", "van", "iface"):
            if key == "iface":
                try:
                    idx_i = int(iid[2:])
                except (ValueError, TypeError):
                    return
                if not (0 <= idx_i < len(res["iface"])):
                    return
                it = res["iface"][idx_i]
                L = ["%s: %s  [%s]" % (t("gui.095") if it["kind"] == "gui" else t("gui.096"),
                                       it["key"], it["kind"])]
                L.append(t("gui.097"))
                L.append("")
                for e in it["entries"]:
                    mark = t("gui.098") if e["rel"] == it["win_rel"] else ""
                    L.append("%-62s -> %s%s" % (e["rel"], e["winner_label"], mark))
                self._set_detail("\n".join(L))
                return
            pool = {"diff": res["diff"], "same": res["same"], "van": res["vanilla"]}[key]
            it = next((x for x in pool if x["rel"] == iid), None)
            if not it:
                return
            L = [t("gui.099") % it["rel"]]
            if key == "diff":
                L.append(t("gui.100"))
            elif key == "same":
                L.append(t("gui.101"))
            else:
                L.append(t("gui.102"))
            if it.get("in_vanilla"):
                L.append(t("gui.103") % os.path.join(res["vanilla_root"], it["rel"]))
            L.append("")
            for r in it["entries"]:
                mark = ""
                if key == "diff":
                    mark = t("gui.098") if r["idx"] == it["winner"] else t("gui.104")
                try:
                    van_st = os.stat(os.path.join(res["vanilla_root"], it["rel"]))
                    vtxt = "%s  %s" % (fmt_size(van_st.st_size), fmt_time(van_st.st_mtime))
                except OSError:
                    vtxt = "-"
                L.append("[%d] %s%s" % (r["idx"] + 1, r["name"], mark))
                L.append("    %s" % r["full"])
                L.append(t("gui.105")
                         % (fmt_size(r["size"]), fmt_time(r["mtime"]),
                            (r["md5"] or "-")[:12], vtxt))
            self._set_detail("\n".join(L))
        elif key == "loc":
            try:
                idx_l = int(iid[3:])
            except (ValueError, TypeError):
                return
            if not (0 <= idx_l < len(self.loc_items)):
                return
            c = self.loc_items[idx_l]
            L = [t("gui.146") + ": " + c["key"]]
            L.append(t("gui.148") + ": " + c["lang"])
            L.append(t("gui.030") + ": " + c["winner_label"])
            L.append(t("loc.002"))
            L.append("")
            L.append(t("gui.083"))
            for e in c["entries"]:
                if e["mod"] < 0:
                    label_ = t("const.011")
                else:
                    label_ = "%d:%s" % (e["mod"] + 1, self._mod_name(e["mod"]))
                mark = t("gui.098") if e["mod"] == c["winner"] else t("gui.104")
                L.append("  %-22s %s%s" % (label_, e.get("rel") or e.get("full", ""),
                                           mark))
            self._set_detail("\n".join(L))
            self._set_action({"src": "loc", "rel": (win_rel := next(
                                  (e.get("rel") or e.get("full", "")
                                   for e in c["entries"] if e["mod"] == c["winner"]),
                                  "")),
                              "lang": c["lang"],
                              "chain": [(("%d:%s" % (e["mod"] + 1,
                                                     self._mod_name(e["mod"])))
                                         if e["mod"] >= 0 else t("const.011"),
                                         e.get("full", ""), e["mod"] == c["winner"])
                                        for e in c["entries"]],
                              "keep_idx": c["winner"],
                              "winner_label": c["winner_label"]})
            return
        elif key == "keys":
            try:
                idx_k = int(iid[3:])
            except (ValueError, TypeError):
                return
            if not (0 <= idx_k < len(res["keys"])):
                return
            it = res["keys"][idx_k]
            L = [t("gui.106") % it["key"]]
            L.append(t("gui.107") % it["dir"])
            raw_type = WIKI_RAW_TYPE.get(it["dir"], "")
            L.append(t("gui.108")
                     % (sem_label(it["sem"]),
                        (t("gui.109") % raw_type) if raw_type and raw_type != it["sem"] else ""))
            if it["sem"] == "FIOS":
                L.append(t("gui.110"))
            elif it["sem"] == "LIOS":
                L.append(t("gui.111"))
            elif it["sem"] == "MERGE":
                L.append(t("gui.112"))
            elif it["sem"] == "UNKNOWN":
                L.append(t("gui.113"))
            else:
                L.append(t("gui.114") % raw_type)
            # 本地实测与 wiki 结论不一致时并列提示，不静默取舍
            k_lower = it["dir"]
            for ck, (cwk, cnote) in CONTESTED.items():
                if k_lower == "common/" + ck or k_lower.endswith("/" + ck):
                    L.append("")
                    L.append(t("gui.115"))
                    L.append("      %s" % cnote)
            note = WIKI_NOTES.get(it["dir"])
            if note:
                err, nt = note
                if nt:
                    L.append("")
                    L.append(t("gui.116") % nt)
                if err:
                    L.append(t("gui.117") % err)
            L.append("")
            L.append(t("gui.118"))
            for e in it["entries"]:
                mark = t("gui.098") if e["rel"] == it["win_rel"] and it["win_rel"] else ""
                src = e["winner_label"]
                extra = t("gui.119") % len(e["paths"]) if e["multi_path"] else ""
                L.append("  %-58s -> %s%s%s" % (e["name"], src, extra, mark))
            if it["upset"]:
                L.append("")
                L.append(t("gui.120"))
                L.append(t("gui.121"))
                for e in it["upset"]:
                    L.append("    %s  (%s)" % (e["rel"], e["winner_label"]))
            if it["has_vanilla"]:
                L.append("")
                L.append(t("gui.122"))
            self._set_detail("\n".join(L))
        else:
            L = [tv.set(iid, "detail")]
            mod_name = tv.set(iid, "mod")
            for rp in res["replace_paths"]:
                if rp["mod"] != mod_name:
                    continue
                L.append("")
                L.append(t("gui.123") % rp["path"])
                L.append(t("gui.124")
                         % (rp["victim_files"], rp["vanilla_files"]))
                if rp["victims"]:
                    for i, n, c in rp["victims"]:
                        L.append(t("gui.125") % (i + 1, n, c))
                else:
                    L.append(t("gui.126"))
            self._set_detail("\n".join(L))

    def _set_detail(self, s):
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", s or "")
        self.txt.configure(state="disabled")

    # ---------- 导出给 AI 的报告 ----------
    def _report_text(self):
        if not self.result:
            return None
        return build_report(self.result)

    def export_report(self):
        rep = self._report_text()
        if rep is None:
            self._set_detail(t("gui.127"))
            return
        from tkinter import filedialog
        desk = _known_folder("{B4BFCC3A-DB2C-424C-B029-BFE99A87C641}")
        if not desk or not os.path.isdir(desk):
            desk = os.path.expanduser("~")
        path = filedialog.asksaveasfilename(
            title=t("gui.128"),
            initialfile=t("gui.129"),
            initialdir=desk,
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), (t("gui.130"), "*.txt"), (t("gui.131"), "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(rep)
            self._set_detail(t("gui.132")
                             % (path, len(rep)))
        except OSError as e:
            self._set_detail(t("gui.133") % e)

    def copy_report(self):
        rep = self._report_text()
        if rep is None:
            self._set_detail(t("gui.127"))
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(rep)
            self.update()
            self._set_detail(t("gui.134") % len(rep))
        except tk.TclError as e:
            self._set_detail(t("gui.135") % e)
