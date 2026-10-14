# 展示站

用 [Astro](https://astro.build) 读取 `data/` 生成静态站：阅读版（封面、凡例、每个本一页）、数据版（所有版本一页、可跨版本检索）、每个本的 `.txt` 与 `.jsonl` 下载，以及 `llms.txt` / `llms-full.txt`。推送到 `main` 后由 `.github/workflows/astro.yml` 构建并发布到 GitHub Pages，地址是 `https://<用户名>.github.io/<仓库名>/`。

站点不另存数据：释文、影像登记、来源与授权都直接来自 `data/`，下载的 `.jsonl` 与仓库里的文件逐字相同。

## 命令

需要 Node 22.12 以上。

```bash
npm ci               # 安装依赖（按 package-lock.json）
npm run dev          # 本地预览；改页面自动刷新，改了 data/ 刷新页面即可
npm run build        # 构建到 dist/（要带 Pages 的地址时加 --site https://x.github.io --base /仓库名）
npm run preview      # 预览 dist/
npm run check        # 类型检查
npm test             # 测试（含两遍完整构建，约半分钟）
```

## 目录

```
src/
  config/<典籍>.yaml     展示信息：书名、副题、简介、凡例、授权说明
  lib/                   数据读取与文本处理、下载内容、缩略图、固定字体、地址、构建后检查
  components/            侧栏、目录树、“⋯”菜单、释文条目、图版等
  layouts/Shell.astro    页面骨架
  views/                 封面、本的页面、数据版
  pages/                 路由：页面、下载文件、缩略图、llms.txt
  integrations/verify.ts 构建结束时的检查
  scripts/app.js         页面脚本（检索、排版、主题、菜单），原样输出，不打包
  styles/site.css        样式
public/fonts/            固定字体子集与授权文本
tests/site/              测试
```

## 页面与地址

| 地址 | 内容 |
|---|---|
| `/` | 第一部典籍的封面 |
| `/<典籍>/` | 封面：文献卡片、凡例 |
| `/<典籍>/<本>/` | 一个本：版本信息、来源与授权、释文、图版 |
| `/<典籍>/data/` | 数据版，`#<本>` 落在某个本 |
| `/<典籍>/<本>.txt`、`.jsonl` | 一个本的释文与数据 |
| `/<典籍>/<文献>-all.txt`、`.jsonl` | 有多个本的文献的合集（如郭店楚简） |
| `/<典籍>/thumbs/*.jpg` | 影像缩略图，构建时由 sharp 从 `data/images/` 缩出；原图链到 GitHub |
| `/llms.txt`、`/llms-full.txt` | 给大模型读的索引与全部释文 |

目录里的层级取自版本名：“郭店楚简《老子》甲组”归入“郭店楚简”，各文献有几个本就列几个；只有一个本的文献直接是一项。

## 新增一部典籍

1. 数据按 `data/` 的结构放好（`witnesses.yaml`、`witnesses/`、`plates/`、`sources/`），通过 `scripts/validate_data.py`。
2. 在 `src/config/` 加一份展示信息，参照 `laozi.yaml`。
3. 在 `src/lib/site.ts` 的 `SOURCES` 里加一行。收录多部典籍时，侧栏会出现典籍切换。
4. 构建时若提示有字不在固定字体里，按下一节重新生成字体。

## 固定字体

页面不依赖观看者机器上的字体：随站点发布思源黑体、思源宋体的子集（SIL OFL 1.1，约 610 KB），子集里没有的字由浏览器逐字回退到系统字体。构建结束时会列出页面用到、但子集里没有的字。

```bash
pip install fonttools brotli
npm run build && scripts/make_fonts.py    # 统计 dist/ 里的用字，重新裁出子集到 public/fonts/
```

来源字体按 URL 和 SHA-256 固定，下载后先校验。释文只用宋体 400，所以其余字重只装界面与标题用字；这靠一个约定区分：**不带属性的 `<p>` 只用于释文正文**，其他段落都要带 class。

## 构建后检查

`src/integrations/verify.ts` 在每次构建结束时检查输出：

- 站内链接（`href`、`src`、`data-go`、样式里的 `url()`）必须指向存在的文件，带锚点的必须有对应的 id，部署在子路径下时绝对路径必须带 base。有问题就让构建失败，不会把断链发布出去。
- 页面用到而固定字体没有的字，只给出提示，不影响构建。

## 测试

`tests/site/` 用占位典籍测数据读取、文本处理、下载内容、缩略图、固定字体、各页面的结构和检查本身，用 `astro build` 跑两遍真实数据（带 `--site`、`--base` 与不带）检查输出，并核对真实数据的结构约定。`tests/test_make_fonts.py` 测字体脚本的用字统计，构建测试里还会核对它与构建时的字体提示对“页面用了哪些字”的统计一致。

## 部署

`.github/workflows/astro.yml` 在推送到 `main` 时运行：`npm ci`，用 `actions/configure-pages` 取得站点地址与 base，`astro build --site … --base …`，再发布 `dist/`。仓库的 Settings → Pages → Source 要选 **GitHub Actions**。
