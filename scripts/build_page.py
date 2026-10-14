#!/usr/bin/env python3
"""生成静态站点：阅读版、数据版、纯文本释文与 llms.txt。实现在 scripts/pagegen/，用法见 `--help`。"""
import sys

from pagegen.cli import main

if __name__ == "__main__":
    sys.exit(main())
