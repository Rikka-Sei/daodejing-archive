import { afterEach, describe, expect, it, vi } from 'vitest';

/** BASE 在模块加载时定下，换 base 要重新加载模块。 */
async function load(env: { BASE_URL?: string; SITE?: string }) {
  vi.resetModules();
  if (env.BASE_URL !== undefined) vi.stubEnv('BASE_URL', env.BASE_URL);
  if (env.SITE !== undefined) vi.stubEnv('SITE', env.SITE);
  return import('../../src/lib/url');
}

afterEach(() => vi.unstubAllEnvs());

describe('站内地址', () => {
  it('根部署：地址从 / 开始', async () => {
    const u = await load({ BASE_URL: '/' });
    expect(u.url('llms.txt')).toBe('/llms.txt');
    expect(u.url()).toBe('/');
    expect(u.coverUrl({ id: 'laozi' })).toBe('/laozi/');
    expect(u.witnessUrl({ id: 'laozi' }, { id: 'guodian-jia' })).toBe('/laozi/guodian-jia/');
    expect(u.readerUrl({ id: 'laozi' }, { id: 'guodian-jia' })).toBe('/laozi/guodian-jia/read/');
    expect(u.chapterUrl({ id: 'laozi' }, 12)).toBe('/laozi/chapters/12/');
    expect(u.studyUrl({ id: 'laozi' }, { id: 'tt24h-daodejing' })).toBe('/laozi/study/tt24h-daodejing/');
  });

  it.each(['/daodejing-archive', '/daodejing-archive/'])('子路径部署（base=%s）：带不带结尾斜杠都一样', async (base) => {
    const u = await load({ BASE_URL: base });
    expect(u.url('laozi/guodian-jia.txt')).toBe('/daodejing-archive/laozi/guodian-jia.txt');
    expect(u.url('/fonts/a.woff2')).toBe('/daodejing-archive/fonts/a.woff2');
    expect(u.coverUrl({ id: 'laozi' })).toBe('/daodejing-archive/laozi/');
    expect(u.readerUrl({ id: 'laozi' }, { id: 'beida' })).toBe('/daodejing-archive/laozi/beida/read/');
    expect(u.chapterUrl({ id: 'laozi' }, 1)).toBe('/daodejing-archive/laozi/chapters/1/');
  });
});

describe('llms.txt 里的站点地址', () => {
  it('配了 site：站点加 base，没有多余的斜杠', async () => {
    expect((await load({ BASE_URL: '/x/', SITE: 'https://example.test/' })).absoluteBase()).toBe('https://example.test/x');
    expect((await load({ BASE_URL: '/', SITE: 'https://example.test' })).absoluteBase()).toBe('https://example.test');
  });

  it('GitHub 把挂在 CDN 后面的自定义域名报成 http：升成 https', async () => {
    expect((await load({ BASE_URL: '/', SITE: 'http://archive.example.test' })).absoluteBase()).toBe('https://archive.example.test');
    expect((await load({ BASE_URL: '/x/', SITE: 'http://archive.example.test/' })).absoluteBase()).toBe('https://archive.example.test/x');
  });

  it.each(['http://localhost:4321', 'http://localhost', 'http://127.0.0.1:4321', 'http://192.168.1.2', 'http://[::1]:4321', 'http://box.local', 'http://example.test:8080'])(
    '本机、内网地址与带端口的地址保持 http：%s',
    async (site) => {
      expect((await load({ BASE_URL: '/', SITE: site })).absoluteBase()).toBe(site);
    },
  );

  it('没配 site 或环境里的 SITE 不是网址（如字符串 "undefined"）：留空，写相对链接', async () => {
    expect((await load({ BASE_URL: '/', SITE: 'undefined' })).absoluteBase()).toBe('');
    expect((await load({ BASE_URL: '/', SITE: '' })).absoluteBase()).toBe('');
  });
});
