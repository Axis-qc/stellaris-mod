# -*- coding: utf-8 -*-
"""语言文件加载与取词。

面向玩家的文字一律不写在代码里，全部放在程序旁边的 lang/ 目录下：
    lang/zh-CN.json   简体中文（缺省语言，同时充当键名基准）
    lang/en-US.json   英文

取词用 t("gui.001")，占位符沿用 Python 的 % 风格，调用时把参数传进来即可：
    t("gui.012", name)        对应 "%s 覆盖了 ..."
    t("gui.013", a, b)        多个参数

找不到所请求的语言时依次回退：请求语言 -> 简体中文 -> 键名本身。
键名本身就是最后兜底，所以任何一条漏翻都只会显示成 gui.012 这种字样，
不会让程序崩掉。
"""

import json
import os
import sys

DEFAULT_LANG = "zh-CN"
LANG_NAMES = (("zh-CN", "简体中文"), ("en-US", "English"))
SUPPORTED = tuple(code for code, _ in LANG_NAMES)

_lang = DEFAULT_LANG
_cat = {}          # 当前语言
_fallback = {}     # 简体中文，作兜底
_loaded = False
_locked = False    # 由命令行等显式指定后置真，后续自动推断不得覆盖


def is_locked():
    return _locked


def lock():
    """锁定当前语言，之后的自动推断不再覆盖它。"""
    global _locked
    _locked = True


def set_language(code, persist_cfg=None, explicit=False):
    """切换语言。persist_cfg 传 None 表示只改内存，不写配置文件。

    explicit=True 表示这是调用方明确指定的语言（如 --lang），
    之后 init_paths 之类的自动推断不会再把它改回去。
    """
    global _lang, _cat, _fallback, _loaded, _locked
    if code not in SUPPORTED:
        code = DEFAULT_LANG
    if not _loaded:
        _fallback = _read_catalog(DEFAULT_LANG)
    _cat = _read_catalog(code) if code != DEFAULT_LANG else _fallback
    _lang = code
    _loaded = True
    if explicit:
        _locked = True
    return _lang


def base_dir():
    """程序所在目录。打包后取 exe 所在目录，源码运行取脚本目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _lang_dirs():
    dirs = [os.path.join(base_dir(), "lang"),
            os.path.join(os.path.dirname(base_dir()), "lang")]
    # PyInstaller onedir 把 --add-data 的内容放进 _MEIPASS（即 _internal）
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        dirs.append(os.path.join(meipass, "lang"))
    out = []
    for d in dirs:
        if d and d not in out:
            out.append(d)
    return out


def _read_catalog(code):
    for d in _lang_dirs():
        p = os.path.join(d, "%s.json" % code)
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return {k: v for k, v in data.items()
                            if isinstance(v, str) and not k.startswith("_")}
            except (OSError, ValueError):
                continue
    return {}


def available():
    """实际存在的语言文件，供界面下拉框使用。"""
    out = []
    for code in SUPPORTED:
        for d in _lang_dirs():
            if os.path.isfile(os.path.join(d, "%s.json" % code)):
                out.append(code)
                break
    return out or [DEFAULT_LANG]


def system_lang():
    """按系统界面语言猜一个默认值，认不出就用简体中文。"""
    try:
        import ctypes
        primary = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0xFF
        # 0x04 是 Windows 的「中文」主语言 ID
        return DEFAULT_LANG if primary == 0x04 else "en-US"
    except Exception:
        pass
    for env in ("LANG", "LC_ALL", "LANGUAGE"):
        v = (os.environ.get(env) or "").lower()
        if v.startswith("zh"):
            return DEFAULT_LANG
        if v:
            return "en-US"
    return DEFAULT_LANG


def languages():
    return list(LANG_NAMES)


def current():
    return _lang


def t(key, *args, **kw):
    """取词并按需套占位符。"""
    if not _loaded:
        set_language(_lang)
    s = _cat.get(key)
    if s is None:
        s = _fallback.get(key)
    if s is None:
        s = key
    if args:
        try:
            return s % args
        except (TypeError, ValueError):
            return s
    if kw:
        try:
            return s % kw
        except (TypeError, ValueError):
            return s
    return s
