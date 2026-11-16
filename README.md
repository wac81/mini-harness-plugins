# Mini Harness 插件市场

这里维护 [Mini Harness 插件目录](catalog.json)、经固定的上游 Skill 包和 [插件投稿](https://github.com/wac81/mini-harness-plugins/issues/new?template=plugin-submission.yml)。在应用里打开 **设置 → 插件 → 刷新目录** 即可加载目录。安装后展开插件详情，将示例命令粘贴到对话。

## 首发精选

| 插件 | 适用任务与选入依据 |
| --- | --- |
| [Last30Days](https://github.com/mvanhorn/last30days-skill) | 持续跟踪社区讨论和产品口碑。Skills.sh 约 6.26 万次安装。有第三方作者报告把它接入每天使用的研究工作流。[安装数据](https://www.skills.sh/mvanhorn/last30days-skill) · [用户案例](https://www.reddit.com/r/ClaudeCode/comments/1uqf6vp/new_to_making_skills_anyone_wanna_test_them/) |
| [Humanizer-zh](https://github.com/op7418/Humanizer-zh) | 给已有的中文文章和文档做最后一遍编辑。Skills.sh 约 5.84 万次安装，社区有人把它接入公众号和小红书编辑流程。[安装数据](https://www.skills.sh/op7418/humanizer-zh/humanizer-zh) · [社区反馈](https://github.com/op7418/Humanizer-zh/issues) |
| [Obsidian Markdown](https://github.com/obsidianmd/obsidian-skills) | 在已有知识库里重复整理会议、学习和项目笔记。单个 Skill 约 9.71 万次安装。[安装数据](https://www.skills.sh/obsidianmd/obsidian-skills/obsidian-markdown) · [用户讨论](https://www.reddit.com/r/ObsidianMD/comments/1q8gn9c/kepano_released_obsidianskills_repo_what_custom/) |
| [Anthropic PPTX](https://github.com/anthropics/skills/tree/main/skills/pptx) 和 [XLSX](https://github.com/anthropics/skills/tree/main/skills/xlsx) | 生成或编辑公司模板下的可编辑 PPT 和工作簿。有用户报告这两个官方技能是他们用得最多的，也有批量按品牌模板生成办公文件的案例。[近期反馈](https://www.reddit.com/r/ClaudeAI/comments/1xevkyg/drop_your_best_claude_skills_in_here/) · [模板复用案例](https://www.reddit.com/r/ClaudeCowork/comments/1tytr32/claude_skill_to_generate_word_documents_based_on/) |

数据采集于 2026 年 11 月 16 日。Skills.sh 统计 CLI 安装，重复使用证据来自发帖者的自述。欢迎在投稿时附上可复现案例、使用周期及产物。

## 维护和许可

[上架指南](CONTRIBUTING.md)列出了提交方式。每个条目链接到原作者固定提交，ZIP 保留上游技能内容和许可。Last30Days 包省略了文档用的演示图片和音频。各插件按自己的许可证分发。

## 自动上架

[同步工作流](.github/workflows/sync-catalog.yml)每天计划在北京时间 10:17 检查 [上游来源](sources.json)。当前跟踪 Last30Days 的稳定 Release、Humanizer-zh、Obsidian 官方 Skill 目录和 Anthropic 的办公 Skill。发现新条目或实质更新后，工作流检查许可证摘要、固定提交、Skill 格式和包完整性，通过后直接推送到 `main`。客户端下次刷新时即读到更新。工作流也支持立即运行。

目录变化只发布插件条目和安装包。用户在各自的项目里选择安装及启用。
