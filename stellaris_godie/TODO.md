# 大逃杀起源 + 入口门禁

## 背景

原版起源自带事件链会在大逃杀中干扰。新增专属起源作为唯一入口，且起源事件直接创建方舟舰+护卫舰队+转移人口+设首都，将 br.701 简化为仅移动舰队。

## 方案

`brstart.1`（`on_game_start_country` 触发，独立 namespace）在母星系创建方舟舰和护卫舰队、转移人口、设首都。之后模式选择/出生点选定流程不变，但 br.701 不再创建/转移/设首都，只移动已有舰队到出生点。

### 新增文件

| 文件 | 用途 |
|---|---|
| `common/governments/civics/br_origins.txt` | 定义 `origin_br_battle_royale` |
| `events/br_origin_events.txt` | 起源初始化事件 br.800 |

### 修改文件

| 文件 | 变更 |
|---|---|
| `common/on_actions/br_on_actions.txt` | `on_game_start_country` 加 br.800 |
| `events/br_origin_events.txt` | **新建**，namespace = brstart，起源事件 `brstart.1` |
| `events/br_pve_init_events.txt` | br.700/701 trigger + br.701 逻辑简化 |
| `events/br_start_events.txt` | br.500/504/505 入口门禁换 `has_origin` |
| `localisation/simp_chinese/br_battleroyale_l_simp_chinese.yml` | 加起源文本 |
| `TODO.md` | 更新状态 |

## 执行步骤

### Step 1 — 起源定义

`common/governments/civics/br_origins.txt`（新建目录+文件）：

```
origin_br_battle_royale = {
    is_origin = yes
    icon = "gfx/interface/icons/origins/origins_default.dds"
    picture = GFX_evt_signing
    potential = { always = yes }
    possible = { always = yes }
}
```

无 `random_weight` → AI 不会自动选此起源。

### Step 2 — 本地化

`origin_br_battle_royale:0 "大逃杀模式"`
`origin_br_battle_royale_desc:0 "宇宙基本常数正在被未知力量重写……"`

### Step 4 — 新增 brstart.1 起源事件（完整初始化）

新建 `events/br_origin_events.txt`，文件头 `namespace = brstart`。

`brstart.1` 承担原 br.701 的全部初始化工作（创建舰船、转移人口、设首都、奖励），仅留下 spawn 位置移动给 br.701。

```
# brstart.1：起源初始化 — 创建方舟舰+护卫、转移人口、设首都、奖励
country_event = {
    id = brstart.1
    hide_window = yes
    is_triggered_only = yes
    trigger = {
        is_ai = no
        has_origin = origin_br_battle_royale
    }
    immediate = {
        set_country_flag = br_player_country

        # 科技
        give_technology = { tech = tech_br_civilian_arkship message = no }
        refresh_auto_generated_ship_designs = yes

        # 保存首都
        capital_scope = {
            planet = { save_event_target_as = br_embarking_capital }
        }

        # 创建方舟舰（标记 fleet_flag 供 br.701 查找）
        create_fleet = {
            effect = {
                save_event_target_as = br_embarking_arkship
                set_owner = root
                set_fleet_flag = br_arkship_flag
                create_ship = {
                    random_existing_design = br_civilian_arkship_tier_1
                    effect = { initialize_arkship_starbase_effect = yes }
                }
            }
        }

        # 创建护卫舰队
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
                set_fleet_flag = br_escort_flag
                while = {
                    count = 10
                    create_ship = {
                        name = random
                        design = NAME_Dagger
                    }
                }
                assign_leader = last_created_leader
            }
        }

        # 转移人口：首都 → 方舟舰
        event_target:br_embarking_capital = {
            transfer_carrier = {
                source = this
                target = event_target:br_embarking_arkship
                transfer_ownership = no
                merge_pops = no
                destroy_colony = yes
            }
        }

        # 方舟舰设为首部
        event_target:br_embarking_arkship = {
            set_owner = root
            colony = {
                upgrade_colony_shelter = yes
                set_capital = yes
            }
        }

        # 奖励系统
        set_country_flag = br_reward_initialized
        add_relic = br_reward_relics
        change_country_flag = random
    }
}
```

### Step 5 — 更新 on_actions

`common/on_actions/br_on_actions.txt`，`on_game_start_country` 列表首行插入 `brstart.1`：

```
on_game_start_country = {
    events = {
        brstart.1
        br.500
        br.1
    }
}
```

### Step 6 — 入口门禁替换

#### br.500 trigger（br_start_events.txt:8-16）

```diff
 trigger = {
     is_ai = no
     NOT = { has_global_flag = br_start_settings_opened }
-    NOT = { has_country_flag = br_player_country }
+    has_origin = origin_br_battle_royale
 }
```

#### br.504 every_country filter（br_start_events.txt:192-201）

```diff
 limit = {
     is_ai = no
     NOT = { has_country_flag = br_player_replacement_scheduled }
-    NOT = { has_country_flag = br_player_country }
+    has_origin = origin_br_battle_royale
 }
```

#### br.505 trigger（br_start_events.txt:216-221）

```diff
 trigger = {
     is_ai = no
-    NOT = { has_country_flag = br_player_country }
+    has_origin = origin_br_battle_royale
 }
```

#### br.700 trigger — player arm（br_pve_init_events.txt:8-18）

```diff
 trigger = {
     OR = {
         is_country_type = br_void
         AND = {
             is_ai = no
-            NOT = { has_country_flag = br_player_country }
+            has_origin = origin_br_battle_royale
         }
     }
 }
```

#### br.700 every_country filter（br_pve_init_events.txt:455-465）

```diff
 limit = {
     is_ai = no
     has_country_flag = br_player_replacement_scheduled
     NOT = { has_country_flag = br_player_replaced }
-    NOR = { has_country_flag = br_player_country }
+    has_origin = origin_br_battle_royale
 }
```

#### br.701 trigger（br_pve_init_events.txt:478-487）

```diff
 trigger = {
     is_ai = no
     has_country_flag = br_player_replacement_scheduled
     NOT = { has_country_flag = br_player_replaced }
-    NOT = { has_country_flag = br_player_country }
+    has_origin = origin_br_battle_royale
 }
```

### Step 7 — 简化 br.701（仅移动舰队 + 房主设置）

br.701 仅做：选出生点、移动已有方舟舰和护卫舰队到出生点、房主设置、排程 br.507。
全部舰船创建、人口转移、设首都已由 brstart.1 完成。

```diff
 immediate = {
     set_country_flag = br_player_replaced
+    # 找已有方舟舰
+    random_owned_fleet = {
+        limit = { has_fleet_flag = br_arkship_flag }
+        save_event_target_as = br_embarking_arkship
+    }
+    # 找已有护卫舰队
+    random_owned_fleet = {
+        limit = { has_fleet_flag = br_escort_flag }
+        save_event_target_as = br_escort_fleet
+    }

     # 选出生点
     random_system = {
         limit = { has_star_flag = br_player_spawn_system }
         save_event_target_as = br_chosen_spawn_system
         star = { save_event_target_as = br_chosen_spawn_star }
     }

-    set_country_flag = br_player_country
-    give_technology = { tech = tech_br_civilian_arkship message = no }
-    refresh_auto_generated_ship_designs = yes
-    capital_scope = { planet = { save_event_target_as = br_embarking_capital } }
-    create_fleet = { ... }  # 含方舟舰创建+set_location
-    event_target:br_embarking_capital = { transfer_carrier = ... }  # 转移人口
-    event_target:br_embarking_arkship = { colony = { set_capital = yes } }  # 设首都
-    set_country_flag = br_reward_initialized
-    add_relic = br_reward_relics
-    change_country_flag = random
-    create_leader = { ... }
-    create_fleet = { ... }  # 护卫舰队
+    # 移动方舟舰到出生点
+    event_target:br_embarking_arkship = {
+        set_location = {
+            target = event_target:br_chosen_spawn_star
+            distance = 50
+            angle = random
+        }
+    }
+    # 移动护卫舰队到出生点
+    event_target:br_escort_fleet = {
+        set_location = {
+            target = event_target:br_chosen_spawn_star
+            distance = 80
+            angle = random
+        }
+    }

     # 房主设置（不变）
     if = {
         limit = { NOT { has_global_flag = br_pve_alliance_leader_set } }
         set_global_flag = br_pve_alliance_leader_set
         save_global_event_target_as = br_pve_alliance_leader
     }

     # 排程 br.507（不变）
     country_event = { id = br.507 days = 1 }
 }
```

## 不变的部分

- br.504 杀AI逻辑（`is_ai = yes` / `NOR { br_void, br_player_country }`）
- br.504 创建虚空国/扩圈排程
- br.700 选出生点逻辑（全部保留）
- br.507 二次清理
- br.702 联盟+敌对势力
- br.799 后备保障
- 所有内部事件（level_events/cycle_events 等）仍用 `has_country_flag = br_player_country`

## 回滚策略

Step 1-7 顺序执行。任一步失败则停止，`git checkout -- .` 恢复所有文件，报告失败详情。

## 新流程总览

```
on_game_start_country
  → brstart.1 [NEW] (创建方舟舰+护卫、转移人口、设首都、奖励、br_player_country)
  → br.500 (入口 now has_origin → 跳过已初始化)
    → br.501 (模式选择) → br.503 (速度选择)
      → br.504 (杀AI，虚空国，扩圈，标记 origin 玩家)
        → br.505 (路由) → br.700 (选出生点)
          → br.701 [仅移动] (方舟舰+护卫 移到出生点，房主设置)
            → br.507 (清理) → br.702 (联盟+敌对势力)
```

## 已完成

- PVE 国家类型重构（commit `20bea54`）
- 缩进格式化 + 模式选择标签（commit `5ac1e94`）
- 创建起源定义 + 起源事件 brstart.1 + 本地化
- `on_game_start_country` 接入 brstart.1（仅起源效果，不含 PVE 逻辑）
