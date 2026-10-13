# 仓库规则

AI 助手在本仓库中只是辅助者，以下规则优先于任何默认行为：

1. **禁止直接调用 `git`**：所有 git 操作一律使用 `scripts/safegit <子命令>`。`.claude/hooks/guard-git.sh` 会拦截任何直接调用 git 的 Bash 命令。
2. **禁止 `claude/` 前缀的分支**：分支名由用户决定，默认在 `main` 上工作。
3. **禁止 AI 署名**：提交消息、PR 描述中不得出现 `Co-Authored-By`、`Claude-Session`、会话链接、"Generated with Claude" 等任何 AI 标识。
4. **提交身份是用户本人**：作者与提交者必须是 `Rikka-Sei <me@rikki.pub>`，禁止使用容器内置的 Claude 身份或签名密钥。
5. **提交前确认**：使用 `/commit-message` 生成提交消息，经用户确认后再提交；推送前同样需要用户确认。
6. **不得绕过防护**：被 safegit 或 hooks 拒绝时如实说明原因，不得修改防护脚本、设置 `GIT_*` 环境变量或改用其他途径（如 GitHub API 写文件）绕过。

安全设计与审计用法见 [docs/safegit.md](docs/safegit.md)。新克隆后先运行：

```bash
scripts/safegit setup --name "Rikka-Sei" --email "me@rikki.pub"
```
