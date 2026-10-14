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

/** 页面地址（目录式，末尾带斜杠）：典籍封面、数据版、某个本。 */
export const coverUrl = (c: { id: string }) => url(`${c.id}/`);
export const dataUrl = (c: { id: string }) => url(`${c.id}/data/`);
export const witnessUrl = (c: { id: string }, w: { id: string }) => url(`${c.id}/${w.id}/`);

/**
 * 配置了 site 时（Pages 构建会传入），llms.txt 里的链接写成绝对地址；否则写相对地址。
 * 只认 http(s) 地址：环境里若有名叫 SITE 的变量（如字符串 "undefined"），不能当成站点地址。
 */
export function absoluteBase(): string {
  const site: unknown = import.meta.env?.SITE;
  return typeof site === 'string' && /^https?:\/\//.test(site) ? `${site.replace(/\/+$/, '')}${BASE}` : '';
}
