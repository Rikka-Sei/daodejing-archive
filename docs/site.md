# 展示站

用 [Astro](https://astro.build) 读取 `data/` 生成静态站：封面与凡例、每个本一页、章节对读页（81 章，各本同列逐字对照）、竹简与帛书的竖排阅读器、对照资料页、每个本的 `.txt` 与 `.jsonl` 下载，以及 `llms.txt` / `llms-full.txt`。推送到 `main` 后由 `.github/workflows/astro.yml` 构建并发布到 GitHub Pages，地址是 `https://<用户名>.github.io/<仓库名>/`，仓库配了自定义域名时是那个域名。

站点不另存数据：释文、影像登记、来源与授权都直接来自 `data/`，下载的 `.jsonl` 与仓库里的文件逐字相同；各章的对读表 JSON 也与 `data/alignment/chapters/` 里的逐字相同。

## 命令

需要 Node 22.12 以上。

```bash
npm ci               # 安装依赖（按 package-lock.json）
npm run dev          # 本地预览；改页面自动刷新，改了 data/ 刷新页面即可
npm run build        # 构建到 dist/（要带 Pages 的地址时加 --site https://x.github.io --base /仓库名）
npm run preview      # 预览 dist/
npm run check        # 类型检查
npm test             # 测试（含两遍完整构建，约半分钟）
npm run fonts        # 重新生成固定字体（先 npm run build，见下文“固定字体”）
```

## 目录

```
src/
  config/<典籍>.yaml     展示信息：书名、副题、简介、章节分篇、凡例、授权说明
  lib/                   数据读取与文本处理、对读表、下载内容、缩略图、固定字体、地址、构建后检查
  components/            侧栏、目录树、“⋯”菜单、释文条目、图版等
  layouts/Shell.astro    页面骨架
  views/                 封面、本的页面、章节对读页、阅读器、对照资料页
  pages/                 路由：页面、下载文件、缩略图、llms.txt
  integrations/verify.ts 构建结束时的检查
  scripts/               页面脚本，原样输出，不打包：app.js（检索、排版、主题、菜单、侧栏两条轴）、
                         reader.js（阅读器的“透视”与专注模式）、align.js（对读表页的列高亮与钉住）
  styles/site.css        样式
public/fonts/            固定字体子集与授权文本
scripts/make-fonts.ts    生成固定字体子集（npm run fonts）
tests/site/              测试
```

## 页面与地址

| 地址 | 内容 |
|---|---|
| `/` | 第一部典籍的封面 |
| `/<典籍>/` | 封面：文献卡片、凡例 |
| `/<典籍>/<本>/` | 一个本：版本信息、来源与授权、释文、图版；章节为单位的本，每章旁有“对读”链接 |
| `/<典籍>/<本>/read/` | 竖排阅读器，自右向左，一简或一行一列；只有带逐行释文的竹简、帛书才有。点一个字或拖选几个字，弹出“透视”，列出其他本在同一处写的什么；按 F 进出只留文字的专注模式 |
| `/<典籍>/chapters/<N>/` | 第 N 章的对读表：各本同列对齐，标出异体与用字差异和共用通行字；指到一个字高亮这一列，点一下钉住 |
| `/<典籍>/chapters/<NNN>.json`、`/<典籍>/alignment.json` | 阅读器按需读取的数据：一章的对读表（与 `data/alignment/chapters/` 逐字相同），以及各行简称、共用通行字规则和造字码位 |
| `/<典籍>/study/<来源>/` | 对照资料页：该资料的概述、凡例、参考书目，以及本站用到的部分 |
| `/<典籍>/<本>.txt`、`.jsonl` | 一个本的释文与数据 |
| `/<典籍>/<文献>-all.txt`、`.jsonl` | 有多个本的文献的合集（如郭店楚简） |
| `/<典籍>/thumbs/*.jpg` | 影像缩略图，构建时由 sharp 从 `data/images/` 缩出；原图链到 GitHub |
| `/llms.txt`、`/llms-full.txt` | 给大模型读的索引与全部释文 |

侧栏有两条轴，点顶部的“材料｜章节”切换，不跳转：

- **材料**：按材料的性质分类列出文献——出土文献（一手）、石刻与拓本（二手）、传世本与校订本、论文与对照资料；没有内容的分类不显示。性质取自 `data/witnesses.yaml` 里的 `kind`（`excavated`、`rubbing`、`transmitted`、`edition`，没写按 `excavated`）；论文与他人编纂的对照资料是 `data/sources/` 里写了 `study: true` 的来源。目录里的层级取自版本名：“郭店楚简《老子》甲组”归入“郭店楚简”，各文献有几个本就列几个；只有一个本的文献直接是一项。
- **章节**：依王弼本分的 81 章（分篇取自展示信息里的 `chapter_parts`），每章后的圆点表示各出土本有没有这一章。

只有 `data/alignment/` 存在的典籍才有章节轴。

## 新增一部典籍

1. 数据按 `data/` 的结构放好（`witnesses.yaml`、`witnesses/`、`plates/`、`sources/`），通过 `scripts/validate_data.py`。
2. 在 `src/config/` 加一份展示信息，参照 `laozi.yaml`。
3. 在 `src/lib/site.ts` 的 `SOURCES` 里加一行。收录多部典籍时，侧栏会出现典籍切换。
4. 有逐章对读表的，放进 `data/alignment/`（结构见 [storage-design.md](storage-design.md)）：页面随之多出章节对读、阅读器和章节轴；没有就没有这些页面。
5. 构建时若提示有字不在固定字体里，按下一节重新生成字体。

## 固定字体

页面不依赖观看者机器上的字体：随站点发布思源黑体、思源宋体的子集（SIL OFL 1.1，共约 880 KB），子集里没有的字由浏览器逐字回退到系统字体。构建结束时会列出页面用到、但子集里没有的字。

```bash
npm run build && npm run fonts    # 统计 dist/ 里的用字，重新裁出子集到 public/fonts/
```

来源字体按 URL 和 SHA-256 固定：首次运行会下载（两个字体共约 43 MB，缓存在 `~/.cache/daodejing-archive/fonts`），校验通过才用。子集由 HarfBuzz 的 hb-subset（WebAssembly 版，随 npm 依赖安装）裁出：取定字重，保留竖排用的 vert/vrt2 等排版特征、版权与授权信息、缺字时显示的方框，再压成 WOFF2。同样的输入得到逐字节相同的文件，不需要装别的工具。释文只用宋体 400，所以其余字重只装界面与标题用字；这靠一个约定区分：**不带属性的 `<p>` 只用于释文正文**，其他段落都要带 class。

对读表和实录里有 Unicode 没有收的造字（用私用区码位）和扩展 B 区以后的生僻字，用 tt24h 随源码发布的补充字体 DaoDeJingExt（`dg-ext-400.woff2`，约 144 KB，SIL OFL 1.1）显示。它整个收录、不裁剪；页面用 `unicode-range: U+E000-F8FF, U+20000-2FFFF` 声明它，页面上出现这些字才下载，也不预加载。字体文件和授权文本随源码存在 `data/raw/tt24h-daodejing/`，已登记在 `data/sources/tt24h-daodejing.yaml`；`npm run fonts` 从那里读入，并按脚本里固定的 SHA-256 校验，通过才转成 WOFF2。

## 构建后检查

`src/integrations/verify.ts` 在每次构建结束时检查输出：

- 站内链接（`href`、`src`、阅读器读取对读表用的 `data-meta`、样式里的 `url()`）必须指向存在的文件，带锚点的必须有对应的 id，部署在子路径下时绝对路径必须带 base。有问题就让构建失败，不会把断链发布出去。
- 页面用到而固定字体没有的字，只给出提示，不影响构建。

## 测试

`tests/site/` 用占位典籍测数据读取、文本处理、对读表、下载内容、缩略图、固定字体、各页面的结构和检查本身，用 `astro build` 跑两遍真实数据（带 `--site`、`--base` 与不带）检查输出，并核对真实数据的结构约定。字体脚本的用字统计、来源校验和子集裁剪也在这里测，不联网：裁剪用 `tests/site/assets/mini-vf.ttf`，那是从固定来源的思源黑体里只裁出六个字、保留字重轴的小字体。

页面脚本 `reader.js`、`align.js` 在 `client-scripts.test.ts` 里放进 `node:vm` 的假页面运行，不引入 DOM 库：点字、拖选、读各章、专注模式、键盘，以及对读表页的高亮与钉住。阅读器里重抄了一份比较与共用通行字的规则（同 `src/lib/alignment.ts`，两处要一起改），这个测试把两边对每一列的结果逐一核对，用占位数据和整套真实数据各跑一遍。`app.js`（侧栏检索、两条轴、菜单）没有自动测试，改动后要在浏览器里看一遍。

Python 一侧的导入与校验脚本另有测试，见 README。

## 部署

`.github/workflows/astro.yml` 在推送到 `main` 时运行：`npm ci`，用 `actions/configure-pages` 取得站点地址与 base，`astro build --site … --base …`，再发布 `dist/`。仓库的 Settings → Pages → Source 要选 **GitHub Actions**。
