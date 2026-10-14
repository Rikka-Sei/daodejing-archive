/** 数据仓库 data/ 里各类记录的形状。只写页面用到的字段，其余原样保留。 */

/** 释文里的残缺标注：按码点区间。 */
export interface Damage {
  start: number;
  end: number;
  kind: string;
}

export interface Note {
  by: string;
  text: string;
}

export type UnitType = 'slip' | 'silk-line' | 'chapter';

/** 一个文本单位：一枚简、帛书一行或一章。 */
export interface Unit {
  id: string;
  unit_type: UnitType;
  unit_no: string | number;
  text: string;
  damage?: Damage[];
  notes?: Note[];
  status?: string;
}

export type PlateKind = 'slip-plate' | 'page' | 'photo';

/** 一张影像及它对应的文本单位。 */
export interface Plate {
  file: string;
  kind: PlateKind;
  locator: string;
  units: string[];
  witness?: string;
  source?: string;
}

/** 版本登记表（witnesses.yaml）或来源登记（sources/*.yaml）里的一条，字段随来源而异。 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Meta = Record<string, any>;
