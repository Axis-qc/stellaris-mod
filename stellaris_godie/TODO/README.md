# br 驿站（Waystation）子系统 —— 备用暂存说明

> 状态：**STANDBY（备用）**。本目录 `_waystation_standby/` 下的内容**当前不加载进游戏**
> （下划线前缀目录不是 Stellaris 的加载路径，游戏不会读取）。
> 功能已实测可用（普通帝国研究科技 → 常规工程舰建造 → 转星港成功），但因需要覆盖原版共享触发器、
> 且识别链路有多处硬编码门槛，暂时搁置，待设计定型后再决定是否接入。

## 一、这是什么

给 **非游牧的普通帝国** 用的「驿站（Waystation）」——原版《Nomads》DLC 的驿站是游牧专属
（`is_nomadic = yes` 闸门），普通帝国用不了。本子系统自建一套 br_ 前缀的驿站，
让普通帝国也能建造、使用驿道网络。

## 二、文件清单（8 个）

| 备用文件（本目录） | 启用时移回位置 | 内容 |
|---|---|---|
| `common_ship_sizes_br_waystation_sizes.txt` | `common/ship_sizes/br_waystation_sizes.txt` | 船体 `br_starbase_waystation_1`（prereq=tech_br_waystation，区段仅 core，4 大型槽） |
| `common_section_templates_br_waystation_sections.txt` | `common/section_templates/br_waystation_sections.txt` | 核心区段 `BR_WAYSTATION_STAGE_1`（large_utility_slots=4） |
| `common_starbase_levels_br_waystation_levels.txt` | `common/starbase_levels/br_waystation_levels.txt` | 星港等级 `br_starbase_level_waystation_1`（2 模块槽，1 级） |
| `common_megastructures_br_waystation_megastructure.txt` | `common/megastructures/br_waystation_megastructure.txt` | 巨型结构 `br_waystation_megastructure`（starbase=br 等级，potential=tech_br_waystation，普通工程舰可造，on_build_complete 仅移除巨型结构本体） |
| `common_scripted_triggers_br_waystation_triggers.txt` | `common/scripted_triggers/br_waystation_triggers.txt` | **覆盖** `is_waystation_starbase` / `is_waystation_ship`（保留原版判断 + 加 br 分支） |
| `common_technology_br_waystation_tech.txt` | `common/technology/br_waystation_tech.txt` | 科技 `tech_br_waystation`（前置 tech_mega_engineering，普通帝国专属，+2 星港容量） |
| `localisation_br_waystation_l_simp_chinese.yml` | `localisation/simp_chinese/br_waystation_l_simp_chinese.yml` | 本地化（科技/巨型结构/船体/组件名，UTF-8 BOM） |
| `common_component_templates_br_waystation_components.txt` | 合并回 `common/component_templates/br_component_templates.txt` 末尾 | 组件 `BR_WAYSTATION_REACTOR`(power_core) + `BR_WAYSTATION_COMBAT_COMPUTER`(combat_computers) |

> 注意：最后一项是**从 `br_component_templates.txt` 里抽出来的**（该文件里还有主宰/方舟的活跃组件，不能整搬）。启用时把这两个组件块合并回去即可，当前该文件已恢复为只有活跃组件。

## 三、识别链路与「覆盖原版」的取舍

- **驿道 UI / 驿站模块 / 驿道网络**：全靠 `is_waystation_starbase` / `is_waystation_ship` 两个触发器识别（原版 150+ 处引用）。
- 本子系统**覆盖**了这两个触发器（保留原版判断 + OR br 分支），原版游牧驿站不受影响。
- 备选方案（未做）：建 br 专属星港类型 `is_waystation = yes` 可免覆盖启用 UI，但驿道网络
  的 `is_waystation_ship`（`is_ship_size = starbase_waystation_*` 等值判断）天然不可能对 br 船体成立，逃不掉覆盖。

## 四、踩坑史（三次尝试的根因，勿重蹈）

1. **覆盖原版 `waystation_megastructure`** → 败。
   - 坑①：原版船体 `starbase_waystation_1.prerequisites = tech_waystation_1`（游牧专属），
     非游牧无有效星港设计 → 转星港报 `invalid starbase design for ship size`。
   - 坑②：原版 `on_build_complete` 里 `prev` 作用域对常规工程舰建造不存在 → 报 `Invalid context switch [prev]`。
2. **godie 自建 br 一套（船体/区段/等级/巨型结构/触发器）** → 仍败。
   - 坑③：`ship_uses_starbase_components` 触发器（`07_scripted_triggers_ships.txt:151`）是**硬编码船体名单**，
     不含 br 船体 → 原版星港反应堆/战斗电脑对其不可用 → 自动设计填不满 `power_core/combat_computers` → 建造完成瞬间消失。
3. **补 br 专属组件** → 成功（本子系统当前状态）。
   - 按 mod 的 `BR_DOMINATOR_*` 组件套路，写 `BR_WAYSTATION_REACTOR` + `BR_WAYSTATION_COMBAT_COMPUTER`，
     让 br 船体自动设计能填满必需组件集。传感器用常规组件（无该门槛）即可。
   - 实测：普通帝国研究「星际驿站工程」→ 常规工程舰建造 → 转星港成功、可装模块、出驿道 UI。

## 五、后续待办（重新启用时）

- 当前只有 **1 级**（核心段仅 core、2 模块槽）。2/3 级升级需补：br 船体/区段/等级 + 升级链 + 对应 2/3 级组件。
- 2/3 级涉及 `has_starbase_size >= starbase_waystation_2/3` 等硬编码尺寸比较（AI 预算、巨型结构
  「驿道上需 2 级驿站」条件、`nomads_effects` 升级检查等），需一并处理 br 分支。
- 可先测「自然尺寸识别」：删掉 `is_waystation_starbase` 覆盖试一局，若 br 星港尺寸天然
  `>= starbase_waystation_1`，则 UI + 模块可零覆盖，只留 `is_waystation_ship` 给网络。
