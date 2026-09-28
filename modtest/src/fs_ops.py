#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件删除与备份（v2 新增，见 tests/contract.md 第三节）。

职责：把「删掉被覆盖的那份、保留想要的版本」做成可撤销的操作。

设计要点：
  备份永远落在 tool_root 下 backups/启动时间戳/mod名/原相对路径 结构，
  绝不写进任何 mod 目录 —— 删除不可逆，所以备份必须先于删除成功，
  备份失败的那一项绝不执行删除；
  备份目录里同时落 manifest.json（备份相对路径 / 目标绝对路径 / mod 名），
  restore_backups 按 manifest 原样放回，即使暂时没有还原界面，
  恢复能力也必须可用；
  删除后从被删文件所在目录向上清理空目录，直到该 mod 的根目录为止，
  mod 根本身绝不删（os.rmdir 只删得动空目录，非空即停，天然安全）。

tool_root 由调用方传入，取 src 目录的上一级（即 modtest 根）：
  os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""

import json
import os
import re
import shutil
import stat
import time

try:
    from i18n import t
except ImportError:      # 以包形式导入或脚本被移动时兜底
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from i18n import t

# 「启动时间戳」：模块被 import 即视为本次启动，同一进程里的多次删除
# 共用同一个备份目录，玩家只需要记住一个位置。测试可显式传 stamp 覆盖。
SESSION_STAMP = time.strftime("%Y%m%d_%H%M%S")

# Windows 文件名非法字符：mod 显示名直接拿来做备份子目录名，必须先洗一遍
_ILLEGAL = re.compile(r'[\\/:*?"<>|]+')


def _safe_name(name):
    """把 mod 显示名洗成可做目录名的字符串。"""
    name = _ILLEGAL.sub("_", (name or "").strip()).strip(" .")
    return name or "mod"


def _is_subpath(p, base):
    """p 是否位于 base 内部（不含 base 本身）。"""
    nc = os.path.normcase(os.path.normpath(p))
    nb = os.path.normcase(os.path.normpath(base))
    return nc.startswith(nb + os.sep)


def manifest_path(backup_dir):
    """备份目录里 manifest.json 的位置。"""
    return os.path.join(backup_dir, "manifest.json")


def backup_dir_for(tool_root, stamp=None):
    """本次（或指定时间戳）的备份根目录，供确认弹窗预告备份位置。"""
    return os.path.join(tool_root, "backups", stamp or SESSION_STAMP)


def _load_manifest(backup_dir):
    try:
        with open(manifest_path(backup_dir), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save_manifest(backup_dir, records):
    """整份重写 manifest。返回失败原因字符串，成功返回空串。"""
    try:
        os.makedirs(backup_dir, exist_ok=True)
        with open(manifest_path(backup_dir), "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return ""
    except OSError as e:
        return t("fs.014") % e


# ---------------------------------------------------------------- 删除清单

def plan_targets(chain_entries, keep_idx, mods=None):
    """把一条冲突链换算成删除清单。

    chain_entries 支持两种写法（调用方哪边方便用哪边）：
      1) mod_conflict_check 里 res["diff"][i]["entries"] 的记录（dict）：
         必须含 full；建议带 idx/name，最好再带 root（mod 根，
         是空目录清理的边界与备份相对路径的基准）。
         若同时传 mods=res["mods"]，name/root 可由 idx 反查，条目本身可不带。
      2) 详情窗格 chain 的 (label, full, is_win) 三元组，label 形如 "2:名字"，
         序号解析自 label；is_win 不参与判断，保留方一律由 keep_idx 决定。
    keep_idx 为要保留的 mod 序号（res["mods"] 的 idx，即启动器序号 - 1）。

    安全规则：原版（idx=-1）永远不是删除目标 —— 本地化等链的 entries 会含
    原版条目，这里一律跳过；原版只能作为保留方（keep_idx=-1 时删除全部
    真实 mod 条目是合法操作）。删游戏原版文件是绝对禁止的操作。

    返回 [{mod, idx, root, rel, full}]。契约要求被删方必须有 full 路径，
    缺失即抛 ValueError（调用方传错数据应尽早暴露，而不是静默删不出东西）。
    """
    out = []
    for e in chain_entries:
        if isinstance(e, dict):
            full = e.get("full") or ""
            idx = e.get("idx")
            name = e.get("name") or ""
            root = e.get("root") or ""
        else:
            label, full = e[0], e[1]
            m = re.match(r"^\s*(\d+)\s*:", str(label))
            if not m:
                if str(label).strip() == t("const.011"):
                    continue             # 原版条目（三元组形式），永不删除
                raise ValueError(t("fs.021") % label)
            idx = int(m.group(1)) - 1
            name, root = "", ""
        if mods is not None and idx is not None and 0 <= idx < len(mods):
            name = name or mods[idx].get("name") or ""
            root = root or mods[idx].get("root") or ""
        if idx is None or idx < 0:
            continue                     # 原版 / 无主条目：绝不进删除清单
        if idx == keep_idx:
            continue                     # 保留方不进删除清单，不需要 full
        if not full:
            raise ValueError(t("fs.020") % (name or idx))
        if root and os.path.normcase(os.path.normpath(full)).startswith(
                os.path.normcase(os.path.normpath(root)) + os.sep):
            rel = os.path.relpath(full, root)
        else:
            root = root if _is_subpath(full, root) else ""
            rel = os.path.relpath(full, root) if root else os.path.basename(full)
        out.append({
            "mod": name or ("mod_%d" % (idx + 1) if idx >= 0 else "unknown"),
            "idx": idx, "root": root, "rel": rel, "full": full,
        })
    return out


# ---------------------------------------------------------------- 执行删除

def execute_deletes(targets, tool_root, stamp=None, progress=None):
    """逐项执行删除清单：备份 → 删除 → 清理空目录 → 追加 manifest。

    返回逐项结果，每项至少含契约字段 {rel, ok, backup, error}，
    另附 mod / full 供界面展示。ok=False 时 error 说明原因；
    ok=True 但 manifest 写入失败时附 warning（删除本身已成功、备份也在磁盘上）。
    stamp 用于测试注入；生产环境不传，统一落在本进程的启动时间戳目录下。
    progress 可选回调，每处理一项前收到该项的 rel（与 scan 的进度回调同风格，
    GUI 批量删除时用它刷新状态栏，避免长时间无响应）。
    """
    stamp = stamp or SESSION_STAMP
    backup_root = backup_dir_for(tool_root, stamp)
    manifest = _load_manifest(backup_root)
    results = []
    for tg in targets:
        if progress:
            progress(tg.get("rel") or tg.get("full") or "")
        full = tg["full"]
        rel = tg.get("rel") or os.path.basename(full)
        item = {"rel": rel, "ok": False, "backup": "", "error": "",
                "mod": tg.get("mod", ""), "full": full}
        results.append(item)

        # 目标存在才处理：不存在说明已被删过，如实记为跳过
        if not os.path.isfile(full):
            item["error"] = t("fs.013") % full
            continue

        # 1) 先备份；备份失败则该项绝不删除
        dest = os.path.join(backup_root, _safe_name(tg.get("mod", "")),
                            rel.replace("/", os.sep))
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(full, dest)
        except OSError as e:
            item["error"] = t("fs.011") % e
            continue

        # 2) 删除。只读文件先去掉只读位再删（Windows 上创意工坊文件常见）
        try:
            os.remove(full)
        except PermissionError:
            try:
                os.chmod(full, stat.S_IWRITE)
                os.remove(full)
            except OSError as e2:
                item["error"] = t("fs.012") % e2
                continue
        except OSError as e:
            item["error"] = t("fs.012") % e
            continue

        # 3) 从文件所在目录向上清理空目录，直到该 mod 的根（不含）
        root = tg.get("root") or ""
        if root and _is_subpath(os.path.dirname(full), root):
            rmtree_empty_dirs(os.path.dirname(full), root)

        item["ok"] = True
        item["backup"] = dest
        manifest.append({
            "backup": os.path.relpath(dest, backup_root).replace(os.sep, "/"),
            "target": full,
            "mod": tg.get("mod", ""),
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    err = _save_manifest(backup_root, manifest)
    if err:
        for item in results:
            if item["ok"]:
                item["warning"] = err
    return results


# ---------------------------------------------------------------- 还原

def restore_backups(backup_dir):
    """按 manifest 把备份文件放回原位（不做界面也可用）。

    backup_dir 为某次启动的备份目录，即 tool_root 下 backups 里以时间戳命名的
    那一层。
    返回逐项结果 [{target, backup, ok, error}]；manifest 缺失/损坏时返回 []，
    调用方拿到空列表可提示 t("fs.018") % manifest_path(backup_dir)。
    目标已存在时跳过不覆盖 —— 还原不该毁掉用户后来手动放回的内容。
    """
    results = []
    records = _load_manifest(backup_dir)
    for rec in records:
        if not isinstance(rec, dict):
            continue
        target = rec.get("target") or ""
        brel = (rec.get("backup") or "").replace("/", os.sep)
        src = os.path.join(backup_dir, brel)
        item = {"target": target, "backup": src, "ok": False, "error": ""}
        results.append(item)
        if not target or not os.path.isfile(src):
            item["error"] = t("fs.016") % (src or target)
            continue
        if os.path.exists(target):
            item["error"] = t("fs.017") % target
            continue
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(src, target)
        except OSError as e:
            item["error"] = t("fs.019") % e
            continue
        item["ok"] = True
    return results


# ---------------------------------------------------------------- 工具判断

def is_workshop(full):
    """路径组件里同时含 workshop 与 281990 时为创意工坊文件（大小写不敏感）。

    UI 据此在确认弹窗里追加「可通过 Steam 验证文件完整性恢复」的提示。
    """
    parts = [p.lower() for p in
             os.path.normpath(str(full)).replace("/", os.sep).split(os.sep)]
    return "workshop" in parts and "281990" in parts


def rmtree_empty_dirs(start_dir, stop_dir):
    """从 start_dir 向上逐个删除空目录，直到 stop_dir（不含）为止。

    os.rmdir 只删得动空目录：目录里还有东西就抛 OSError，此处即停。
    因此 mod 根本身永远不会被删，也不用事先判断目录是否为空。
    start_dir 不在 stop_dir 内部时整个不做（防调用方传错边界）。
    """
    cur = os.path.normpath(os.path.abspath(start_dir))
    stop = os.path.normpath(os.path.abspath(stop_dir))
    while cur != stop and _is_subpath(cur, stop):
        try:
            os.rmdir(cur)
        except OSError:
            break
        cur = os.path.dirname(cur)
