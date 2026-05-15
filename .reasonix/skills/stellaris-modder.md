---
name: stellaris-modder
description: 群星 (Stellaris) 模组开发助手。覆盖事件脚本、common 系统（政策/科技/特性/modifier/on_actions 等）以及本地化文件的编写、修改与校验。
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
- **大文件勿全量读取**：超过 500 行的文件优先用搜索而非通读。

## 当前主要 mod

`stellaris_godie`（群星：大逃杀模式），namespace 前缀为 `br`。事件 ID 使用 `br.XXX` 格式。

## 文件规范

- **编码**：所有 `.txt`、`.yml`、`.gui`、`.mod` 文件必须是 **UTF-8 without BOM**，行尾 **LF**。
- **缩进**：与目标文件现有风格保持一致。
- **禁止创建备份文件**（`.bak`、`.old`、`~` 结尾），版本回退用 git。

## 命名与 ID

- 所有自定义 key（事件 ID、科技 ID、特性 ID 等）必须加前缀（如 `br_`）避免冲突。
- 本地化 key 格式：`前缀_描述:0 "文本"`。

### KEY 命名约定

| 类型 | 模式 | 示例 |
|------|------|------|
| 事件标题 | `br_{事件名}_title` | `br_skill_choose_title` |
| 事件描述 | `br_{事件名}_desc` | `br_skill_choose_desc` |
| 选项按钮 | `br_{选项名}` | `br_skill_choose_overclock` |
| 悬浮提示 | `br_{提示名}_tooltip` | `br_skill_overclock_tooltip` |
| modifier 名 | `br_{modifier}` | `br_vanguard_self_repair` |
| modifier 描述 | `br_{modifier}_desc` | `br_vanguard_self_repair_desc` |
| 舰船/组件名 | `BR_{NAME}` | `BR_VANGUARD_CORE_POWER` |

## 事件 (Events)

### 基础模板

**隐藏事件（纯逻辑 / 被触发事件）：**
```
country_event = {
    id = br.XXX
    hide_window = yes
    is_triggered_only = yes
    trigger = { ... }
    immediate = { ... }
}
```

**带选项事件：**
```
country_event = {
    id = br.XXX
    title = br_xxx_title
    desc = br_xxx_desc
    picture = GFX_evt_xxx
    trigger = { ... }
    option = {
        name = br_xxx_option
        custom_tooltip = br_xxx_tooltip
        ...
    }
}
```

### 触发器速查

| 目标 | 触发器 | 说明 |
|------|--------|------|
| 检查 flag | `has_country_flag = br_xxx` | 国家 flag |
| 检查变量 | `check_variable = { which = br_xxx value >= N }` | 数值比较 |
| 检查 modifier | `has_modifier = br_xxx` | buff 检测 |
| 检查组件 | `has_component = BR_XXX` | 舰船组件检测 |
| 检查舰船尺寸 | `is_ship_size = br_xxx` | 舰船类型检测 |

### modifier 定义

```
br_vanguard_xxx = {
    ship_damage_reduction_mult = 1.0
    ship_weapon_damage = -1.0
}
```

## 本地化 (Localisation)

### YML 格式

```yaml
l_simp_chinese:
 BR_KEY:0 "中文文本"
```

### 颜色码

- `§G` 绿色 / `§R` 红色 / `§Y` 黄色 / `§B` 蓝色 / `§H` 标题色 / `§!` 重置

### 动态文本 (scripted_loc)

在 `common/scripted_loc/` 中定义 `defined_text`，在本地化文件中引用。

## 跨域一致性检查清单

- [ ] 事件 ID 在文件头部声明的区间内
- [ ] 事件中引用的 key 在本地化文件中存在
- [ ] modifier 的 key 在 `static_modifiers/` 和本地化文件中均存在
- [ ] `set_country_flag` 有对应的 `has_country_flag` 使用处
- [ ] 所有自定义 key 带 `br_` 前缀
- [ ] 本地化文件编码为 UTF-8 without BOM
- [ ] 文件末尾有换行（LF）

## 反模式

1. **凭空编造语法** — 不确定的触发器/效果必须查 Wiki
2. **忘记本地化** — 新增事件却忘记 YML 条目
3. **flag 命名不一致** — set 和 has 不匹配
4. **变量名拼写错误** — 难排查
5. **overflow ID** — 事件 ID 超出区间
6. **隐藏事件写了 option** — `hide_window = yes` 不应有 option
7. **作用域混乱** — 在舰船 scope 内直接写国家效果而不切换
