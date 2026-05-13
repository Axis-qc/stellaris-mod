---
name: stellaris-modder
description: 群星 (Stellaris) 模组开发助手。覆盖事件脚本、common 系统（政策/科技/特性/modifier/on_actions 等）以及本地化文件的编写、修改与校验。当用户需要编写群星 mod 事件、添加科技或政策、定义 modifier、编写 on_actions、添加本地化文本、或讨论群星 mod 脚本语法时，使用此技能。
---

# 群星 Mod 开发

## 关键路径

- 项目目录（mod 开发）：`C:\Users\hp\Documents\Paradox Interactive\Stellaris\mod`
- 游戏原版目录：`G:\SteamLibrary\steamapps\common\Stellaris`
- 错误日志：`%USERPROFILE%\Documents\Paradox Interactive\Stellaris\logs\error.log`

## 工作流程

- **禁止擅动**：只有用户说"开始实施"四个字才视为执行授权，任何其他表述（包括"开始"、"干吧"、"执行"、"直接修改"等）均归为讨论修改范畴，不可进行文件写入。无"开始实施"授权时，保持沟通与研究状态，只读不写。
- **兼容性先问**：涉及语法的版本兼容性（新旧版本语法差异、是否需兼容旧版本写法等）必须询问用户，禁止自行决定。
- **先查找，后编写**：修改或新增前，先搜索本项目 mod；未找到再查原版目录。禁止凭空编造 Stellaris 脚本语法。
- **精确编辑**：修改已有文件使用 Edit 工具局部修改，禁止整文件 Write 覆盖。
- **不确定的语法不编造**：遇到不确定的触发器/效果/修饰符/作用域，使用 `webfetch` 直接查询群星 Modding Wiki（https://stellaris.paradoxwikis.com/Modding），勿凭空编造。
- **大文件勿全量读取**：以下超大文件禁止 Read 全量扫描，应使用搜索定位具体行号再局部读取：
  - `stellaris_godie/events/br_expand_events.txt`（扩圈事件，1w+ 行）
  - 其他超过 500 行的文件优先用搜索而非通读

## 当前主要 mod

`stellaris_godie`（群星：大逃杀模式），namespace 前缀为 `br`。事件 ID 使用 `br.XXX` 格式，各文件内注释标注了 ID 区间。

## 文件规范

- **编码**：所有 `.txt`、`.yml`、`.gui`、`.mod` 文件必须是 **UTF-8 without BOM**，行尾 **LF**。
- **缩进**：与目标文件现有风格保持一致。
- **禁止创建备份文件**（`.bak`、`.old`、`~` 结尾），版本回退用 git。

## 命名与 ID

- 所有自定义 key（事件 ID、科技 ID、特性 ID 等）必须加前缀（如 `br_`）避免冲突。禁止纯数字或无意义命名。
- 文件名应体现实质内容。
- 本地化 key 格式：`前缀_描述:0 "文本"`。

### KEY 命名约定

| 类型 | 模式 | 示例 |
|---|---|---|
| 事件标题 | `br_{事件名}_title` | `br_skill_choose_title` |
| 事件描述 | `br_{事件名}_desc` | `br_skill_choose_desc` |
| 选项按钮 | `br_{选项名}` | `br_skill_choose_overclock` |
| 悬浮提示 | `br_{提示名}_tooltip` | `br_skill_overclock_tooltip` |
| modifier 名 | `br_{modifier}` | `br_vanguard_self_repair` |
| modifier 描述 | `br_{modifier}_desc` | `br_vanguard_self_repair_desc` |
| 舰船/组件名 | `BR_{NAME}` | `BR_VANGUARD_CORE_POWER` |

## .mod 文件

- 根目录 `.mod` 文件（启动器识别用）与 mod 目录内 `descriptor.mod`（发布用）需保持同步。
- mod 目录结构平行于原版（`common/`、`events/`、`localisation/`、`gfx/` 等）。

## 版本控制

- Commit 格式：`<类型>: 简短描述`，类型可选 `feat`、`fix`、`docs`、`refactor`、`localize` 等。
- 修改前确保工作区已 commit 或 stash。

## 安全约束

- **绝对禁止修改游戏原版目录**（`G:\SteamLibrary\steamapps\common\Stellaris`）下的任何文件。
- **变更前确认**：涉及文件写入的操作，必须先展示变更内容并等待用户批准（即"开始实施"）。

## 事件 (Events)

### 基础模板

**隐藏事件（纯逻辑 / 被触发事件）：**
```
country_event = {
    id = br.XXX
    hide_window = yes
    is_triggered_only = yes

    trigger = { ... }       # 可选，被触发事件也可加 trigger 过滤
    immediate = {
        # 即时执行的逻辑
    }
}
```

**玩家可见事件（选择弹窗）：**
```
country_event = {
    id = br.XXX
    title = br_xxx_title
    desc = br_xxx_desc
    picture = GFX_evt_xxx
    is_triggered_only = yes

    option = {
        name = br_xxx_option_1
        custom_tooltip = br_xxx_tooltip_1
        # effects...
    }
    option = {
        name = br_xxx_option_2
        # effects...
    }
}
```

- 隐藏事件不写 `title`/`desc`/`picture`/`option`
- 新文件第一行写 `namespace = br`
- 文件头注释标注 ID 区间：`# 事件ID区间：XXX-XXX。新增或修改事件ID不得超出此区间喵`

### 触发器速查

```
is_ai = no                             # 是否为 AI
has_global_flag = xxx                  # 全局 flag
has_country_flag = xxx                 # 国家 flag
has_star_flag = xxx                    # 恒星 flag
has_fleet_flag = xxx                   # 舰队 flag
is_country_type = xxx                  # 国家类型（如 br_player）
is_ship_size = xxx                     # 舰船类型（如 br_vanguard）
has_component = xxx                    # 是否有某组件
check_variable = { which = xxx value >= N } # 变量比较
has_modifier = xxx                     # 是否有某 modifier
is_triggered_only = yes                # 只能被触发（不能自我触发）
exists = xxx                           # 某作用域对象存在
count_owned_ship = { limit = {...} count >= N } # 计数触发器
```

常用逻辑组合：
```
AND = { ... }                          # 与（默认）
OR = { ... }                           # 或
NOT = { ... }                          # 非
NOR = { ... }                          # 或非
NAND = { ... }                         # 与非
```

### 效果速查

```
set_country_flag = xxx                 # 设置国家 flag
remove_country_flag = xxx              # 移除国家 flag
country_event = { id = xxx days = N }  # 延迟排程事件
add_modifier = { modifier = xxx days = N }                       # 固定时长 modifier
add_modifier = { modifier = xxx days = N mult = var_name }      # 按变量倍率 modifier（普通变量直接按名访问）
# 注意：value: 前缀专用于引用 common/scripted_variables/ 常量
# 普通脚本变量：同作用域直接写变量名；跨作用域用 scope.var_name
set_variable = { which = xxx value = N } # 设置变量
change_variable = { which = xxx value = N } # 加减变量
multiply_variable = { which = xxx value = N } # 乘变量
save_event_target_as = xxx             # 保存当前作用域为事件目标
add_resource = { energy = 100 }        # 加资源
create_ship = { ... }                  # 创建舰船
destroy_country = yes                  # 摧毁国家
```

### 作用域切换

- `root`：事件的最顶层上下文（`country_event` → 触发国家，`fleet_event` → 舰队）
- `owner`：舰船/舰队/星球的所有者国家
- `from`：触发此事件的来源（一级调用链），`fromfrom`（二级），`fromfromfrom`（三级）
- `event_target:xxx`：引用已保存的事件目标
- `prev`：返回上一层作用域

常用切换：
```
# 从 country 作用域遍历所有拥有舰船
every_owned_ship = {
    limit = { is_ship_size = br_vanguard }
    # 此处作用域为 ship
    owner = { add_resource = { energy = 100 } }  # 回到 country
}

# 从 country 作用域遍历所有系统 -> 所有舰队
every_system = {
    every_system_fleet = {
        # 此处作用域为 fleet
    }
}
```

### 变量系统

变量存在国家作用域下，跨事件持久化：
```
# 设置
set_variable = { which = br_skill_cd value = 60 }

# 修改
change_variable = { which = br_skill_cd value = -1 }     # 每日 tick 减 1
multiply_variable = { which = br_mult value = 2 }         # 翻倍

# 读取（在 modifier 中）
# 注意：value: 前缀是 scripted_variables 常量，普通变量直接用变量名
add_modifier = { modifier = xxx days = br_skill_cd mult = br_mult }
# 跨作用域引用：owner.var_name  /  event_target:xxx.var_name

# 条件判断
check_variable = { which = br_skill_cd value <= 0 }
```

### 条件分支

```
if = {
    limit = { has_country_flag = xxx }
    set_country_flag = yyy
}
else_if = {
    limit = { has_country_flag = zzz }
    set_country_flag = www
}
else = {
    set_country_flag = default
}
```

### 技能系统特殊模式

若涉及英雄舰技能，注意以下完整链路：

| 层面 | 文件位置 | 动作 |
|---|---|---|
| 技能选择 | `events/heroship_level_events.txt` | 在 `heroship.4` 路由中添加 |
| 技能触发 | `events/heroship_skill_xxx_events.txt` | 实现触发逻辑 |
| on_actions | `common/on_actions/br_on_actions.txt` | 注册钩子 |
| scripted_triggers | `common/scripted_triggers/br_vanguard_skill_triggers.txt` | 添加触发器 |
| modifier | `common/static_modifiers/br_countrybuff.txt` | 添加效果值 |
| scripted_loc | `common/scripted_loc/br_vanguard_scripted_loc.txt` | 动态显示 |
| 数值引用 | `common/scripted_loc/br_hero_ship_script_values_loc.txt` | 变量引用 |
| 本地化 | `localisation/simp_chinese/br_hero_ship_l_simp_chinese.yml` | 文本 |
| 测试法令 | `common/edicts/br_test_skill_edicts.txt` | 可选调试 |

CD 变量命名：`br_vanguard_{core}_skill_cd`（core = power/defense/support）
解锁 flag：`br_skill_{name}_unlocked`

## Common 系统

### 目录速查

常见需求对应的目录：
- 国家类型 → `common/country_types/`
- 政策/法令 → `common/edicts/`
- 修饰符 → `common/static_modifiers/`
- 科技 → `common/technology/`
- 事件钩子 → `common/on_actions/`
- 自定义触发器 → `common/scripted_triggers/`
- 自定义效果 → `common/scripted_effects/`
- 动态文本 → `common/scripted_loc/`
- 常量 → `common/scripted_variables/`

### modifier 定义

```
# 在 common/static_modifiers/ 中
br_xxx_buff = {
    ship_fire_rate_mult = 0.4
    ship_hull_regen_add_perc = 0.02
    ship_speed_mult = 0.15
}
```

命名约定：`br_{系统}_{效果名}`。同一 modifier 的事件引用和本地化 key 需匹配。

### 科技定义

```
tech_br_xxx = {
    cost = @tierNcost1          # 引用 scripted_variables 常量
    area = engineering           # engineering / physics / society
    tier = N                    # 0-5
    category = { voidcraft }
    weight = 0                  # 0 = 不自然刷，仅事件发放
    gateway = ship              # 可选
    is_rare = yes               # 可选，稀有科技
    ai_weight = { weight = 0 }
}
```

### on_actions

```
# 自定义 on_action 定义
on_br_xxx_activated = {
    events = {
        br.XXX
        br.YYY
    }
}
```

触发方式：`country_event = { id = xxx }` 中执行后，对应事件被触发。

### scripted_triggers / scripted_effects

自定义触发器命名：`br_has_xxx = { ... }`
自定义效果命名：`br_do_xxx = { ... }`

使用时直接写名称即可，无需括号：
```
trigger = {
    br_has_power_vanguard = yes
}
immediate = {
    br_reset_skill_cd = yes
}
```

## 本地化 (Localisation)

### YML 格式

文件路径：`localisation/simp_chinese/xxx_l_simp_chinese.yml`

```
l_simp_chinese:
 key:0 "文本"
```

严格要求：
- 文件编码 UTF-8 without BOM，行尾 LF
- 首行 `l_simp_chinese:`
- 条目缩进一个空格，`key:0 "文本"`（冒号后一个空格）
- 值必须用英文双引号 `""`，内无英文双引号

### 颜色码

```
§G 绿色  §R 红色  §Y 黄色  §H 强调（亮黄）
§B 蓝色  §M 紫色  §! 结束颜色
```

常见用法：
```
br_vanguard_component:0 "§R火力核心§!"
br_vanguard_active_skill:0 "§H主动技能§!"
```

### 动态文本 (scripted_loc)

```
# 在 common/scripted_loc/ 中
defined_text = {
    name = GetBRVanguardActive1
    text = {
        trigger = { always = yes }
        localization_key = br_vanguard_active_1_value
    }
}
```

```
# 在本地化文件中
br_vanguard_active_1_value:0 "[Root.GetBRVanguardActive1]"
```

## 跨域一致性检查清单

编写完成后逐项自检：

- [ ] 事件 ID 在文件头部声明的区间内
- [ ] 事件中 `title`/`desc`/`option name`/`custom_tooltip` 引用的 key 在本地化文件中存在
- [ ] modifier 的 key 在 `static_modifiers/` 和本地化文件中均存在
- [ ] `set_country_flag` 的 flag 名有对应的 `has_country_flag` 使用处
- [ ] scripted_trigger/effect 名称有对应定义文件
- [ ] 所有自定义 key 带 `br_` 前缀
- [ ] 本地化文件编码为 UTF-8 without BOM
- [ ] 文件末尾有换行（LF）

## 反模式（避开这些坑）

1. **凭空编造语法**：不确定的触发器/效果/作用域必须查 Wiki 或原版文件确认。
2. **忘记本地化**：新增事件 title/desc 却忘记在 YML 中添加对应条目，进游戏会显示乱码 key。
3. **flag 命名不一致**：`set_country_flag = br_xxx` 和 `has_country_flag = br_yyy` 不匹配。
4. **变量名拼写错误**：`value:br_skill_cd` 写成 `value:br_skil_cd`，难排查。
5. **overflow ID**：事件 ID 超出文件头部声明的区间，容易与其他人事件冲突。
6. **隐藏事件写了 option**：`hide_window = yes` 的事件不应有 `option = {}` 块。
7. **作用域混乱**：在 `every_owned_ship` 内直接写 `add_resource` 而不先切换到 `owner`。
