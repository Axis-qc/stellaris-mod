# BR 等级 UI 文档

本文档记录 BR 等级 UI 的当前实施状态和技术要点。

> **当前状态**：底部横向5标签页已实施：总览 / 后勤 / 舰队 / 统计 / 其他。总览页三行布局（Row1: 玩家等级+等级规则，Row2: 英雄舰等级+英雄经验规则，Row3: 三列技能），后勤页左右分栏（资源月产+舰队Buff），舰队页左右分栏（永久强化+消耗品限时）。UI 骨架完成，购买按钮使用占位效果。

## 参考来源

- 本 mod：`stellaris_godie/interface/br_level_view.gui`
- 本 mod：`stellaris_godie/events/br_level_ui_events.txt`
- 参考 mod：`G:\SteamLibrary\steamapps\workshop\content\281990\2660548454`

## 文件清单

| 文件 | 说明 |
|------|------|
| `interface/br_level_view.gui` | 主 GUI。背景/标题/右上关闭/内容区/底部标签栏/隐藏必需控件 |
| `interface/br_level_view_option.gui` | option 自定义 GUI（右上角关闭按钮） |
| `common/button_effects/br_level_ui_buttons.txt` | 按钮效果。5组 `_active`（内容显隐，potential）+ 5组 tab（按钮禁用，allow）+ 3组占位 placeholder |
| `common/button_effects/br_level_ui_hero_skill_buttons.txt` | 英雄舰技能切换按钮。6组技能槽切换（`br_level_ui_active_slot1/2`、`br_level_ui_passive_slot1/2`、`br_level_ui_ultimate_slot1/2`），支持同一技能组内两个槽位互切 |
| `common/scripted_loc/br_level_ui_loc.txt` | `GetBRNextLevelThreshold`，根据等级返回下级阈值 |
| `common/scripted_loc/br_level_ui_hero_skill_loc.txt` | 英雄舰技能 UI scripted_loc。6组技能槽短名 + 3组技能描述，根据英雄核心类型 flag 和技能槽选中 flag 动态返回对应文本 |
| `events/br_level_ui_events.txt` | `immediate` 初始化 `br_level_ui_tab = 1`；option 加 `custom_gui` + `custom_tooltip` |
| `localisation/simp_chinese/br_level_ui_l_simp_chinese.yml` | UI 专用本地化（窗口/标签/总览/后勤/舰队/阈值/占位） |

## 标签切换机制

- **变量**：`br_level_ui_tab`（值 1/2/3/4/5）
- **按钮**：5 个 `effectButtonType`，统一 `GFX_expedition_log_tab` 纹理，`allow` 检查非当前页时禁用（引擎自动灰化），点击 `set_variable` 切换
- **按钮位置**：`x=0/160/320/480/640`，每按钮宽160（容器总宽824，5×160=800刚好）

## 内容区显隐

- **总览页**（tab=1）：每个元素 `effect = br_level_ui_tab_overview_active`
- **后勤页**（tab=2）：背景/标题 `effect = br_level_ui_tab_logistics_active`，购买按钮 `effect = br_ui_placeholder_logistics`
- **舰队页**（tab=3）：背景/标题 `effect = br_level_ui_tab_fleet_active`，购买按钮 `effect = br_ui_placeholder_fleet`
- **统计页**（tab=4）：`effect = br_level_ui_tab_stats_active`
- **其他页**（tab=5）：`effect = br_level_ui_tab_other_active`

核心机制：`effectButtonType` 的 `effect` 属性引用 `button_effects` 中的效果，引擎会评估其 `potential` 来决定元素显隐。背景面板和标题用 `_active` 效果（无 effect 块），购买按钮用 `_placeholder` 效果（有 allow 但无 effect 块，可点击无动作）。

## 各页布局

**总览页（tab=1）三行布局：**

| 行 | 左面板 | 右面板 |
|:--:|:-------|:-------|
| Row1 | 玩家等级状态（等级/评分/击杀） | 等级规则说明 |
| Row2 | 英雄舰等级（英雄等级/英雄经验） | 英雄经验规则说明 |
| Row3 | 三列技能（主动技能/被动技能/旗舰超载） | — |

**其他页面：**

| 页 | tab | 左面板 | 右面板 |
|:--:|:---:|:-------|:-------|
| 后勤 | 2 | 10个资源月产兑换按钮 | 5个舰队Buff叠层按钮 |
| 舰队 | 3 | 4个永久强化按钮（稀有资源） | 3个消耗品限时按钮（消费品） |
| 统计 | 4 | 占位文本 | — |
| 其他 | 5 | 占位文本 | — |

## 动态变量

- `effectButtonType` 的 `buttonText` 支持 `[from.xxx]` 直接解析（已验证）
- 下级阈值通过 `scripted_loc` + `[from.GetBRNextLevelThreshold]` 实现
- `heading` 是引擎预留名，diplomatic 窗口下会被覆盖，总览页标题实际使用 `br_title`
- **技能槽动态显示**：使用 `[from.GetBRUIActiveSlot1]`、`[from.GetBRUIPassiveSlot1]`、`[from.GetBRUIUltimateSlot1]` 等 scripted_loc
- **技能描述动态显示**：使用 `[from.GetBRUIActiveDesc]`、`[from.GetBRUIPassiveDesc]`、`[from.GetBRUIUltimateDesc]` 等 scripted_loc

## 购买按钮占位效果

当前为 UI 骨架阶段，所有功能按钮使用占位效果：
- `br_ui_placeholder` — 通用占位（`potential = always`，始终可见）
- `br_ui_placeholder_logistics` — 后勤页占位（`potential` 检查 tab=2）
- `br_ui_placeholder_fleet` — 舰队页占位（`potential` 检查 tab=3）

每个占位效果 `allow = { always = yes }`（按钮可点击），无 `effect` 块（点击无动作）。功能效果待 UI 定稿后再实现。

**实际实现的按钮数量：**
- 后勤页左：10个资源月产兑换按钮（合金/能量/矿物/食物/消费品/凝聚力/贸易/水晶/气体/灵雾）
- 后勤页右：5个舰队Buff叠层按钮（武器伤害/射速/船体/护甲/护盾）
- 舰队页左：4个永久强化按钮（英雄舰船体/再生/护甲/移速）
- 舰队页右：3个消耗品限时按钮（战斗专注/紧急防护/超载武器）

## 注意事项

- **`effectButtonType` + `quadTextureSprite` 时 `size` 无效**：按钮尺寸由纹理决定，`size = { }` 设置不生效。应注释掉 `size` 行或标记说明。
- **显隐通过 `effect` 引用实现**：直接在 GUI 元素上加 `potential` 无效。必须在 button_effects 中定义效果，在 GUI 中用 `effect =` 引用。
- **作用域**：button_effects 中的 `potential = { from = { ... } }` 的 `from` 指向国家，`root` 不可用。
- **必需控件**：`close`（ESC快捷键）、`confirm_button`、`tts_button`、`alien_message`、`heading`、`option_list` 等事件 GUI 必需控件全部保留 off-screen。

---

## 下次接续提示

**当前状态**：UI 骨架已完成，购买按钮使用占位效果（可点击无动作）

下次继续时，可以先做：

1. **后勤/舰队页功能效果**：为各购买按钮编写实际的 button_effects（检查资源→扣资源→改变量/add_modifier），参考 `br_reward_relics.txt` 中的 `br_reward_xxx` 变量体系
2. **总览页完善**：英雄舰状态数据（船体/护甲/护盾实时数值）等
3. **统计页实装**：战斗数据统计面板
4. **经验条/进度显示**：如需可视化进度条，需研究原版 progressbarType 是否能在自定义 GUI 中使用

实施前需检查：

- `error.log` 是否有控件缺失报错
- 所有 off-screen 必需控件（`tts_button`、`empire_flag`、`portrait`、`action_desc`、`option_list` 等）是否保留
