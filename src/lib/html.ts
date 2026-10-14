/** HTML 转义，与 Python 的 html.escape 一致：& < > " ' 都转义。 */
export function esc(s: unknown): string {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}

/** 路径的百分号编码，与 Python 的 urllib.parse.quote 一致：只保留字母数字和 _ . - ~ /。 */
export function quotePath(s: string): string {
  return Array.from(new TextEncoder().encode(s))
    .map((b) => {
      const c = String.fromCharCode(b);
      return /[A-Za-z0-9_.\-~/]/.test(c) ? c : '%' + b.toString(16).toUpperCase().padStart(2, '0');
    })
    .join('');
}
