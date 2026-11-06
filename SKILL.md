---
name: wechat-chat-export
description: Export the user's own Windows WeChat 4.x local chat history to files, including selected individual chats or groups. Use for requests to export, archive, or back up readable WeChat chat records; this does not send messages or analyze conversations.
---

# Windows 微信聊天记录导出

将已登录账号的本机微信数据库解密到短期临时目录，按会话精确导出 JSON、CSV 和 HTML。不要把聊天正文或数据库密钥打印到对话、日志或外部服务。只导出用户明确指定的会话及格式，不分析内容，除非另有要求。

## 使用

- 需要 Windows、已登录的微信 4.x、本机已有聊天记录，以及 Python 3.10+。当前实现曾在微信 4.1.15.56 验证过；新版本可能不兼容。手机中未同步到电脑的记录无法保证导出。
- 技能目录自带经裁剪的 Moect `wx4` 导出代码（GPL-3.0，见 `vendor/LICENSE-Moect.txt`）。优先使用技能目录下 `.venv\Scripts\python.exe`；如环境缺失，重建并安装 `pycryptodomex==3.24.1`、`zstandard==0.25.0`、`psutil==7.2.2`。不要使用旧的 `wechat-skill`。
- 运行 `python scripts/export_wechat.py accounts` 查看本机账号目录。只有一个账号时可自动选择；多个账号时必须用 `--account` 指定准确目录名，不能把最近修改视为必然是目标账号。账号标识本身也应视为敏感信息。
- 运行 `export ... --list` 仅显示精确名称匹配的会话编号、类型、消息数和时间范围，不输出正文。会话 ID 和同名会话排序可能变化；同名时先核对并让用户确认，用 `--session <会话ID>` 精确选择，或在用户明确要求全部同名群时使用 `--all-matches`。不要根据搜索顺序臆断。
- 用户已明确要求导出时，运行 `export ... --out <目录> --chat <精确名称>`；可重复 `--chat`。提供 `--group-only` 限定群聊；`--all-matches` 仅用于用户明确要求全部同名会话。默认生成 JSON、CSV、HTML，可以用 `--formats` 限定。输出路径必须为用户指定或清楚约定的位置，避免覆盖已有文件。
- 示例：`python scripts/export_wechat.py export --account <账号目录名> --chat "项目群" --group-only --list`，确认后去掉 `--list` 并加 `--out D:\\微信导出`。运行后核对每个会话的计数、时间范围、文件与缺失数据库提示；不要把部分导出描述为完整备份。
- 密钥仅在内存中，程序在临时目录保存解密数据库、关闭连接并清理。若被强制中止，检查并清理其输出的临时目录。临时目录包括其他聊天的数据库内容，需保护访问权限；不得提供数据库原件或密钥。保留解密失败和缺失分片警告。
- 默认导出消息记录及文本中可解析的元数据，不导出图片、视频、语音和文件原件；仅当用户另行要求且经验证后处理媒体。说明取决于本机数据及微信版本，不能保证历史完整。
