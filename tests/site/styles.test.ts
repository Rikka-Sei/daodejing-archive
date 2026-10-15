/** 样式的回归：这些规则是为修过的显示问题写的，改样式时别丢。 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const css = readFileSync(join(__dirname, '../../src/styles/site.css'), 'utf-8');
const rule = (sel: string) => css.split('\n').find((l) => l.startsWith(`${sel}{`)) ?? '';

describe('样式', () => {
  it('对读表高亮、钉住的底色垫在字下面，不盖住字', () => {
    expect(rule('table.al td')).toContain('isolation:isolate');
    expect(rule('table.al td.hl:after,table.al td.pin:after')).toContain('z-index:-1');
  });

  it('侧栏的子项不被压缩、滚动条不占宽度：任何页面、两条轴里检索框一样大，左右边距一致', () => {
    expect(rule('#side>*')).toContain('flex:none');
    expect(rule('#side')).toContain('scrollbar-width:none');
    expect(rule('#side')).not.toContain('scrollbar-gutter');
    expect(css).toContain('#side::-webkit-scrollbar{display:none}');
  });
});
