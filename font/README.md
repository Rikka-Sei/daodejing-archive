# DaoSong：本项目的字库

DaoSong 是思源宋体（Noto Serif SC）Regular 的**派生字体**。上游字体没有收、`tt24h` 补充字体也没有的几个生僻字，在这里逐笔手绘成矢量字形，补进同一个字体里；其余字形原样沿用思源宋体。站点的宋体 400（释文正文）用的就是它，所以补进去的字和身边的字同一套笔画、同一个字重，不靠回退字体拼凑。

| 字 | 码位 | 结构 | 说明 |
| --- | --- | --- | --- |
| 𠂤 | U+200A4 | ⿱丿㠯 | 堆的本字：丿下一道左竖，右边上下两个分开的框，同 追 師 的右旁 |
| 𠕁 | U+20541 | ⿵冂卄 | 冂内套卄，近“冊” |
| 𠚕 | U+20695 | ⿶凵⿳从一从 | 凵内叠两个从，近“齿” |
| 𣐩 | U+23429 | ⿱白木 | 上白下木，近“杲” |
| 𤤀 | U+24900 | ⿰王屯 | 左王（末笔作提）右屯，同 珅 纯 的偏旁写法 |
| 𭇁 | U+2D1C1 | ⿱𫝀口 | 上 𫝀（U+2B740）下口，即 吾 去掉首横 |

字形的写法以 Unicode 字表（The Unicode Standard 18.0，CJK Unified Ideographs Extension B、F）里的通用字形为准；这里画的是按思源宋体笔法画出的宋体版本，不是任何字体的现成轮廓。

## 目录

```
font/
  font.yaml          登记：字体名、版本、上游字体（URL 与 SHA-256）、手绘的字（码位、结构、参考字）
  glyphs/uXXXXX.svg  字形，每笔一条 <path>（1000×1000 字身框，基线在 y=880 的红线上）；由 tools/draw.py 生成，构建只读它们
  build.py           生成字体：上游字体取定字重 400，加入 SVG 里的字形，改名，存成 TTF
  glyphlib.py        SVG 读写、笔画合并、转成 TrueType 曲线
  tools/strokes.py   笔画：横、竖、撇、捺、提、斜竖、横折钩、竖弯钩……尺寸常量在文件开头
  tools/parts.py     部件，按部位命名：wang_left（左旁王）、tun_right（右旁屯）、mu_bottom（字底木）、
                     bai_top（字头白）、cong_top（字头从）、yi（㠯）、kou_frame（口框）
  tools/draw.py      6 个字的摆法，字形的唯一源头；运行它重写 glyphs/*.svg
  tools/fit.py       在思源宋体的参考字上量出部件落点（measure 列轮廓范围，fit 逐笔拟合）
  OFL.txt            授权文本（上游的 SIL OFL 1.1 加上本项目的版权说明）
```

## 怎么画的

- **笔画尺寸**：横 30、竖 66，横的右端有三角形顿角，竖头有小钩，竖脚向左收圆，都量自思源宋体 Regular，写成 `tools/strokes.py` 开头的常量。每一笔都按这些尺寸现画，不取用思源宋体的轮廓。
- **按同部位的字定比例**：同一个部件在字头、字底、偏旁里写法不同（王作左旁末笔是提，木在字底是扁的，从在字头撇更斜），所以部件按部位命名，各自对照思源宋体里**同一部件在同一部位**的参考字（登记在 `font.yaml` 的 `refs`）。
- **拟合**：`tools/fit.py` 把每一笔对应到参考字的一个或几个轮廓，用笔画函数画出这一笔，求两者的重合度（交集面积 ÷ 并集面积），逐个参数爬坡到不再升高；`parts.py` 里的坐标就是它的输出。头宽、尖宽、轻重这类参数单凭重合度会被拟到失形，所以按目测取定、只拟合落点与曲线。重新核对：

  ```bash
  python3 font/tools/fit.py --upstream "NotoSerifSC[wght].ttf" fit        # 打印各部件每一笔的参数与重合度
  python3 font/tools/fit.py --upstream "NotoSerifSC[wght].ttf" measure 冊  # 列出参考字各轮廓的范围
  ```

- **不是拼贴**：部件只按字框移动笔画的落点，横竖的粗细和收笔不随字框缩放；撇捺在缩小的部件里按缩小比例的平方根减轻，和思源宋体里小部件的笔画轻重一致，不会像把整个字缩放后那样细成线。
- **改字形**：改 `tools/draw.py`（或 `parts.py`、`strokes.py`）里的坐标，运行 `python3 font/tools/draw.py` 重写 SVG。`draw.py` 是唯一的源头，SVG 是它生成的产物，可以在矢量软件里打开查看，但不要手改：`tests/test_font.py` 核对 SVG 与 `draw.py` 的输出逐字相同。

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

1. 在思源宋体里找同一部件在同一部位的参考字，用 `fit.py measure` 看它的轮廓；需要新部件时在 `parts.py` 里按部位命名，在 `fit.py` 的 `SPECS` 里登记、拟合出落点。
2. 在 `tools/draw.py` 里加一个函数摆笔画、登记到 `GLYPHS`，运行它生成 SVG。
3. 在 `font.yaml` 的 `glyphs` 里登记码位、结构与参考字，再 `npm run build && npm run fonts`。
4. 把字形和参考字放大并排看一遍、在正文字号下看一遍，再跑 `python3 -m unittest tests.test_font` 与 `npm test`。
