"""HTML 渲染。common.py 公共部分（外壳、侧栏目录树、来源），book.py 阅读版（封面与每个本一页），data_view.py 数据版。

样式与脚本是 assets/ 下的独立文件，构建时内联进每个页面。版式参照 Claude 应用：288px 侧栏、14px/20px、近白底与 0.5px 细边线；
释文默认横排，可一键切到自右向左的竖排。
"""
from .common import REPO_URL, Ctx  # noqa: F401
