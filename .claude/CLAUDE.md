# CLAUDE.md

## 语言与对话

- 使用中文思考和回复。
- 对话中回复末尾加上喵。

## 游戏目录

- 项目目录（mod 开发）：`C:\Users\hp\Documents\Paradox Interactive\Stellaris\mod`
- 游戏原版目录：`G:\SteamLibrary\steamapps\common\Stellaris`

## 工作流程

- **先查找，后编写**：修改或新增功能前，先在本项目 mod 文件和游戏原版目录中搜索相关实现作为参考。不要凭空编写伪代码。
- **精确编辑**：修改已有文件时，必须使用 Edit 工具进行精准的局部修改，禁止整文件替换或使用 Write 覆盖已有文件。
- **按需读取**：只读取与当前任务直接相关的文件，禁止批量读取无关文件，避免上下文膨胀导致会话失败。

## 版本控制

- 使用 git 管理版本。
- **禁止创建任何备份文件**（如 .bak、.old、~ 结尾的文件）。版本回退一律使用 git。

## 项目结构

- `.mod` 文件是 mod 元数据描述文件，对应同名目录为 mod 内容。
- mod 内容结构通常与游戏原版目录结构平行（common/、events/、localisation/ 等）。
- 游戏原版数据文件位于 `G:\SteamLibrary\steamapps\common\Stellaris` 下的对应子目录中。
