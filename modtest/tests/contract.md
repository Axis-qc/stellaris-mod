# v2 升级数据契约（队友共同遵守，改契约先经 Lead）

## 一、扫描结果新增字段（scan() 返回的 res）

res["loc"]：本地化 key 级冲突列表，每项：
  key        str  本地化 key 原文
  lang       str  语言段名，如 l_simp_chinese
  entries    list 按加载顺序升序：{rel, mod(int, 原版=-1), full(绝对路径)}
  winner     int  生效 mod 的 idx（本地化语义：后加载者胜，文件名无关）
  winner_label / loser_mods / mods / has_vanilla / mod_vs_mod
  mod_vs_mod 判定：参与的真实 mod >= 2（与原版撞 key 属正常覆盖，不算冲突行）

res["loc_stats"]：逐 mod 统计，{idx: {"defined": n, "lost": n, "beaten_by": [mod名]}}，
另含 res["loc_files"]（扫过的 yml 数）与 res["loc_keys"]（唯一 (lang,key) 数）。

覆盖总表行新增 kind_code "loc"，key 形如 "loc:<lang>:<key>"，sortable=True。
overview_stats 不改结构，loc 行自然计入 rows/nosort/sortable。

## 二、解析规则

localisation/**/*.yml，strip BOM，逐行：`#` 注释跳过；语言段头 `^\s*(l_\w+):`；
条目 `^\s*(.+?):\d+\s*"(.*)"\s*$` 取 group(1) 为 key（key 可含空格，取冒号前全部）。
同一 (lang,key) 跨文件合并；同 mod 重复定义用 set 归并。原版参与（idx=-1）。

## 三、删除与备份（src\fs_ops.py）

fs_ops.plan_targets(chain_entries, keep_idx) -> 删除清单（被删方必须有 full 路径）。
fs_ops.execute_deletes(targets, tool_root) -> 每项 {rel, ok, backup, error}：
  备份目录 = <tool_root>\backups\<启动时间戳>\<mod名>\，保留原相对路径结构；
  备份后 os.remove；删除后向上清理空目录直到 mod 根（fs_ops.rmtree_empty_dirs）。
  tool_root = src 目录的上一级（即 modtest 根），绝不写进任何 mod 目录。
fs_ops.is_workshop(full) -> 路径含 workshop 与 281990 组件时 True，UI 据此加提示。
fs_ops.restore_backups(backup_dir) 保留能力，暂不做 UI。

## 四、语言 key 分工

core：loc.*（扫描与本地化域文案）、report.075+（报告新增节）、scan.024+。
gui：gui.143+（新控件与动作文案）、act.* 不新开。
lang json 双语同步、只增不改不删；写冲突（FS_STALE）就重读再补。

## 五、界面结构（gui_app.py）

App 移入 src\gui_app.py；main() 由 Lead 接线。
右区：Notebook[文件树, 高级]。高级=嵌套 Notebook：覆盖总表、同路径、冗余、覆盖原版、
同 key、界面元素、本地化、描述符、删除清单。左 mod 列表、横幅、路径栏、语言切换不变。
文件树：只挂 mod 互抢路径（同路径 diff + loc yml）；按 / 分段建层级；文件节点第二列
「生效者：N:名」；子节点按加载顺序上→下（上=先加载=低优先），绿=生效、灰=被覆盖。
详情窗格：链下拉框选保留方 + 打开文件位置 / 打开 mod 根目录 / 删除并保留此版本 /
加入删除清单；确认弹窗逐条列删留；工坊文件追加 Steam 恢复提示。
删除清单页签：列（文件、保留、删除）+ 执行删除 / 移除选中；执行后自动重扫。

## 六、回归验收

python src\mod_conflict_check.py --report <after.md> 与 tests\baseline\report_before.md 比：
第 1-8 节所有数字必须一致；允许差异=新增本地化节 + report.073 免责句改写。
GUI 自测不依赖真实窗口枚举，沿用 winfo + 行数断言；删除流程在 tests\fixture 临时夹具验证。

## 七、待议新功能（完成主线后讨论，双方同意且有余力才做）

a 文件树顶部搜索框按文件名过滤；b 删除后清空父目录；c 备份一键还原入口；d 横幅点击跳到树中首个冲突。
