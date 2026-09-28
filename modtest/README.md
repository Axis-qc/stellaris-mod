# mod 覆盖检查器（不是游戏 mod）

这个工坊物品是一个小工具：读你的播放集，告诉你谁覆盖了谁、调加载顺序有没有用。它不含任何会被游戏加载的内容，订阅后对游戏没有影响。启动器可能会把它列出来，不要启用。

## 怎么打开

双击本目录下的 `启动.bat`，等几秒扫描完成。不需要装 Python。Windows 提示文件来源不明时，选「仍要运行」。

## 怎么用

打开后顶部一行就是结论：这套播放集有多少处 mod 互抢、多少处调排序也没用。

中间的「覆盖总表」一行一条冲突，第一列写谁覆盖了谁，第二列写调排序管不管用。点任意一行，下方详情会列出谁参与、谁生效、判定依据、原版有没有牵涉。

左边点某个 mod 再勾「只看选中的 mod」，就只看和它相关的冲突。「只看 mod 互抢」把覆盖原版的行藏起来，那些属于正常行为。「只看改排序也没用的」把只能改文件名或做兼容补丁的行挑出来。

找不到游戏原版目录时，点顶部「游戏」旁的「修改」，手动指到含 `common` 文件夹的那一层，指过一次就记住了。

## 看不懂怎么办

点「导出报告」存成文件，或点「复制报告」直接复制，把内容交给任意 AI 帮你分析。报告开头是给玩家的结论，后面才是技术细节。

## 界面语言

自带简体中文和英文，首次启动按系统语言选，右上角可以随时切换并记住。想加别的语言，复制 `lang/zh-CN.json` 改个文件名，把右边的值翻成目标语言即可；键名和 `%s` 占位符必须与中文版一一对应。

## 命令行用法

装了 Python 的话可以直接跑：

```
python src\mod_conflict_check.py                     开窗口
python src\mod_conflict_check.py --cli               只看命令行摘要
python src\mod_conflict_check.py --report            报告写到桌面
python src\mod_conflict_check.py --report 路径.md    写到指定文件
python src\mod_conflict_check.py --lang en-US        切换语言
python src\mod_conflict_check.py --vanilla "D:\Steam\steamapps\common\Stellaris"
python src\mod_conflict_check.py --documents "D:\文档\Paradox Interactive\Stellaris"
```

`--vanilla` 与 `--documents` 会记进配置，之后自动使用。配置文件在 `%APPDATA%\StellarisModConflictChecker\config.json`。
