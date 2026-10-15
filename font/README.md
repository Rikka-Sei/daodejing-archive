# DaoSong：本项目的字库

DaoSong 是思源宋体（Noto Serif SC）Regular 的**派生字体**。上游字体没有收、`tt24h` 补充字体也没有的几个生僻字，在这里逐笔手绘成矢量字形，补进同一个字体里；其余字形原样沿用思源宋体。站点的宋体 400（释文正文）用的就是它，所以补进去的字和身边的字同一套笔画、同一个字重，不靠回退字体拼凑。

| 字 | 码位 | 结构 | 说明 |
| --- | --- | --- | --- |
| 𠂤 | U+200A4 | ⿱丿㠯 | 堆的本字，字表中的写法近“自” |
| 𠕁 | U+20541 | ⿵冂卄 | 冂内套卄，近“冊” |
| 𠚕 | U+20695 | ⿶凵⿳从一从 | 凵内叠两个从，近“齿” |
| 𣐩 | U+23429 | ⿱白木 | 上白下木，近“杲” |
| 𤤀 | U+24900 | ⿰王屯 | 左王右屯 |
| 𭇁 | U+2D1C1 | ⿱𫝀口 | 上 𫝀（U+2B740）下口 |

字形的写法以 Unicode 字表（The Unicode Standard 18.0，CJK Unified Ideographs Extension B、F）里的通用字形为准；这里画的是按思源宋体笔法画出的宋体版本，不是任何字体的现成轮廓。

## 目录

```
font/
  font.yaml          登记：字体名、版本、上游字体（URL 与 SHA-256）、手绘的字
  glyphs/uXXXXX.svg  手绘的字形，每笔一条 <path>（1000×1000 字身框，基线在 y=880 的红线上）
  build.py           生成字体：上游字体取定字重 400，加入 SVG 里的字形，改名，存成 TTF
  glyphlib.py        SVG 读写、笔画合并、转成 TrueType 曲线
  tools/strokes.py   笔画的画法：横、竖、撇、捺、竖弯钩……按思源宋体量得的尺寸现画
  tools/parts.py     部件：木 王 屯 白 从 口框……按字框摆放笔画
  tools/draw.py      6 个字的摆法；运行它重写 glyphs/*.svg
  OFL.txt            授权文本（上游的 SIL OFL 1.1 加上本项目的版权说明）
```

## 怎么画的

- **笔画尺寸**：用思源宋体 Regular 的 白、木、王、屯、从 等字量得：横 30、竖 66，横的右端有三角形顿角，竖头有小钩，竖脚向左收圆，撇捺的曲线比例是在这些字上拟合出来的。`tools/strokes.py` 里每一笔都按这些尺寸现画，画出的白、木、王、屯、从与原字叠在一起几乎重合。
- **不是拼贴**：部件只按字框移动笔画的落点，笔画的粗细和收笔不随字框缩放。挤窄、压扁之后笔画仍然和正文一样粗，不会像把整个字缩放后那样变细或变形。
- **改字形**：改 `tools/draw.py` 里的坐标，运行 `python3 font/tools/draw.py` 重写 SVG；也可以直接用矢量软件（Inkscape、Illustrator 等）改 SVG，只要保留 `<path>`，构建只认 SVG。`tests/test_font.py` 会核对 SVG 与 `draw.py` 的输出一致：直接改了 SVG 的话，要么把改动画回 `draw.py`，要么删掉那条对应字的核对。

## 生成

制作字体要用 Python（只在重新生成字体时需要，站点构建与浏览不需要）：

```bash
python3 -m pip install fonttools skia-pathops pyyaml brotli
npm run build && npm run fonts   # 会调用 font/build.py，得到站点用的 dao-song-400.woff2
```

也可以单独生成完整的 TTF（约 14 MB，含思源宋体的全部字形）：

```bash
python3 font/build.py --upstream "NotoSerifSC[wght].ttf" --out DaoSong-Regular.ttf
```

上游字体是 `font.yaml` 里固定的版本，`build.py` 会核对它的 SHA-256。同样的输入得到逐字节相同的字体。

## 授权

SIL OFL 1.1（见 `OFL.txt`）。按这份授权，派生字体必须改名（所以叫 DaoSong，不沿用 Noto 或 Source 之名）、带上授权文本，也不能单独出售字体本身。上游的版权声明保留在字体的 name 表和 `OFL.txt` 里。

## 补新字的步骤

在 `tools/draw.py` 里加一个函数摆笔画、登记到 `GLYPHS`，运行它生成 SVG，在 `font.yaml` 的 `glyphs` 里登记码位，再 `npm run build && npm run fonts`；然后跑 `python3 -m unittest tests.test_font` 与 `npm test`。
