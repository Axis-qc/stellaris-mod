# AGENTS.md

## 对话

- 使用中文思考和回复，回复末尾加"喵"。
- **遇歧义先询问**：遇到多种可行方案或不明确的需求时，必须询问用户确认，禁止自行推测。
- **先计划后实施**：非简单修改（新增事件链、机制、政策等）必须先制定计划，经用户批准后再实施。

## 关键路径

- 项目目录（mod 开发）：`C:\Users\hp\Documents\Paradox Interactive\Stellaris\mod`
- 游戏原版目录：`G:\SteamLibrary\steamapps\common\Stellaris`
- 错误日志：`%USERPROFILE%\Documents\Paradox Interactive\Stellaris\logs\error.log`

## 工作流程

- **先查找，后编写**：修改或新增前，先搜索本项目 mod；未找到再查原版目录。禁止凭空编造 Stellaris 脚本语法。
- **精确编辑**：修改已有文件使用 Edit 工具局部修改，禁止整文件 Write 覆盖。
- **不确定的语法不编造**：遇到不确定的触发器/效果/修饰符/作用域，询问用户或查阅官方文档。
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

## .mod 文件

- 根目录 `.mod` 文件（启动器识别用）与 mod 目录内 `descriptor.mod`（发布用）需保持同步。
- mod 目录结构平行于原版（`common/`、`events/`、`localisation/`、`gfx/` 等）。

## 本地化

- 当前仅维护 `localisation/simp_chinese/*.yml`。
- 以 `l_simp_chinese:` 开头，条目格式 ` key:0 "文本"`（冒号后一个空格）。值区域外使用英文双引号。

## 版本控制

- Commit 格式：`<类型>: 简短描述`，类型可选 `feat`、`fix`、`docs`、`refactor`、`localize` 等。
- 修改前确保工作区已 commit 或 stash。

## 安全约束

- **绝对禁止修改游戏原版目录**（`G:\SteamLibrary\steamapps\common\Stellaris`）下的任何文件。
- **变更前确认**：涉及文件写入的操作，必须先展示变更内容并等待用户批准（除非用户已授权"无需确认"）。
