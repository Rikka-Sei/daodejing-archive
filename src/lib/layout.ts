/**
 * 简牍排布：把一个本的每一简、每一行排开，看它们各落在哪些章。纯函数，不读文件。
 * 一简（行）的 refs 依次指向对读表的一章和这一章里的若干列；相邻同章的合成一段，段的长短就是这一章在这一简上占几列（几个字）。
 */
import type { Line } from './alignment';

export interface Run {
  /** 章次 */
  n: number;
  /** 这一章在这一简（行）上占几个字 */
  len: number;
}

export interface Tile {
  no: string;
  /** 全部字数 */
  len: number;
  runs: Run[];
}

export interface Roll {
  /** 卷名：分卷时是分篇的名字，不分卷时为空 */
  title: string;
  tiles: Tile[];
}

export function tileOf(line: Line): Tile {
  const runs: Run[] = [];
  let len = 0;
  for (const [n, cols] of line.refs) {
    if (!cols.length) continue;
    len += cols.length;
    const last = runs[runs.length - 1];
    if (last && last.n === n) last.len += cols.length;
    else runs.push({ n, len: cols.length });
  }
  return { no: line.no, len, runs };
}

/** 一简属于哪一篇：取占字最多的那一章所在的篇（parts 里每篇的 to 是最后一章，升序）。 */
function partOf(t: Tile, parts: { to: number }[]): number {
  const by = new Map<number, number>();
  for (const r of t.runs) {
    const i = parts.findIndex((p) => r.n <= p.to);
    by.set(i, (by.get(i) ?? 0) + r.len);
  }
  let best = 0;
  let max = -1;
  for (const [i, len] of by) if (len > max) [best, max] = [i, len];
  return best;
}

/**
 * 把一个本的各简排成卷。依分篇切：相邻的简属于不同的篇时另起一卷，
 * 但只有每一篇恰好是连续的一段才分卷（如帛书德篇在前、道篇在后）；郭店这样各篇交错的就不分，合成一卷。
 */
export function rollsOf(lines: Line[], parts: { title: string; to: number }[]): Roll[] {
  const tiles = lines.map(tileOf);
  if (parts.length < 2 || !tiles.length) return [{ title: '', tiles }];
  const idx = tiles.map((t) => partOf(t, parts));
  const starts = idx.flatMap((p, i) => (i === 0 || p !== idx[i - 1] ? [i] : []));
  const seen = new Set(starts.map((s) => idx[s]));
  if (starts.length < 2 || seen.size !== starts.length) return [{ title: '', tiles }];
  return starts.map((s, k) => ({ title: parts[idx[s]].title, tiles: tiles.slice(s, starts[k + 1] ?? tiles.length) }));
}
