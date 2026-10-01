#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stellaris 播放集 mod 冲突初筛。

读 dlc_load.json 的 enabled_mods 拿到当前播放集与加载顺序（顺序即优先级，
后加载者整文件覆盖先加载者），逐个解析 .mod 描述符得到真实根目录，然后比对：

  L1  mod 间同相对路径、内容不同   —— 后者整文件盖掉前者，真覆盖
  L1  mod 间同相对路径、字节相同   —— 纯冗余，无实质影响
  L2  mod 路径在原版也存在         —— mod 在改原版内容，属覆盖信息
  L3  不同文件名注册同名 key       —— 按目录语义决定谁胜，与 mod 加载顺序无关
  L4  描述符问题与 replace_path    —— replace_path 会整目录卸载前面所有来源
  L5  本地化 (语言,key) 级覆盖     —— localisation 逐 key 合并、后加载者胜，
      与文件名无关，细节见 loc_scan.py

L1/L2 看的是「同路径整文件替换」，L3 看的是「不同文件名之间的同名定义覆盖」。
这是两套彼此独立的优先级：实测存在靠前加载的 mod 仅因文件名排序靠后而压掉
靠后 mod 的情况（见 L3 页签的「压过加载顺序」一列）。

只用标准库。GUI 基于 tkinter，另带 --cli 供命令行核对。
"""

import argparse
import ctypes
import hashlib
import json
import os
import queue
import re
import threading
import time

from i18n import t  # 所有面向玩家的文字都在 lang/*.json，不硬编码
import i18n

APP_NAME = "StellarisModConflictChecker"
GAME_DIR_NAME = "Stellaris"

# 这三个路径在启动时探测，玩家也可手动指定并记进 config.json。
# 写死路径是分发的头号杀手：游戏装在哪个盘、文档是否被 OneDrive 重定向，人人不同。
DOC_ROOT = ""
VANILLA_ROOT = ""
PLAYLIST = ""
DETECT = {"vanilla": "", "documents": "", "vanilla_found": False,
          "notes": [], "source_vanilla": "", "source_docs": ""}


# ---------------------------------------------------------------- 路径探测

def _guid_struct(s):
    """把 '{FDD39AD0-...}' 解析成 ctypes GUID。"""
    p = s.strip("{}").split("-")

    class G(ctypes.Structure):
        _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                    ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]

    g = G()
    g.Data1 = int(p[0], 16)
    g.Data2 = int(p[1], 16)
    g.Data3 = int(p[2], 16)
    raw = bytes.fromhex(p[3]) + bytes.fromhex(p[4])
    g.Data4 = (ctypes.c_ubyte * 8)(*list(raw))
    return g


def _known_folder(fid):
    """走 Windows 已知文件夹接口取目录，正确处理 OneDrive 重定向。"""
    try:
        g = _guid_struct(fid)
        ptr = ctypes.c_wchar_p()
        hr = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(g), 0, None, ctypes.byref(ptr))
        if hr == 0 and ptr.value:
            path = ptr.value
            ctypes.windll.ole32.CoTaskMemFree(ptr)
            return path
    except Exception:
        pass
    return ""


def _reg_documents():
    try:
        import winreg
        k = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
        v, _ = winreg.QueryValueEx(k, "Personal")
        return os.path.expandvars(v)
    except Exception:
        return ""


def _steam_roots_from_registry():
    cands = []
    try:
        import winreg
    except Exception:
        return cands
    probes = ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
              (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
              (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"))
    for root, sub in probes:
        for val in ("SteamPath", "InstallPath"):
            try:
                k = winreg.OpenKey(root, sub)
                v, _ = winreg.QueryValueEx(k, val)
                if v:
                    cands.append(os.path.normpath(v))
            except Exception:
                pass
    return cands


def _library_roots(steam_roots):
    """从 libraryfolders.vdf 解析出全部 Steam 库目录（游戏可能不在主库里）。"""
    roots = list(steam_roots)
    for sr in steam_roots:
        for cand in (os.path.join(sr, "steamapps", "libraryfolders.vdf"),
                     os.path.join(sr, "config", "libraryfolders.vdf")):
            if not os.path.isfile(cand):
                continue
            try:
                with open(cand, encoding="utf-8", errors="replace") as f:
                    txt = f.read()
            except OSError:
                continue
            for m in re.finditer(r'"path"\s+"([^"]+)"', txt):
                roots.append(os.path.normpath(m.group(1).replace("\\\\", "\\")))
    out, seen = [], set()
    for r in roots:
        k = os.path.normcase(r)
        if r and k not in seen:
            seen.add(k)
            out.append(r)
    return out


def find_vanilla():
    """返回 (游戏原版目录, 来源说明, Steam 根)。找不到返回空串。"""
    sroots = _steam_roots_from_registry()
    for r in _library_roots(sroots):
        p = os.path.join(r, "steamapps", "common", GAME_DIR_NAME)
        if os.path.isdir(p):
            return p, t("path.001"), (sroots[0] if sroots else r)
    # 兜底：各盘符的常见位置，最多 26*4 次目录检查，很快
    for drive in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        d = drive + ":\\"
        if not os.path.isdir(d):
            continue
        for rel in (("SteamLibrary", "steamapps", "common", GAME_DIR_NAME),
                    ("Steam", "steamapps", "common", GAME_DIR_NAME),
                    ("Program Files (x86)", "Steam", "steamapps", "common",
                     GAME_DIR_NAME),
                    ("steamapps", "common", GAME_DIR_NAME)):
            p = os.path.join(d, *rel)
            if os.path.isdir(p):
                return p, t("path.002"), ""
    return "", "", (sroots[0] if sroots else "")


def find_doc_root():
    """返回 (Paradox/Stellaris 文档目录, 来源说明)。"""
    cands = []
    kf = _known_folder("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}")
    if kf:
        cands.append((kf, t("path.003")))
    rd = _reg_documents()
    if rd:
        cands.append((rd, t("path.004")))
    od = os.environ.get("OneDrive")
    if od:
        cands.append((os.path.join(od, "Documents"), "OneDrive"))
    cands.append((os.path.join(os.path.expanduser("~"), "Documents"), t("path.005")))
    for base, src in cands:
        p = os.path.join(base, "Paradox Interactive", GAME_DIR_NAME)
        if os.path.isdir(p):
            return p, src
    base, src = cands[0]
    return os.path.join(base, "Paradox Interactive", GAME_DIR_NAME), src + t("path.006")


def config_path():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME, "config.json")


def load_config():
    try:
        with open(config_path(), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_config(cfg):
    p = config_path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def init_paths():
    """探测路径，手动指定的值优先。结果写进 DETECT 供界面与报告展示。"""
    global DOC_ROOT, VANILLA_ROOT, PLAYLIST
    cfg = load_config()
    notes = []

    # 语言：命令行显式指定 > 配置里记的 > 系统语言。
    # 显式指定过的（i18n.is_locked）不再被这里覆盖，否则 --lang 会被静默忽略。
    if not i18n.is_locked():
        lang = cfg.get("lang") or ""
        i18n.set_language(lang if lang in i18n.SUPPORTED else i18n.system_lang())

    v = cfg.get("vanilla") or ""
    if v and os.path.isdir(v):
        VANILLA_ROOT, vsrc, vok = v, t("path.007"), True
    else:
        VANILLA_ROOT, vsrc, _ = find_vanilla()
        vok = bool(VANILLA_ROOT)
        if v:
            notes.append(t("path.008") % v
                         if vok else
                         t("path.009") % v)
    if not vok:
        notes.append(t("path.010"))

    d = cfg.get("documents") or ""
    if d and os.path.isdir(d):
        DOC_ROOT, dsrc = d, t("path.007")
    else:
        DOC_ROOT, dsrc = find_doc_root()
        if d:
            notes.append(t("path.011") % d)

    PLAYLIST = os.path.join(DOC_ROOT, "dlc_load.json")
    if not os.path.isfile(PLAYLIST):
        notes.append(t("path.012"))

    DETECT.update({"vanilla": VANILLA_ROOT, "documents": DOC_ROOT,
                   "vanilla_found": vok, "notes": notes,
                   "source_vanilla": vsrc, "source_docs": dsrc})
    return DETECT

# 参与原版比对的顶层目录（dlc/ 单独处理，见 scan）
VANILLA_DIRS = ("common", "events", "interface", "localisation", "gfx", "sound",
                "map", "fonts", "flags", "prescripted_countries", "music")

# 必然重名、与冲突无关的文件
NOISE = {"descriptor.mod", "thumbnail.png", ".ds_store", "metadata.json",
         ".gitattributes", ".gitignore", "readme.md"}

# 缩略图变体（#thumbnail.png、1111thumbnail.png 之类），位于 mod 根目录，
# 不参与游戏加载，出现同名不代表冲突
THUMB_RE = re.compile(r"^[^/]*thumbnail\.(png|jpg|jpeg)$")


def is_noise(relpath):
    base = relpath.rsplit("/", 1)[-1].lower()
    if base in NOISE:
        return True
    # 只在 mod 根目录的 thumbnail 变体算噪声，避免误伤深层同名资源
    if "/" not in relpath and THUMB_RE.match(base):
        return True
    return False

NAME_RE = re.compile(r'(?<![A-Za-z0-9_])name\s*=\s*"([^"]*)"')
PATH_RE = re.compile(r'(?<![A-Za-z0-9_])path\s*=\s*"([^"]*)"')
RP_RE = re.compile(r'(?<![A-Za-z0-9_])replace_path\s*=\s*"([^"]*)"')
DEPS_RE = re.compile(r'dependencies\s*=\s*\{([^}]*)\}', re.S)
VER_RE = re.compile(r'(?<![A-Za-z0-9_])supported_version\s*=\s*"([^"]*)"')

# ============================ L3：同 key 覆盖 ============================
#
# 目录覆盖语义取自 Stellaris 官方 wiki 的 Modding 页「Common folder」覆盖规则总表
# （160 个目录），见同目录 wiki_overwrite.py。wiki 未标注（标 ?）的目录归 UNKNOWN，
# 本工具对 UNKNOWN 只列候选、不判胜负。
#
# 语义取值：
#   FIOS        文件名靠前者胜（First In Only Served）
#   LIOS        文件名靠后者胜（Last In Only Served）
#   DUPL        多份定义并存，往往需同路径整份替换原版文件才生效
#   NO          不能单独覆盖
#   DUPL_LIOS / DUPL_NO / NO_DUPL_FIOS / DUPL_FIOS   混合型
#   MERGE       同名条目内容合并，不互相覆盖
#   UNKNOWN     wiki 未标注，语义未验证

try:
    from wiki_overwrite import (WIKI_COMMON_OVERWRITE, WIKI_RAW_TYPE,
                                WIKI_NOTES, CONTESTED)
except ImportError:      # 以包形式导入或脚本被移动时兜底
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    from wiki_overwrite import (WIKI_COMMON_OVERWRITE, WIKI_RAW_TYPE,
                                WIKI_NOTES, CONTESTED)

try:
    import loc_scan      # L5 本地化 key 级覆盖扫描
except ImportError:      # 同上兜底
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import loc_scan


# 结构关键字：出现在 `X = {` 左侧但不是具名定义
STRUCT_KEYWORDS = {
    "and", "or", "not", "nor", "nand", "xor", "if", "else", "elseif", "while",
    "ai_weight", "weight", "potential", "possible", "trigger", "limit", "modifier",
    "description", "desc", "name", "icon", "picture", "sound", "prerequisites",
    "prereq", "on_enabled", "on_disabled", "effect", "effects", "hidden_effect",
    "show_if", "abort_trigger", "abort_effect", "immediate", "after", "option",
    "custom_tooltip", "random_list", "random", "switch", "case", "resources",
    "resource", "cost", "allow", "is_visible", "visible", "owned", "count",
    "value", "values", "days", "months", "years", "mult", "factor", "triggered_desc",
    "text", "key", "type", "category", "start", "end", "upgrade_path", "component",
    "multiplier", "inline_script", "class", "slot", "sections", "stages",
}

# 容器包裹类目录：真 key 在内层字段上，而不是顶层块名
# 容器包裹类目录 -> 承载真 key 的字段名（按优先级列出候选）。
# None 表示「顶层块名本身就是 key」。
#
# 不能按单一包裹块名匹配：实测同目录存在多个包裹名，例如 component_templates 有
# utility_component_template / weapon_component_template / strike_craft_component_template
# 三种，scripted_loc 有 defined_text / define_text / defined_txt 等变体。
# 因此这里只声明「取哪个内层字段」，任何顶层块都视为容器。
CONTAINER_KEY_FIELD = {
    "common/scripted_loc": ["name"],
    "common/ship_behaviors": ["name"],
    "common/special_projects": ["key", "name"],
    "common/section_templates": ["key"],
    "common/ambient_objects": ["name"],
    "common/component_sets": ["key"],
    "common/global_ship_designs": ["name"],
    "common/message_types": ["key", "name"],
    "common/component_templates": ["key"],
    # 该目录按 location 判定「每个位置取第一个有效 part」，故身份是 location
    "common/start_screen_messages": ["location"],
    # 该目录顶层块名即 key（如 black_hole_nomad_init），走默认提取
    "common/solar_system_initializers": None,
}

_MISSING = object()


BLOCK_RE = re.compile(r"([A-Za-z_@][A-Za-z0-9_.\-@]*)\s*=\s*$")
VAR_RE = re.compile(r"^\s*(@[A-Za-z0-9_.\-]+)\s*=")
STRFIELD_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"([^"]+)"')


def strip_comments(txt):
    """去掉 # 注释，保留字符串内的 #。"""
    out, i, n, in_q = [], 0, len(txt), False
    while i < n:
        c = txt[i]
        if c == '"':
            in_q = not in_q
            out.append(c)
        elif c == "#" and not in_q:
            while i < n and txt[i] != "\n":
                i += 1
            out.append("\n")
        else:
            out.append(c)
        i += 1
    return "".join(out)


def line_iter(text):
    """逐行产出 (原始行, 进入该行前的大括号深度)。"""
    depth = 0
    for ln in text.splitlines():
        yield ln, depth
        s = ln
        depth += s.count("{") - s.count("}")
        if depth < 0:
            depth = 0


def extract_keys(path, reldir):
    """从 common/ 下的 txt 提取「具名定义 key」。

    reldir 为相对 mod 根的小写目录（如 common/scripted_loc），决定取值方式：
      - 容器类目录取容器块内的 name/key 字符串字段
      - defines 取二级 GROUP = { KEY = value }
      - scripted_variables 取 @变量名
      - 其余取顶层 `key = {`
    """
    try:
        raw = open(path, "rb").read()
    except OSError:
        return set()
    if raw[:3] == b"\xef\xbb\xbf":
        raw = raw[3:]
    txt = strip_comments(raw.decode("utf-8", "replace"))

    found = set()

    # --- scripted_variables: @name = value ---
    if reldir.startswith("common/scripted_variables"):
        for ln, _ in line_iter(txt):
            m = VAR_RE.match(ln)
            if m:
                found.add(m.group(1))
        return found

    # --- defines: GROUP = { KEY = value } ---
    if reldir.startswith("common/defines"):
        group = None
        for ln, depth in line_iter(txt):
            s = ln.strip()
            if not s:
                continue
            if depth == 0:
                m = BLOCK_RE.match(s.rstrip("{").strip())
                if m and "{" in s:
                    group = m.group(1)
            elif depth == 1 and group:
                m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", ln)
                if m:
                    found.add("%s.%s" % (group, m.group(1)))
        return found

    # --- 容器类目录：任意顶层块内取 name / key / location 字段 ---
    if reldir in CONTAINER_KEY_FIELD and CONTAINER_KEY_FIELD[reldir]:
        fields = CONTAINER_KEY_FIELD[reldir]
        in_block = False
        for ln, depth in line_iter(txt):
            if depth == 0:
                in_block = ln.strip().endswith("{")
                continue
            if not in_block:
                continue
            for fld in fields:
                m = re.match(r'^\s*%s\s*=\s*"?([^"\s]+)"?' % fld, ln)
                if m:
                    found.add(m.group(1))
                    in_block = False
                    break
        return found

    # --- 其余：顶层 key = { ---
    for ln, depth in line_iter(txt):
        if depth != 0:
            continue
        s = ln.strip()
        if not s.endswith("{"):
            continue
        m = BLOCK_RE.match(s[:-1].strip())
        if not m:
            continue
        k = m.group(1)
        if k.lower() in STRUCT_KEYWORDS:
            continue
        if k.startswith("@"):
            continue
        found.add(k)
    return found


# ==================== L4：interface 的 .gui / .gfx 覆盖 ====================
#
# interface/ 目录整体是 LIOS（wiki Interface modding：「This folder is using the
# LIOS file loading method」），覆盖身份是**具名元素与 sprite 名**：
#   .gui  —— guiTypes = { ... } 里的顶层元素，按 name 覆盖整个元素块
#   .gfx  —— spriteTypes = { ... } 里的 spriteType 等，按 name 覆盖整个 sprite
#
# 口径与 Irony Mod Manager 的 Conflict Solver 一致（其 Generic/GraphicsParser.cs 用
#   GuiTypesId = "guiTypes={"、ExpectedGraphicsIds = [guiTypes, spriteTypes,
#   objectTypes, bitmapfonts]、ExpectedGraphicFolders = [gui, gfx, interface,
#   fonts, dlc, sound, music, ...]、ValidExtensions = [.gui, .gfx, .asset]
# 并以 name 作为 id）。因此本工具与之结果可互相印证。
#
# 只有**顶层**元素才跨文件覆盖：嵌套元素按名替换未实测（详见 README 局限）。

GUI_ELEMENT_TYPES = {
    "containerWindowType", "buttonType", "effectButtonType", "iconType",
    "instantTextBoxType", "scrollbarType", "extendedScrollbarType", "spinnerType",
    "guiButtonType", "positionType", "listboxType", "smoothListboxType",
    "overlappingElementsBoxType", "gridBoxType", "checkboxType", "editBoxType",
    "dropDownBoxType", "expandButton", "expandedWindow", "windowType",
}
SPRITE_TYPES = ("spriteType", "corneredTileSpriteType", "progressbarType",
                "portraitType", "objectType")
SPRITE_BLOCK_RE = re.compile(
    r"^\s*(%s)\s*=\s*\{" % "|".join(SPRITE_TYPES))


def gui_top_elements(txt):
    """取 .gui 里 guiTypes 的直接子元素 [(类型, name)]。

    跨文件覆盖只发生在顶层元素上，所以只取深度 1 的具名块。
    """
    out = []
    depth = 0
    pending = None
    for ln in strip_comments(txt).splitlines():
        s = ln.strip()
        if not s:
            continue
        if depth == 1:
            m = re.match(r"^(\w+)\s*=\s*\{", s)
            if m and m.group(1) in GUI_ELEMENT_TYPES:
                pending = m.group(1)
        if depth >= 1 and pending is not None:
            nm = re.match(r'^name\s*=\s*"([^"]+)"', s)
            if nm:
                out.append((pending, nm.group(1)))
                pending = None
        depth += s.count("{") - s.count("}")
        if depth <= 1:
            pending = None
        if depth < 0:
            depth = 0
    return out


def gfx_sprites(txt):
    """取 .gfx 里的 sprite [(类型, name)]。"""
    out = []
    cur = None
    for ln in strip_comments(txt).splitlines():
        m = SPRITE_BLOCK_RE.match(ln)
        if m:
            cur = m.group(1)
            continue
        if cur:
            nm = re.match(r'^\s*name\s*=\s*"([^"]+)"', ln)
            if nm:
                out.append((cur, nm.group(1)))
                cur = None
            elif ln.strip().startswith("}"):
                cur = None
    return out


def dir_semantics(reldir):
    """返回该目录的覆盖语义（见模块顶部语义表）。

    wiki 表的键是相对 common/ 的路径（如 buildings、country_limits/ship_of_size_limits），
    而 reldir 形如 common/buildings，故先剥掉 common/ 前缀。
    查表用「最具体匹配」：先试完整相对路径，再逐级上溯。
    """
    rel = reldir
    if rel.startswith("common/"):
        rel = rel[len("common/"):]
    elif rel == "common":
        rel = ""
    d = rel
    while d:
        if d in WIKI_COMMON_OVERWRITE:
            return WIKI_COMMON_OVERWRITE[d]
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return "UNKNOWN"


def sem_label(code):
    """覆盖语义的显示名。

    必须做成函数而不是模块级字典：字典在 import 时求值，语言切换后
    里面的文字会停在启动语言，界面上就会中英混杂。
    """
    key = {"FIOS": "const.001", "LIOS": "const.002", "MERGE": "const.003",
           "DUPL": "const.004", "DUPL_LIOS": "const.005", "DUPL_NO": "const.006",
           "NO_DUPL_FIOS": "const.007", "DUPL_FIOS": "const.008",
           "NO": "const.009", "UNKNOWN": "const.010"}.get(code)
    return t(key) if key else code


def fmt_size(n):
    if n < 1024:
        return "%d B" % n
    if n < 1024 * 1024:
        return "%.1f KB" % (n / 1024.0)
    return "%.1f MB" % (n / 1048576.0)


def fmt_time(t):
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(t))
    except Exception:
        return "-"


def md5_of(path):
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                h.update(b)
    except OSError:
        return ""
    return h.hexdigest()


def read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:3] == b"\xef\xbb\xbf":
        raw = raw[3:]
    return raw.decode("utf-8", "replace")


def parse_descriptor(path):
    """返回 (name, mod_path, replace_paths, deps, supported)。"""
    txt = read_text(path)
    m = NAME_RE.search(txt)
    name = m.group(1) if m else ""
    m = PATH_RE.search(txt)
    mod_path = m.group(1) if m else ""
    rps = RP_RE.findall(txt)
    m = DEPS_RE.search(txt)
    deps = re.findall(r'"([^"]*)"', m.group(1)) if m else []
    m = VER_RE.search(txt)
    ver = m.group(1) if m else ""
    return name, mod_path, rps, deps, ver


def resolve_root(mod_path):
    p = mod_path.replace("\\", "/").strip()
    if not p:
        return ""
    if os.path.isabs(p) or (len(p) > 1 and p[1] == ":"):
        return os.path.normpath(p)
    return os.path.normpath(os.path.join(DOC_ROOT, p))


def scan(include_dlc=False, progress=None):
    t0 = time.time()

    def say(msg):
        if progress:
            progress(msg)

    res = {
        "playlist": PLAYLIST,
        "mods": [],
        "diff": [],
        "same": [],
        "vanilla": [],
        "keys": [],
        "l3_files": 0,
        "iface": [],
        "l4_files": 0,
        "problems": [],
        "replace_paths": [],
        "vanilla_count": 0,
        "elapsed": 0.0,
        "vanilla_root": VANILLA_ROOT,
    }

    if not os.path.isfile(PLAYLIST):
        res["problems"].append({"mod": "-", "kind": t("scan.001"), "detail": PLAYLIST})
        res["elapsed"] = time.time() - t0
        return res

    try:
        data = json.loads(read_text(PLAYLIST))
    except Exception as e:
        res["problems"].append({"mod": "-", "kind": t("scan.002"), "detail": str(e)})
        res["elapsed"] = time.time() - t0
        return res

    entries = data.get("enabled_mods") or []

    # ---------- 原版索引 ----------
    say(t("scan.003"))
    van = set()
    if os.path.isdir(VANILLA_ROOT):
        for top in VANILLA_DIRS:
            d = os.path.join(VANILLA_ROOT, top)
            if not os.path.isdir(d):
                continue
            for dp, dn, fn in os.walk(d):
                dn[:] = [x for x in dn if not x.startswith(".")]
                for f in fn:
                    rel = os.path.relpath(os.path.join(dp, f), VANILLA_ROOT)
                    van.add(rel.replace(os.sep, "/").lower())
        if include_dlc:
            dd = os.path.join(VANILLA_ROOT, "dlc")
            if os.path.isdir(dd):
                for sub in sorted(os.listdir(dd)):
                    sd = os.path.join(dd, sub)
                    if not os.path.isdir(sd):
                        continue
                    for dp, dn, fn in os.walk(sd):
                        dn[:] = [x for x in dn if not x.startswith(".")]
                        for f in fn:
                            rel = os.path.relpath(os.path.join(dp, f), sd)
                            van.add(rel.replace(os.sep, "/").lower())
    else:
        res["problems"].append({"mod": "-", "kind": t("scan.004"),
                                "detail": t("scan.005") % VANILLA_ROOT})
    res["vanilla_count"] = len(van)

    # ---------- 逐个 mod 建路径索引 ----------
    index = {}  # rel -> [记录]
    seen_names = {}

    for i, entry in enumerate(entries):
        ep = os.path.join(DOC_ROOT, entry.replace("/", os.sep).replace("\\", os.sep))
        if not os.path.isfile(ep):
            alt = os.path.join(DOC_ROOT, "mod", os.path.basename(entry))
            if os.path.isfile(alt):
                ep = alt

        rec = {
            "idx": i, "entry": entry,
            "stem": os.path.splitext(os.path.basename(entry))[0],
            "desc": ep, "name": "", "root": "", "files": 0,
            "vover": 0, "ovr": 0, "beaten": 0, "redund": 0,
            "rp": [], "deps": [], "ver": "", "errors": [],
        }

        if not os.path.isfile(ep):
            rec["errors"].append(t("scan.006"))
            rec["name"] = rec["stem"]
            res["problems"].append({"mod": rec["stem"], "kind": t("scan.006"), "detail": ep})
            res["mods"].append(rec)
            continue

        try:
            name, mpath, rps, deps, ver = parse_descriptor(ep)
        except Exception as e:
            name, mpath, rps, deps, ver = "", "", [], [], ""
            rec["errors"].append(t("scan.007"))
            res["problems"].append({"mod": rec["stem"], "kind": t("scan.007"), "detail": str(e)})

        rec["name"] = name or rec["stem"]
        rec["deps"] = deps
        rec["ver"] = ver
        rec["rp"] = rps
        if not name:
            rec["errors"].append(t("scan.008"))
            res["problems"].append({"mod": rec["stem"], "kind": t("scan.008"), "detail": ep})

        root = resolve_root(mpath)
        rec["root"] = root
        if not mpath:
            rec["errors"].append(t("scan.009"))
            res["problems"].append({"mod": rec["name"], "kind": t("scan.009"), "detail": ep})
        elif not os.path.isdir(root):
            rec["errors"].append(t("scan.010"))
            res["problems"].append({"mod": rec["name"], "kind": t("scan.010"), "detail": root})
        else:
            say(t("scan.011") % rec["name"])
            for dp, dn, fn in os.walk(root):
                dn[:] = [x for x in dn if not x.startswith(".")]
                for f in fn:
                    full = os.path.join(dp, f)
                    rel = os.path.relpath(full, root).replace(os.sep, "/").lower()
                    if is_noise(rel):
                        continue
                    try:
                        st = os.stat(full)
                        size, mtime = st.st_size, st.st_mtime
                    except OSError:
                        size, mtime = -1, 0
                    index.setdefault(rel, []).append({
                        "idx": i, "name": rec["name"], "full": full,
                        "size": size, "mtime": mtime, "md5": None,
                    })
                    rec["files"] += 1

        for rp in rps:
            res["replace_paths"].append({"mod": rec["name"], "idx": i, "path": rp})
            res["problems"].append({"mod": rec["name"], "kind": "replace_path",
                                    "detail": t("scan.012") % rp})

        key = rec["name"].strip().lower()
        if key:
            if key in seen_names:
                res["problems"].append({
                    "mod": rec["name"], "kind": t("scan.013"),
                    "detail": t("scan.014")
                              % (seen_names[key] + 1)})
                rec["errors"].append(t("scan.015"))
            else:
                seen_names[key] = i

        res["mods"].append(rec)

    # ---------- L3：不同文件名注册同名 key ----------
    #
    # 三点必须做对，否则会漏报或错报（均由 error.log 对账发现）：
    # 1) 原版也是参与者。mod 与不同文件名的原版定义撞 key 时，谁胜取决于文件排序，
    #    不是 mod 一定赢 —— 这正是「加了 mod 却没生效」的常见原因。
    # 2) 同路径的多个 mod 归并成一条候选，其生效者由 L1 的加载顺序决定，
    #    再拿它去参与文件名字符序的比较。
    # 3) 只有「不同文件名」之间才谈得上字符序；同文件名必然是同路径，归 L1。
    say(t("scan.016"))
    key_owners = {}     # (reldir, key) -> {basename: {relpath: set(mod idx or -1)}}
    l3_files = 0

    def harvest(root, mod_idx, tag):
        cdir = os.path.join(root, "common")
        if not os.path.isdir(cdir):
            return 0
        n = 0
        for dp, dn, fn in os.walk(cdir):
            dn[:] = [x for x in dn if not x.startswith(".")]
            for f in fn:
                if not f.lower().endswith(".txt"):
                    continue
                full = os.path.join(dp, f)
                relpath = os.path.relpath(full, root).replace(os.sep, "/").lower()
                reldir = os.path.dirname(relpath)
                n += 1
                for k in extract_keys(full, reldir):
                    slot = key_owners.setdefault((reldir, k), {})
                    slot.setdefault(os.path.basename(relpath), {}).setdefault(
                        relpath, set()).add(mod_idx)
        return n

    for i, rec in enumerate(res["mods"]):
        root = rec.get("root") or ""
        if root and os.path.isdir(root):
            l3_files += harvest(root, i, "mod")
    # 原版以 -1 参与（加载顺序最靠前，优先级最低）
    if os.path.isdir(VANILLA_ROOT):
        harvest(VANILLA_ROOT, -1, "vanilla")

    say(t("scan.017"))

    def display(idx):
        if idx < 0:
            return t("const.011")
        return "%d:%s" % (idx + 1, res["mods"][idx]["name"])

    for (reldir, k), byname in key_owners.items():
        # 同一目录内，不同文件名之间才比较
        if len(byname) < 2:
            continue

        mods_involved = set()
        for rels in byname.values():
            for s in rels.values():
                mods_involved |= s
        real_mods = {m for m in mods_involved if m >= 0}
        # 至少要有一个 mod 参与，纯原版内部重复不报
        if not real_mods:
            continue
        # 必须来自 >=2 个不同来源（mod 或原版）；同一 mod 内部两文件重名不是 mod 冲突
        if len(mods_involved) < 2:
            continue

        sem = dir_semantics(reldir)

        # MERGE（如 common/on_actions）：不属互抢，直接跳过，不进 res["keys"]。
        # 依据 Stellaris 官方 wiki Modding 页 Common folder 总表 on_actions 行：
        # Overwrite Type = "NO/MERGE"，Error Log = "[none]"，Notes =
        # "Cannot modify existing entries; new entries will be merged with the
        # existing entry with the same NAME={}."；本地 CWTools 规则 on_actions.cwt
        # 的 type[on_action] 块内也只有 events / random_events，未定义同名条目互相
        # 覆盖；原版 common/on_actions/99_README_ON_ACTIONS.txt 亦说明 on_action
        # 触发时会遍历 events 列表并全部触发。
        # 即同目录下不同文件只是把各自条目追加合并到同名 on_action 上，不存在谁覆盖
        # 谁、没有胜者，把它记进 keys 会被统计与文件树当成交互抢占，故在此拦掉。
        # res["diff"] 是纯路径比对的整文件替换，不涉语义，照旧报。
        if sem == "MERGE":
            continue

        names = sorted(byname.keys())        # 文件名 ASCII 升序

        # 每个文件名对应的「生效 mod」：同路径多个 mod 时取加载顺序最靠后者
        entries = []
        for nm in names:
            rels = byname[nm]
            mods_here = set()
            for s in rels.values():
                mods_here |= s
            winner_here = max(mods_here)     # -1 表示只有原版
            entries.append({
                "name": nm,
                "rel": sorted(rels.keys())[0],
                "paths": sorted(rels.keys()),
                "mods": sorted(m for m in mods_here if m >= 0),
                "winner": winner_here,
                "winner_label": display(winner_here),
                "multi_path": len(rels) > 1,
            })

        # 只有纯 FIOS / LIOS 能给确定的生效者。混合型（DUPL_LIOS 等）无法逐 key
        # 判断哪些条目是多份并存、哪些是 LIOS，故不判胜负；DUPL / NO / MERGE 同理。
        if sem == "FIOS":
            win = entries[0]
        elif sem == "LIOS":
            win = entries[-1]
        else:
            win = None

        # 谁被文件名顺序压掉了：生效者不是它，且它的加载顺序更靠后
        upset = []
        if win is not None:
            # 找出真正会生效的那一份：其余同名 key 定义都被丢弃
            for e in entries:
                if e is win:
                    continue
                if e["winner"] > win["winner"]:
                    upset.append(e)

        res["keys"].append({
            "key": k, "dir": reldir, "sem": sem,
            "win_rel": win["rel"] if win else "",
            "win_label": win["winner_label"] if win else "",
            "win_mod": win["winner"] if win else -1,
            "entries": entries, "upset": upset,
            "mods": sorted(real_mods),
            "has_vanilla": -1 in mods_involved,
        })

    res["l3_files"] = l3_files
    res["keys"].sort(key=lambda x: (x["sem"], x["dir"], x["key"]))

    # ---------- L4：interface 的 .gui 元素 / .gfx sprite 覆盖 ----------
    #
    # 同为 LIOS：文件名靠后者胜；但覆盖单位是「具名元素/sprite」而非整个文件，
    # 所以不同文件名之间也会互相覆盖，与 L3 同理。原版也参与。
    say(t("scan.018"))
    iface = {}          # (kind, name) -> {relpath: set(mod idx or -1)}
    l4_files = 0

    def harvest_iface(root, mod_idx):
        nonlocal l4_files
        idir = os.path.join(root, "interface")
        if not os.path.isdir(idir):
            return
        for dp, dn, fn in os.walk(idir):
            dn[:] = [x for x in dn if not x.startswith(".")]
            for f in fn:
                low = f.lower()
                if not (low.endswith(".gui") or low.endswith(".gfx")):
                    continue
                full = os.path.join(dp, f)
                rel = os.path.relpath(full, root).replace(os.sep, "/").lower()
                try:
                    txt = read_text(full)
                except OSError:
                    continue
                l4_files += 1
                if low.endswith(".gui"):
                    for typ, nm in gui_top_elements(txt):
                        iface.setdefault(("gui", nm), {}).setdefault(rel, set()).add(mod_idx)
                else:
                    for typ, nm in gfx_sprites(txt):
                        iface.setdefault(("gfx", nm), {}).setdefault(rel, set()).add(mod_idx)

    for i, rec in enumerate(res["mods"]):
        root = rec.get("root") or ""
        if root and os.path.isdir(root):
            harvest_iface(root, i)
    if os.path.isdir(VANILLA_ROOT):
        harvest_iface(VANILLA_ROOT, -1)

    say(t("scan.019"))
    for (kind, nm), files in iface.items():
        sources = set()
        for s in files.values():
            sources |= s
        # 需要 >=2 个不同来源才构成冲突（同一 mod 内同名不算）
        if len(sources) < 2:
            continue
        # LIOS：文件名靠后者胜
        ordered = sorted(files.keys(), key=lambda p: os.path.basename(p))

        entries = []
        for rel in ordered:
            mods_here = sorted(m for m in files[rel] if m >= 0)
            winner_here = max(files[rel])
            entries.append({
                "rel": rel, "mods": mods_here,
                "winner": winner_here,
                "winner_label": (t("const.011") if winner_here < 0
                                 else "%d:%s" % (winner_here + 1,
                                                 res["mods"][winner_here]["name"])),
            })
        win = entries[-1]
        upset = [e for e in entries if e is not win and e["winner"] > win["winner"]]

        res["iface"].append({
            "key": nm, "kind": kind,
            "win_rel": win["rel"], "win_label": win["winner_label"],
            "win_mod": win["winner"],
            "entries": entries, "upset": upset,
            "mods": sorted(m for m in sources if m >= 0),
            "has_vanilla": -1 in sources,
        })

    res["l4_files"] = l4_files
    res["iface"].sort(key=lambda x: (x["kind"], x["key"]))

    # ---------- 比对 ----------
    say(t("scan.020"))
    for rel, lst in index.items():
        in_van = rel in van
        if len(lst) >= 2:
            order = sorted(lst, key=lambda r: r["idx"])
            sizes = {r["size"] for r in order}
            identical = False
            if len(sizes) == 1:
                for r in order:
                    r["md5"] = md5_of(r["full"])
                identical = len({r["md5"] for r in order}) == 1
            else:
                # 尺寸已不同，仍算 md5 作为「确实不同」的证据
                for r in order:
                    r["md5"] = md5_of(r["full"])
            item = {
                "rel": rel, "entries": order, "in_vanilla": in_van,
                "winner": order[-1]["idx"], "winner_name": order[-1]["name"],
            }
            if identical:
                res["same"].append(item)
                for r in order:
                    res["mods"][r["idx"]]["redund"] += 1
            else:
                res["diff"].append(item)
                w = res["mods"][order[-1]["idx"]]
                w["ovr"] += len(order) - 1
                for r in order[:-1]:
                    res["mods"][r["idx"]]["beaten"] += 1
        if in_van:
            for r in lst:
                res["mods"][r["idx"]]["vover"] += 1
            res["vanilla"].append({
                "rel": rel, "entries": sorted(lst, key=lambda r: r["idx"]),
                "in_vanilla": True,
                "multi": len(lst) >= 2,
            })

    # ---------- replace_path 影响面 ----------
    # 声明 replace_path 的 mod 会整目录卸载此前所有来源在该目录下的内容，
    # 所以统计被它作废的前序 mod 文件数，以及原版同目录的文件数。
    for rp in res["replace_paths"]:
        pref = rp["path"].replace("\\", "/").strip("/").lower()
        owner = rp["idx"]
        hit = {}
        for rel, lst in index.items():
            if pref and not (rel == pref or rel.startswith(pref + "/")):
                continue
            for r in lst:
                if r["idx"] < owner:
                    hit[r["idx"]] = hit.get(r["idx"], 0) + 1
        van_hit = 0
        for v in van:
            if pref and (v == pref or v.startswith(pref + "/")):
                van_hit += 1
        rp["victims"] = sorted(((i, res["mods"][i]["name"], n) for i, n in hit.items()))
        rp["victim_files"] = sum(hit.values())
        rp["vanilla_files"] = van_hit
        res["problems"].append({
            "mod": rp["mod"], "kind": t("scan.021"),
            "detail": t("scan.022")
                      % (len(hit), rp["victim_files"], van_hit, rp["path"]),
        })

    res["diff"].sort(key=lambda x: x["rel"])

    res["same"].sort(key=lambda x: x["rel"])
    res["vanilla"].sort(key=lambda x: x["rel"])

    # ---------- L5：本地化 (语言,key) 级覆盖 ----------
    # localisation 与 common/ 的取舍规则不同：逐 key 合并、后加载者胜，与文件
    # 名无关，同名 yml 整文件并不互相顶掉。结果以 loc/loc_stats/loc_files/
    # loc_keys/loc_elapsed 并入 res，报告节与总表行分别由 loc_scan 产出。
    say(t("scan.024"))
    res.update(loc_scan.scan_localisation(res["mods"], VANILLA_ROOT, progress=say))

    res["elapsed"] = time.time() - t0
    say(t("scan.023"))
    return res


def ordering_fixable(entries):
    """判断这组冲突能否靠调整 mod 加载顺序解决。

    群星的取舍顺序是：先按**文件名 ASCII** 排，文件名相同时才看启动器里的加载顺序。
    因此只有「参与冲突的文件名完全相同」（即同路径整文件替换）才受排序影响；
    文件名不同时，胜者是字符序决定的，调排序毫无作用。

    返回 (能否靠排序解决, 说明文字)。
    """
    names = {os.path.basename(e["rel"]) for e in entries if e.get("rel")}
    if len(names) <= 1:
        return True, (t("why.001"))
    return False, (t("why.002")
                   % " / ".join(sorted(names)[:3]))


def speak_row(r):
    """把一条冲突说成人话，玩家不用懂 FIOS/LIOS 也能看明白。"""
    win = r["winner_label"]
    losers = r["losers"]
    many = len(losers)
    if many == 0:
        return t("speak.001") % win
    if many == 1:
        s = t("speak.002") % (win, losers[0])
    elif many <= 3:
        s = t("speak.002") % (win, t("sep.list").join(losers))
    else:
        s = t("speak.003") % (win, t("sep.list").join(losers[:2]), many)
    obj = r.get("subject") or r.get("key") or ""
    # 用稳定的内部代码判断类型，不能拿翻译后的文字比较——语言一换就失效。
    if r["kind_code"] == "same_path":
        s += t("speak.005") % obj
    elif r["kind_code"] == "same_key":
        s += t("speak.007") % obj
    else:
        s += t("speak.008") % r.get("key", "")
    if not r["sortable"]:
        s += t("speak.009")
    return s


def build_overview(res):
    """把三类冲突统一成一张「谁覆盖了谁」的总表。

    玩家不关心 L1/L3/L4 的分层，只想知道「我想要的生效了吗、被谁压了」。
    所以这里把同路径整文件替换、同 key 覆盖、interface 覆盖合并成同一种行结构，
    每行都带一句人话结论和一串可直接喂 AI 的证据。
    """
    rows = []

    def label(idx, name):
        return t("const.011") if idx < 0 else "%d:%s" % (idx + 1, name)

    # 同路径整文件替换：靠后加载者整份生效
    for it in res["diff"]:
        order = it["entries"]
        win = order[-1]
        losers = order[:-1]
        rows.append({
            "kind": t("speak.004"),
            "kind_code": "same_path",
            "key": it["rel"],
            "subject": it["rel"],
            "winner_mod": win["idx"],
            "winner_label": label(win["idx"], win["name"]),
            "winner_file": it["rel"],
            "losers": [label(r["idx"], r["name"]) for r in losers],
            "loser_mods": [r["idx"] for r in losers],
            "sortable": True,
            "reason": t("ov.001"),
            "sem": t("ov.002"),
            "chain": [(label(r["idx"], r["name"]), r["full"], r["idx"] == win["idx"])
                      for r in order],
            "mods": sorted({r["idx"] for r in order}),
            "in_vanilla": it["in_vanilla"],
            "mod_vs_mod": len({r["idx"] for r in order}) >= 2,
            "evidence": t("ov.003")
                        % (it["rel"], label(win["idx"], win["name"])),
        })

    # 同 key 覆盖：不同文件名之间由目录语义 + 文件名字符序决定
    for k in res["keys"]:
        if not k["win_rel"]:
            continue
        win_name = os.path.basename(k["win_rel"])
        if k["sem"] == "FIOS":
            reason = t("ov.004")
        elif k["sem"] == "LIOS":
            reason = t("ov.005")
        else:
            reason = t("ov.006")
        losers = [e for e in k["entries"] if e["rel"] != k["win_rel"]]
        # 同一 mod 的两个文件抢同一个 key 时，会得到「4 覆盖了 4」这种自相矛盾的
        # 说法，那不是 mod 之间互抢，展示时剔除，但候选链里仍保留。
        shown = [e for e in losers if e["winner"] != k["win_mod"]]
        other_mods = {e["winner"] for e in shown if e["winner"] >= 0}
        rows.append({
            "kind": t("speak.006"),
            "kind_code": "same_key",
            "key": k["key"],
            "subject": k["key"],
            "winner_mod": k["win_mod"],
            "winner_label": k["win_label"],
            "winner_file": k["win_rel"],
            "losers": [e["winner_label"] for e in shown],
            "loser_mods": sorted({m for e in shown for m in e["mods"]}),
            "sortable": False,
            "reason": t("ov.007") % (reason, win_name),
            "sem": sem_label(k["sem"]),
            "chain": [(e["winner_label"], e["rel"], e["rel"] == k["win_rel"])
                      for e in k["entries"]],
            "mods": list(k["mods"]),
            "in_vanilla": k["has_vanilla"],
            "mod_vs_mod": bool(other_mods),
            "evidence": (t("ov.008")
                         % (k["key"], k["dir"], len(k["entries"]), k["win_rel"])),
            "upset": [e["winner_label"] for e in k["upset"]],
        })

    # interface：具名元素/sprite 覆盖，LIOS
    for it in res["iface"]:
        losers = [e for e in it["entries"] if e["rel"] != it["win_rel"]]
        shown = [e for e in losers if e["winner"] != it["win_mod"]]
        other_mods = {e["winner"] for e in shown if e["winner"] >= 0}
        rows.append({
            "kind": t("ov.009"),
            "kind_code": "iface",
            "key": it["key"],
            "subject": t("ov.012") % (it["key"], it["kind"]),
            "winner_mod": it["win_mod"],
            "winner_label": it["win_label"],
            "winner_file": it["win_rel"],
            "losers": [e["winner_label"] for e in shown],
            "loser_mods": sorted({m for e in shown for m in e["mods"]}),
            "sortable": False,
            "reason": t("ov.010"),
            "sem": "LIOS",
            "chain": [(e["winner_label"], e["rel"], e["rel"] == it["win_rel"])
                      for e in it["entries"]],
            "mods": list(it["mods"]),
            "in_vanilla": it["has_vanilla"],
            "mod_vs_mod": bool(other_mods) or len(it["mods"]) >= 2,
            "evidence": (t("ov.011")
                         % (it["kind"], it["key"], len(it["entries"]), it["win_rel"])),
            "upset": [e["winner_label"] for e in it["upset"]],
        })

    # 本地化冲突行（kind_code "loc"，mod_vs_mod 口径一致，自然计入总表统计）
    rows.extend(loc_scan.overview_rows(res, res["mods"]))
    return rows


def overview_stats(res, rows=None):
    """总表口径的统计，供顶部横幅与报告开头使用。

    「冲突」只统计 mod 之间互抢的那种；mod 覆盖原版属于正常行为，单列计数。
    否则一套装了几十个 mod 的播放集会报出上千条，玩家第一眼就被数字吓住，
    反而看不到真正需要处理的那几条。
    """
    if rows is None:
        rows = build_overview(res)
    vs = [r for r in rows if r.get("mod_vs_mod")]
    nosort = [r for r in vs if not r["sortable"]]
    return {
        "rows": len(vs),
        "nosort": len(nosort),
        "sortable": len(vs) - len(nosort),
        "vs_vanilla": len(rows) - len(vs),
        "all_rows": len(rows),
        "mods": len(res["mods"]),
        "files": sum(m["files"] for m in res["mods"]),
        "vanilla_files": res["vanilla_count"],
        "redundant": len(res["same"]),
        "vanilla_touched": len(res["vanilla"]),
        "problems": len(res["problems"]),
        "upset": sum(1 for r in rows if r.get("upset")),
    }


def focus_stats(rows, idx):
    """只看某个 mod：它压了谁、被谁压了（再分开能不能靠排序救）。"""
    beats, beaten, beaten_fixable = [], [], []
    for r in rows:
        if r["winner_mod"] == idx:
            beats.append(r)
        if idx in r["loser_mods"]:
            beaten.append(r)
            if r["sortable"]:
                beaten_fixable.append(r)
    return {"beats": beats, "beaten": beaten,
            "beaten_fixable": beaten_fixable,
            "beaten_nosort": [r for r in beaten if not r["sortable"]]}


def conflict_buckets(res):
    """把冲突按「信号强度 + 能否靠排序解决」分桶。

    分桶是这份报告的核心：原始数据有 1500+ 条同 key 记录，其中绝大多数是
    「mod 覆盖原版同名 key」这类正常行为。全部倒给 AI 只会淹没重点，
    所以这里只把真正需要决策的挑出来，其余归入计数。

    返回 dict，键为桶名。
    """
    b = {}

    # 需要决策：调排序有效（同路径整文件替换）
    b["sortable"] = [it for it in res["diff"] if ordering_fixable(it["entries"])[0]]

    # 需要决策：调排序无效（文件名不同，胜负由字符序定）
    b["key_nosort"] = [k for k in res["keys"]
                       if not ordering_fixable(k["entries"])[0]]
    b["iface_nosort"] = [k for k in res["iface"]
                         if not ordering_fixable(k["entries"])[0]]
    # interface 同路径的那部分与 L1 同源，不重复列
    b["iface_samepath"] = [k for k in res["iface"]
                           if ordering_fixable(k["entries"])[0]]

    # 高信号子集一：加载顺序更靠后却输了的（该 mod 定义实际没生效）
    b["order_upset"] = [k for k in res["keys"] if k["upset"]] + \
                       [k for k in res["iface"] if k["upset"]]

    # 高信号子集二：mod 输给原版（加了 mod 却没生效）
    b["beaten_by_vanilla"] = [k for k in res["keys"]
                              if k["win_mod"] == -1 and k["win_rel"]]

    # 高信号子集三：纯 mod 对 mod 的同 key 冲突（不含原版参与）
    b["mod_vs_mod"] = [k for k in res["keys"] if not k["has_vanilla"]]

    b["diff"] = res["diff"]
    b["same"] = res["same"]
    b["vanilla"] = res["vanilla"]
    b["multi_vanilla"] = [v for v in res["vanilla"] if v.get("multi")]
    b["keys"] = res["keys"]
    b["iface"] = res["iface"]
    b["problems"] = res["problems"]
    return b


def build_report(res, detail_limit=60, modlist=True):
    """生成可喂 AI 的 Markdown 冲突报告。

    设计取向是**信号优先、控制体量**：只把需要决策的冲突展开，其余给计数。
    并把「调排序能否解决」作为第一节，因为这是排序推荐最容易踩的坑。
    """
    b = conflict_buckets(res)
    ov_rows = build_overview(res)
    ov_mod_rows = [r for r in ov_rows if r.get("mod_vs_mod")]
    st = overview_stats(res, ov_rows)
    L = []
    A = L.append

    A(t("report.001"))
    A("")
    A(t("report.002")
      % (res["vanilla_root"] or t("report.003"), res["elapsed"]))
    A("")
    A(t("report.004"))
    A("")
    A(t("report.005"))
    A("")
    A(t("report.006")
      % (st["rows"], st["nosort"], st["sortable"], st["vs_vanilla"]))
    A("")
    A(t("report.007"))
    A("")
    A(t("report.008"))
    A("")
    if not ov_mod_rows:
        A(t("report.009"))
    else:
        A(t("report.010"))
        A("| --- | --- | --- | --- | --- |")
        for r in ov_mod_rows[:detail_limit]:
            A("| %s | %s | `%s` | %s | %s |"
              % (speak_row(r).replace("|", "/"), r["kind"], r["subject"],
                 r["sem"], t("report.011") if not r["sortable"] else t("report.012")))
        if len(ov_mod_rows) > detail_limit:
            A("")
            A(t("report.013")
              % (len(ov_mod_rows) - detail_limit))
    A("")
    if b["order_upset"]:
        A(t("report.014") % len(b["order_upset"]))
        A("")
        A(t("report.015"))
        A("")
        for k in b["order_upset"][:detail_limit]:
            if "kind" in k:
                A(t("report.016")
                  % (k["kind"], k["key"], k["win_label"], k["win_rel"]))
            else:
                A(t("report.016")
                  % (k["dir"], k["key"], k["win_label"], k["win_rel"]))
            for e in k["upset"]:
                A(t("report.017") % (e["rel"], e["winner_label"]))
        A("")
    if b["beaten_by_vanilla"]:
        A(t("report.018")
          % len(b["beaten_by_vanilla"]))
        A("")
        A(t("report.019"))
        A("")
        for k in b["beaten_by_vanilla"][:detail_limit]:
            A(t("report.020")
              % (k["dir"], k["key"], k["win_rel"],
                 t("sep.list").join(e["rel"] for e in k["entries"])))
        A("")
    A("")

    # ---------- 最关键的前提 ----------
    A(t("report.021"))
    A("")
    A(t("report.022"))
    A(t("report.023"))
    A("")
    A(t("report.024"))
    A(t("report.025"))
    A("")
    A(t("report.026"))
    A("")
    A(t("report.027"))
    A("")
    A(t("report.028"))
    A("")
    A(t("report.029"))
    A("| --- | --- | --- |")
    A(t("report.030") % len(b["sortable"]))
    A(t("report.031") % len(b["key_nosort"]))
    A(t("report.032") % len(b["iface_nosort"]))
    A(t("report.033") % len(b["iface_samepath"]))
    A(t("report.034") % len(b["order_upset"]))
    A(t("report.035") % len(b["beaten_by_vanilla"]))
    A(t("report.036") % len(b["mod_vs_mod"]))
    A(t("report.037") % len(b["same"]))
    A(t("report.038") % len(b["vanilla"]))
    A(t("report.039") % len(b["problems"]))
    A("")
    A(t("report.040"))
    A("")
    A(t("report.041"))
    A("")

    # ---------- A 类：能靠排序解决 ----------
    A(t("report.042") % len(b["sortable"]))
    A("")
    A(t("report.043"))
    A("")
    if not b["sortable"]:
        A(t("report.044"))
    else:
        for it in b["sortable"][:detail_limit]:
            losers = ", ".join("%d:%s" % (r["idx"] + 1, r["name"]) for r in it["entries"][:-1])
            flag = t("report.045") if it["in_vanilla"] else ""
            A("- `%s`%s" % (it["rel"], flag))
            A(t("report.046") % (it["winner"] + 1, it["winner_name"]))
            A(t("report.047") % losers)
        if len(b["sortable"]) > detail_limit:
            A(t("report.048") % (len(b["sortable"]) - detail_limit))
    A("")

    # ---------- B 类：排序无效 ----------
    A(t("report.049"))
    A("")
    A(t("report.050"))
    A("")

    A(t("report.051")
      % len(b["mod_vs_mod"]))
    A("")
    if not b["mod_vs_mod"]:
        A(t("report.044"))
    else:
        for k in b["mod_vs_mod"][:detail_limit]:
            A(t("report.052") % (k["dir"], k["key"],
                                       sem_label(k["sem"])))
            if k["win_rel"]:
                A(t("report.053") % (k["win_label"], k["win_rel"]))
            else:
                A(t("report.054"))
            for e in k["entries"]:
                tag = t("report.055") if e["rel"] == k["win_rel"] and k["win_rel"] else ""
                A("    - `%s` → %s%s" % (e["rel"], e["winner_label"], tag))
        if len(b["mod_vs_mod"]) > detail_limit:
            A(t("report.056") % (len(b["mod_vs_mod"]) - detail_limit))
    A("")

    # ---------- 其余计数 ----------
    A(t("report.057"))
    A("")
    A(t("report.058") % len(b["same"]))
    A(t("report.059")
      % (len(b["vanilla"]), len(b["multi_vanilla"])))
    A(t("report.060")
      % (len(b["keys"]), len(b["iface"])))
    if b["multi_vanilla"]:
        A("")
        A(t("report.061"))
        A("")
        for it in b["multi_vanilla"][:detail_limit]:
            mods = ", ".join("%d:%s" % (r["idx"] + 1, r["name"]) for r in it["entries"])
            A("- `%s` ← %s" % (it["rel"], mods))
        if len(b["multi_vanilla"]) > detail_limit:
            A(t("report.056") % (len(b["multi_vanilla"]) - detail_limit))
    A("")

    # ---------- 5bis：本地化 key 覆盖（loc_scan 产出）----------
    A(loc_scan.build_report_section(res, res["mods"], detail_limit))
    A("")

    A(t("report.062"))
    A("")
    if not b["problems"]:
        A(t("report.044"))
    else:
        for p in b["problems"]:
            A(t("report.074") % (p["kind"], p["mod"], p["detail"]))
    A("")
    if res["replace_paths"]:
        A(t("report.063"))
        A("")

    # ---------- mod 列表 ----------
    if modlist:
        A(t("report.064"))
        A("")
        A(t("report.065"))
        A("")
        A(t("report.066"))
        A("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for m in res["mods"]:
            A("| %d | %s | %d | %d | %d | %d | %d | %s |"
              % (m["idx"] + 1, m["name"], m["files"], m["vover"], m["ovr"],
                 m["beaten"], m["redund"], t("sep.list").join(m["errors"]) or t("report.067")))
        A("")

    A(t("report.068"))
    A("")
    A(t("report.069"))
    A(t("report.070"))
    A(t("report.071"))
    A(t("report.072"))
    A("")
    A(t("report.073"))
    A("")
    return "\n".join(L)


def print_summary(res):
    print(t("cli.001") % res["playlist"])
    print(t("cli.002")
          % (len(res["mods"]), res["vanilla_count"], res["elapsed"]))
    print(t("cli.003")
          % (len(res["diff"]), len(res["same"]), len(res["vanilla"]), len(res["problems"])))
    known = sum(1 for k in res["keys"] if k["sem"] in ("FIOS", "LIOS"))
    unk = sum(1 for k in res["keys"] if k["sem"] == "UNKNOWN")
    upset = sum(1 for k in res["keys"] if k["upset"])
    print(t("cli.004")
          % (len(res["keys"]), known, unk, upset))
    from collections import Counter as _C
    bd = _C(k["sem"] for k in res["keys"])
    print(t("cli.005") + "  ".join("%s=%d" % (s, bd[s]) for s in sorted(bd)))
    print("")
    if res["diff"]:
        print(t("cli.006"))
        for it in res["diff"]:
            losers = ", ".join("%d:%s" % (r["idx"] + 1, r["name"]) for r in it["entries"][:-1])
            tag = t("cli.007") if it["in_vanilla"] else ""
            print(t("cli.008")
                  % (it["rel"], it["winner"] + 1, it["winner_name"], losers, tag))
    if res["problems"]:
        print("")
        print(t("cli.009"))
        for p in res["problems"]:
            print("  [%s] %s : %s" % (p["kind"], p["mod"], p["detail"]))
    up = [k for k in res["keys"] if k["upset"]]
    if up:
        print("")
        print(t("cli.010"))
        for k in up[:25]:
            print(t("cli.011") % (k["key"], k["dir"], k["win_label"]))
            for e in k["upset"]:
                print(t("cli.012") % (e["rel"], e["winner_label"]))
    if res["replace_paths"]:
        print("")
        print(t("cli.013"))
        for rp in res["replace_paths"]:
            print(t("cli.014") % (rp["mod"], rp["path"]))
            if rp["victims"]:
                for i, n, c in rp["victims"]:
                    print(t("cli.015") % (i + 1, n, c))
            else:
                print(t("cli.016"))


def main():
    # 先定语言再建 argparse，否则 --help 的文字会停在 import 时的语言。
    init_paths()

    ap = argparse.ArgumentParser(
        description=t("cli.017"))
    ap.add_argument("--cli", action="store_true", help=t("cli.018"))
    ap.add_argument("--report", metavar=t("gui.019"), nargs="?",
                    const="", default=None,
                    help=t("cli.019"))
    ap.add_argument("--detail-limit", type=int, default=60,
                    help=t("cli.020"))
    ap.add_argument("--include-dlc", action="store_true",
                    help=t("cli.021"))
    ap.add_argument("--vanilla", metavar=t("cli.022"), default=None,
                    help=t("cli.023"))
    ap.add_argument("--documents", metavar=t("cli.022"), default=None,
                    help=t("cli.024"))
    ap.add_argument("--lang", metavar=t("cli.027"), default=None,
                    choices=list(i18n.SUPPORTED),
                    help=t("cli.028"))
    a = ap.parse_args()

    if a.vanilla or a.documents or a.lang:
        cfg = load_config()
        if a.vanilla:
            cfg["vanilla"] = a.vanilla
        if a.documents:
            cfg["documents"] = a.documents
        if a.lang:
            cfg["lang"] = a.lang
        save_config(cfg)
        # 语言与路径提示都要按新设置重算一遍。
        # 注意先无条件 set_language：写配置可能失败（用户目录只读、被安全软件
        # 挡住等），那时若只靠重新读配置，--lang 会被静默忽略、又退回系统语言。
        if a.lang:
            i18n.set_language(a.lang, explicit=True)
        init_paths()

    if a.report is not None:
        res = scan(include_dlc=a.include_dlc, progress=lambda m: None)
        rep = build_report(res, detail_limit=a.detail_limit)
        if a.report:
            outp = a.report
        else:
            desk = _known_folder("{B4BFCC3A-DB2C-424C-B029-BFE99A87C641}")
            outp = os.path.join(desk if desk and os.path.isdir(desk)
                                else os.path.expanduser("~"),
                                t("gui.129"))
        try:
            with open(outp, "w", encoding="utf-8") as f:
                f.write(rep)
            print(t("cli.025") % outp)
            print(t("cli.026") % len(rep))
        except OSError as e:
            print(t("gui.133") % e)
            print(rep)
        return

    if a.cli:
        print_summary(scan(include_dlc=a.include_dlc, progress=lambda m: None))
    else:
        from gui_app import App as GuiApp  # GUI 已迁至 gui_app.py
        GuiApp(include_dlc=a.include_dlc).mainloop()


if __name__ == "__main__":
    main()
