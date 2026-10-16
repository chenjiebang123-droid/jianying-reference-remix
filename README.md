# JianYing Reference Remix Skill

参考视频分析、完整动作选镜、差异化混剪和剪映可编辑工程交付。

本包将实际批量剪辑流程整理为可配置 skill：分析每条参考片的结构、镜头、字幕、音乐节奏、开头钩子和 CTA，再由代理审看素材、编写分镜计划并生成工程。默认每条三版，单稿内同一源文件只出现一次。选镜优先考虑语义与动作完整性，再考虑跨版本素材差异。

## 安装

将仓库中的 `jianying-reference-remix` 文件夹复制到 Codex 的个人 skills 目录，例如 Windows 的 `%USERPROFILE%\.codex\skills\`，重新加载技能后使用：

```text
使用 $jianying-reference-remix 处理我的素材目录，每条参考片生成三个剪映工程。
```

Python 3.10+、FFmpeg、FFprobe 用于分析。生成工程还需单独安装 `jianying-editor`（JyWrapper）；本包不分发该第三方工具或其依赖。通过 `JY_SKILL_ROOT` 指定其安装位置，或使用默认个人 skills 目录。路径与素材均由用户提供。

`scripts/remix.py` 提供 inventory、analyze、check-plan、build、verify 命令。运行 `python jianying-reference-remix/scripts/remix.py --help` 查看用法。计划格式见技能内的 `references/plan-format.md`。

## 输出与边界

输出包含分析证据、审看后的计划、素材清单、工程索引、工程备份和核验结果。视频素材通过原始路径引用，移动素材后需要重新链接。FFmpeg 的切点与 BPM 是候选估计；代理仍须审看完整动作和语义。工程结构通过验证不代表最终画面已验收；音乐、配音、剪映打开测试及 MP4 导出状态须在交付中说明。

仓库仅包含通用工作流与工具，不包含用户视频、客户报告、个人路径、账号凭据或旧工程。

## 配音技能

仓库另含 `jianying-voiceover`：按确认文案生成中文、巴西葡语、英语等语言配音，输出 WAV、按实测片段时间生成的 SRT 和配音清单，也支持用户已有的 PCM WAV 录音。将该文件夹复制到个人 skills 目录后，可使用：

```text
使用 $jianying-voiceover 为这条视频生成巴西葡语配音和分段字幕，并接入剪映工程。
```

在线生成依赖单独安装的 `speech` skill、OpenAI Python SDK 和本机 `OPENAI_API_KEY` 环境变量；密钥不要写入仓库或聊天。默认内置音色 cedar，支持在脚本中调整音色、语气、语速和停顿。配音为 AI 生成。无密钥时可先 `--dry-run` 检查请求，或用 `assemble` 拼接已有录音。

配音脚本格式见 `jianying-voiceover/references/script-format.md`，巴西葡语示例在 `assets/example-pt-BR.json`。`generate` 调用 speech 的批量工具；`assemble` 根据实际音频时长生成字幕；`attach` 将配音接入新版 remix 计划。超过时长预算的配音会保留完整语句并标记需调整，未解决的超时不能直接接入工程。最终发音与画面同步仍需核听。
