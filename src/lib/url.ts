/** 站内地址与仓库地址。 */

export const REPO_URL = 'https://github.com/Rikka-Sei/daodejing-archive';
export const REPO_RAW = 'https://raw.githubusercontent.com/Rikka-Sei/daodejing-archive/main/';

/**
 * 站点的 base，不带结尾斜杠：本地构建为空串，Pages 项目站点如“/daodejing-archive”。
 * Astro 的 BASE_URL 是否带斜杠取决于传进来的 base，所以统一在这里处理。
 */
export const BASE: string = (import.meta.env?.BASE_URL ?? '/').replace(/\/+$/, '');

/** 站内路径（相对站点根，如 laozi/guodian-yi.txt）→ 带 base 的地址。 */
export function url(path = ''): string {
  return `${BASE}/${path.replace(/^\/+/, '')}`;
}

/** 页面地址（目录式，末尾带斜杠）：典籍封面、某个本、它的阅读器、某一章的对读页、一份对照资料。 */
export const coverUrl = (c: { id: string }) => url(`${c.id}/`);
export const witnessUrl = (c: { id: string }, w: { id: string }) => url(`${c.id}/${w.id}/`);
export const readerUrl = (c: { id: string }, w: { id: string }) => url(`${c.id}/${w.id}/read/`);
export const chapterUrl = (c: { id: string }, n: number) => url(`${c.id}/chapters/${n}/`);
export const studyUrl = (c: { id: string }, s: { id: string }) => url(`${c.id}/study/${s.id}/`);
/** 打开一个本的入口：有逐行释文的竹简、帛书进阅读器，其余进本的页面。 */
export const openUrl = (c: { id: string; readable: { id: string }[] }, w: { id: string }) =>
  c.readable.some((r) => r.id === w.id) ? readerUrl(c, w) : witnessUrl(c, w);
export const lensUrl = (c: { id: string }) => url(`${c.id}/lens/`);
export const prefaceUrl = (c: { id: string }) => url(`${c.id}/preface/`);

/**
 * 站点地址：http 升成 https。Pages 总是提供 https，但自定义域名前面有 CDN（如 Cloudflare）时，
 * GitHub 会把站点报告成 http://。本机、内网地址和带端口的地址是在本地预览或自己架的服务器，保持原样。
 */
function secure(site: string): string {
  if (!URL.canParse(site)) return site;
  const { protocol, hostname, port } = new URL(site);
  const local = /^(localhost|\[.*\]|\d+(\.\d+){3})$|\.(localhost|local|lan|internal)$/i.test(hostname);
  return protocol === 'http:' && !port && !local ? `https:${site.slice('http:'.length)}` : site;
}

/**
 * 配置了 site 时（Pages 构建会传入），llms.txt 里的链接写成绝对地址；否则写相对地址。
 * 只认 http(s) 地址：环境里若有名叫 SITE 的变量（如字符串 "undefined"），不能当成站点地址。
 */
export function absoluteBase(): string {
  const site: unknown = import.meta.env?.SITE;
  return typeof site === 'string' && /^https?:\/\//.test(site) ? `${secure(site).replace(/\/+$/, '')}${BASE}` : '';
}
