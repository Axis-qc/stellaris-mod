# BR 等级 UI 参考方案

本文档记录 BR 等级 UI 的设计参考和已实施状态。以下"当前问题"和"方案"为历史参考。

> **最新状态**：底部横向5标签页已实施：总览 / 后勤 / 舰队 / 统计 / 其他。总览页左右分栏（等级数据+英雄舰技能），后勤页左右分栏（资源月产+舰队Buff），舰队页左右分栏（永久强化+消耗品限时）。详见文末实施记录。

本文档参考来源：

- 本 mod：`stellaris_godie/interface/br_level_view.gui`
- 本 mod：`stellaris_godie/events/br_level_ui_events.txt`
- 参考 mod：`G:\SteamLibrary\steamapps\workshop\content\281990\2660548454`
- 参考 mod UI：`G:\SteamLibrary\steamapps\workshop\content\281990\2660548454\interface`

## 当前问题

当前 UI 已经能打开，但存在两个主要问题：

1. 普通 `instantTextBoxType` 里写本地化变量时，`[Root.br_power_level]` 这类内容会按字面显示，不能解析成变量值。
2. 界面后续需要支持按钮切换页面，不能继续依赖 `option_list` 这种事件选项列表按钮。

原因判断：

- `custom_gui` 事件窗口里的 `alien_message` / 事件 `desc` 属于事件文本上下文，更容易解析 `[Root.xxx]`。
- 普通 GUI 文本框不是事件描述文本，不一定拥有同样的 `Root` 解析上下文。
- 因此，把等级、战斗评分、击杀分数拆成多个普通文本框后，视觉上更好拆分，但动态变量解析失效。

## 参考 mod 的整体结构

参考 mod 使用事件打开自定义 UI：

- 事件文件：`events\AOW_evts_core.txt`
- GUI 文件：`interface\AOW_gui_ui_main.gui`
- 按钮效果：`common\button_effects\AOW_btn_main_ui_page.txt`
- 其他按钮效果：`common\button_effects\AOW_btn_main_ui_presets.txt`
- 滚动条：`interface\AOW_gui_slider.gui`
- GFX 资源：`interface\AOW_gfx_ui_vanilla.gfx`

它的主 UI 事件大致结构：

```txt
country_event = {
    id = AOW_core.100
    diplomatic = yes
    custom_gui = "AOW_main_ui"
    force_open = yes

    immediate = {
        if = {
            limit = { NOT = { has_variable = AOW_var_page } }
            set_variable = { which = AOW_var_page value = 1 }
        }
    }

    option = {
        name = AOW_xxx
        custom_gui = "AOW_main_ui_option"
    }
}
```

可参考点：

- `custom_gui = "AOW_main_ui"` 负责主窗口。
- `custom_gui = "AOW_main_ui_option"` 负责重绘事件 option 按钮。
- `AOW_var_page` 用国家变量记录当前页面。
- `force_open = yes` 可保证窗口强制打开。

## 参考截图的布局结构

参考 mod 的实际界面更接近“左侧导航 + 右侧内容区”，不是顶部页签。

结构示意：

```txt
┌──────────────────────────── 信号传输接入 ────────────────────────────┐
│ ┌──────────────┐ ┌────────────────────────────────────────────────────┐ │
│ │ 总览          │ │ 当前右侧页面内容                                    │ │
│ │ 等级奖励      │ │                                                    │ │
│ │ 战斗统计      │ │ 总览页：等级、经验、战斗评分、击杀分数、规则说明      │ │
│ │ 预留功能      │ │ 奖励页：每级解锁列表                                │ │
│ │              │ │ 战斗统计页：后续统计扩展                            │ │
│ └──────────────┘ └────────────────────────────────────────────────────┘ │
│                                                        [关闭]           │
└────────────────────────────────────────────────────────────────────────┘
```

建议尺寸：

- 主窗口继续保持约 `1024 x 720`。
- 左侧导航宽度约 `150-180`。
- 右侧内容区占剩余宽度。
- 左侧按钮垂直排列，当前页按钮高亮。
- 右侧只显示当前页内容，其他页内容通过 `potential` 隐藏。

推荐页面（当前已实施）：

- `br_level_ui_tab = 1`：**总览**，左=玩家等级数据（等级/评分/击杀），右=英雄舰技能槽
- `br_level_ui_tab = 2`：**后勤**，左=资源月产兑换，右=舰队Buff叠层
- `br_level_ui_tab = 3`：**舰队**，左=永久强化，右=消耗品限时
- `br_level_ui_tab = 4`：**统计**，占位页面
- `br_level_ui_tab = 5`：**其他**，占位页面

## 方案一：按钮切换页面

推荐使用 `effectButtonType` + `common/button_effects`。

基本思路：

1. 在事件 `immediate` 中初始化页面变量，例如 `br_level_ui_tab = 1`。
2. 左侧做多个纵向导航按钮，例如：总览、等级奖励、战斗统计、预留功能。
3. 每个导航按钮做两套按钮：
    - active：当前页面显示，用高亮外观，不执行切换。
    - inactive：非当前页面显示，点击后设置变量切换页面。
4. 页面内容也通过 `potential` 判断 `br_level_ui_tab` 来显示或隐藏。

参考按钮效果结构：

```txt
br_level_ui_tab_overview_active = {
    potential = {
        from = {
            check_variable = { which = br_level_ui_tab value = 1 }
        }
    }
    allow = { always = yes }
}

br_level_ui_tab_overview_inactive = {
    potential = {
        from = {
            check_variable = { which = br_level_ui_tab value != 1 }
        }
    }
    allow = { always = yes }
    effect = {
        hidden_effect = {
            from = {
                set_variable = { which = br_level_ui_tab value = 1 }
            }
        }
    }
}
```

GUI 中按钮参考结构：

```txt
effectButtonType = {
    name = "br_tab_overview_active"
    quadTextureSprite = "GFX_standard_button_142_34_button"
    buttonText = "BR_LEVEL_UI_TAB_OVERVIEW"
    effect = "br_level_ui_tab_overview_active"
}

effectButtonType = {
    name = "br_tab_overview_inactive"
    quadTextureSprite = "GFX_standard_button_142_34_button"
    buttonText = "BR_LEVEL_UI_TAB_OVERVIEW"
    effect = "br_level_ui_tab_overview_inactive"
}
```

优点：

- 可以实现真正的 GUI 内页面切换。
- 不需要关闭事件窗口再重新打开。
- 可扩展多个页面。

注意：

- active / inactive 两套按钮需要位置完全重叠。
- 显示逻辑依赖 `button_effects` 的 `potential`。
- 具体 `from` 是否指向国家作用域，需要以游戏内测试为准；AOW mod 使用的是 `from = { check_variable = ... }`。

## 方案二：保留事件文本上下文显示动态变量

这是最稳的变量显示方案。

做法：

- 继续使用事件 `desc` 或 GUI 中必要的事件描述控件承载动态文本。
- 把等级、评分、击杀分数、说明文字统一放回事件文本上下文。
- 用背景、分割线、缩进、颜色来模拟“分块 UI”。

优点：

- `[Root.br_power_level]` 等变量最可能正常解析。
- 实现成本最低。
- 对 Stellaris 事件 UI 最安全。

缺点：

- 左侧文本无法真正拆成多个独立动态控件。
- 布局精细度较低。

适合当前要优先稳定打开、稳定读变量的阶段。

## 方案三：使用 scripted_loc 给普通 GUI 提供动态文本

参考 mod 中大量使用 `common\scripted_loc` 和本地化文本组合动态显示。

可尝试做法：

1. 新增 `common/scripted_loc/br_level_ui_scripted_loc.txt`。
2. 定义获取等级、评分、击杀分数的 scripted localization。
3. 本地化里使用类似 `[Root.GetBRLevelUILevel]` 的形式。
4. GUI 中使用 `buttonText` 或文本控件引用对应本地化 key。

概念示例：

```txt
defined_text = {
    name = GetBRLevelUILevel
    text = {
        trigger = { always = yes }
        localization_key = BR_LEVEL_UI_LEVEL_VALUE
    }
}
```

优点：

- 有机会让拆开的普通 GUI 控件显示动态值。
- 适合后续做更精细的界面。

风险：

- 需要实际进游戏验证普通 GUI 控件是否能触发 scripted_loc。
- 不同控件对本地化解析支持可能不同。
- 不能保证 `instantTextBoxType` 与 `effectButtonType buttonText` 表现完全一致。

建议：

- 如果要拆分左侧每一行，优先尝试 `effectButtonType` 的 `buttonText`，因为参考 mod 在按钮文本上大量使用动态显示。
- 如果 `instantTextBoxType` 仍不解析，则不要继续在普通文本框上硬试。

## 方案四：经验显示处理

参考 mod 在 `AOW_gfx_ui_vanilla.gfx` 中虽然定义了进度条资源：

```txt
progressbarType = {
    name = "GFX_AOW_progressbar"
    textureFile1 = "gfx/interface/progressbars/progressbar_933.dds"
    textureFile2 = "gfx/interface/progressbars/progressbar_933_empty.dds"
    size = { x = 580 y = 35 }
    effectFile = "gfx/FX/progress_startend.shader"
}
```

可参考点：

- 可以借用原版进度条贴图风格做静态装饰。
- 但从参考截图看，它实际主要使用按钮、文本、格子和图标组合界面，没有依赖真正的动态进度条。

限制：

- 原版 `progressbarType` 很多是硬编码窗口或特殊系统喂值。
- 自定义事件 GUI 不一定能直接把国家变量绑定到进度条百分比。
- 为了避免把时间消耗在不稳定控件上，BR 等级 UI 暂不采用真正进度条。

最终采用：

- 经验固定使用文字格式：`经验：40 / 100`。
- 如果当前等级经验上限不是 100，则改成对应上限，例如 `经验：40 / 200`。
- 文本颜色可以继续使用本地化颜色标记，例如 `经验：§G40§! / §Y100§!`。
- 不做字符伪进度条，不做真正 `progressbarType` 变量绑定。

本地化示例：

```yml
BR_LEVEL_UI_EXP_TEXT:0 "经验：§G[Root.br_level_exp]§! / §Y100§!"
```

这种方式不是进度条，但稳定、清楚，也方便后续放在左侧导航或右侧总览页中。

## 方案五：滚动内容区

参考 mod 使用：

- `verticalScrollbar = "AOW_right_vertical_slider"`
- `smooth_scrolling = yes`
- `clipping = yes`

适合后续“等级奖励列表”“功能说明”“日志”等内容变多时使用。

建议：

- 当前 BR 等级 UI 暂时不需要滚动。
- 如果右侧预留功能区将来有大量条目，再加滚动容器。
- 滚动条样式可以参考 `AOW_gui_slider.gui`。

## 方案六：重绘事件 option 按钮

参考 mod 没有直接依赖原版 `option_list` 的视觉，而是单独定义 option GUI：

```txt
containerWindowType = {
    name = "AOW_main_ui_option"
    buttonType = {
        name = "option_button"
        quadTextureSprite = "GFX_AOW_button_enter"
    }
}
```

对本 UI 的意义：

- 如果 `option_list` 是事件窗口必需控件，可以保留但隐藏。
- 真正给玩家点击的关闭按钮、切页按钮都使用自定义 `effectButtonType` / `buttonType`。
- 如果需要重绘事件 option，可以单独定义 `BR_LEVEL_UI_OPTION` 风格。

当前建议：

- 保留隐藏 `option_list`，避免事件 UI 缺控件导致崩溃。
- 可见关闭按钮继续用自定义 `close`。
- 页面切换按钮不用 `option_list`，改用 `effectButtonType`。

## 实际实施的最终结构

当前已实施的 UI 框架：

- **页面切换**：底部横向5标签页，`effectButtonType` 单按钮 + `allow` 禁用态，点击 `set_variable` 切换
- **内容显隐**：通过 `effect = xxx_active` 引用 button_effects 的 `potential` 控制
- **动态数值**：`effectButtonType` 的 `buttonText` 直接解析 `[from.xxx]`（已验证可行）
- **经验显示**：暂未实现（总览页左侧有规则说明区域可用于后续扩展）
- **滚动区**：暂不做
- **option**：保留隐藏必需控件，关闭按钮通过自定义 option GUI 实现

## 下次接续提示

下次继续时，可以先做：

1. **后勤/舰队页功能效果**：为各购买按钮编写实际的 button_effects（检查资源→扣资源→改变量/add_modifier），参考 `br_reward_relics.txt` 中的 `br_reward_xxx` 变量体系
2. **总览页完善**：英雄舰状态数据（船体/护甲/护盾实时数值）等
3. **统计页实装**：战斗数据统计面板
4. **经验条/进度显示**：如需可视化进度条，需研究原版 progressbarType 是否能在自定义 GUI 中使用

实施前需检查：

- `error.log` 是否有控件缺失报错
- 所有 off-screen 必需控件（`tts_button`、`empire_flag`、`portrait`、`action_desc`、`option_list` 等）是否保留

---

## 实施记录：当前 UI 框架（底部5标签页）

布局：底部横向5标签页 + 全幅内容区。每个标签页内容通过 `effect = xxx_active` 的 `potential` 控制显隐。关闭按钮通过自定义事件 option GUI（`br_level_view_option.gui`）实现。

### 文件清单

| 文件 | 说明 |
|------|------|
| `interface/br_level_view.gui` | 主 GUI。背景/标题/右上关闭/内容区/底部标签栏/隐藏必需控件 |
| `interface/br_level_view_option.gui` | option 自定义 GUI（右上角关闭按钮） |
| `common/button_effects/br_level_ui_buttons.txt` | 按钮效果。5组 `_active`（内容显隐，potential）+ 5组 tab（按钮禁用，allow）+ 3组占位 placeholder |
| `common/scripted_loc/br_level_ui_loc.txt` | `GetBRNextLevelThreshold`，根据等级返回下级阈值 |
| `events/br_level_ui_events.txt` | `immediate` 初始化 `br_level_ui_tab = 1`；option 加 `custom_gui` + `custom_tooltip` |
| `localisation/simp_chinese/br_level_ui_l_simp_chinese.yml` | UI 专用本地化（窗口/标签/总览/后勤/舰队/阈值/占位） |

### 标签切换机制

- **变量**：`br_level_ui_tab`（值 1/2/3/4/5）
- **按钮**：5 个 `effectButtonType`，统一 `GFX_standard_button_116_34` 纹理，`allow` 检查非当前页时禁用（引擎自动灰化），点击 `set_variable` 切换
- **按钮位置**：`x=0/160/320/480/640`，每按钮宽160（容器总宽824，5×160=800刚好）

### 内容区显隐

- **总览页**（tab=1）：每个元素 `effect = br_level_ui_tab_overview_active`
- **后勤页**（tab=2）：背景/标题 `effect = br_level_ui_tab_logistics_active`，购买按钮 `effect = br_ui_placeholder_logistics`
- **舰队页**（tab=3）：背景/标题 `effect = br_level_ui_tab_fleet_active`，购买按钮 `effect = br_ui_placeholder_fleet`
- **统计页**（tab=4）：`effect = br_level_ui_tab_stats_active`
- **其他页**（tab=5）：`effect = br_level_ui_tab_other_active`

核心机制：`effectButtonType` 的 `effect` 属性引用 `button_effects` 中的效果，引擎会评估其 `potential` 来决定元素显隐。背景面板和标题用 `_active` 效果（无 effect 块），购买按钮用 `_placeholder` 效果（有 allow 但无 effect 块，可点击无动作）。

### 各页布局

| 页 | tab | 左面板 | 右面板 |
|:--:|:---:|:-------|:-------|
| 总览 | 1 | 等级/评分/击杀/规则说明 | 英雄舰技能槽（主动/被动/旗舰超载） |
| 后勤 | 2 | 10个资源月产兑换按钮 | 5个舰队Buff叠层按钮 |
| 舰队 | 3 | 4个永久强化按钮（稀有资源） | 3个消耗品限时按钮（消费品） |
| 统计 | 4 | 占位文本 | — |
| 其他 | 5 | 占位文本 | — |

### 注意事项

- **`effectButtonType` + `quadTextureSprite` 时 `size` 无效**：按钮尺寸由纹理决定，`size = { }` 设置不生效。应注释掉 `size` 行或标记说明。
- **显隐通过 `effect` 引用实现**：直接在 GUI 元素上加 `potential` 无效。必须在 button_effects 中定义效果，在 GUI 中用 `effect =` 引用。
- **作用域**：button_effects 中的 `potential = { from = { ... } }` 的 `from` 指向国家，`root` 不可用。
- **必需控件**：`close`（ESC快捷键）、`confirm_button`、`tts_button`、`alien_message`、`heading`、`option_list` 等事件 GUI 必需控件全部保留 off-screen。

### 动态变量

- `effectButtonType` 的 `buttonText` 支持 `[from.xxx]` 直接解析（已验证）
- 下级阈值通过 `scripted_loc` + `[from.GetBRNextLevelThreshold]` 实现
- `heading` 是引擎预留名，diplomatic 窗口下会被覆盖，总览页标题实际使用 `br_title`

### 购买按钮占位效果

当前为 UI 骨架阶段，所有功能按钮使用占位效果：
- `br_ui_placeholder` — 通用占位（`potential = always`，始终可见）
- `br_ui_placeholder_logistics` — 后勤页占位（`potential` 检查 tab=2）
- `br_ui_placeholder_fleet` — 舰队页占位（`potential` 检查 tab=3）

每个占位效果 `allow = { always = yes }`（按钮可点击），无 `effect` 块（点击无动作）。功能效果待 UI 定稿后再实现。
