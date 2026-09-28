#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地化 key 级覆盖扫描（v2 新增，见 tests/contract.md 第一、二节）。

语义依据：群星的 localisation 目录与 common/ 不同，**逐 key 合并、后加载者
覆盖先加载者**（LIOS 按加载顺序），与文件名无关——同名 yml 整文件并不会互相
顶掉，只有 (语言,key) 都相同的条目才互斥。游戏先读原版再按播放集顺序读各
mod，因此每个 (lang,key) 的胜者 = 参与来源里 mod idx 最大者，全部是原版时
winner = -1。

解析规则（contract.md 第二节，版本号可选为 Lead 2026-09-29 批准的放宽）：
  localisation/**/*.yml（含 replace 子目录一并纳入，都是本地化）；
  UTF-8 读入并剥 BOM；逐行：`#` 注释跳过；语言段头形如 `l_simp_chinese:`；
  条目 `KEY:` 后版本号可选（`KEY:0 "…"` 与 `KEY: "…"` 都合法），key 取
  冒号前全部（可含空格，先 strip）；
  同一 (lang,key) 跨文件合并；同 mod 重复定义用 set 归并；原版参与（idx=-1）。

性能设计（原版本地化 2 万+ key，全量目标 10 秒内）：
  归并阶段只记录每个 (lang,key) 的「参与 mod idx 集合」与文件路径，
  不存文本；只有出现 >=2 个不同来源的 (lang,key) 才进 res["loc"]，
  纯 mod 覆盖原版、纯原版内部重复不进列表。
  但 loc_stats 的 defined/lost 必须按全量 key 统计（定义归属本来就要
  逐 key 记一份 owner 集合，与冲突筛选共用同一份归并数据，无额外开销）。

只用标准库。
"""

import os
import re
import time

try:
    from i18n import t
except ImportError:      # 以包形式导入或脚本被移动时兜底
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from i18n import t

# 语言段头：行首允许空白，l_ 开头的标识符 + 冒号（如 l_simp_chinese:）
LANG_RE = re.compile(r"^\s*(l_\w+):")

# 条目：key 可含空格；版本号可选（`KEY:0 "…"` 与 `KEY: "…"` 都合法，
# 实测原版 2101/2327 个文件是无版本号格式）。注意 `(?:\d+)?` 不吃后面的
# 空格：若写 `(?:\d+\s*)?`，在无版本号行上 `\d+` 失败导致整个可选组回溯，
# `"` 会被 `(.+?)` 吸进 key 里，匹配全部失败（探针实测，Lead 批准的放宽
# 版即此写法）。
ENTRY_RE = re.compile(r"^\s*(.+?):(?:\d+)?\s*\"(.*)\"\s*$")


def _read_yml(path):
    """读一个 yml 文件为文本，剥 UTF-8 BOM。读不了返回 None。"""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        return None
    if raw[:3] == b"\xef\xbb\xbf":
        raw = raw[3:]
    return raw.decode("utf-8", "replace")


def _iter_loc_ymls(root):
    """产出 root 下 localisation/**/*.yml 的绝对路径（含 replace 子目录）。"""
    loc_root = os.path.join(root, "localisation")
    if not os.path.isdir(loc_root):
        return
    for dp, _dn, fn in os.walk(loc_root):
        for f in fn:
            if f.lower().endswith(".yml"):
                yield os.path.join(dp, f)


def _parse_file(txt):
    """把一个 yml 解析成 [(lang, key)]；文本本身不需要保留。

    同文件内同 (lang,key) 重复定义由上层 set 归并，这里照单全收。
    """
    out = []
    lang = ""
    for ln in txt.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        m = LANG_RE.match(ln)
        if m:
            lang = m.group(1)
            continue
        if not lang:
            continue                     # 语言段头之前的条目不属于任何语言，跳过
        m = ENTRY_RE.match(ln)
        if m:
            out.append((lang, m.group(1).strip()))
    return out


def _vanilla_name():
    """原版的显示名（const.011 =「原版」/「vanilla」）。"""
    return t("const.011")


def _vanilla_label():
    """原版的报告标签，保持与主程序一致的「原版」字样（不编号）。"""
    return _vanilla_name()


def scan_localisation(mods, vanilla_root, progress=None):
    """扫描全部 mod 与原版的本地化，产出 contract.md 第一节的数据。

    参数：
      mods         mod_conflict_check.scan() 里 res["mods"] 的同构列表，
                   每项至少含 idx/name/root。
      vanilla_root 原版目录；目录不存在时原版不参与（等价于没有原版文件）。
      progress     可选回调，收进度文案（与主程序 scan 的 progress 同用法）。

    返回 dict：
      res["loc"]       冲突列表（>=2 个不同来源参与且至少 2 个真实 mod），
                       每项按 contract.md：key/lang/entries/winner/winner_label/
                       loser_mods/mods/has_vanilla/mod_vs_mod
      res["loc_stats"] {idx: {"defined": n, "lost": n, "beaten_by": [mod名]}}
      res["loc_files"] 扫过的 yml 数
      res["loc_keys"]  唯一 (lang,key) 数
      res["loc_elapsed"] 耗时秒数（便于对账）
    """
    t0 = time.time()

    def say(msg):
        if progress:
            progress(msg)

    res = {"loc": [], "loc_stats": {}, "loc_files": 0, "loc_keys": 0,
           "loc_elapsed": 0.0}
    stats = {m["idx"]: {"defined": 0, "lost": 0, "beaten_by": []}
             for m in mods}

    say(t("scan.024"))

    def harvest(root, idx):
        """扫一个根的全部 yml，把 (lang,key) 并进 merge 表。"""
        n = 0
        for full in _iter_loc_ymls(root):
            txt = _read_yml(full)
            if txt is None:
                continue
            n += 1
            for lk in _parse_file(txt):
                merge.setdefault(lk, {}).setdefault(idx, set()).add(full)
        return n

    # ---------- 归并：每个 (lang,key) -> {idx: {文件路径}} ----------
    # idx=-1 为原版。条目按加载顺序升序展示：原版最前，mod 按 idx 升序。
    merge = {}
    files = 0
    if vanilla_root and os.path.isdir(vanilla_root):
        files += harvest(vanilla_root, -1)
    for m in mods:
        root = m.get("root") or ""
        if root and os.path.isdir(root):
            files += harvest(root, m["idx"])
    res["loc_files"] = files

    # ---------- 统计 + 筛冲突 ----------
    say(t("scan.025"))
    loc_rows = []
    n_keys = 0
    for (lang, key), byidx in merge.items():
        n_keys += 1
        idxs = byidx.keys()
        # defined：该 mod 定义的唯一 (lang,key) 数（全量口径，不只冲突 key）
        for i in idxs:
            if i >= 0 and i in stats:
                stats[i]["defined"] += 1
        if len(byidx) < 2:
            continue                     # 只有一个来源：不存在任何覆盖
        real_mods = sorted(i for i in idxs if i >= 0)
        if len(real_mods) < 2:
            continue                     # mod 覆盖原版 / 纯原版重复：不算冲突行
        winner = max(idxs)               # 后加载者胜 = idx 最大者
        order = sorted(byidx.keys())     # -1 最前，mod idx 升序
        entries = []
        for i in order:
            base = vanilla_root if i < 0 else (mods[i]["root"] if i < len(mods) else "")
            rel = ""
            full = ""
            if base:
                full = sorted(byidx[i])[0]
                try:
                    rel = os.path.relpath(full, base).replace(os.sep, "/")
                except ValueError:
                    rel = full
            entries.append({"rel": rel, "mod": i, "full": full})
        winner_label = (_vanilla_label() if winner < 0
                        else "%d:%s" % (winner + 1, mods[winner]["name"]))
        losers = [i for i in real_mods if i != winner]
        # lost：被更高优先级（更靠后）mod 压掉的 key 数；
        # 被原版压掉不算「被真实 mod 压」，mod 覆盖原版是正常语义。
        if winner >= 0:
            win_name = mods[winner]["name"] if winner < len(mods) else "?"
            for i in losers:
                if i in stats:
                    stats[i]["lost"] += 1
                    if win_name not in stats[i]["beaten_by"]:
                        stats[i]["beaten_by"].append(win_name)
        loc_rows.append({
            "key": key, "lang": lang, "entries": entries,
            "winner": winner, "winner_label": winner_label,
            "loser_mods": losers,
            "mods": real_mods,
            "has_vanilla": -1 in idxs,
            "mod_vs_mod": True,
        })

    res["loc_keys"] = n_keys
    # 报告顺序：语言、key，稳定且方便人工对账
    loc_rows.sort(key=lambda r: (r["lang"], r["key"]))
    res["loc"] = loc_rows
    res["loc_stats"] = stats
    res["loc_elapsed"] = time.time() - t0
    return res


# ================================================================ 报告

def _label(idx, mods):
    if idx < 0:
        return _vanilla_label()
    m = mods[idx] if 0 <= idx < len(mods) else {"name": "?"}
    return "%d:%s" % (idx + 1, m.get("name", "?"))


def build_report_section(res, mods, detail_limit=60):
    """本地化节的 Markdown 正文，插在主报告第 5 节与第 6 节之间。

    措辞与现有 report.* 一致：玩家能懂的人话 + 给 AI 的结构化信息并存。
    """
    L = []
    A = L.append
    loc = res.get("loc") or []
    A(t("report.075"))
    A("")
    A(t("report.076"))
    A("")
    A(t("report.077")
      % (len(loc), res.get("loc_files", 0), res.get("loc_keys", 0)))
    A("")
    A(t("loc.002"))
    A("")
    if not loc:
        A(t("report.078"))
    else:
        A(t("report.079"))
        A("")
        A(t("loc.007"))
        A("| --- | --- | --- | --- |")
        for r in loc[:detail_limit]:
            suppressed = [_label(e["mod"], mods) for e in r["entries"]
                          if e["mod"] != r["winner"]]
            A(t("loc.008") % (r["lang"], r["key"], r["winner_label"],
                              t("sep.list").join(suppressed) or t("const.011")))
        if len(loc) > detail_limit:
            A("")
            A(t("report.013") % (len(loc) - detail_limit))
        A("")
        A(t("report.080"))
        A("")
        stats = res.get("loc_stats") or {}
        A(t("loc.010"))
        A("| --- | --- | --- | --- | --- |")
        for m in mods:
            s = stats.get(m["idx"])
            if not s:
                continue
            beaten = t("sep.list").join(s["beaten_by"])
            if not s["defined"]:
                detail = t("loc.013")
            elif not s["lost"]:
                detail = t("loc.012")
            else:
                detail = beaten
            A(t("loc.011") % (m["idx"] + 1, m["name"], s["defined"],
                              s["lost"], detail))
    A("")
    return "\n".join(L)


def overview_rows(res, mods):
    """本地化冲突的覆盖总表行（contract.md 第一节的 kind_code "loc"）。

    与 build_overview 的行结构同构，Lead 直接把返回值 extend 进总表即可：
    key 形如 "loc:<lang>:<key>"，sortable=True（本地化胜负由加载顺序决定，
    排序有效——把想生效的 mod 往后放）。
    """
    rows = []
    for r in res.get("loc") or []:
        winner = r["winner"]
        rows.append({
            "kind": t("loc.001"),
            "kind_code": "loc",
            "key": "loc:%s:%s" % (r["lang"], r["key"]),
            "subject": r["key"],
            "winner_mod": winner,
            "winner_label": r["winner_label"],
            "winner_file": (r["entries"][-1]["rel"] if r["entries"] else ""),
            "losers": [_label(i, mods) for i in r["loser_mods"]],
            "loser_mods": list(r["loser_mods"]),
            "sortable": True,
            "reason": t("loc.002"),
            "sem": t("loc.023") % (r["lang"], r["winner_label"]),
            "chain": [(_label(e["mod"], mods), e["rel"] or e["full"],
                       e["mod"] == winner) for e in r["entries"]],
            "mods": list(r["mods"]),
            "in_vanilla": r["has_vanilla"],
            "mod_vs_mod": r["mod_vs_mod"],
            "evidence": t("loc.027") % ("loc:%s:%s" % (r["lang"], r["key"])),
        })
    return rows


# ================================================================ 自测

def _selftest():
    """真实数据自测：跑当前播放集 + 原版，打印结果摘要。"""
    import argparse
    import json
    import sys
    ap = argparse.ArgumentParser(description="loc_scan 自测（--cli 模式）")
    ap.add_argument("--cli", action="store_true", help="跑真实播放集数据")
    ap.add_argument("--vanilla", default=None, help="手动指定原版目录")
    a = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    # 只用主程序里无副作用的取数函数，不触发 GUI
    import mod_conflict_check as mcc
    mcc.init_paths()
    if a.vanilla:
        mcc.VANILLA_ROOT = os.path.normpath(a.vanilla)

    # 复刻 scan() 的 mod 发现逻辑（不重扫文件，只拿 idx/name/root）
    doc = mcc.DOC_ROOT
    with open(mcc.PLAYLIST, encoding="utf-8") as f:
        entries = (json.load(f) or {}).get("enabled_mods") or []
    mods = []
    for i, entry in enumerate(entries):
        ep = os.path.join(doc, entry.replace("/", os.sep))
        if not os.path.isfile(ep):
            ep = os.path.join(doc, "mod", os.path.basename(entry))
        if not os.path.isfile(ep):
            continue
        name, mpath, _rps, _deps, _ver = mcc.parse_descriptor(ep)
        mods.append({"idx": i, "name": name or os.path.splitext(
            os.path.basename(entry))[0], "root": mcc.resolve_root(mpath)})

    res = scan_localisation(mods, mcc.VANILLA_ROOT, progress=lambda s: print(s))
    print("")
    print("loc conflicts : %d" % len(res["loc"]))
    print("loc_files     : %d" % res["loc_files"])
    print("loc_keys      : %d" % res["loc_keys"])
    print("elapsed       : %.1fs" % res["loc_elapsed"])
    for r in res["loc"][:10]:
        print("  [%s] %s <- %s  (%d entries)" % (
            r["lang"], r["key"], r["winner_label"], len(r["entries"])))
    print("...")
    stats = res["loc_stats"]
    for m in mods:
        s = stats.get(m["idx"], {})
        print("  %d %s: defined=%s lost=%s beaten_by=%s" % (
            m["idx"] + 1, m["name"], s.get("defined"), s.get("lost"),
            s.get("beaten_by")))
    # 报告节与总表行也实跑一遍，保证不缺 key、不抛异常
    section = build_report_section(res, mods)
    print("")
    print("report section: %d chars" % len(section))
    ov = overview_rows(res, mods)
    print("overview rows  : %d  (first key: %s, sortable=%s)" % (
        len(ov), ov[0]["key"] if ov else "-", ov[0]["sortable"] if ov else "-"))


if __name__ == "__main__":
    _selftest()
