/**
 * HarfBuzz 的子集化（hb-subset 的 WebAssembly 版，随 harfbuzzjs 发布）。
 *
 * 现成的 Node 封装（如 subset-font）没有开放“保留 .notdef 轮廓”和 name 表语言的开关：缺字时浏览器画的是
 * 第一个字体的 .notdef，轮廓被去掉就成了空白，读者看不出这里缺了字。所以这里直接调用，选项对应 pyftsubset 的
 * --layout-features=* --name-IDs=* --name-languages=* --name-legacy --notdef-outline --no-hinting。
 */
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

type Fn = (...args: number[]) => number;

/** 用到的 hb-subset 导出函数 */
interface HbSubset {
  memory: WebAssembly.Memory;
  _initialize(): void;
  malloc: Fn;
  free: Fn;
  hb_blob_create: Fn;
  hb_blob_destroy: Fn;
  hb_blob_get_data: Fn;
  hb_blob_get_length: Fn;
  hb_face_create: Fn;
  hb_face_destroy: Fn;
  hb_face_reference_blob: Fn;
  hb_set_add: Fn;
  hb_set_clear: Fn;
  hb_set_invert: Fn;
  hb_subset_input_create_or_fail: Fn;
  hb_subset_input_destroy: Fn;
  hb_subset_input_get_flags: Fn;
  hb_subset_input_set: Fn;
  hb_subset_input_set_flags: Fn;
  hb_subset_input_unicode_set: Fn;
  hb_subset_input_pin_axis_location: Fn;
  hb_subset_or_fail: Fn;
}

const HB_MEMORY_MODE_WRITABLE = 2;
/** OpenType 规定的标准 name 条目是 0 到 25 */
const MAX_NAME_ID = 25;
// hb_subset_sets_t
const SET_NAME_ID = 4;
const SET_NAME_LANG_ID = 5;
const SET_LAYOUT_FEATURE_TAG = 6;
// hb_subset_flags_t
const FLAG_NO_HINTING = 0x1;
const FLAG_NAME_LEGACY = 0x8;
const FLAG_NOTDEF_OUTLINE = 0x40;

let loaded: Promise<HbSubset> | undefined;
function load(): Promise<HbSubset> {
  loaded ??= WebAssembly.instantiate(readFileSync(createRequire(import.meta.url).resolve('harfbuzzjs/dist/harfbuzz-subset.wasm'))).then(
    ({ instance }) => {
      const hb = instance.exports as unknown as HbSubset;
      hb._initialize();
      return hb;
    },
  );
  return loaded;
}

const tag = (name: string) => [...name].reduce((a, ch) => (a << 8) + ch.charCodeAt(0), 0);

/**
 * 只留 text 里的字，得到 TrueType 字体。axes 把变体字体的轴取定成一个数值（如 { wght: 400 } 得到静态字体）。
 * 竖排用的 vert/vrt2 等排版特征、name 表的标准条目（各语言）、缺字时画的 .notdef 轮廓都保留，hinting 去掉。
 */
export async function hbSubset(font: Uint8Array, text: string, axes: Record<string, number> = {}): Promise<Uint8Array> {
  const hb = await load();
  const heap = () => new Uint8Array(hb.memory.buffer); // 内存增长后旧的视图会失效，每次现取

  const input = hb.hb_subset_input_create_or_fail();
  if (!input) throw new Error('hb_subset_input_create_or_fail 失败');
  const fontPtr = hb.malloc(font.byteLength);
  heap().set(font, fontPtr);
  const blob = hb.hb_blob_create(fontPtr, font.byteLength, HB_MEMORY_MODE_WRITABLE, 0, 0);
  const face = hb.hb_face_create(blob, 0);
  hb.hb_blob_destroy(blob);
  let subset = 0;
  try {
    for (const set of [SET_LAYOUT_FEATURE_TAG, SET_NAME_LANG_ID]) {
      const s = hb.hb_subset_input_set(input, set);
      hb.hb_set_clear(s);
      hb.hb_set_invert(s); // 清空再取反，就是全部保留
    }
    // name 表只留标准条目（版权、授权等）；取定字重后用不到的“字体实例”名称（256 以上）不要
    const nameIds = hb.hb_subset_input_set(input, SET_NAME_ID);
    for (let id = 0; id <= MAX_NAME_ID; id++) hb.hb_set_add(nameIds, id);
    hb.hb_subset_input_set_flags(
      input,
      hb.hb_subset_input_get_flags(input) | FLAG_NO_HINTING | FLAG_NAME_LEGACY | FLAG_NOTDEF_OUTLINE,
    );
    const unicodes = hb.hb_subset_input_unicode_set(input);
    for (const c of text) hb.hb_set_add(unicodes, c.codePointAt(0)!);
    for (const [axis, value] of Object.entries(axes)) {
      if (!hb.hb_subset_input_pin_axis_location(input, face, tag(axis), value)) {
        throw new Error(`没法把字体的 ${axis} 轴取定为 ${value}：字体里可能没有这根轴`);
      }
    }
    subset = hb.hb_subset_or_fail(face, input);
    if (!subset) throw new Error('hb_subset_or_fail 失败：字体文件可能已损坏');
    const out = hb.hb_face_reference_blob(subset);
    try {
      const length = hb.hb_blob_get_length(out);
      if (!length) throw new Error('裁出的子集是空的');
      const offset = hb.hb_blob_get_data(out, 0);
      return Uint8Array.from(heap().subarray(offset, offset + length)); // 复制出来，wasm 里的内存随后释放
    } finally {
      hb.hb_blob_destroy(out);
    }
  } finally {
    if (subset) hb.hb_face_destroy(subset);
    hb.hb_face_destroy(face);
    hb.hb_subset_input_destroy(input);
    hb.free(fontPtr);
  }
}
