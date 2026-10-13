# shellcheck shell=bash
# safegit 策略定义：被 scripts/safegit 与 .githooks/* 共同 source。
# 修改本文件即修改仓库的 git 安全策略，请走评审。

# 禁止的分支/引用名（任意位置出现 claude/ 前缀）
SAFEGIT_FORBIDDEN_REF_RE='(^|[/:+])claude/'

# 提交消息中禁止出现的 AI 署名标记（不区分大小写，ERE）
SAFEGIT_FORBIDDEN_MSG_RE='co-authored-by[[:space:]]*:|claude-session[[:space:]]*:|claude\.ai/code|claude\.com/claude-code|generated (with|by) \[?claude|noreply@anthropic\.com|anthropic|🤖'

# 禁止的提交身份（作者/提交者的名字或邮箱）
SAFEGIT_FORBIDDEN_IDENT_RE='anthropic|(^|[^a-z])claude([^a-z]|$)'

# 禁止使用的签名配置（容器内置的 Claude 签名密钥/签名程序）
SAFEGIT_FORBIDDEN_SIGNING_RE='claude|/tmp/code-sign'

safegit_ref_forbidden() {
  printf '%s' "$1" | grep -Eiq -- "$SAFEGIT_FORBIDDEN_REF_RE"
}

safegit_msg_forbidden() {
  # 参数：消息文件路径；忽略 # 开头的注释行
  grep -v '^#' -- "$1" | grep -Eio -- "$SAFEGIT_FORBIDDEN_MSG_RE" | head -n1
}

safegit_ident_forbidden() {
  printf '%s' "$1" | grep -Eiq -- "$SAFEGIT_FORBIDDEN_IDENT_RE"
}
