# PVE 生存模式 BOSS 虚空裂隙体系实施计划

## 一、新增文件

### 1. `common/static_modifiers/br_countrybuff.txt` — 末尾追加
在现有文件末尾追加每道虚空裂隙的基础强化值。用 `multiplier` 乘 `br_rift_count` 变量来叠加：
```
br_pve_rift_buff = {
    ship_fire_rate_mult = 0.10
    ship_hull_add = 500
    ship_armor_add = 300
    ship_shield_add = 300
}
```

### 2. `common/scripted_effects/br_pve_rift_spawn.txt`
新增效果 `br_spawn_rift_fleet`：
- 作用域：`event_target:br_pve_enemy_country`（天灾国）
- 目标星系通过 `event_target:br_spawn_tmp` 传入（event_target 本身就是 solar_system 域）
- 计算天灾舰数量：`small = cycle × 2`、`medium = cycle`、`large = max(1, cycle / 2)`
- 设置变量后调用 `br_crisis_create_fleet`（复用现有随机编队流程：10% 纯肃正 / 10% 纯恶魔 / 10% 纯虫子 / 10% 纯女王 / 40% 混合编队）

---

## 二、修改文件

### 1. `events/br_pve_enemy_boss_events.txt`

#### br.900（初始化）— 追加末尾
- `event_target:br_pve_enemy_country` 设变量 `br_boss_spawn_cycle = 1`、`br_rift_count = 0`
- 排程 `country_event = { id = br.920 days = 360 }`

#### br.912（BOSS 跳跃）— 功能拆分
跳跃阶段**只搬迁舰队 + 通知**，开辟虚空裂隙延迟到战斗结束后：
1. 全图随机选目标星系
2. 搬迁 BOSS 舰队 + 护卫舰队到目标星系（现有逻辑保持）
3. 通知玩家 BOSS 已跳跃（保持）
4. 排程 **新事件 br.915** 检查该星系战斗是否结束（90 天后），用于开辟裂隙
5. **原有 br.911 追击排程保持**（10 天后追击）

#### br.915（新）— 虚空裂隙建立（战斗结束后）
```
country_event id = br.915 is_triggered_only

trigger: br_mode_pve, exists br_pve_enemy_country

immediate:
  A. event_target:br_pve_enemy_country 的 BOSS 舰队所在星系
  B. 检查该星系是否有和天灾国敌对的舰队（仍在交战）
     if = {
       limit = {
         any_fleet_in_system = {
           owner = { is_hostile = event_target:br_pve_enemy_country }
         }
       }
       # 还在打 → 90 天后再检查
       country_event = { id = br.915 days = 90 }
     }
     else = {
       # 清空了 → 开辟虚空裂隙（随机四天灾之一）
       random_list = {
           25 = { create_starbase = { size = starbase_swarm owner = event_target:br_pve_enemy_country } }
           25 = { create_starbase = { size = starbase_exd owner = event_target:br_pve_enemy_country } }
           25 = { create_starbase = { size = starbase_ai owner = event_target:br_pve_enemy_country } }
           25 = { create_starbase = { size = starbase_synth_queen owner = event_target:br_pve_enemy_country } }
       }
       set_star_flag = br_void_rift
       创建 3 队守卫舰队（br_rift_guard, aggressive）
       br_rift_count += 1
       remove_modifier + add_modifier { multiplier = value:br_rift_count } 叠加强化
       create_message 通知"虚空裂隙已在星系中开辟"
     }
```

#### br.920（新）— 年度刷敌（舰队从裂隙中涌现）
```
country_event id = br.920 is_triggered_only

trigger: br_mode_pve, exists br_pve_enemy_country

immediate:
  A. BOSS 位置刷敌
     → event_target:br_pve_enemy_country 的 random_owned_fleet { limit = { has_fleet_flag = br_boss_fleet } }
        → solar_system 作用域（BOSS 舰队所在星系）→ save_event_target_as = br_spawn_tmp
     → event_target:br_pve_enemy_country 调用 br_spawn_rift_fleet
  B. 每道裂隙位置刷敌
     → every_system { limit = { has_star_flag = br_void_rift } }
         → 当前已是 system 作用域 → save_event_target_as = br_spawn_tmp
         → event_target:br_pve_enemy_country 调用 br_spawn_rift_fleet
  C. 新刷舰队 aggressive_stance = yes
  D. br_boss_spawn_cycle += 1（上限 100）
  E. 自排程 br.920 days = 360
```

> 注：必须经 `br_spawn_tmp` 传参，因为 `br_crisis_create_fleet` 内部通过 `set_location = { target = event_target:br_spawn_tmp }` 定位刷敌星系。

#### br.914（新）— 虚空裂隙被摧毁
```
country_event id = br.914 is_triggered_only

trigger: br_mode_pve, exists br_pve_enemy_country
→ 由 on_starbase_disabled 触发，from = 被摧毁的恒星基地

immediate:
  A. if { limit = { from = { has_star_flag = br_void_rift } } }：
     └─ from 星系 remove_star_flag = br_void_rift
     └─ br_rift_count -= 1（保底 0）
     └─ 强化更新：`remove_modifier = br_pve_rift_buff` + `add_modifier { modifier = br_pve_rift_buff days = -1 multiplier = value:br_rift_count }`
     └─ create_message 通知玩家"虚空裂隙已关闭"
```

#### br.901（BOSS 击杀）— 全清
胜利逻辑末尾追加：
```
event_target:br_pve_enemy_country = {
    remove_modifier = br_pve_rift_buff
    clear_variable = br_rift_count
    every_owned_fleet = { destroy_fleet = yes }
    every_owned_starbase = { destroy_starbase = yes }
}
every_system = { remove_star_flag = br_void_rift }
```

### 2. `common/on_actions/br_on_actions.txt`
`on_starbase_disabled` 节点添加 br.914 触发

### 3. `localisation/simp_chinese/br_pve_l_simp_chinese.yml`
新增本地化：
- `br.920.toast` — "虚空裂隙在 §H[星系名]§! 中涌现出增援舰队"
- `br.914.toast` — "§H[星系名]§! 的虚空裂隙已被关闭，BOSS 失去一层强化"
- `br.915.toast` — "§H[星系名]§! 中开辟了一道虚空裂隙"
- `br_pve_rift_buff` — modifier 名与描述

---

## 三、数据流

```
br.900
  ├─ br_boss_spawn_cycle = 1
  ├─ br_rift_count = 0
  └─ → br.920（360天后）

br.912（每5年跳跃）
  ├─ BOSS 跳星系 → 自动开战
  ├─ 排程 br.915（90天后开辟裂隙）
  └─ → br.911（10天后追击）

br.915（跳跃90天/战斗结束后）
  ├─ 星系有敌对舰队？→ 再等90天
  └─ 已清空 → 开辟裂隙
      ├─ br_rift_count++
      ├─ 叠加强化
      └─ 通知玩家

br.920（每年）
  ├─ BOSS 位置刷敌（cycle×2/cycle/cycle/2）
  ├─ 每道裂隙位置刷敌（相同数量）
  ├─ 全部 aggressive
  ├─ cycle++
  └─ → br.920（360天后）

br.914（裂隙被拆）
  ├─ 清除标记、br_rift_count--
  └─ remove_modifier + add_modifier { multiplier = value:br_rift_count } 重算强化

br.901（BOSS 死）
  ├─ 全清舰队 + 基地
  └─ 清除所有裂隙标记
```

---

## 四、难度曲线

| 年数 | cycle | BOSS 位置 | 每裂隙 | 3次跳跃后（4裂隙） |
|---|---|---|---|---|
| 1 | 1 | 小2 | 小2 | — |
| 5 | 5 | 小10+中5+大2 | 小10+中5+大2 | — |
| 10 | 10 | 小20+中10+大5 | 小20+中10+大5 | ×4裂隙≈800舰 |
| 15 | 15 | 小30+中15+大7 | 小30+中15+大7 | ×5裂隙→指数级 |

待确认后开始实施。
