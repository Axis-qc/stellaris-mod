# 技能系统重构计划：槽位标志替代 unlock 标志

## 核心思路

- **只用 6 个 slot 标志**记录玩家选了哪个选项：`br_skill_{active|passive|ultimate}_slot_{1|2}`
- **删除 18 个** `br_skill_xxx_unlocked` 技能解锁标志
- **删除 3 个** `br_xxx_slot_unlocked` 统一解锁标志
- **删除 3 个** `br_hero_core_xxx` 核心标志（只靠组件判断）
- **scripted_triggers 中核心过滤器去掉 flag**，只保留 `has_component`
- **技能效果事件** trigger 中 unlock flag → slot flag（核心过滤已由 scripted_trigger 覆盖）
- **本地化 loc** 中 `br_hero_core_xxx` → `any_owned_ship` + `has_component`

## 旧标志 → 新标志映射

### 删除的标志（24 个）

| 类别 | 旧标志 | 替代方案 |
|---|---|---|
| 核心标志 | `br_hero_core_power` | 不需要，`has_component` 判断 |
| 核心标志 | `br_hero_core_defense` | 不需要，`has_component` 判断 |
| 核心标志 | `br_hero_core_carrier` | 不需要，`has_component` 判断 |
| 统一解锁 | `br_active_slot_unlocked` | `NOR { br_skill_active_slot_1, br_skill_active_slot_2 }` |
| 统一解锁 | `br_passive_slot_unlocked` | `NOR { br_skill_passive_slot_1, br_skill_passive_slot_2 }` |
| 统一解锁 | `br_ultimate_slot_unlocked` | `NOR { br_skill_ultimate_slot_1, br_skill_ultimate_slot_2 }` |
| 技能解锁 | `br_skill_energy_overclock_unlocked` | `br_skill_active_slot_1` |
| 技能解锁 | `br_skill_weakness_scan_unlocked` | `br_skill_active_slot_2` |
| 技能解锁 | `br_skill_phase_shift_unlocked` | `br_skill_active_slot_1` |
| 技能解锁 | `br_skill_barrier_unlocked` | `br_skill_active_slot_2` |
| 技能解锁 | `br_skill_sortie_unlocked` | `br_skill_active_slot_1` |
| 技能解锁 | `br_skill_aat_unlocked` | `br_skill_active_slot_2` |
| 技能解锁 | `br_skill_combat_stack_unlocked` | `br_skill_passive_slot_1` |
| 技能解锁 | `br_skill_kill_stack_unlocked` | `br_skill_passive_slot_2` |
| 技能解锁 | `br_skill_structure_unlocked` | `br_skill_passive_slot_1` |
| 技能解锁 | `br_skill_field_unlocked` | `br_skill_passive_slot_2` |
| 技能解锁 | `br_skill_swarm_guard_unlocked` | `br_skill_passive_slot_1` |
| 技能解锁 | `br_skill_deck_maintenance_unlocked` | `br_skill_passive_slot_2` |
| 技能解锁 | `br_skill_fullfire_unlocked` | `br_skill_ultimate_slot_1` |
| 技能解锁 | `br_skill_final_volley_unlocked` | `br_skill_ultimate_slot_2` |
| 技能解锁 | `br_skill_collapse_unlocked` | `br_skill_ultimate_slot_1` |
| 技能解锁 | `br_skill_projection_unlocked` | `br_skill_ultimate_slot_2` |
| 技能解锁 | `br_skill_full_deck_unlocked` | `br_skill_ultimate_slot_1` |
| 技能解锁 | `br_skill_total_air_supremacy_unlocked` | `br_skill_ultimate_slot_2` |

### 保留的标志（6 个）

`br_skill_active_slot_1` / `br_skill_active_slot_2` / `br_skill_passive_slot_1` / `br_skill_passive_slot_2` / `br_skill_ultimate_slot_1` / `br_skill_ultimate_slot_2`

## 涉及文件清单（12 个）

### 第 1 步：基础触发器

#### `common/scripted_triggers/br_vanguard_skill_triggers.txt`

6 个核心过滤触发器去掉 `br_hero_core_xxx` flag 检查，只保留组件：

```
# 改前：
br_has_power_vanguard = {
    any_owned_ship = {
        is_ship_size = br_vanguard
        has_component = BR_VANGUARD_CORE_POWER
    }
    owner = { has_country_flag = br_hero_core_power }
}

# 改后：
br_has_power_vanguard = {
    any_owned_ship = {
        is_ship_size = br_vanguard
        has_component = BR_VANGUARD_CORE_POWER
    }
}
```

同理 `br_has_defense_vanguard` / `br_has_carrier_vanguard` / `country_has_power_vanguard` / `country_has_defense_vanguard` / `country_has_carrier_vanguard`

### 第 2 步：技能选择事件

#### `events/heroship_level_events.txt`

- **heroship.10**（主动槽 Lv2）：trigger 改 `NOR { br_skill_active_slot_1, br_skill_active_slot_2 }`；hidden_effect 删 unlock + slot_unlocked，只留 slot 标志
- **heroship.11**（被动槽 Lv4）：trigger 改 `NOR { br_skill_passive_slot_1, br_skill_passive_slot_2 }`；hidden_effect 同上
- **heroship.12**（大招槽 Lv6）：trigger 改 `NOR { br_skill_ultimate_slot_1, br_skill_ultimate_slot_2 }`；hidden_effect 同上

### 第 3 步：技能效果事件

核心过滤已由 `br_has_xxx_vanguard` scripted_trigger 覆盖，只需替换 unlock flag → slot flag。

#### `events/heroship_skill_power_events.txt`

| 事件 ID | 旧 trigger | 新 trigger | 备注 |
|---|---|---|---|
| heroship.1100（能量超频） | `br_skill_energy_overclock_unlocked` | `br_skill_active_slot_1` | 有 `br_has_power_vanguard` 过滤 |
| heroship.1101（弱点扫描） | `br_skill_weakness_scan_unlocked` | `br_skill_active_slot_2` | 有 `br_has_power_vanguard` 过滤 |
| heroship.1102（越战越勇） | `br_skill_kill_stack_unlocked` | `br_skill_passive_slot_2` | ⚠️ country_event 无核心过滤，需内联补充 `has_component` |
| heroship.1103（战意过载） | `br_skill_combat_stack_unlocked` | `br_skill_passive_slot_1` | 有 `br_has_power_vanguard` 过滤 |
| 后续火力全开/终末齐射 | `br_skill_fullfire/full_volley_unlocked` | `br_skill_ultimate_slot_1/2` | 有核心过滤 |

**heroship.1102 特殊处理**（替换后必须内联补充核心过滤）：
```
trigger = {
    has_country_flag = br_skill_passive_slot_2
    any_owned_ship = {
        is_ship_size = br_vanguard
        has_component = BR_VANGUARD_CORE_POWER
    }
    ...
}
```

#### `events/heroship_skill_defense_events.txt`

| 事件 ID | 旧 trigger | 新 trigger | 备注 |
|---|---|---|---|
| heroship.1200（相位偏移） | `br_skill_phase_shift_unlocked` | `br_skill_active_slot_1` | 有 `br_has_defense_vanguard` |
| heroship.1201（能量屏障） | `br_skill_barrier_unlocked` | `br_skill_active_slot_2` | 有 `br_has_defense_vanguard` |
| heroship.1202（结构强化） | `br_skill_structure_unlocked` | `br_skill_passive_slot_1` | ⚠️ 有 `owner = {}` 作用域 bug，需顺带修复（见下方） |
| heroship.1203（能量力场） | `br_skill_field_unlocked` | `br_skill_passive_slot_2` | 月度脉冲触发 |
| heroship.1204（力场初始化） | `br_skill_field_unlocked`（immediate 中） | `br_skill_passive_slot_2` | 由 1203 hidden_effect 调用 |
| 引力坍缩/力场投射 | `br_skill_collapse/projection_unlocked` | `br_skill_ultimate_slot_1/2` | 有核心过滤 |

#### `events/heroship_skill_carrier_events.txt`

| 事件 ID | 旧 trigger | 新 trigger | 备注 |
|---|---|---|---|
| heroship.1300（编队出击） | `br_skill_sortie_unlocked` | `br_skill_active_slot_1` | 有 `br_has_carrier_vanguard` |
| heroship.1301（防空阵型） | `br_skill_aat_unlocked` | `br_skill_active_slot_2` | 有 `br_has_carrier_vanguard` |
| heroship.1310（全甲板入口） | `br_skill_full_deck_unlocked` | `br_skill_ultimate_slot_1` | 有 `br_has_carrier_vanguard` |
| heroship.1331（无人机月度链） | `br_skill_swarm_guard_unlocked` / `br_skill_deck_maintenance_unlocked` | `br_skill_passive_slot_1` / `br_skill_passive_slot_2` | 月度脉冲触发，内部用 if 分支检查 |
| heroship.1335（航母 buff 处理） | `br_skill_swarm_guard_unlocked` / `br_skill_deck_maintenance_unlocked` | `br_skill_passive_slot_1` / `br_skill_passive_slot_2` | ⚠️ TODO 遗漏，内部 immediate 中检查 |
| 绝对制空 | `br_skill_total_air_supremacy_unlocked` | `br_skill_ultimate_slot_2` | 有核心过滤 |

### 第 4 步：UI 按钮

#### `common/button_effects/br_level_ui_hero_skill_buttons.txt`

- 删除 effect 中所有 `remove/set_country_flag = br_skill_xxx_unlocked` 互换逻辑
- 删除 `if { limit { has_country_flag = br_hero_core_xxx } }` 分支
- 只保留 slot 标志的互换：`remove_country_flag = br_skill_ultimate_slot_2` / `set_country_flag = br_skill_ultimate_slot_1`

### 第 5 步：本地化文本

#### `common/scripted_loc/br_level_ui_hero_skill_loc.txt`

`defined_text` 中每个 `text` 块的 trigger 从 flag 改为 `any_owned_ship` + `has_component`（约 18 处）：

```
# 改前：
trigger = { has_country_flag = br_hero_core_power }

# 改后：
trigger = {
    any_owned_ship = {
        is_ship_size = br_vanguard
        has_component = BR_VANGUARD_CORE_POWER
    }
}
```

#### `common/scripted_loc/br_vanguard_scripted_loc.txt`

**⚠️ 第二轮审查发现，52 处引用完全不在原计划中！**

该文件是先锋舰的技能名称/描述/计数的脚本化本地化，包含：
- **18 处** `defined_text` 中的技能名称 trigger（每个技能 unlock flag 一处）
- **12 处** 被动技能计数文本块的 `has_country_flag` 检查
- **6 处** 大招技能计数文本块的 `has_country_flag` 检查
- **约 16 处** 光环名称显示文本块的 `has_country_flag` 检查

全部需要将 `br_skill_xxx_unlocked` → 对应 slot flag。同时 `owner = { has_country_flag = ... }` 作用域需检查是否正确。

### 第 6 步：测试 edict

#### `common/edicts/br_test_skill_edicts.txt`

- `set/remove/has_country_flag = br_skill_xxx_unlocked` → 对应 slot 标志
- `set/remove/has_country_flag = br_hero_core_xxx` → 删除

### 第 7 步：核心选择事件

#### `events/heroship_events.txt`

heroship.101 三个 option 中的 `set_country_flag = br_hero_core_xxx` 删除

## 执行顺序

1. `br_vanguard_skill_triggers.txt` — scripted_trigger 去 flag
2. `heroship_level_events.txt` — 选择事件 trigger + hidden_effect
3. `heroship_skill_power_events.txt` — unlock flag → slot flag（注意 1102 补充核心过滤）
4. `heroship_skill_defense_events.txt` — unlock flag → slot flag（注意 1202 作用域 bug 修复 + 1204 补充）
5. `heroship_skill_carrier_events.txt` — unlock flag → slot flag（注意 1335 补充）
6. `br_level_ui_hero_skill_buttons.txt` — 删 unlock flag 互换逻辑
7. `br_level_ui_hero_skill_loc.txt` — `br_hero_core_xxx` → `has_component`
8. `br_vanguard_scripted_loc.txt` — unlock flag → slot flag（52 处）
9. `br_test_skill_edicts.txt` — 完全重写，直接 toggle slot 标志
10. `heroship_events.txt` — 删 `br_hero_core_xxx` 设置
11. `br_vanguard_auras.txt` — 清理注释中的旧标志（可选）
12. `br_variables_l_simp_chinese.yml` — 清理孤立本地化条目（可选）

## 需顺带修复的已有 bug

### heroship.1202 作用域 bug

`events/heroship_skill_defense_events.txt` 中 heroship.1202 是 `country_event`，但 trigger 里用了 `owner = { has_country_flag = ... }`。country_event 的 scope 已经是国家，`owner` 无效，flag 检查从未生效。重构时顺带修复：

```
# 改前（bug）：
trigger = {
    country_has_defense_vanguard = yes
    owner = {
        has_country_flag = br_skill_structure_unlocked
    }
}

# 改后：
trigger = {
    country_has_defense_vanguard = yes
    has_country_flag = br_skill_passive_slot_1
}
```

## 风险点

1. **heroship.1102 核心过滤遗漏** — 替换后必须内联补充 `has_component` 检查
2. **测试 edict 重置功能** — 需完全重写，去掉 `br_hero_core_xxx` 路由，直接 toggle slot 标志，同时保留 `country_event` 调用（如结构增幅刷新）
3. **heroship.1335 遗漏** — 航母被动 buff 内部 immediate 中的 unlock flag 也需替换
4. **heroship.1204 遗漏** — immediate 中的 `br_skill_field_unlocked` 也需替换
5. **br_vanguard_scripted_loc.txt 52 处遗漏** — 第二轮审查发现，技能名称/描述/计数文本全部引用旧 unlock flag，必须同步替换
6. **scripted_loc 18 处替换** — 需逐一替换，不能只改一处示例
