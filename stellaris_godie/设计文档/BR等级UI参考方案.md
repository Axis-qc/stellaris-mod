# BR 等级 UI 参考方案

本文档记录 BR 等级 UI 的设计参考和已实施状态。以下"当前问题"和"方案"为历史参考。

> **最新状态**：底部横向标签页已实施，总览页左右分栏、动态变量接入、scripted_loc 阈值均已落地。详见文末实施记录。

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

推荐页面：

- `br_level_ui_tab = 1`：总览，显示等级、经验、战斗评分、击杀分数、规则说明。
- `br_level_ui_tab = 2`：等级奖励，显示 Lv1-Lv8 解锁内容。
- `br_level_ui_tab = 3`：战斗统计，预留后续统计功能。
- `br_level_ui_tab = 4`：预留功能，放后续系统入口。

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

## 推荐下次实施顺序

下次继续时，建议按以下顺序做，避免一次改太多导致不好排错。

### 第一步：稳定页面切换

修改文件：

- `stellaris_godie/events/br_level_ui_events.txt`
- `stellaris_godie/interface/br_level_view.gui`
- 新增 `stellaris_godie/common/button_effects/br_level_ui_buttons.txt`
- 修改 `stellaris_godie/localisation/simp_chinese/br_pve_l_simp_chinese.yml`

目标：

- 初始化 `br_level_ui_tab = 1`。
- 左侧增加纵向导航按钮。
- 点击左侧导航能切换右侧内容区。
- 暂时不处理动态变量解析。

### 第二步：恢复动态变量显示

优先尝试顺序：

1. 把动态值放回事件文本上下文，确认变量能读。
2. 如果要独立控件，尝试 scripted_loc + `buttonText`。
3. 如果仍失败，保留事件文本上下文，把独立控件只用于静态标题和装饰。

### 第三步：经验条

最终处理方式：

- 使用文字经验：`经验：40 / 100`。
- 不做字符伪进度条。
- 不尝试真正 `progressbarType` 变量绑定。
- 如需强化视觉，只在文字附近加静态分割线或背景块。

### 第四步：美化

参考方向：

- 窗口继续保持约 `1024 x 720`。
- 左侧做纵向导航栏。
- 右侧根据当前导航切换：
    - 总览：等级、经验、战斗评分、击杀分数、规则说明。
    - 等级奖励：每级奖励列表。
    - 战斗统计：后续统计扩展。
    - 预留功能：后续系统入口。
- 背景用深色半透明块。
- 分割线用金色线条或参考 mod 的分割线 sprite。

## 建议采用的最终结构

推荐最终采用混合方案：

- 页面切换：方案一，左侧纵向导航使用 `effectButtonType + button_effects + br_level_ui_tab`。
- 动态数值：优先方案二，事件文本上下文；如果验证可行，再升级方案三。
- 经验显示：采用方案四的固定文字格式，例如 `经验：40 / 100`。
- 滚动区：暂不做，等内容变多再引入方案五。
- option：保留隐藏必需控件，可见操作全部自定义。

这个方案的好处是：

- 先保证不闪退。
- 再保证变量能显示。
- 最后逐步增强交互和美观。
- 每一步都能单独进游戏验证。

## 下次接续提示

如果下次要继续实施，可以直接说：

```txt
按 stellaris_godie/设计文档/BR等级UI参考方案.md 的推荐结构，开始实施第一步：做左侧导航切换右侧内容。
```

实施前需要先检查：

- 当前 `br_level_view.gui` 是否仍保留 `tts_button`、`empire_flag`、`portrait`、`action_desc`、`option_list` 等事件 UI 必需控件。
- `error.log` 是否还有新的缺控件报错。
- 普通 GUI 文本是否仍不能解析 `[Root.xxx]`。

---

## 实施记录：底部横向标签页框架

布局从"左侧信息+右侧预留"改为"底部横向标签页+全幅内容区"。关闭按钮通过自定义事件 option GUI（`br_level_view_option.gui`）实现，原 `close` 按钮丢屏幕外保留 ESC 快捷键。

### 文件清单

| 文件 | 说明 |
|------|------|
| `interface/br_level_view.gui` | 主 GUI。背景/标题/右上关闭/内容区/底部标签栏/隐藏必需控件 |
| `interface/br_level_view_option.gui` | option 自定义 GUI（右上角关闭按钮） |
| `common/button_effects/br_level_ui_buttons.txt` | 按钮效果。4组 `_active`（内容显隐，potential）+ 4组 tab（按钮禁用，allow） |
| `common/scripted_loc/br_level_ui_loc.txt` | `GetBRNextLevelThreshold`，根据等级返回下级阈值 |
| `events/br_level_ui_events.txt` | `immediate` 初始化 `br_level_ui_tab = 1`；option 加 `custom_gui` + `custom_tooltip` |
| `localisation/simp_chinese/br_level_ui_l_simp_chinese.yml` | UI 专用本地化（窗口/标签/总览/阈值/占位） |

### 标签切换机制

- **变量**：`br_level_ui_tab`（值 1/2/3/4）
- **按钮**：4 个 `effectButtonType`，统一 `GFX_button_60_29`，`allow` 检查非当前页时禁用（引擎自动灰化），点击 `set_variable` 切换
- **内容显隐**：各标签内容元素引用 `_active` effect，`potential` 统一控制

### 关闭按钮

- 通过事件 option 的 `custom_gui = "br_level_view_option"` 实现
- `option_button` 定位右上角，tooltip 由 `custom_tooltip` 控制
- 原 `buttonType name="close"` 丢屏幕外保留 ESC 快捷键

### 动态变量

- `effectButtonType` 的 `buttonText` 支持 `[Root.xxx]` 直接解析（已验证）
- 下级阈值通过 `scripted_loc` + `[Root.GetBRNextLevelThreshold]` 实现
- `heading` 是引擎预留名，diplomatic 窗口下会被覆盖，已改名为 `br_title`

### 必需控件（勿删）

`alien_message`、`heading`（隐藏）、`action_title`、`their_opinion` 等事件 GUI 必需控件全部保留，隐藏 off-screen。
