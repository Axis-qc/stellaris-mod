# Stellaris Modding 已验证机制参考

> 所有内容均来自原版游戏文件验证，标注了文件路径和行号。

---

## 一、关键 modifier 一览

### 1. `ship_fire_rate_mult` — 射速倍率

| 来源 | 文件 | 行号 | 值 |
|---|---|---|---|
| 指挥官特质 | `common/static_modifiers/00_static_modifiers.txt` | 1283 | `0.03` |
| 负值范例 | 同上 | 1508 | `-0.05` |
| 高值范例 | `22_static_modifiers_machine_age.txt` | 73 | `1.5` |
| 极端负值 | `02_static_modifiers.txt` | 996 | `-0.5` |

**用法**：`ship_fire_rate_mult = 0.4` 表示 +40% 射速。

### 2. `ship_weapon_damage` — 武器伤害（加算）

| 来源 | 文件 | 行号 | 值 |
|---|---|---|---|
| 大将难度 | `common/static_modifiers/00_static_modifiers.txt` | 181 | `0.50` |
| 负值 | 同上 | 219 | `-0.25` |
| 精英舰船等级 | 同上 | 1425 | `0.4` |
| 极端高值 | `01_static_modifiers.txt` | 454 | `8` |

**用法**：`ship_weapon_damage = 0.01` 表示 +1% 武器伤害。注意这是加算无 `_mult` 后缀。

### 3. `ship_hull_regen_add_perc` — 每日船体回复百分比

| 来源 | 文件 | 行号 | 值 |
|---|---|---|---|
| 再生组件（标准） | `common/component_templates/00_utilities_aux.txt` | 137 | `0.05` |
| 再生组件（高级） | 同上 | 356 | `0.10` |
| 再生组件（顶级） | 同上 | 534 | `0.25` |
| **负值范例** | `common/component_templates/00_leviathans_utilities.txt` | 163 | `-1.25` |
| 恒星基地光环（负值） | `common/component_templates/00_starbase_building_auras.txt` | 178 | `-0.3` |
| 生物起源（负值） | `common/static_modifiers/23_static_modifiers_biogenesis.txt` | 1000 | `-0.1` |

**关键结论**：负值完全可用，`-0.01` = 每日掉 1% 最大船体。原版多处使用负值实现 debuff。

### 4. `ship_hull_damage_mult` — 船体伤害倍率

| 来源 | 文件 | 行号 | 值 |
|---|---|---|---|
| 虚空蠕虫 | `21_static_modifiers_grand_archive.txt` | 26 | `2.5` |
| 黑色针刺 | 同上 | 456 | `-0.25` |

使用稀少，但确认存在。

---

## 二、on_action 事件钩子

### `on_ship_destroyed_perp` — 舰船被击杀时触发

**文件**：`common/on_actions/00_on_actions.txt` 第 1368-1410 行

**Scope 定义**：
```
This       = 击杀者所属国家
From       = 被击杀者所属国家
FromFrom   = 击杀者舰船 (ship scope)
FromFromFrom = 被击杀的舰船 (ship scope)
```

**原版已注册事件举例**：`leviathans.1016`, `crisis.1283`, `paragon_2.1005`, `grand_archive.1050` 等 30+ 个。

**事件中可对 `fromfrom` 使用的操作**：
- `is_ship_size = xxx`
- `has_component = xxx`
- `has_fleet_flag = xxx`
- `has_trait = xxx`
- `modify_species = { ... }`
- `location = fromfrom` (作为位置引用)

### `on_fleet_combat_joined_attacker` / `on_fleet_combat_joined_defender`

**文件**：`common/on_actions/00_on_actions.txt` 第 3953-3977 行

**Scope 定义**：
- Attacker：`This = 攻击方舰队`, `From = 被攻击方舰队`
- Defender：`This = 被攻击方舰队`, `From = 攻击方舰队`

---

## 三、事件命令

### `damage_ship` — 直接对舰船造成伤害

已经原版多处验证可用：

| 文件 | 行号 | 用法 |
|---|---|---|
| `common/inline_scripts/ship_components/collateral_damage.txt` | 15 | `damage_ship = $DAMAGE$` |
| `common/scripted_effects/biogenesis_effects.txt` | 2370 | `damage_ship = @behemoth_superweapon_damage` |
| `events/cosmic_storms_events_1.txt` | 809 | `damage_ship = value:storm_ship_damage_received` |
| `events/grand_archive_events.txt` | 7558 | `damage_ship = local_damage_value` |

可配合 `reduce_shield` 同时扣护盾。

### `repair_percentage` — 按百分比回复船体

| 文件 | 行号 | 用法 |
|---|---|---|
| `events/leviathans_events_2.txt` | 766 | `repair_percentage = 0.075` |
| `events/biogenesis_crisis_events.txt` | 815 | `repair_percentage = 0.2` |
| `events/grand_archive_events.txt` | 7456 | `repair_percentage = root.local_heal_value` (动态值) |

### `repair_armor_percentage` / `repair_shield_percentage`

同样存在，用法相同，分别回复装甲和护盾百分比。

---

## 四、modifier 操作模式

### `add_modifier` + `days = -1` — 永久 modifier

**文件**：`events/crime_events.txt`（大量使用）

```starlang
add_modifier = { modifier = "criminal_underworld" days = -1 }
```

`days = -1` 表示永不过期。其他文件中同样大量使用。

### `mult` 参数 — modifier 动态倍率

**文件**：`common/scripted_effects/02_machine_age_effects.txt` 第 2027 行

```starlang
add_modifier = {
    modifier = synth_queen_regen_debuff
    days = -1
    mult = 2
}
```

也支持 `mult = variable_name` 使用变量值作为倍率，本项目已在使用（如 `mult = br_vanguard_power_combat_stack`）。

### `remove_modifier` — 移除 modifier

标准模式（`common/scripted_effects/00_scripted_effects.txt` 第 1719 行）：

```starlang
if = {
    limit = { has_modifier = xxx }
    remove_modifier = xxx
}
```

---

## 五、scripted_action 组件字段

**参考文件**：`common/component_templates/00_scripted_action_components.txt`

完整字段列表（在 `utility_component_template` 内）：

| 字段 | 说明 |
|---|---|
| `scope = self/planet` | 作用域 |
| `possible = { ... }` | 按钮可见条件 |
| `button_visible = { ... }` | 按钮是否显示 |
| `button_clickable = { ... }` | 按钮是否可点击（灰色/亮色） |
| `finished = { ... }` | 标记 action 完成的 flag 条件 |
| `name = on_xxx` | 触发时执行的 on_action 名称 |
| `tooltip = xxx` | 按钮 tooltip 文本 key |
| `icon = GFX_xxx` | 按钮图标 |
| `icon_selected = GFX_xxx` | 按钮选中态图标 |
| `on_cancel = on_xxx` | 取消时的回调 on_action |
| `activity_key = xxx` | 进度条文本 key |
| `context_menu_name = xxx` | 右键菜单名称 key |
| `progress_activity_key = xxx` | 进行中文本 key |
| `required_progress = N` | 所需进度值 |
| `cooldown = N` | 冷却天数 |
| `slot = N` | 按钮槽位编号 |

---

## 六、常用 scope 操作

### 舰船 scope (`is_ship_size`, `has_component`)

```starlang
any_owned_ship = {
    is_ship_size = br_vanguard
    has_component = BR_VANGUARD_CORE_POWER
}
```

### 舰队 scope (`has_fleet_flag`, `set_fleet_flag`)

```starlang
if = {
    limit = { NOT = { has_fleet_flag = br_overclock_active } }
    set_fleet_flag = br_overclock_active
}
```

### 国家 scope (`has_country_flag`, `set_country_flag`)

```starlang
owner = { has_country_flag = br_skill_self_repair_unlocked }
```

### 变量操作

```starlang
set_variable = { which = br_vanguard_kill_count value = 0 }
change_variable = { which = br_vanguard_kill_count value = 1 }
check_variable = { which = br_vanguard_kill_count value < 50 }
```

### 舰船 modifier 施加

```starlang
add_modifier = {
    modifier = br_vanguard_power_energy_overclock
    days = 10
}
```

---

## 七、本项目已实现的模式速查

| 功能 | 事件 ID | 文件 | 模式 |
|---|---|---|---|
| 自修技能（主动） | `br.1210` | `br_dominator_action_events.txt` | `repair_percentage = 1` |
| 战意过载（被动） | `br.1211`/`br.1212` | 同上 | 战斗加入初始化 + 每日叠层 + `mult` 动态 modifier |
| 母舰光环切换 | `br.1201` | 同上 | fleet flag + 星系范围 `add_modifier` |
| 杀敌经验 | `reward.6201` | `reward_core_events.txt` | `on_ship_destroyed_perp` + 按尺寸加经验 |
| 核心选择 | `reward.6101` | `reward_core_events.txt` | country flag 门控 + 技能解锁 |
| 脚本化文本 | `GetBRVanguardSkillActive` | `br_vanguard_scripted_loc.txt` | `defined_text` 按 flag 切换显示 |
