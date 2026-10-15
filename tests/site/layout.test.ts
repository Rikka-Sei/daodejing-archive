/** 简牍排布：一简占哪几章、按分篇分卷。用占位的行，不含真实释文。 */
import { describe, expect, it } from 'vitest';
import type { Line } from '../../src/lib/alignment';
import { rollsOf, tileOf } from '../../src/lib/layout';

const line = (no: string, ...refs: [number, number[]][]): Line => ({ no, text: '', refs });
const PARTS = [
  { title: '上篇', to: 3 },
  { title: '下篇', to: 6 },
];

describe('tileOf', () => {
  it('按列数算字数；相邻同章的合成一段，跨章的分成几段', () => {
    expect(tileOf(line('1', [1, [0, 1, 2]]))).toEqual({ no: '1', len: 3, runs: [{ n: 1, len: 3 }] });
    expect(tileOf(line('2', [1, [4, 5]], [1, [6]], [2, [0, 1]]))).toEqual({
      no: '2',
      len: 5,
      runs: [
        { n: 1, len: 3 },
        { n: 2, len: 2 },
      ],
    });
  });

  it('没有列的记号不算字', () => {
    expect(tileOf(line('3', [1, []], [2, [0]]))).toEqual({ no: '3', len: 1, runs: [{ n: 2, len: 1 }] });
  });
});

describe('rollsOf', () => {
  it('每一篇恰好是连续的一段时分卷，卷名取分篇的名字', () => {
    const rolls = rollsOf([line('1', [5, [0]]), line('2', [6, [0]]), line('3', [1, [0]]), line('4', [2, [0]])], PARTS);
    expect(rolls.map((r) => [r.title, r.tiles.map((t) => t.no)])).toEqual([
      ['下篇', ['1', '2']],
      ['上篇', ['3', '4']],
    ]);
  });

  it('各篇交错（回到前一篇）就不分卷', () => {
    const rolls = rollsOf([line('1', [1, [0]]), line('2', [5, [0]]), line('3', [2, [0]])], PARTS);
    expect(rolls).toHaveLength(1);
    expect(rolls[0].title).toBe('');
    expect(rolls[0].tiles).toHaveLength(3);
  });

  it('全在一篇、没有分篇、没有行：一卷', () => {
    expect(rollsOf([line('1', [1, [0]]), line('2', [2, [0]])], PARTS)).toHaveLength(1);
    expect(rollsOf([line('1', [1, [0]]), line('2', [5, [0]])], [])).toHaveLength(1);
    expect(rollsOf([], PARTS)).toEqual([{ title: '', tiles: [] }]);
  });

  it('一简跨两篇时归占字多的一篇', () => {
    const rolls = rollsOf([line('1', [1, [0]], [5, [0, 1, 2]]), line('2', [2, [0]])], PARTS);
    expect(rolls.map((r) => r.title)).toEqual(['下篇', '上篇']);
  });
});
