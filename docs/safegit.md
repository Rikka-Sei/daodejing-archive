# safegit：git 防护与安全审计

本仓库禁止 AI 助手直接调用 `git`，所有 git 操作都必须经过 `scripts/safegit`。目标有三个：

1. 不出现 `claude/` 前缀的分支；
2. 提交历史里不出现任何 AI 署名（`Co-Authored-By`、`Claude-Session`、会话链接等），提交身份始终是仓库所有者本人；
3. 每一次 git 操作都留下可校验的审计记录。

## 防护分层

| 层 | 文件 | 作用 |
|---|---|---|
| 1. Claude Code 权限 | `.claude/settings.json` | `deny` 掉 `Bash(git *)`、`.git/**` 写入，以及 GitHub MCP 的写文件、建分支、合并等工具；改动防护文件、`safegit push`、`safegit setup` 都要用户确认；关闭提交与 PR 的自动署名；`deny` 掉 GitHub MCP 创建 PR、Issue、评论和评审的工具（服务端会自动追加 AI 页脚） |
| 2. Claude Code hook | `.claude/hooks/guard-git.sh` | PreToolUse 拦截任何位置上的 git 调用，包括 `cd x && git`、`env git`、`xargs git`、`bash -c "git …"`、`$(git …)`、`/usr/bin/git`；禁止设置 `GIT_*` 环境变量；通过 shell 改写受保护文件时要求确认。被拦截的调用写入审计日志 |
| 2b. GitHub 工具 hook | `.claude/hooks/guard-github.sh` | PreToolUse 拦截 GitHub MCP 的发帖类工具（与第 1 层的 deny 列表一致，作为第二道防线）；其余 GitHub 工具的参数中出现 AI 署名标记时拒绝，规则取自策略库 |
| 3. safegit 包装器 | `scripts/safegit` | 子命令白名单加参数检查，清除调用方的 `GIT_*` 环境变量，并强制 `core.hooksPath=.githooks` |
| 4. git hooks | `.githooks/commit-msg`、`.githooks/pre-push` | 无论从哪个入口提交或推送，都会检查消息、身份和引用名 |
| 5. 策略库 | `scripts/lib/safegit-policy.sh` | 第 2b、3、4 层共用的正则规则 |

## safegit 拒绝的操作

- **分支**：任何参数或当前分支含 `claude/`；`branch -D/-d/-m/-M/-f`；`switch -C/-f`；`checkout -B/-f/--/.`
- **提交**：`--amend`、`--no-verify`、`--author`、`--date`、复用消息；作者或提交者身份含 `anthropic`/`claude`；用容器内置的 Claude 密钥签名
- **推送**：`--force*`、`--mirror`、`--all`、`--delete`、`+refspec`、`:refspec`、`--no-verify`
- **破坏性命令**：`reset`、`rebase`、`clean`、`filter-branch`、`update-ref`、`config` 写入、`remote add/set-url`、`stash drop/clear`、`reflog expire/delete`，以及其他不在白名单中的子命令
- **全局选项**：只接受 `-c user.signingkey=<GPG 指纹>[!]`，供 `/commit-message` 的"预置 GPG KEY"选项使用

## 审计

审计日志位于 `.git/safegit/audit.log`，在 `.git` 目录内，不会进入版本历史，权限为 600。每行是一条 JSON，记录时间、执行者（`claude-code` 或用户名）、pid、目录、分支、完整参数、放行或拒绝、原因、退出码。每条记录包含上一条的哈希（`prev`）和本条的 SHA-256（`hash`），形成哈希链。

```bash
scripts/safegit audit log 50   # 查看最近 50 条记录
scripts/safegit audit verify   # 校验哈希链：中间任何一条被改动或删除都会被发现
scripts/safegit audit scan     # 全面体检：分支名、全部提交的身份和消息、本地配置、日志完整性
```

## 已知局限

- 这是一套纵深防御，不是沙箱。能执行任意代码的进程仍然可以绕过，例如用变量拼出命令名，或在 Python 里调用 git。hook 只能拦截能看出来的写法。
- 哈希链只能证明日志写入后没被篡改，不能防止整份日志被删除后重建。需要更强保证时，可以定期把 `audit verify` 的最后一个哈希记录到仓库外。
- hook 的规则偏严，会误拦参数里写着 `"git ..."` 字样的命令（例如 `grep "git status"`）。此时请换一种写法，不要放宽规则。
- 新克隆的仓库必须先运行 `scripts/safegit setup`，否则 `.githooks` 不会被普通 `git` 使用（safegit 自身始终会强制启用）。
