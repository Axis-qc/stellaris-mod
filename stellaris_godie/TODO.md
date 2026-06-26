# PVE 模式：国家类型重构 + 方舟舰迁移计划

## 背景

自定义 `country_type`（`br_player_pvp`/`br_player_pve`）的模块配置与原版不兼容，导致方舟舰殖民地的建筑和岗位异常。新版本原版国家类型已支持 `has_capital = no` 等属性，不再需要自定义玩家国家类型。

**先只改 PVE，PVP 后续再做。**

## 方案

1. **标注废弃** 3 个自定义玩家国家类型（`br_player`、`br_player_pvp`、`br_player_pve`），暂不删除
2. **PVE 初始化流程改为**：在原版国家上直接操作，用 `transfer_carrier` 将人口迁移到方舟舰，方舟舰设为首都
3. **所有 `is_country_type` 检查改为 `has_country_flag = br_player_country`**

## 涉及文件（PVE 相关）

### 第 1 步：标注国家类型为废弃

#### `common/country_types/br_country_types.txt`

在 `br_player`、`br_player_pvp`、`br_player_pve` 上方加注释 `# [废弃]`，暂不删除。

### 第 2 步：重写 PVE 初始化事件

#### `events/br_pve_init_events.txt` — br.701（第 478-663 行）

**改后流程**（去掉 `create_country`/`set_player`，所有效果直接在 root 上执行）：

```
immediate = {
    set_country_flag = br_player_replaced

    # 随机选择出生点
    random_system = { limit = { has_star_flag = br_player_spawn_system }
        save_event_target_as = br_chosen_spawn_system
        star = { save_event_target_as = br_chosen_spawn_star }
    }

    # 标记为玩家国家
    set_country_flag = br_player_country

    # 给科技确保方舟舰设计可用
    give_technology = { tech = tech_br_civilian_arkship message = no }
    refresh_auto_generated_ship_designs = yes

    # 保存首都星球引用
    capital_scope = { planet = { save_event_target_as = br_embarking_capital } }

    # 在出生星系创建方舟舰
    create_fleet = {
        effect = {
            set_owner = root
            create_ship = {
                random_existing_design = br_civilian_arkship_tier_1
                effect = {
                    save_event_target_as = br_embarking_arkship
                    initialize_arkship_starbase_effect = yes
                }
            }
            set_location = { target = event_target:br_chosen_spawn_star distance = 50 angle = random }
        }
    }

    # 迁移人口：首都星球 → 方舟舰（跨星系）
    event_target:br_embarking_capital = {
        transfer_carrier = {
            source = this
            target = event_target:br_embarking_arkship
            transfer_ownership = no
            merge_pops = no
            destroy_colony = yes
        }
    }

    # 方舟舰设为首都
    event_target:br_embarking_arkship = {
        set_owner = root
        colony = { upgrade_colony_shelter = yes set_capital = yes }
    }

    # 设置房主（仅首位玩家）
    if = { limit = { NOT = { has_global_flag = br_pve_alliance_leader_set } }
        set_global_flag = br_pve_alliance_leader_set
        save_global_event_target_as = br_pve_alliance_leader
    }

    # 初始化奖励系统（原 create_country effect 块中的效果）
    set_country_flag = br_reward_initialized
    add_relic = br_reward_relics
    change_country_flag = random

    # 创建初始舰队（护卫）——作用域为 root，不再经 br_new_player_country 中转
    create_leader = {
        class = commander
        species = owner_main_species
        name = "BR_ESCORT_COMMANDER"
        skill = 3
    }
    create_fleet = {
        name = "BR_ESCORT_FLEET"
        effect = {
            set_owner = root
            while = {
                count = 10
                create_ship = {
                    name = random
                    design = NAME_Dagger
                }
            }
            assign_leader = last_created_leader
            set_location = {
                target = event_target:br_chosen_spawn_star
                distance = 80
                angle = random
            }
        }
    }

    # 排程后续
    country_event = { id = br.507 days = 1 }
}
```

> 注意：`set_graphical_culture = root` 不迁移，因为重构后 root 本身就是原版国家，已有图形文化。

#### `events/br_pve_init_events.txt` — br.700（第 4-475 行）

trigger 中 `is_country_type = br_void` 保留。3 处 NOR 块中的 `is_country_type = br_player / br_player_pvp / br_player_pve` 改为 `has_country_flag = br_player_country`：
- 第 13-17 行（trigger 入口）
- 第 464-468 行（every_country 遍历过滤）
- 第 488-492 行（br.701 的 trigger，注意此处属于 br.701 但紧接在 br.700 的 every_country 循环中）

#### `events/br_pve_init_events.txt` — br.702（第 666-781 行）

3 处 `is_country_type = br_player_pve` → `has_country_flag = br_player_country`：
- 第 671 行（trigger）
- 第 682 行（every_country 遍历过滤）
- 第 764 行（every_country 遍历过滤）

#### `events/br_pve_init_events.txt` — br.799（第 784-841 行）

2 处 `is_country_type = br_player_pve` → `has_country_flag = br_player_country`：
- 第 790 行（trigger）
- 第 829 行（every_country 遍历过滤）

### 第 3 步：修改启动事件中的过滤条件

#### `events/br_start_events.txt`

**3.1 替换 NOR 块**（`NOR { is_country_type = br_player / br_player_pvp / br_player_pve }` → `NOR { has_country_flag = br_player_country }`）：
- br.500 trigger（第 13-17 行）
- br.504（第 120-125 行，第 201-205 行）
- br.505 trigger（第 223-227 行）
- br.507 immediate 内（第 307-311 行，第 321-325 行）

> 注意：br.507 第 321-325 行 NOR 块同时包含 `is_country_type = br_void`，替换后应为 `NOR { is_country_type = br_void, has_country_flag = br_player_country }`，即保留 `br_void` 的排除。

**3.2 br.507 trigger（第 271-275 行）**：`OR { is_country_type = br_player_pve / br_player_pvp }` → `has_country_flag = br_player_country`

> 注意：重构后 PVE 国家不再有 `br_player_pve` 类型，br.507 的 trigger 若保留 `is_country_type` 检查会导致 PVE 路径失效。PVP 初始化（br.600）也设置了 `br_player_country` flag，所以统一改为 flag 检查即可。

### 第 4 步：替换所有 PVE 相关文件中的 `is_country_type` 检查

| 文件 | 处数 | 替换内容 |
|---|---|---|
| `events/br_level_events.txt` | 19 | `is_country_type = br_player_pve` → `has_country_flag = br_player_country` |
| `events/br_countrybuff_events.txt` | 3 | 同上（第 43、57、297 行） |
| `events/br_countrybuff_events.txt` | 1 | `is_country_type = br_player_pvp` → `has_country_flag = br_player_country`（第 298 行，br.1015 trigger，与第 297 行在同一 OR 块中） |
| `events/br_cycle_events.txt` | 3 | `is_country_type = br_player_pve` → `has_country_flag = br_player_country` |
| `events/br_pve_reinforce_events.txt` | 4 | 同上 |
| `events/br_pve_enemy_spawn_rings.txt` | 4 | 同上 |
| `events/br_pve_enemy_boss_events.txt` | 2 | 同上 |
| `events/br_level_ui_events.txt` | 1 | 同上（第 12 行；第 34 行已注释跳过） |
| `events/reward_exploration_events.txt` | 1 | 同上 |
| `common/edicts/br_test_skill_edicts.txt` | 2 | 同上 |
| `common/scripted_actions/br_vanguard_actions.txt` | 2 | 同上（第 16 行 `br_player_pve`，第 17 行 `br_player_pvp`） |
| `events/br_pve_init_events.txt` | 8 | 同上（已在第 2 步覆盖） |
| `events/br_pvp_init_events.txt` | 2 | `is_country_type = br_player_pve` → `has_country_flag = br_player_country`（第 15、151 行，br.600/601 trigger 中的 PVE 过滤） |

> 已注释的行（`br_level_edicts.txt` 第 13 行、`br_level_ui_events.txt` 第 34 行、`br_ship_sizes.txt` 第 117 行）不修改。设计文档（`设计文档\核心-航母.md`）不修改。

## 执行顺序

1. `common/country_types/br_country_types.txt` — 标注废弃注释
2. `events/br_pve_init_events.txt` — 重写 br.700/701/702/799
3. `events/br_start_events.txt` — 修改过滤条件
4. 其余 10 个文件 — 批量替换 `is_country_type = br_player_pve` → `has_country_flag = br_player_country`

## 已验证

- `transfer_carrier` 可在非游牧国家上正常工作
- `transfer_carrier` 支持跨星系迁移
- `random_existing_design = br_civilian_arkship_tier_1` 配合 `give_technology` + `refresh_auto_generated_ship_designs` 可正常创建方舟舰
