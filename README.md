# 《道德经》出土本存档

收录《老子》三种出土本、共六个版本的释文、简帛影像和元数据。每一行释文、每一张图都能追溯到一份登记了 SHA-256 的原始文件，释文照抄来源，不做任何转换。

设计细节见 [docs/storage-design.md](docs/storage-design.md)。

## 收录范围

| 版本 id | 内容 | 文本单位 | 影像 |
|---|---|---|---|
| `guodian-jia` | 郭店楚简《老子》甲组 | 39 枚简 | 39 张单简图版 |
| `guodian-yi` | 郭店楚简《老子》乙组 | 18 枚简 | 18 张单简图版 + 1 张照片 |
| `guodian-bing` | 郭店楚简《老子》丙组 | 14 枚简 | 14 张单简图版 |
| `mawangdui-jia` | 马王堆帛书《老子》甲本 | 81 章 | 8 页图版 + 1 张照片 |
| `mawangdui-yi` | 马王堆帛书《老子》乙本 | 81 章 | 8 页图版 |
| `beida` | 北京大学藏西汉竹书《老子》 | 223 条（221 枚简正面 + 2 条简背篇题） | 108 页图版 |

合计 456 条文本单位、197 张影像。马王堆两本暂按维基文库的通行本章节入库（`unit_type: chapter`），还没有逐行切分。传世本（王弼、河上公等）不在本阶段范围内。

各版本的出土时间、简数、出版信息等登记在 [data/witnesses.yaml](data/witnesses.yaml)，每条事实都写明依据；依据只来自网络搜索摘要的标为 `search-summary`，拿不准的字段写 `null`。

## 来源

| 来源 id | 内容 | 授权 |
|---|---|---|
| `wikisource-guodian` | 维基文库《郭店楚墓竹簡》，郭店三组释文 | CC BY-SA 4.0 |
| `wikisource-boshu` | 维基文库《老子 (帛書本)》，马王堆甲乙本按章释文 | 公有领域 |
| `tt24h-daodejing` | tt24h/daodejing v0.1.3 实录，北大本逐简释文；帛书逐行释文与排版数据暂只存原始文件 | CC0 1.0 |
| `jianbo-shufa-guodian-2002` | 《简帛书法选·郭店楚墓竹简·老子》（文物出版社 2002），郭店单简图版 | 见下 |
| `mawangdui-jicheng-2014` | 《长沙马王堆汉墓简帛集成》（中华书局 2014）册 1，帛书图版 | 见下 |
| `beida-2012` | 《北京大学藏西汉竹书〔贰〕》（上海古籍出版社 2012），北大本图版 | 见下 |
| `commons-laozi` | Wikimedia Commons 两张照片 | CC BY-SA 4.0 / 公有领域 |
| `guodian-1998` | 《郭店楚墓竹简》（文物出版社 1998） | 仅登记，未抓取 |
| `mawangdui-boshu-1` | 《马王堆汉墓帛书〔壹〕》 | 仅登记，未抓取 |

授权依据写在各来源记录 `data/sources/<id>.yaml` 的 `license.evidence` 里。项目所有者于 2026-10-14 决定：《道德经》为公版作品，本仓库用于学术研究，释文和影像全文入库，来源未标明授权条款的按可收录处理。各来源记录同时如实保留了来源自身的声明。

## 目录

```
data/
  witnesses.yaml          版本登记表
  sources/<id>.yaml       来源记录：出版信息、授权、抓取日期、原始文件哈希
  raw/<source>/           抓取到的原始文件，原样保存
  images/<source>/        简帛影像（从扫描本原样抽出的 JPEG，不重新编码）
  witnesses/<版本>.jsonl  文本单位，每行一枚简、帛书一行或一章，按阅读顺序
  plates/<版本>.jsonl     影像登记：每张图来自哪一页、对应哪些文本单位
schema/                   上述数据的 JSON Schema
scripts/                  导入、抽图版与校验脚本，以及 safegit
tests/                    测试（只用占位字符，不含真实释文）
docs/                     存储设计与 safegit 说明
```

文本单位的 `text` 照抄来源写法，包括通假字、隶定字形和符号；符号另在 `marks` 里结构化标注，残缺与补字记在 `damage`，来源注释记在 `notes`。目前所有单位的 `status` 都是 `unverified`，即只核对过一个来源。字段定义见 `schema/unit.schema.json`。

## 脚本

需要 Python 3 和 PyYAML、jsonschema。

```bash
python3 scripts/validate_data.py             # 校验全部数据
python3 -m unittest discover -s tests        # 运行测试
```

校验脚本检查结构、编号连续性、残缺区间、来源追溯、原始文件和影像的哈希，以及影像与文本单位的关联；授权状态为 `unknown` 的来源不能入库。有任何问题时退出码为 1。

| 脚本 | 作用 |
|---|---|
| `scripts/import_wikisource.py` | 把 `data/raw/` 下的维基文库页面切分成郭店（按简）和马王堆（按章）文本单位 |
| `scripts/import_tt24h.py` | 把 tt24h 北大汉简实录按简切分 |
| `scripts/extract_plates.py <PDF 目录>` | 从扫描本 PDF 原样抽出图版页 JPEG，生成 `data/plates/`；需要 poppler 的 `pdfimages`，PDF 的 SHA-256 必须与脚本内登记一致 |

两个导入脚本只读已登记哈希的原始文件，不联网。扫描本 PDF 本身不进仓库，只抽图版页。

## 还没做的事

- **章序对照**：把各版本对到通行本 81 章，需要有依据的底本。
- **交叉核对**：用第二个独立来源逐字核对，才能把 `status` 升为 `double-checked`。
- 马王堆两本按帛书行号逐行切分（tt24h 逐行释文已存于 `data/raw/`）。
- 《郭店楚墓竹简》（1998）和《马王堆汉墓帛书〔壹〕》尚无电子本，未抓取；Commons 上郭店甲、丙组两张照片因限速未下载。

## 参与

git 操作一律通过 `scripts/safegit`，新克隆后先运行：

```bash
scripts/safegit setup --name "<姓名>" --email "<邮箱>"
```

防护分层与审计用法见 [docs/safegit.md](docs/safegit.md)。
