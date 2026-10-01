# Stellaris 播放集冲突报告

工具产出，供玩家自己看，也供 AI 做排序分析与冲突排查。原版目录 `G:\SteamLibrary\steamapps\common\Stellaris`，扫描耗时 8.2 秒。

## 这份报告怎么看（给玩家）

看不懂下面的技术细节没关系。把这份文件整个丢给任意 AI，让它按第 1 节的结论帮你调整 mod 顺序即可。

一句话结论：本播放集有 68 处 mod 之间互相覆盖，其中 55 处**改加载顺序也没用**，13 处可以靠调整顺序解决。另有 1101 处是 mod 覆盖原版，属正常行为。

「mod 之间互相覆盖」指两个 mod 抢同一份内容，只有一个能生效。「改加载顺序也没用」的那些，胜负在文件名上就定了，把 mod 拖到列表最下面也救不回来。

## 1. 谁覆盖了谁（mod 之间互抢，逐条）

| 结论 | 类型 | 冲突对象 | 判定依据 | 改排序有用吗 |
| --- | --- | --- | --- | --- |
| 2:UI Overhaul Dynamic - Extended Topbar 覆盖了 1:UI Overhaul Dynamic（同一个文件 interface/main_alerts.gui） | 同路径文件 | `interface/main_alerts.gui` | 加载顺序 | 有用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 2:UI Overhaul Dynamic - Extended Topbar（同一个文件 interface/main_topbar.gui） | 同路径文件 | `interface/main_topbar.gui` | 加载顺序 | 有用 |
| 2:UI Overhaul Dynamic - Extended Topbar 覆盖了 1:UI Overhaul Dynamic（同一个文件 interface/resource_groups/ui_overhaul_merged_resource_groups.txt） | 同路径文件 | `interface/resource_groups/ui_overhaul_merged_resource_groups.txt` | 加载顺序 | 有用 |
| 2:UI Overhaul Dynamic - Extended Topbar 覆盖了 1:UI Overhaul Dynamic（同一个文件 interface/ui_overhaul_qhd-gfx/ui_overhaul_qhd_fonts.gfx） | 同路径文件 | `interface/ui_overhaul_qhd-gfx/ui_overhaul_qhd_fonts.gfx` | 加载顺序 | 有用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NAI.PEACE_RELATIVE_NAVY_STRENGTH_FACTOR）　—— 调加载顺序改不了 | 同名定义 | `NAI.PEACE_RELATIVE_NAVY_STRENGTH_FACTOR` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NCamera.GALAXY_MAX_PITCH）　—— 调加载顺序改不了 | 同名定义 | `NCamera.GALAXY_MAX_PITCH` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NCamera.GALAXY_MIN_PITCH）　—— 调加载顺序改不了 | 同名定义 | `NCamera.GALAXY_MIN_PITCH` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NCamera.SYSTEM_MAX_PITCH）　—— 调加载顺序改不了 | 同名定义 | `NCamera.SYSTEM_MAX_PITCH` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NCamera.SYSTEM_MIN_PITCH）　—— 调加载顺序改不了 | 同名定义 | `NCamera.SYSTEM_MIN_PITCH` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGameplay.COMMAND_LIMIT_MAX）　—— 调加载顺序改不了 | 同名定义 | `NGameplay.COMMAND_LIMIT_MAX` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGameplay.NAVAL_CAPACITY_MAX）　—— 调加载顺序改不了 | 同名定义 | `NGameplay.NAVAL_CAPACITY_MAX` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGameplay.NAVAL_CAPACITY_NO_LEADER_PENALTY）　—— 调加载顺序改不了 | 同名定义 | `NGameplay.NAVAL_CAPACITY_NO_LEADER_PENALTY` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGameplay.NAVAL_CAPACITY_POP_MULT）　—— 调加载顺序改不了 | 同名定义 | `NGameplay.NAVAL_CAPACITY_POP_MULT` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.BALLISTIC_PROJECTILE_MISSED_LIFETIME）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.BALLISTIC_PROJECTILE_MISSED_LIFETIME` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.MAX_GFX_MISSILES）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.MAX_GFX_MISSILES` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.MAX_GFX_PRIO_PROJECTILES）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.MAX_GFX_PRIO_PROJECTILES` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.MAX_GFX_PROJECTILES）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.MAX_GFX_PROJECTILES` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.MISSILE_HEIGHT_OFFSET）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.MISSILE_HEIGHT_OFFSET` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.MISSILE_RANDOM_OFFSET_MAX_RADIUS）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.MISSILE_RANDOM_OFFSET_MAX_RADIUS` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.MISSILE_RANDOM_OFFSET_MIN_RADIUS）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.MISSILE_RANDOM_OFFSET_MIN_RADIUS` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.MUZZLE_FLASH_DURATION）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.MUZZLE_FLASH_DURATION` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.MUZZLE_FLASH_LIMIT）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.MUZZLE_FLASH_LIMIT` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.SHIELD_DISTANCE_FROM_SHIP）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.SHIELD_DISTANCE_FROM_SHIP` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.SHIELD_DISTANCE_FROM_SHIP_MULT）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.SHIELD_DISTANCE_FROM_SHIP_MULT` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.SHIELD_EFFECT_LOOP_INTERVAL）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.SHIELD_EFFECT_LOOP_INTERVAL` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.SHIELD_EFFECT_TIME_SCALE）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.SHIELD_EFFECT_TIME_SCALE` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.SHIP_RANDOM_HEIGHT_OFFSET）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.SHIP_RANDOM_HEIGHT_OFFSET` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.STRIKE_CRAFT_HEIGHT_OFFSET）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.STRIKE_CRAFT_HEIGHT_OFFSET` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.STRIKE_CRAFT_HEIGHT_RANDOM）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.STRIKE_CRAFT_HEIGHT_RANDOM` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.STRIKE_CRAFT_TRAIL_FADE_RATE）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.STRIKE_CRAFT_TRAIL_FADE_RATE` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NGraphics.TRAILS_ALPHA_FADE）　—— 调加载顺序改不了 | 同名定义 | `NGraphics.TRAILS_ALPHA_FADE` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NShip.FLEET_BASE_FORMATION_DIV）　—— 调加载顺序改不了 | 同名定义 | `NShip.FLEET_BASE_FORMATION_DIV` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NShip.FLEET_BASE_FORMATION_SCALE）　—— 调加载顺序改不了 | 同名定义 | `NShip.FLEET_BASE_FORMATION_SCALE` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NShip.FLEET_FORMATION_CIRCLE_RADIUS_PER_LAYER_MULT）　—— 调加载顺序改不了 | 同名定义 | `NShip.FLEET_FORMATION_CIRCLE_RADIUS_PER_LAYER_MULT` | LIOS 靠后者胜 | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 原版、5:群星：星海旗舰（同一个定义 NShip.FLEET_FORMATION_CIRCLE_SHIPS_PER_LAYER_MULT）　—— 调加载顺序改不了 | 同名定义 | `NShip.FLEET_FORMATION_CIRCLE_SHIPS_PER_LAYER_MULT` | LIOS 靠后者胜 | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 覆盖了 原版（同一个界面元素 GFX_alerticon_banner_high）　—— 调加载顺序改不了 | 界面元素 | `GFX_alerticon_banner_high（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 覆盖了 原版（同一个界面元素 GFX_alerticon_banner_low）　—— 调加载顺序改不了 | 界面元素 | `GFX_alerticon_banner_low（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 覆盖了 原版（同一个界面元素 GFX_alerticon_banner_med）　—— 调加载顺序改不了 | 界面元素 | `GFX_alerticon_banner_med（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 覆盖了 1:UI Overhaul Dynamic（同一个界面元素 GFX_resource_nanites_large）　—— 调加载顺序改不了 | 界面元素 | `GFX_resource_nanites_large（gfx）` | LIOS | 没用 |
| 1:UI Overhaul Dynamic 覆盖了 2:UI Overhaul Dynamic - Extended Topbar（同一个界面元素 GFX_tiles_frame_notrans）　—— 调加载顺序改不了 | 界面元素 | `GFX_tiles_frame_notrans（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 生效 | 界面元素 | `GFX_ui_alert_icon_1_line（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 生效 | 界面元素 | `GFX_ui_alert_icon_2_line（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 生效 | 界面元素 | `GFX_ui_message_frame（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 生效 | 界面元素 | `GFX_ui_topbar_background（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 生效 | 界面元素 | `GFX_ui_topbar_background_corner（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 生效 | 界面元素 | `GFX_ui_topbar_background_corner_hexagon（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 生效 | 界面元素 | `GFX_ui_topbar_background_hexagon（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 生效 | 界面元素 | `GFX_ui_topbar_bar（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 生效 | 界面元素 | `GFX_ui_topbar_bg_tile（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 生效 | 界面元素 | `GFX_ui_topbar_musicplayer_background（gfx）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 覆盖了 原版（同一个界面元素 alerticon_offset）　—— 调加载顺序改不了 | 界面元素 | `alerticon_offset（gui）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 覆盖了 原版（同一个界面元素 alerticon_per_row）　—— 调加载顺序改不了 | 界面元素 | `alerticon_per_row（gui）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 覆盖了 原版（同一个界面元素 alerticon_startposition）　—— 调加载顺序改不了 | 界面元素 | `alerticon_startposition（gui）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 覆盖了 原版（同一个界面元素 alerticon_window）　—— 调加载顺序改不了 | 界面元素 | `alerticon_window（gui）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 覆盖了 1:UI Overhaul Dynamic（同一个界面元素 fleet_view_max_height_subtraction）　—— 调加载顺序改不了 | 界面元素 | `fleet_view_max_height_subtraction（gui）` | LIOS | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 1:UI Overhaul Dynamic（同一个界面元素 maingui）　—— 调加载顺序改不了 | 界面元素 | `maingui（gui）` | LIOS | 没用 |
| 2:UI Overhaul Dynamic - Extended Topbar 覆盖了 原版（同一个界面元素 message_window）　—— 调加载顺序改不了 | 界面元素 | `message_window（gui）` | LIOS | 没用 |
| 原版 覆盖了 1:UI Overhaul Dynamic（同一个界面元素 outliner_member_waystation_entry_window）　—— 调加载顺序改不了 | 界面元素 | `outliner_member_waystation_entry_window（gui）` | LIOS | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 1:UI Overhaul Dynamic（同一个界面元素 single_resource_entry）　—— 调加载顺序改不了 | 界面元素 | `single_resource_entry（gui）` | LIOS | 没用 |
| 4:联机用(需要放在UImod的下方） 覆盖了 3:领袖培养小飞地（同一个界面元素 loc:l_simp_chinese:dgds_subclass_tt） | 本地化 key 覆盖 | `dgds_subclass_tt` | 语言 l_simp_chinese · 生效 4:联机用(需要放在UImod的下方） | 有用 |

（其余 8 条同类省略，可用 --detail-limit 调大）

### 1.1 特别注意：排得更靠后却仍然输了（33 条）

这些 mod 在播放集里排在对方下面，按理该它赢，实际却没有生效，因为文件名排序输给了对方。想让它生效只能改文件名或做兼容补丁。

- [common/defines] `NAI.PEACE_RELATIVE_NAVY_STRENGTH_FACTOR`：生效 4:联机用(需要放在UImod的下方）（`common/defines/啊_sx_defines.txt`）
  - 未生效：common/defines/br_ship_defines.txt（5:群星：星海旗舰）
- [common/defines] `NCamera.GALAXY_MAX_PITCH`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NCamera.GALAXY_MIN_PITCH`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NCamera.SYSTEM_MAX_PITCH`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NCamera.SYSTEM_MIN_PITCH`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGameplay.COMMAND_LIMIT_MAX`：生效 4:联机用(需要放在UImod的下方）（`common/defines/啊_sx_defines.txt`）
  - 未生效：common/defines/br_ship_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGameplay.NAVAL_CAPACITY_MAX`：生效 4:联机用(需要放在UImod的下方）（`common/defines/啊_sx_defines.txt`）
  - 未生效：common/defines/br_ship_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGameplay.NAVAL_CAPACITY_NO_LEADER_PENALTY`：生效 4:联机用(需要放在UImod的下方）（`common/defines/啊_sx_defines.txt`）
  - 未生效：common/defines/br_ship_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGameplay.NAVAL_CAPACITY_POP_MULT`：生效 4:联机用(需要放在UImod的下方）（`common/defines/啊_sx_defines.txt`）
  - 未生效：common/defines/br_ship_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.BALLISTIC_PROJECTILE_MISSED_LIFETIME`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.MAX_GFX_MISSILES`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.MAX_GFX_PRIO_PROJECTILES`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.MAX_GFX_PROJECTILES`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.MISSILE_HEIGHT_OFFSET`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.MISSILE_RANDOM_OFFSET_MAX_RADIUS`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.MISSILE_RANDOM_OFFSET_MIN_RADIUS`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.MUZZLE_FLASH_DURATION`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.MUZZLE_FLASH_LIMIT`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.SHIELD_DISTANCE_FROM_SHIP`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.SHIELD_DISTANCE_FROM_SHIP_MULT`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.SHIELD_EFFECT_LOOP_INTERVAL`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.SHIELD_EFFECT_TIME_SCALE`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.SHIP_RANDOM_HEIGHT_OFFSET`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.STRIKE_CRAFT_HEIGHT_OFFSET`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.STRIKE_CRAFT_HEIGHT_RANDOM`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.STRIKE_CRAFT_TRAIL_FADE_RATE`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NGraphics.TRAILS_ALPHA_FADE`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NShip.FLEET_BASE_FORMATION_DIV`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NShip.FLEET_BASE_FORMATION_SCALE`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NShip.FLEET_FORMATION_CIRCLE_RADIUS_PER_LAYER_MULT`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [common/defines] `NShip.FLEET_FORMATION_CIRCLE_SHIPS_PER_LAYER_MULT`：生效 4:联机用(需要放在UImod的下方）（`common/defines/ship_zx_defines.txt`）
  - 未生效：common/defines/br_sx_defines.txt（5:群星：星海旗舰）
- [gfx] `GFX_tiles_frame_notrans`：生效 1:UI Overhaul Dynamic（`interface/ui_overhaul_qhd-gfx/ui_overhaul_qhd_planet_view.gfx`）
  - 未生效：interface/ui_overhaul_qhd-gfx/ui_overhaul_qhd_modicons.gfx（2:UI Overhaul Dynamic - Extended Topbar）
- [gui] `outliner_member_waystation_entry_window`：生效 原版（`interface/waystation_network_view.gui`）
  - 未生效：interface/outliner.gui（1:UI Overhaul Dynamic）


## 2. 判定前提（分析前必读）

群星的取舍顺序是：**先按文件名 ASCII 排，文件名相同时才看启动器里的加载顺序**。
所以冲突分两种，处理方式完全不同：

- **调排序有效**：参与冲突的文件名完全相同（同路径整文件替换）。把想生效的 mod 放到对方下面即可。
- **调排序无效**：参与冲突的文件名不同。胜者由文件名字符序决定，**改加载顺序没有任何作用**，只能改文件名或做兼容补丁。

原版按加载顺序最靠前、优先级最低参与比较，因此 mod 未必一定赢。

覆盖语义表来自官方 wiki 的 Common folder 总表加本地实测对账，游戏大版本更新后某些目录的规则可能变化。本报告给出的生效者若有疑问，以 error.log 里的实际记录为准，搜索 `already exists, using the one at`，该行给出的文件才是真正生效的那份。

## 3. 汇总

| 类别 | 数量 | 调排序能否解决 |
| --- | --- | --- |
| 同路径内容不同（硬冲突） | 4 | 能 |
| 同 key 覆盖，不同文件名 | 110 | **不能** |
| interface 覆盖，不同文件名 | 153 | **不能** |
| interface 覆盖，同路径 | 900 | 能（与硬冲突同源） |
| 其中：加载更靠后却输了的 | 33 | 不能（文件名字符序输了） |
| 其中：mod 输给原版（mod 没生效） | 0 | 不能 |
| 其中：纯 mod 对 mod 的同 key 冲突 | 0 | 视文件名而定 |
| 冗余相同（字节一致，可忽略） | 31 | 不适用 |
| mod 改原版同路径（正常行为） | 461 | 不能（原版恒输） |
| 描述符 / replace_path | 0 | 不适用 |

第 5.1 节把同 key 与 interface 两类混排，每条的方括号标出类型：`common/...` 是同 key 覆盖，`gui`/`gfx` 是 interface 覆盖。

下面所有路径均为相对 mod 根目录；`N:名字` 表示播放集里第 N 位的 mod。

## 4. 调排序可以解决的冲突（4 条）

同路径整文件替换，靠后加载者整份生效。要谁生效就把它放到对方下面。

- `interface/main_alerts.gui`
  - 当前生效：**2:UI Overhaul Dynamic - Extended Topbar**
  - 被压住：1:UI Overhaul Dynamic
- `interface/main_topbar.gui`
  - 当前生效：**4:联机用(需要放在UImod的下方）**
  - 被压住：2:UI Overhaul Dynamic - Extended Topbar
- `interface/resource_groups/ui_overhaul_merged_resource_groups.txt`
  - 当前生效：**2:UI Overhaul Dynamic - Extended Topbar**
  - 被压住：1:UI Overhaul Dynamic
- `interface/ui_overhaul_qhd-gfx/ui_overhaul_qhd_fonts.gfx`
  - 当前生效：**2:UI Overhaul Dynamic - Extended Topbar**
  - 被压住：1:UI Overhaul Dynamic

## 5. 调排序无效的冲突（完整清单）

胜负由文件名字符序决定，改加载顺序无用。第 1.1、1.2 节已列出其中最要紧的两类，这里是全部明细。

### 5.1 纯 mod 对 mod 的同 key 冲突（不含原版，0 条）

（无）

## 6. 其余（无需逐条决策）

- 冗余相同 31 条：同路径且字节一致，互相覆盖无影响。
- mod 改原版同路径 461 条：正常覆盖行为，原版恒输；其中被多个 mod 同时改的 0 条。
- 同 key 覆盖总计 110 条、interface 覆盖总计 1053 条，绝大多数是 mod 覆盖原版同名定义，已收入上面的分桶。

## 5bis. 本地化 key 覆盖（插在第 5 节与第 6 节之间）

本地化与 common/ 不同：localisation 目录按**加载顺序逐 key 合并**，后加载者的同名 (语言,key) 覆盖先加载者，与文件名无关。原版最先加载。mod 覆盖原版 key 属正常行为，不计入冲突；只有两个以上真实 mod 抢同一个 key 才列出。

本地化冲突（mod 互抢同名 key）共 9 条；扫过 yml 文件 2382 个，唯一 (语言,key) 1494124 个。

本地化目录（localisation/**/*.yml，含 replace 子目录）按加载顺序逐 key 合并：后加载者的同名 (语言,key) 覆盖先加载者，与文件名无关。原版按加载顺序最靠前参与。

本地化冲突逐条清单（生效者 = 加载顺序最靠后者）：

| 语言 | key | 生效者 | 被压者 |
| --- | --- | --- | --- |
| l_simp_chinese | `dgds_subclass_tt` | 4:联机用(需要放在UImod的下方） | 3:领袖培养小飞地 |
| l_simp_chinese | `fyds_subclass_tt` | 4:联机用(需要放在UImod的下方） | 3:领袖培养小飞地 |
| l_simp_chinese | `mod_leader_commanders_unity_upkeep_add` | 4:联机用(需要放在UImod的下方） | 3:领袖培养小飞地 |
| l_simp_chinese | `mod_leader_officials_unity_upkeep_add` | 4:联机用(需要放在UImod的下方） | 3:领袖培养小飞地 |
| l_simp_chinese | `mod_leader_scientists_unity_upkeep_add` | 4:联机用(需要放在UImod的下方） | 原版、3:领袖培养小飞地 |
| l_simp_chinese | `subclass_commander_fyds` | 4:联机用(需要放在UImod的下方） | 3:领袖培养小飞地 |
| l_simp_chinese | `subclass_commander_fyds_desc` | 4:联机用(需要放在UImod的下方） | 3:领袖培养小飞地 |
| l_simp_chinese | `subclass_official_dgds` | 4:联机用(需要放在UImod的下方） | 3:领袖培养小飞地 |
| l_simp_chinese | `subclass_official_dgds_desc` | 4:联机用(需要放在UImod的下方） | 3:领袖培养小飞地 |

### 5bis.1 每个 mod 的本地化生效情况

| # | Mod | 定义 key 数 | 被压 key 数 | 压它的 mod |
| --- | --- | --- | --- | --- |
| 1 | UI Overhaul Dynamic | 470 | 0 | （该 mod 未被任何其他 mod 压掉本地化 key） |
| 2 | UI Overhaul Dynamic - Extended Topbar | 0 | 0 | （该 mod 未定义本地化 key） |
| 3 | 领袖培养小飞地 | 397 | 9 | 联机用(需要放在UImod的下方） |
| 4 | 联机用(需要放在UImod的下方） | 809 | 0 | （该 mod 未被任何其他 mod 压掉本地化 key） |
| 5 | 群星：星海旗舰 | 3142 | 0 | （该 mod 未被任何其他 mod 压掉本地化 key） |
| 6 | Fancy Skies [4.0] | 0 | 0 | （该 mod 未定义本地化 key） |
| 7 | Warship Girls Advisor | 18 | 0 | （该 mod 未被任何其他 mod 压掉本地化 key） |
| 8 | 吞食天地 | 0 | 0 | （该 mod 未定义本地化 key） |
| 9 | ! Immersive Energy Shield | 0 | 0 | （该 mod 未定义本地化 key） |
| 10 | Zeph's Better Borders | 0 | 0 | （该 mod 未定义本地化 key） |
| 11 | Special Effects Beautification | 0 | 0 | （该 mod 未定义本地化 key） |


## 7. 描述符与 replace_path

（无）

## 8. 加载顺序与统计

数组序即加载序，靠后者优先。「被覆盖」数值大说明该 mod 放得太靠前；「覆盖别人」大说明它在压别人。

| # | Mod | 文件 | 改原版 | 覆盖别人 | 被覆盖 | 冗余 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | UI Overhaul Dynamic | 815 | 317 | 0 | 3 | 20 | 正常 |
| 2 | UI Overhaul Dynamic - Extended Topbar | 28 | 0 | 3 | 1 | 20 | 正常 |
| 3 | 领袖培养小飞地 | 120 | 7 | 0 | 0 | 3 | 正常 |
| 4 | 联机用(需要放在UImod的下方） | 216 | 21 | 1 | 0 | 10 | 正常 |
| 5 | 群星：星海旗舰 | 483 | 27 | 0 | 0 | 1 | 正常 |
| 6 | Fancy Skies [4.0] | 69 | 18 | 0 | 0 | 0 | 正常 |
| 7 | Warship Girls Advisor | 346 | 0 | 0 | 0 | 0 | 正常 |
| 8 | 吞食天地 | 33 | 3 | 0 | 0 | 0 | 正常 |
| 9 | ! Immersive Energy Shield | 6 | 5 | 0 | 0 | 0 | 正常 |
| 10 | Zeph's Better Borders | 1 | 1 | 0 | 0 | 0 | 正常 |
| 11 | Special Effects Beautification | 192 | 62 | 0 | 0 | 8 | 正常 |

## 9. 请分析者给出

1. 第 4 节那些冲突，要按什么顺序调整才能真正生效（具体到「把 X 放到 Y 下面」）。
2. 第 5 节哪些值得改文件名或做兼容补丁，哪些可以接受现状。
3. 当前加载顺序有无明显放错位置的 mod。
4. 哪些看起来相关、但本报告因只做静态检查而发现不了的冲突。

本报告只做静态文件检查，不运行游戏。未覆盖：`.asset`/`.shader` 覆盖、脚本层作用域错误、运行时热加载差异等；`.yml` 本地化 key 覆盖已升级为独立扫描，见第 5bis 节。
