# 《道德经》文献存档

收录《老子》三种出土本、共六个版本的释文、简帛影像和元数据，以及传世的王弼本、后人校订的本子，和 tt24h 整理的逐章对读表（八个版本同列逐字对照）。每一行释文、每一张图都能追溯到一份登记了 SHA-256 的原始文件，释文照抄来源，不做任何转换。

设计细节见 [docs/storage-design.md](docs/storage-design.md)，展示站见 [docs/site.md](docs/site.md)。

## 收录范围

| 版本 id | 内容 | 文本单位 | 影像 |
|---|---|---|---|
| `guodian-jia` | 郭店楚简《老子》甲组 | 39 枚简 | 39 张单简图版 |
| `guodian-yi` | 郭店楚简《老子》乙组 | 18 枚简 | 18 张单简图版 + 1 张照片 |
| `guodian-bing` | 郭店楚简《老子》丙组 | 14 枚简 | 14 张单简图版 |
| `mawangdui-jia` | 马王堆帛书《老子》甲本 | 81 章 | 8 页图版 + 1 张照片 |
| `mawangdui-yi` | 马王堆帛书《老子》乙本 | 81 章 | 8 页图版 |
| `beida` | 北京大学藏西汉竹书《老子》 | 223 条（221 枚简正面 + 2 条简背篇题） | 108 页图版 |
| `wangbi` | 王弼本《老子》（传世本；释文取自 tt24h 实录，底本浙江書局本） | 81 章 | 无 |
| `jiaoding` | 校订本（tt24h 整理者对照各本断句校订的本子） | 81 章 | 无 |

合计 618 条文本单位（出土本 456 条，王弼本、校订本各 81 章）、197 张影像。马王堆两本在 `data/witnesses/` 里仍按维基文库的通行本章节入库（`unit_type: chapter`），逐行的实录在 `data/alignment/lines/`。河上公等其他传世本、拓本和论文类资料暂未收录，之后可按同样的结构追加。

各版本的出土时间、简数、出版信息等登记在 [data/witnesses.yaml](data/witnesses.yaml)，每条事实都写明依据；依据只来自网络搜索摘要的标为 `search-summary`，拿不准的字段写 `null`。`kind` 标明材料的性质：出土本（一手材料）、拓本、传世本、校订本。

## 来源

| 来源 id | 内容 | 授权 |
|---|---|---|
| `wikisource-guodian` | 维基文库《郭店楚墓竹簡》，郭店三组释文 | CC BY-SA 4.0 |
| `wikisource-boshu` | 维基文库《老子 (帛書本)》，马王堆甲乙本按章释文 | 公有领域 |
| `tt24h-daodejing` | tt24h/daodejing v0.1.3（《老子道德经：四种原文表》源码）：北大本逐简释文，王弼本与校订本，八个版本的逐章对读表，帛书与郭店的逐行实录，补充字体 | CC0 1.0（字体为 OFL 1.1） |
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
  alignment/              逐章对读表与逐行释文（tt24h 整理）；由 scripts/import_alignment.py 从 raw/ 生成，不手改
schema/                   上述数据的 JSON Schema
scripts/                  导入、抽图版与校验脚本，生成固定字体的脚本，以及 safegit
src/、public/             展示站（Astro），见 docs/site.md
tests/                    测试（只用占位字符，不含真实释文）
docs/                     存储设计、展示站与 safegit 说明
```

文本单位的 `text` 照抄来源写法，包括通假字、隶定字形和符号；符号另在 `marks` 里结构化标注，残缺与补字记在 `damage`，来源注释记在 `notes`。目前所有单位的 `status` 都是 `unverified`，即只核对过一个来源。字段定义见 `schema/unit.schema.json`。

对读表按王弼本分 81 章，同一章里各版本的格子同列对齐；逐行释文是各底本照简、照行的原文，每个字指向对读表里的一格。格子与文件的写法见 [docs/storage-design.md](docs/storage-design.md)。

## 脚本

需要 Python 3 和 PyYAML、jsonschema。

```bash
python3 scripts/validate_data.py             # 校验全部数据
python3 -m unittest discover -s tests        # 运行测试
```

校验脚本检查结构、编号连续性、残缺区间、来源追溯、原始文件和影像的哈希，影像与文本单位的关联，以及对读表与逐行释文是否互相对得上；授权状态为 `unknown` 的来源不能入库。有任何问题时退出码为 1。

| 脚本 | 作用 |
|---|---|
| `scripts/import_wikisource.py` | 把 `data/raw/` 下的维基文库页面切分成郭店（按简）和马王堆（按章）文本单位 |
| `scripts/import_tt24h.py` | 把 tt24h 北大汉简实录按简切分 |
| `scripts/import_alignment.py` | 把 tt24h 的排版数据按底本顺序拼回、逐字对上实录，生成 `data/alignment/` 以及王弼本、校订本的文本单位；对不上就报错、不写文件。`--check` 不写文件，只核对已有的文件能否原样重新生成 |
| `scripts/alignment.py` | 对读表的解析、拼回与核对，供 `import_alignment.py` 和 `validate_data.py` 共用 |
| `scripts/extract_plates.py <PDF 目录>` | 从扫描本 PDF 原样抽出图版页 JPEG，生成 `data/plates/`；需要 poppler 的 `pdfimages`，PDF 的 SHA-256 必须与脚本内登记一致 |

导入脚本只读已登记哈希的原始文件，不联网。扫描本 PDF 本身不进仓库，只抽图版页。生成站点固定字体的 `scripts/make-fonts.ts` 属于展示站，见 [docs/site.md](docs/site.md)。

## 还没做的事

- **独立核对对读表**：对读表是 tt24h 整理者的对齐（以王弼本分章），本仓库没有另找依据复核；哪些处的对齐有争议，需要有依据的底本才能判断。
- **交叉核对**：用第二个独立来源逐字核对，才能把 `status` 升为 `double-checked`。
- 马王堆两本在 `data/witnesses/` 里还是按章的维基文库释文；tt24h 的逐行实录已在 `data/alignment/lines/`，尚未并入文本单位。
- 《郭店楚墓竹简》（1998）和《马王堆汉墓帛书〔壹〕》尚无电子本，未抓取；Commons 上郭店甲、丙组两张照片因限速未下载。
- 展示站：在图版上框选字并对到其他本（按位置估算）、帛书整页影像并排与翻页、跨本全文检索、尾注框对应到具体的字。

## 参与

git 操作一律通过 `scripts/safegit`，新克隆后先运行：

```bash
scripts/safegit setup --name "<姓名>" --email "<邮箱>"
```

防护分层与审计用法见 [docs/safegit.md](docs/safegit.md)。
