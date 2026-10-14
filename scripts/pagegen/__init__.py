"""静态站点生成器。

模块分工：
  corpus.py   读取一部典籍的数据（witnesses.yaml、释文、影像索引、来源），把版本归入文献（目录里的文件夹）
  textutil.py 文献分组命名、识语、简号标签、授权说法、残缺标注（纯函数，无 I/O）
  thumbs.py   影像缩略图（Pillow 可选）
  render/     HTML 渲染，样式与脚本在 assets/ 下
  fonts.py    固定字体（assets/fonts/，由 scripts/make_fonts.py 生成）：引用、复制、检查站点用字
  llms.py     纯文本与 jsonl 下载、llms.txt、llms-full.txt
  check.py    生成后检查站内相对链接（含样式里的 url()）
  cli.py      命令行入口与流程编排；presets/ 放内置典籍的展示信息（标题、凡例、授权说明）
"""
