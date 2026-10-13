#!/usr/bin/env bash
# Claude Code PreToolUse hook（Bash）：
#   1. 拒绝任何直接调用 git 的命令，只允许 scripts/safegit；
#   2. 拒绝通过 shell 改动 safegit 自身、git hooks 与 Claude 配置。
# 被拒绝的调用会写入 safegit 审计日志。
set -uo pipefail

input="$(cat)"
cmd="$(jq -r '.tool_input.command // empty' <<<"$input")"
[[ -z "$cmd" ]] && exit 0

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

decide() {  # decide <deny|ask> <reason>
  "$ROOT/scripts/safegit" __log "claude-hook: $2" "$cmd" >/dev/null 2>&1 || true
  jq -cn --arg d "$1" --arg r "$2" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse", permissionDecision:$d, permissionDecisionReason:$r}}'
  exit 0
}

# 命令位置上出现的 git（行首、; & | ( ` 引号、$( 之后，可带 env/sudo/xargs 等前缀、VAR=x 赋值和路径）
RAW_GIT_RE='(^|[;&|({`"'"'"'!]|\$\()[[:space:]]*((sudo|env|exec|command|builtin|nohup|time|xargs|nice|eval|timeout[[:space:]]+[0-9.]+[smh]?)[[:space:]]+)*([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*\\?([^[:space:];&|"'"'"'`]*/)?git([[:space:];&|)`"'"'"']|$)'
if grep -Eq -- "$RAW_GIT_RE" <<<"$cmd"; then
  decide deny "本仓库禁止直接调用 git，请改用 scripts/safegit <子命令>（例如 scripts/safegit status）"
fi

# GIT_* 环境变量可绕过 safegit 的路径与配置约束
if grep -Eq -- '(^|[[:space:];&|])(export[[:space:]]+)?GIT_[A-Z_]+=' <<<"$cmd"; then
  decide deny "禁止在命令中设置 GIT_* 环境变量"
fi

# 改动受保护文件需要用户确认
PROTECTED_RE='scripts/safegit|scripts/lib/safegit-policy\.sh|\.githooks|\.claude/(settings[^[:space:]]*\.json|hooks)|\.git/(hooks|config|safegit)'
WRITE_RE='(^|[[:space:];&|])(rm|mv|cp|ln|chmod|chown|truncate|tee|dd|install|sed[[:space:]]+(-[a-zA-Z]*i|--in-place)|perl[[:space:]]+-[a-zA-Z]*i)([[:space:]]|$)'
REDIRECT_RE=">[[:space:]]*[^[:space:]&]*($PROTECTED_RE)"
if { grep -Eq -- "$PROTECTED_RE" <<<"$cmd" && grep -Eq -- "$WRITE_RE" <<<"$cmd"; } \
   || grep -Eq -- "$REDIRECT_RE" <<<"$cmd"; then
  decide ask "该命令可能修改 safegit / git hooks / Claude 配置等受保护文件，需要用户确认"
fi

exit 0
