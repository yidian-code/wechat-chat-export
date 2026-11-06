# 微信聊天记录导出技能

这是一个供 Codex 使用的 Windows 微信 4.x 本地聊天记录导出技能。你可以按会话导出已有的聊天记录，生成 HTML、CSV 和 JSON 文件。它不会发送消息或分析聊天内容。

该项目基于 [Moect](https://github.com/mofan6/Moect) 的部分代码，使用 GPL-3.0 许可证，与微信及腾讯没有官方关联。

## 使用前了解

- 需要 Windows、Python 3.10 或更高版本，以及已登录的 Windows 微信 4.x。已在微信 4.1.15.56 上完成一次实际导出；其他版本需要自行验证。
- 只能读取电脑上已有的数据。手机上的聊天记录如果没有同步到电脑，可能不会出现在导出结果中。
- 默认导出消息和可解析的文本元数据；图片、语音、视频和文件原件不会随消息导出。
- 导出期间，程序从本机微信进程读取数据库密钥，仅保存在内存中，并将相关数据库解密到系统临时目录。临时数据库可能包含其他会话的内容。正常结束时程序关闭连接并删除临时目录；如果进程被强制终止，请根据程序打印的路径检查并删除残留。
- 请只导出自己有权访问和处理的聊天记录。导出文件含有对话双方的信息，请妥善保管。

## 安装到 Codex

1. 下载或克隆本仓库，在 PowerShell 中进入项目目录。
2. 将项目复制到你的用户技能目录：

   ```powershell
   $skillDir = Join-Path $env:USERPROFILE '.codex\skills\wechat-chat-export'
   if (Test-Path -LiteralPath $skillDir) { throw '技能目录已存在，请先检查。' }
   New-Item -ItemType Directory -Force (Split-Path $skillDir) | Out-Null
   Copy-Item -LiteralPath (Get-Location).Path -Destination $skillDir -Recurse
   ```

3. 为技能创建 Python 环境并安装依赖：

   ```powershell
   python -m venv "$skillDir\.venv"
   & "$skillDir\.venv\Scripts\python.exe" -m pip install -r "$skillDir\requirements.txt"
   & "$skillDir\.venv\Scripts\python.exe" "$skillDir\scripts\export_wechat.py" --help
   ```

4. 在下一轮 Codex 对话中，要求使用 `wechat-chat-export` 导出指定联系人或群聊，并指定保存目录。

如果技能没有出现在新对话中，重启 Codex 后重试。安装技能不会自动导出数据。

## 命令行使用

保持电脑微信登录。在 PowerShell 中设置技能路径和 Python 路径：

```powershell
$skillDir = Join-Path $env:USERPROFILE '.codex\skills\wechat-chat-export'
$python = Join-Path $skillDir '.venv\Scripts\python.exe'
$tool = Join-Path $skillDir 'scripts\export_wechat.py'
$env:PYTHONIOENCODING = 'utf-8'
```

列出本机账号目录：

```powershell
& $python $tool accounts
```

有多个账号时，把以下 `ACCOUNT_DIR` 替换为上一步显示的准确账号目录名，并将 `CHAT_NAME` 替换为微信中的完整会话名。先只查看匹配情况：

```powershell
& $python $tool export --account 'ACCOUNT_DIR' --chat 'CHAT_NAME' --group-only --list
```

确认群聊后，将 `OUTPUT_DIR` 替换为目标文件夹并导出：

```powershell
& $python $tool export --account 'ACCOUNT_DIR' --chat 'CHAT_NAME' --group-only --out 'OUTPUT_DIR'
```

`--chat` 可以重复传入。对于个人会话，去掉 `--group-only`。如果有同名会话，先使用 `--list` 查看会话 ID，确认后添加 `--session 'SESSION_ID'`；需要全部同名会话时才使用 `--all-matches`。使用 `--formats csv json` 可指定格式。已有目标文件不会被覆盖。

完成后检查程序显示的消息条数、时间范围和警告。无法解密的数据库分片或电脑上缺失的历史记录可能导致结果不完整。

## 故障排查

- **找不到账号或密钥**：确认 Windows 微信已经登录，且账号数据保存在本机。程序必须有读取微信进程及数据目录的权限；部分环境可能需要以管理员身份运行。
- **找不到群聊**：检查群名是否完全一致，以及当前选择的账号是否正确。先用 `--list` 检查匹配结果。
- **消息条数少于预期**：检查电脑微信的历史记录是否完整，并留意缺失数据库或解密失败的警告。
- **新版微信无法读取**：微信的数据库和进程结构可能发生变化；不要把已验证版本的结果推断为所有版本均兼容。

## 许可证

项目使用 [GPL-3.0](LICENSE)。来源与第三方许可信息见 [vendor/SOURCE.txt](vendor/SOURCE.txt) 和 [第三方声明](vendor/THIRD_PARTY_NOTICES.md)。
