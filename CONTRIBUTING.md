# 向 Mini Harness 插件市场投稿

1. 在公开 GitHub 仓库里发布 Agent Skill。入口 `SKILL.md` 使用 UTF-8，frontmatter 写明 `name` 和 `description`，并提供许可证。
2. 用 `harness --skills-dir /path/to/skills` 在示例工作区试跑，记录命令、输入、产物、依赖和验证方式。移除示例中的隐私信息。
3. [提交插件](https://github.com/wac81/mini-harness-plugins/issues/new?template=plugin-submission.yml)，或者提交修改 `catalog.json` 的 PR。提供固定到完整 Git 提交的源码、许可证和实测示例。若你在报告使用量，请写明它统计下载、安装还是实际调用。

## 目录格式

`catalog.json` 的 `schema` 为 `2`，`plugins` 为条目数组。每条需要稳定的 `id`、三段数字版号 `version`、`category`、`author`、`license` 和 `source`。可选分类为 `office`、`writing`、`media`、`research`。`title`、`description` 和 `example` 取 `{ "en": "…", "zh": "…" }`，中文可省略。

`source` 包含 GitHub `repo`、40 位 `commit`、以 `SKILL.md` 结尾的 `path` 和文件内容 `sha256`。多文件 Skill 再提供 `source.archive`，字段相同，路径以 `.zip` 结尾。ZIP 根目录放原版 `SKILL.md`，保留相对脚本、参考资料和许可证。必须能验证与源码链接处的 `SKILL.md` 逐字节一致。ZIP 支持普通文件，压缩和解压大小各限 24 MiB。多文件插件在 Mini Harness 的本地工作区使用，安装只解包和验摘要，运行时继续使用应用的工具权限和依赖。

审核合并后，用户可以在应用内刷新目录。更新请保留 ID 并提高版本号，提供新的固定提交和摘要。

## 自动上架来源

`sources.json` 描述跟踪的发布者、目录、版本来源及许可证摘要。配置中的目录加入新 Skill 或已跟踪的包发生变化时，工作流经过内容检查自动发布。投稿适合推荐新的发布者和目录。维护者也可以直接提交目录条目。
