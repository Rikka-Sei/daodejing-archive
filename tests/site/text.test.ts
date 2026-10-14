import { describe, expect, it } from 'vitest';
import { esc, quotePath } from '../../src/lib/html';
import { colophon, commonId, facts, labelText, licenseBrief, licenseLabel, markDamage, splitName } from '../../src/lib/text';
import type { Unit } from '../../src/lib/types';

const unit = (unit_type: string, unit_no: string) => ({ unit_type, unit_no }) as Unit;

describe('编号与命名', () => {
  it('单位的标签', () => {
    expect(labelText(unit('slip', '12'))).toBe('简12');
    expect(labelText(unit('chapter', '38'))).toBe('第38章');
    expect(labelText(unit('slip', '2背'))).toBe('简2背');
    expect(labelText(unit('silk-line', '5'))).toBe('行5');
  });

  it('一组版本 id 的共同前缀', () => {
    expect(commonId(['guodian-jia', 'guodian-yi', 'guodian-bing'])).toBe('guodian');
    expect(commonId(['w-a', 'w-b'])).toBe('w');
    expect(commonId(['beida'])).toBe('beida');
    expect(commonId(['x-a', 'y-b'])).toBe('x-a'); // 没有共同前缀：取第一个
  });

  it('版本名拆成文献名与本名', () => {
    expect(splitName('甲书《占位》甲组')).toEqual(['甲书', '甲组']);
    expect(splitName('乙书《占位》')).toEqual(['乙书', '全本']);
    expect(splitName('丙书')).toEqual(['丙书', '全本']);
  });
});

describe('残缺标注', () => {
  it('转义并包上样式', () => {
    expect(markDamage('甲<乙>丙丁', [{ kind: 'missing', start: 1, end: 3 }])).toBe(
      '甲<span class="d-missing">&lt;乙</span>&gt;丙丁',
    );
  });

  it('区间按码点算：生僻字占两个 UTF-16 单元，不能错位', () => {
    expect(markDamage('𠕁甲乙', [{ kind: 'missing', start: 1, end: 2 }])).toBe('𠕁<span class="d-missing">甲</span>乙');
  });

  it('没有标注、区间越界都照常输出', () => {
    expect(markDamage('甲乙', null)).toBe('甲乙');
    expect(markDamage('甲乙', [{ kind: 'missing', start: 1, end: 9 }])).toBe('甲<span class="d-missing">乙</span>');
  });
});

describe('授权与识语', () => {
  it('授权的一句话', () => {
    expect(licenseLabel({ status: 'cc', name: 'CC BY-SA 4.0' })).toBe('CC BY-SA 4.0');
    expect(licenseLabel({ status: 'public-domain', name: null })).toBe('来源未标明，按可收录处理');
    expect(licenseLabel({ status: 'unknown' })).toBe('来源未标明');
    expect(licenseLabel(null)).toBe('来源未标明');
  });

  it('授权概要：授权名去重，没登记的记作未标明', () => {
    expect(licenseBrief([{ license: { name: 'CC0' } }, { license: { name: 'CC0' } }, {}])).toBe('CC0、未标明');
    expect(licenseBrief([{ license: { name: 'CC0；CC BY 4.0' } }])).toBe('CC0、CC BY 4.0');
  });

  it('识语与版本信息', () => {
    const w = { excavated: { year: 1993, month: 10, place: '某地' }, slips: { count: 39 } };
    expect(colophon(w)).toBe('1993年10月出土于某地；存简39枚。');
    expect(Object.fromEntries(facts(w))).toEqual({ '出土 / 入藏': '1993 年 10 月 · 某地', 简数: '39 枚' });
  });
});

describe('转义', () => {
  it('与 Python 的 html.escape 一致', () => {
    expect(esc(`<a href="x">&'</a>`)).toBe('&lt;a href=&quot;x&quot;&gt;&amp;&#x27;&lt;/a&gt;');
  });

  it('路径转义保留斜杠，其余按 UTF-8 百分号转义', () => {
    expect(quotePath('data/images/郭店楚简《老子乙》01826.jpg')).toBe(
      'data/images/%E9%83%AD%E5%BA%97%E6%A5%9A%E7%AE%80%E3%80%8A%E8%80%81%E5%AD%90%E4%B9%99%E3%80%8B01826.jpg',
    );
  });
});
