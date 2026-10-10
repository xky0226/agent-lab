"""
探针：__name__ 在两个场合，分别是几？

同一个文件，两种跑法：
    ① 当脚本直接跑   python _probe_name.py
    ② 被别的模块 import

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _probe_name.py
    .venv\\Scripts\\python.exe -c "import _probe_name"
"""

print(f"  [我这一行被执行了]  此刻 __name__ = {__name__!r}")
