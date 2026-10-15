"""第 8 步 ①：出题机 —— 给「修 bug Agent」造靶场，并且给每道题上四道闸。

为什么要机器子上闸（《Agent 方案A 详细设计》§9 §11）：
    「公平」不是靠自觉，是靠**机器把坏题挡在门外**。人写的那点 bug，
    很容易写成「死代码 bug」——改不改测试都绿，白占一道题的名额。

四道闸（比设计文档 §11 多一道 ③）：给每道题跑四次 pytest，四次全过才准入库
    ① src_对 + 可见测试  → 必须【全绿】。红 = 题本身坏了，不是模型的锅。
    ② src_bug + 可见测试 → 必须【红】。绿 = 这是个死代码 bug，作废。
    ③ src_对 + 判分测试  → 必须【全绿】。红 = 判分卷自己写坏了（新增的一道）。
    ④ src_bug + 判分测试 → 记下【基线失败数】，以后拿来算「修好了多少」。

⚠️ src_对【绝不进靶场】—— 它只在闸箱里跑，用来验题。盘上只落 src_bug。

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe arena\\_make_tasks.py
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

根 = Path(__file__).resolve().parent          # arena/
题目目录 = 根 / "tasks"
判分目录 = 根 / "hidden"

# ══════════════════════════════════════════════════════════════
# 两种抬头 —— 解决「测试文件怎么 import 到 src/ 那个模块」
#
# 可见测试（tests/ 下面，模型看得见）用【相对自己走两步】：tests/test_x.py → ../src
#   ⚠️ 不靠 conftest.py / pytest.ini —— 那两个正是 edit_src 要挡的东西，
#      自己的靶场里再摆一份，等于给攻击面留个样板。零魔法，三行搞定。
#
# 判分测试（藏在 arena/hidden/）用【环境变量 ARENA_SRC】：
#   ⚠️ 它不在题目目录里，../src 走不到；而且 _eval.py 以后会把题目【复制】到
#      _run/ 再跑，写死绝对路径就会去判【原件】的代码 —— 判错东西还不报错。
#      由启动方把 src 的真实位置塞进来，复制到哪都对。
# ══════════════════════════════════════════════════════════════
可见抬头 = '''import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
'''

判分抬头 = '''import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)
'''


# ══════════════════════════════════════════════════════════════
# 二十道题。难易按设计文档 §9 的三档分：
#   易（t01~t08）= 运算符 / 下标 / 变量名 —— 症状长在出错那一行
#   中（t09~t15）= 边界条件 —— 空 / 零 / 全负 / 并列 / 多一个分隔符
#   难（t16~t20）= 传递式逻辑错 —— 错在 A，症状出现在 B
#
# ⚠️ 每题都必须【自己带着一个能红的可见测试】。闸②拦的就是那种
#    「测试抓不到」的死代码 bug —— 人写 bug 最容易写成那种，
#    机器不看代码，只看测试红不红，所以拦得住。
# ══════════════════════════════════════════════════════════════

题目表 = {

    # ── 易：比较运算符漏了等号（`>` 该是 `>=`）─────────────
    "t01_grade_boundary": {
        "档次": "易 · 运算符（`>` 漏了等号）",
        "文件名": "grade.py",
        "导入语句": "from grade import grade",
        "题面": """# t01 · 成绩等级

`src/grade.py` 里的 `grade()` 在某个分数上给错了等级。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def grade(score):
    """百分制转等级：>=90 得 A，>=80 得 B，>=70 得 C，>=60 得 D，其余 F。"""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"
''',
        "src_bug": '''def grade(score):
    """百分制转等级：>=90 得 A，>=80 得 B，>=70 得 C，>=60 得 D，其余 F。"""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score > 60:
        return "D"
    return "F"
''',
        "可见测试": "test_grade.py",
        "tests": '''def test_top():
    assert grade(95) == "A"


def test_mid():
    assert grade(75) == "C"


def test_pass_line():
    assert grade(60) == "D"


def test_fail():
    assert grade(59) == "F"
''',
        "判分测试": "test_grade_hidden.py",
        "hidden": '''def test_a_line():
    assert grade(90) == "A"


def test_b_line():
    assert grade(80) == "B"


def test_c_line():
    assert grade(70) == "C"


def test_d_line():
    assert grade(60) == "D"


def test_edges():
    assert grade(100) == "A"
    assert grade(0) == "F"
    assert grade(59) == "F"
''',
    },

    # ── 中：边界条件（空输入）──────────────────────────────
    "t02_average_empty": {
        "档次": "中 · 边界条件（空列表没判）",
        "文件名": "stats.py",
        "导入语句": "from stats import average",
        "题面": """# t02 · 平均值

`src/stats.py` 里的 `average()` 在某些输入下会直接崩。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def average(nums):
    """求平均值（保留两位小数）。空列表返回 None。"""
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)
''',
        "src_bug": '''def average(nums):
    """求平均值（保留两位小数）。空列表返回 None。"""
    return round(sum(nums) / len(nums), 2)
''',
        "可见测试": "test_stats.py",
        "tests": '''def test_three():
    assert average([1, 2, 3]) == 2.0


def test_decimal():
    assert average([1, 2]) == 1.5


def test_empty():
    assert average([]) is None
''',
        "判分测试": "test_stats_hidden.py",
        "hidden": '''def test_single():
    assert average([5]) == 5.0


def test_empty_none():
    assert average([]) is None


def test_zeros():
    assert average([0, 0]) == 0.0


def test_negative():
    assert average([-1, 1]) == 0.0


def test_rounding():
    assert average([1, 2, 3, 4]) == 2.5
''',
    },

    # ── 难：传递式 bug（错在 strip_ext，症状出在 group_by_stem）──
    #    真凶是 rstrip 的语义：参数是【一堆字符】，不是【一个后缀】。
    "t03_filename_suffix": {
        "档次": "难 · 逻辑错（传递式：错在 A，症状出现在 B）",
        "文件名": "filenames.py",
        "导入语句": "from filenames import group_by_stem, strip_ext",
        "题面": """# t03 · 文件名归类

`src/filenames.py` 里的 `group_by_stem()` 把文件名归类归错了——
本该归到一起的没归到一起，主名也被截短了。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def strip_ext(name):
    """去掉文件名末尾的 ".txt" 后缀。"""
    return name.removesuffix(".txt")


def group_by_stem(names):
    """按「去后缀后的主名」归类，返回 主名 -> 出现次数。"""
    counts = {}
    for n in names:
        stem = strip_ext(n)
        counts[stem] = counts.get(stem, 0) + 1
    return counts
''',
        "src_bug": '''def strip_ext(name):
    """去掉文件名末尾的 ".txt" 后缀。"""
    return name.rstrip(".txt")


def group_by_stem(names):
    """按「去后缀后的主名」归类，返回 主名 -> 出现次数。"""
    counts = {}
    for n in names:
        stem = strip_ext(n)
        counts[stem] = counts.get(stem, 0) + 1
    return counts
''',
        "可见测试": "test_filenames.py",
        # ⚠️ 故意让【看着没问题的】那两条先过，让红的那条指向 group_by_stem
        #    —— 症状在 B，真凶在 A。这就是这道题要考的东西。
        "tests": '''def test_strip_plain():
    assert strip_ext("notes.txt") == "notes"
    assert strip_ext("data.txt") == "data"


def test_group():
    assert group_by_stem(["report.txt", "next.txt"]) == {"report": 1, "next": 1}
''',
        "判分测试": "test_filenames_hidden.py",
        "hidden": '''def test_strip_basic():
    assert strip_ext("notes.txt") == "notes"
    assert strip_ext("a.txt") == "a"


def test_strip_single_letter():
    assert strip_ext("x.txt") == "x"


def test_strip_trap():
    assert strip_ext("test.txt") == "test"
    assert strip_ext("index.txt") == "index"


def test_strip_no_ext():
    assert strip_ext("readme") == "readme"


def test_group_counts():
    assert group_by_stem(["report.txt", "next.txt", "report.txt"]) == {"report": 2, "next": 1}
''',
    },

    # ══════════════════════════════════════════════════════════════
    # 易：运算符 / 下标 / 变量名（t04 ~ t08）
    #    症状就长在出错那一行，读一遍代码基本能看见。用来给模型热身，
    #    也用来测「最笨的那类 bug 你会不会修」。
    # ══════════════════════════════════════════════════════════════

    # ── 易：切片差一（[:n] 写成了 [:n-1]）────────────────────
    "t04_first_n_slice": {
        "档次": "易 · 下标（切片差一）",
        "文件名": "slices.py",
        "导入语句": "from slices import first_n",
        "题面": """# t04 · 取前几个

`src/slices.py` 里的 `first_n()` 取出来的元素个数不对。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def first_n(items, n):
    """返回 items 的前 n 个元素（新列表）；n 比长度大就全给。"""
    return list(items[:n])
''',
        "src_bug": '''def first_n(items, n):
    """返回 items 的前 n 个元素（新列表）；n 比长度大就全给。"""
    return list(items[:n - 1])
''',
        "可见测试": "test_slices.py",
        "tests": '''def test_two():
    assert first_n([1, 2, 3], 2) == [1, 2]


def test_one():
    assert first_n(["a", "b"], 1) == ["a"]


def test_more_than_len():
    assert first_n([1, 2], 5) == [1, 2]
''',
        "判分测试": "test_slices_hidden.py",
        "hidden": '''def test_all():
    assert first_n([1, 2, 3], 3) == [1, 2, 3]


def test_zero():
    assert first_n([1, 2], 0) == []


def test_empty():
    assert first_n([], 3) == []


def test_keeps_order():
    assert first_n("abcd", 2) == ["a", "b"]


def test_no_alias():
    src = [1, 2, 3]
    out = first_n(src, 2)
    out.append(99)
    assert src == [1, 2, 3]
''',
    },

    # ── 易：循环体里用错了变量（永远是第一个元素）────────────
    "t05_double_all_var": {
        "档次": "易 · 变量名（循环里用错变量）",
        "文件名": "lists.py",
        "导入语句": "from lists import double_all",
        "题面": """# t05 · 全体翻倍

`src/lists.py` 里的 `double_all()` 返回的列表不对——里面的元素不是各自翻倍的结果。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def double_all(nums):
    """返回新列表：每个元素乘 2。不改动传入的列表。"""
    out = []
    for n in nums:
        out.append(n * 2)
    return out
''',
        "src_bug": '''def double_all(nums):
    """返回新列表：每个元素乘 2。不改动传入的列表。"""
    out = []
    for n in nums:
        out.append(nums[0] * 2)
    return out
''',
        "可见测试": "test_lists.py",
        "tests": '''def test_three():
    assert double_all([1, 2, 3]) == [2, 4, 6]


def test_single():
    assert double_all([7]) == [14]
''',
        "判分测试": "test_lists_hidden.py",
        "hidden": '''def test_negative():
    assert double_all([0, -1, -2]) == [0, -2, -4]


def test_empty():
    assert double_all([]) == []


def test_float():
    assert double_all([0.5, 1.5]) == [1.0, 3.0]


def test_not_alias():
    src = [1, 2]
    out = double_all(src)
    out.append(0)
    assert src == [1, 2]
''',
    },

    # ── 易：切片步长（[::2] 写成 [1::2]，整体挪了一格）────────
    "t06_every_other_step": {
        "档次": "易 · 下标（步长切片挪了一格）",
        "文件名": "picks.py",
        "导入语句": "from picks import every_other",
        "题面": """# t06 · 隔一个取一个

`src/picks.py` 里的 `every_other()` 该取第 0、2、4… 个，现在取错了一批。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def every_other(items):
    """取第 0、2、4… 个元素（跳过奇数下标），返回新列表。"""
    return list(items[::2])
''',
        "src_bug": '''def every_other(items):
    """取第 0、2、4… 个元素（跳过奇数下标），返回新列表。"""
    return list(items[1::2])
''',
        "可见测试": "test_picks.py",
        "tests": '''def test_four():
    assert every_other(["a", "b", "c", "d"]) == ["a", "c"]


def test_three():
    assert every_other([1, 2, 3]) == [1, 3]
''',
        "判分测试": "test_picks_hidden.py",
        "hidden": '''def test_empty():
    assert every_other([]) == []


def test_one():
    assert every_other([9]) == [9]


def test_numbers():
    assert every_other([1, 2, 3, 4, 5]) == [1, 3, 5]


def test_string():
    assert every_other("abcde") == ["a", "c", "e"]
''',
    },

    # ── 易：拼字符串漏了分隔符（" " 写成了 ""）───────────────
    "t07_join_tags_sep": {
        "档次": "易 · 拼接（join 的分隔符丢了）",
        "文件名": "tags.py",
        "导入语句": "from tags import join_tags",
        "题面": """# t07 · 标签拼串

`src/tags.py` 里的 `join_tags()` 拼出来的字符串粘成了一坨。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def join_tags(tags):
    """把标签拼成 "#a #b" 的形式；空列表返回空串。"""
    return " ".join("#" + t for t in tags)
''',
        "src_bug": '''def join_tags(tags):
    """把标签拼成 "#a #b" 的形式；空列表返回空串。"""
    return "".join("#" + t for t in tags)
''',
        "可见测试": "test_tags.py",
        "tests": '''def test_two():
    assert join_tags(["a", "b"]) == "#a #b"


def test_one():
    assert join_tags(["py"]) == "#py"


def test_empty():
    assert join_tags([]) == ""
''',
        "判分测试": "test_tags_hidden.py",
        "hidden": '''def test_three():
    assert join_tags(["a", "b", "c"]) == "#a #b #c"


def test_keeps_order():
    assert join_tags(["z", "a"]) == "#z #a"


def test_no_alias():
    src = ["a"]
    join_tags(src)
    assert src == ["a"]
''',
    },

    # ── 易：漏了 ×100（比例当成了百分数）────────────────────
    "t08_percent_scale": {
        "档次": "易 · 运算符（漏乘 100）",
        "文件名": "ratio.py",
        "导入语句": "from ratio import percent",
        "题面": """# t08 · 完成率

`src/ratio.py` 里的 `percent()` 算出来的数字量级不对。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def percent(done, total):
    """完成率，百分数（保留一位小数）。total 为 0 时返回 0.0。"""
    if total == 0:
        return 0.0
    return round(done / total * 100, 1)
''',
        "src_bug": '''def percent(done, total):
    """完成率，百分数（保留一位小数）。total 为 0 时返回 0.0。"""
    if total == 0:
        return 0.0
    return round(done / total, 1)
''',
        "可见测试": "test_ratio.py",
        "tests": '''def test_half():
    assert percent(1, 2) == 50.0


def test_all():
    assert percent(3, 3) == 100.0


def test_zero_total():
    assert percent(0, 0) == 0.0
''',
        "判分测试": "test_ratio_hidden.py",
        "hidden": '''def test_third():
    assert percent(1, 3) == 33.3


def test_zero_done():
    assert percent(0, 5) == 0.0


def test_over():
    assert percent(5, 4) == 125.0


def test_rounding():
    assert percent(2, 3) == 66.7
''',
    },

    # ══════════════════════════════════════════════════════════════
    # 中：边界条件（t09 ~ t15）
    #    正常输入下看不出来，得想到「空 / 零 / 全负 / 并列 / 多一个冒号」
    #    那一格才会红。考的是「你会不会自己造边界」。
    # ══════════════════════════════════════════════════════════════

    # ── 中：除零检查写在了除法后面（顺序错）──────────────────
    "t09_safe_div_order": {
        "档次": "中 · 边界（除零检查写晚了）",
        "文件名": "maths.py",
        "导入语句": "from maths import safe_div",
        "题面": """# t09 · 安全除法

`src/maths.py` 里的 `safe_div()` 在某些输入下会直接崩。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def safe_div(a, b):
    """a / b，保留两位小数；b 为 0 时返回 None。"""
    if b == 0:
        return None
    return round(a / b, 2)
''',
        "src_bug": '''def safe_div(a, b):
    """a / b，保留两位小数；b 为 0 时返回 None。"""
    result = round(a / b, 2)
    if b == 0:
        return None
    return result
''',
        "可见测试": "test_maths.py",
        "tests": '''def test_normal():
    assert safe_div(6, 2) == 3.0


def test_zero_divisor():
    assert safe_div(1, 0) is None
''',
        "判分测试": "test_maths_hidden.py",
        "hidden": '''def test_negative():
    assert safe_div(-6, 3) == -2.0


def test_zero_divided():
    assert safe_div(0, 5) == 0.0


def test_rounding():
    assert safe_div(1, 3) == 0.33


def test_zero_over_zero():
    assert safe_div(0, 0) is None
''',
    },

    # ── 中：空白没压（只 strip 了首尾）───────────────────────
    "t10_normalize_whitespace": {
        "档次": "中 · 边界（内部连续空白没处理）",
        "文件名": "clean.py",
        "导入语句": "from clean import normalize",
        "题面": """# t10 · 规范化空白

`src/clean.py` 里的 `normalize()` 在有些输入上留下的空白不对。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def normalize(s):
    """去掉首尾空白，并把中间连续空白压成一个空格。"""
    return " ".join(s.split())
''',
        "src_bug": '''def normalize(s):
    """去掉首尾空白，并把中间连续空白压成一个空格。"""
    return s.strip()
''',
        "可见测试": "test_clean.py",
        "tests": '''def test_edges():
    assert normalize("\\ta\\n") == "a"


def test_inner_spaces():
    assert normalize("  a  b  ") == "a b"
''',
        "判分测试": "test_clean_hidden.py",
        "hidden": '''def test_mixed_whitespace():
    assert normalize("a \\t\\n b") == "a b"


def test_only_whitespace():
    assert normalize("   ") == ""


def test_untouched():
    assert normalize("word") == "word"


def test_three_words():
    assert normalize(" a  b   c ") == "a b c"
''',
    },

    # ── 中：去重用了 set，顺序全丢 ──────────────────────────
    "t11_dedup_order": {
        "档次": "中 · 边界（去重后顺序没了）",
        "文件名": "dedupe.py",
        "导入语句": "from dedupe import dedup",
        "题面": """# t11 · 去重

`src/dedupe.py` 里的 `dedup()` 去重之后元素的次序乱了。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def dedup(items):
    """去重，保持每个元素【第一次出现】的先后顺序。"""
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
''',
        "src_bug": '''def dedup(items):
    """去重，保持每个元素【第一次出现】的先后顺序。"""
    return list(set(items))
''',
        "可见测试": "test_dedupe.py",
        "tests": '''def test_simple():
    assert dedup([1, 1]) == [1]


def test_empty():
    assert dedup([]) == []


def test_order():
    assert dedup([3, 1, 3, 2]) == [3, 1, 2]
''',
        "判分测试": "test_dedupe_hidden.py",
        "hidden": '''def test_all_same():
    assert dedup([7, 7, 7]) == [7]


def test_no_mutation():
    src = [1, 1, 2]
    dedup(src)
    assert src == [1, 1, 2]


def test_mixed_order():
    assert dedup([5, 4, 5, 4, 3]) == [5, 4, 3]
''',
    },

    # ── 中：并列时没有第二排序键 ────────────────────────────
    "t12_sort_by_len_tie": {
        "档次": "中 · 边界（长度并列时没排序）",
        "文件名": "sorting.py",
        "导入语句": "from sorting import sort_by_len",
        "题面": """# t12 · 按长度排序

`src/sorting.py` 里的 `sort_by_len()` 排出来的顺序在某种情况下不稳定。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def sort_by_len(words):
    """按长度升序；长度一样按字母序。返回新列表。"""
    return sorted(words, key=lambda w: (len(w), w))
''',
        "src_bug": '''def sort_by_len(words):
    """按长度升序；长度一样按字母序。返回新列表。"""
    return sorted(words, key=lambda w: len(w))
''',
        "可见测试": "test_sorting.py",
        "tests": '''def test_by_length():
    assert sort_by_len(["ccc", "a", "bb"]) == ["a", "bb", "ccc"]


def test_tie():
    assert sort_by_len(["bb", "aa", "ab"]) == ["aa", "ab", "bb"]
''',
        "判分测试": "test_sorting_hidden.py",
        "hidden": '''def test_mixed():
    assert sort_by_len(["bbb", "a", "cc", "dd"]) == ["a", "cc", "dd", "bbb"]


def test_empty():
    assert sort_by_len([]) == []


def test_one():
    assert sort_by_len(["zz"]) == ["zz"]


def test_all_same_len():
    assert sort_by_len(["c", "a", "b"]) == ["a", "b", "c"]
''',
    },

    # ── 中：最大值种子写成了 0（全负数就错）──────────────────
    "t13_max_seed_negative": {
        "档次": "中 · 边界（种子值 0，全负数时错）",
        "文件名": "peak.py",
        "导入语句": "from peak import max_of",
        "题面": """# t13 · 找最大值

`src/peak.py` 里的 `max_of()` 在某一类列表上给错了结果。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def max_of(nums):
    """返回列表里的最大值；空列表返回 None。"""
    if not nums:
        return None
    best = nums[0]
    for n in nums[1:]:
        if n > best:
            best = n
    return best
''',
        "src_bug": '''def max_of(nums):
    """返回列表里的最大值；空列表返回 None。"""
    if not nums:
        return None
    best = 0
    for n in nums[1:]:
        if n > best:
            best = n
    return best
''',
        "可见测试": "test_peak.py",
        "tests": '''def test_positive():
    assert max_of([1, 5, 3]) == 5


def test_single():
    assert max_of([7]) == 7


def test_negative():
    assert max_of([-5, -2, -9]) == -2
''',
        "判分测试": "test_peak_hidden.py",
        "hidden": '''def test_empty():
    assert max_of([]) is None


def test_all_equal():
    assert max_of([4, 4]) == 4


def test_mixed():
    assert max_of([-1, 0, 1]) == 1


def test_float():
    assert max_of([0.5, -0.5]) == 0.5
''',
    },

    # ── 中：except 只接住了 TypeError，漏了 ValueError ────────
    "t14_parse_int_except": {
        "档次": "中 · 边界（异常类型接窄了）",
        "文件名": "convert.py",
        "导入语句": "from convert import parse_int",
        "题面": """# t14 · 宽松转整数

`src/convert.py` 里的 `parse_int()` 在某些输入下不但没兜住，还直接把异常甩了出来。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def parse_int(s, default=0):
    """把字符串转成整数；转不了（包括 None）就给 default。"""
    try:
        return int(s)
    except (ValueError, TypeError):
        return default
''',
        "src_bug": '''def parse_int(s, default=0):
    """把字符串转成整数；转不了（包括 None）就给 default。"""
    try:
        return int(s)
    except TypeError:
        return default
''',
        "可见测试": "test_convert.py",
        "tests": '''def test_number():
    assert parse_int("42") == 42


def test_negative():
    assert parse_int("-7") == -7


def test_bad():
    assert parse_int("abc") == 0


def test_custom_default():
    assert parse_int("x", -1) == -1
''',
        "判分测试": "test_convert_hidden.py",
        "hidden": '''def test_none():
    assert parse_int(None) == 0


def test_spaces():
    assert parse_int("  8  ") == 8


def test_float_string():
    assert parse_int("3.9") == 0


def test_empty():
    assert parse_int("") == 0
''',
    },

    # ── 中：切分没限次数（多个冒号就散架）────────────────────
    "t15_parse_pair_maxsplit": {
        "档次": "中 · 边界（split 没限次数）",
        "文件名": "pairs.py",
        "导入语句": "from pairs import parse_pair",
        "题面": """# t15 · 拆键值对

`src/pairs.py` 里的 `parse_pair()` 只该按【第一个】冒号拆成两半，
现在碰到多冒号的输入就拆多了。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def parse_pair(s):
    """把 "名字:值" 拆成 (名字, 值)。

    没有冒号 -> 值给空串；只按【第一个】冒号拆。
    """
    if ":" not in s:
        return (s, "")
    return tuple(s.split(":", 1))
''',
        "src_bug": '''def parse_pair(s):
    """把 "名字:值" 拆成 (名字, 值)。

    没有冒号 -> 值给空串；只按【第一个】冒号拆。
    """
    if ":" not in s:
        return (s, "")
    return tuple(s.split(":"))
''',
        "可见测试": "test_pairs.py",
        "tests": '''def test_simple():
    assert parse_pair("a:b") == ("a", "b")


def test_no_colon():
    assert parse_pair("abc") == ("abc", "")


def test_two_colons():
    assert parse_pair("a:b:c") == ("a", "b:c")
''',
        "判分测试": "test_pairs_hidden.py",
        "hidden": '''def test_empty_value():
    assert parse_pair("k:") == ("k", "")


def test_empty_key():
    assert parse_pair(":v") == ("", "v")


def test_empty():
    assert parse_pair("") == ("", "")


def test_many_colons():
    assert parse_pair("a:b:c:d") == ("a", "b:c:d")
''',
    },

    # ══════════════════════════════════════════════════════════════
    # 难：传递式（错在 A，症状出现在 B）+ 逻辑错（t16 ~ t20）
    #    这一类才是真正要考的：**眼睛盯着的那个函数往往是对的**，
    #    红的地方离真凶隔了一层，得顺着数据往回走。
    # ══════════════════════════════════════════════════════════════

    # ── 难：可变默认参数（第一次调用污染了后面每一次）────────
    "t16_mutable_default_box": {
        "档次": "难 · 传递式（可变默认参数，症状跨调用）",
        "文件名": "boxes.py",
        "导入语句": "from boxes import add_item",
        "题面": """# t16 · 往盒子里放东西

`src/boxes.py` 里的 `add_item()` 返回的字典里，
有时候会多出【上一次调用】留下的东西。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def add_item(key, value, box=None):
    """把 key->value 放进 box 并返回它。

    box 省略或传 None -> 新建一个空字典（每次都是新的）；
    传了字典 -> 就地改它（改动会留在外面）。
    """
    if box is None:
        box = {}
    box[key] = value
    return box
''',
        "src_bug": '''def add_item(key, value, box={}):
    """把 key->value 放进 box 并返回它。

    box 省略或传 None -> 新建一个空字典（每次都是新的）；
    传了字典 -> 就地改它（改动会留在外面）。
    """
    if box is None:
        box = {}
    box[key] = value
    return box
''',
        "可见测试": "test_boxes.py",
        "tests": '''def test_one_call():
    assert add_item("a", 1) == {"a": 1}


def test_two_calls_independent():
    add_item("x", 1)
    box = add_item("y", 2)
    assert box == {"y": 2}
''',
        "判分测试": "test_boxes_hidden.py",
        "hidden": '''def test_fresh_dict_each_time():
    assert add_item("a", 1) == {"a": 1}
    assert add_item("b", 2) == {"b": 2}


def test_explicit_box_is_mutated():
    box = {"z": 0}
    out = add_item("a", 1, box)
    assert out == {"z": 0, "a": 1}
    assert box == {"z": 0, "a": 1}


def test_none_gives_new_dict():
    assert add_item("k", 9, None) == {"k": 9}
    assert add_item("k", 9, None) == {"k": 9}


def test_overwrite():
    assert add_item("a", 2, {"a": 1}) == {"a": 2}
''',
    },

    # ── 难：别名（out = items 而不是拷贝，把入参改了）────────
    "t17_alias_mutates_input": {
        "档次": "难 · 传递式（没拷贝，改坏了入参）",
        "文件名": "padding.py",
        "导入语句": "from padding import pad_right",
        "题面": """# t17 · 右边补位

`src/padding.py` 里的 `pad_right()` 返回值看着是对的，
但调用它的地方发现【传进去的列表被改了】。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def pad_right(items, n, fill=0):
    """返回长度 n 的新列表，不够的用 fill 补在右边。

    已经有 n 个或更多就原样返回一份拷贝（不截断）。
    传入的 items 不会被改动。
    """
    out = list(items)
    while len(out) < n:
        out.append(fill)
    return out
''',
        "src_bug": '''def pad_right(items, n, fill=0):
    """返回长度 n 的新列表，不够的用 fill 补在右边。

    已经有 n 个或更多就原样返回一份拷贝（不截断）。
    传入的 items 不会被改动。
    """
    out = items
    while len(out) < n:
        out.append(fill)
    return out
''',
        "可见测试": "test_padding.py",
        "tests": '''def test_pads():
    assert pad_right([1, 2], 4) == [1, 2, 0, 0]


def test_input_untouched():
    src = [1, 2]
    pad_right(src, 4)
    assert src == [1, 2]
''',
        "判分测试": "test_padding_hidden.py",
        "hidden": '''def test_empty():
    assert pad_right([], 2) == [0, 0]


def test_already_long():
    assert pad_right([1, 2, 3], 2) == [1, 2, 3]


def test_custom_fill():
    assert pad_right(["a"], 3, "-") == ["a", "-", "-"]


def test_untouched_when_padded():
    src = [1]
    out = pad_right(src, 3)
    assert out == [1, 0, 0]
    assert src == [1]
''',
    },

    # ── 难：传递式（错在 to_cents 的浮点截断，症状在 total_cents）─
    "t18_cents_float_truncate": {
        "档次": "难 · 传递式（浮点截断，错在 A 症状在 B）",
        "文件名": "money.py",
        "导入语句": "from money import to_cents, total_cents",
        "题面": """# t18 · 金额换算

`src/money.py` 里的 `total_cents()` 加出来的总分会少几分钱。
少的那点出在 `to_cents()` 上。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def to_cents(yuan):
    """元 -> 分（四舍五入到整数分）。"""
    return int(round(yuan * 100))


def total_cents(prices):
    """把一组单价（元）换算成分之后加起来。"""
    return sum(to_cents(p) for p in prices)
''',
        "src_bug": '''def to_cents(yuan):
    """元 -> 分（四舍五入到整数分）。"""
    return int(yuan * 100)


def total_cents(prices):
    """把一组单价（元）换算成分之后加起来。"""
    return sum(to_cents(p) for p in prices)
''',
        "可见测试": "test_money.py",
        "tests": '''def test_simple():
    assert total_cents([1.5, 2.5]) == 400


def test_awkward():
    assert total_cents([0.29, 0.01]) == 30
''',
        "判分测试": "test_money_hidden.py",
        "hidden": '''def test_single_awkward():
    assert to_cents(0.29) == 29


def test_zero():
    assert to_cents(0) == 0


def test_exact():
    assert to_cents(3.5) == 350


def test_negative():
    assert to_cents(-1.5) == -150
''',
    },

    # ── 难：传递式（错在 words 没小写，症状在 count_words）────
    "t19_words_lower_downstream": {
        "档次": "难 · 传递式（错在 words，症状在 count_words）",
        "文件名": "counting.py",
        "导入语句": "from counting import words, count_words",
        "题面": """# t19 · 数单词

`src/counting.py` 里的 `count_words()` 把同一个词数成了好几个——
大小写不同的词本该算同一个，现在被分成了两拨。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def words(text):
    """按空白切词，并统一转成小写。"""
    return text.lower().split()


def count_words(text):
    """统计每个词出现的次数，返回 词 -> 次数。"""
    counts = {}
    for w in words(text):
        counts[w] = counts.get(w, 0) + 1
    return counts
''',
        "src_bug": '''def words(text):
    """按空白切词，并统一转成小写。"""
    return text.split()


def count_words(text):
    """统计每个词出现的次数，返回 词 -> 次数。"""
    counts = {}
    for w in words(text):
        counts[w] = counts.get(w, 0) + 1
    return counts
''',
        "可见测试": "test_counting.py",
        # ⚠️ 同 t03：让「看着没问题」的那条先过，红的那条指向调用方 count_words
        "tests": '''def test_words_plain():
    assert words("a b") == ["a", "b"]


def test_count_case():
    assert count_words("Hello hello HELLO") == {"hello": 3}
''',
        "判分测试": "test_counting_hidden.py",
        "hidden": '''def test_words_lower():
    assert words("A B") == ["a", "b"]


def test_words_empty():
    assert words("") == []


def test_count_mixed():
    assert count_words("a A b") == {"a": 2, "b": 1}


def test_count_empty():
    assert count_words("") == {}


def test_count_whitespace():
    assert count_words("  a   a  ") == {"a": 2}
''',
    },

    # ── 难：逻辑错（每个位置都重置了最大值，忘了比较）────────
    "t20_running_max_forget_compare": {
        "档次": "难 · 逻辑错（忘了跟历史最大值比）",
        "文件名": "series.py",
        "导入语句": "from series import running_max",
        "题面": """# t20 · 史上最高

`src/series.py` 里的 `running_max()` 应该给出「到当前位置为止的最大值」，
现在给的是当前位置自己的值——一遇到下降就掉回去了。

修好它，让 `tests/` 里的用例全绿。

规则：
- 只改 `src/` 下的代码；`tests/` 只读，不许动。
- 改完必须自己跑一遍测试验证。
""",
        "src_对": '''def running_max(nums):
    """返回新列表：每个位置是「从开头到当前位置」的最大值。空列表返回 []。"""
    out = []
    best = None
    for n in nums:
        if best is None or n > best:
            best = n
        out.append(best)
    return out
''',
        "src_bug": '''def running_max(nums):
    """返回新列表：每个位置是「从开头到当前位置」的最大值。空列表返回 []。"""
    out = []
    for n in nums:
        out.append(n)
    return out
''',
        "可见测试": "test_series.py",
        "tests": '''def test_rising():
    assert running_max([1, 3, 2]) == [1, 3, 3]


def test_falling():
    assert running_max([5, 1]) == [5, 5]
''',
        "判分测试": "test_series_hidden.py",
        "hidden": '''def test_empty():
    assert running_max([]) == []


def test_single():
    assert running_max([4]) == [4]


def test_all_equal():
    assert running_max([2, 2]) == [2, 2]


def test_negative():
    assert running_max([-3, -1, -5]) == [-3, -1, -1]
''',
    },
}


# ══════════════════════════════════════════════════════════════
# 闸箱：在临时目录里搭一份最小靶场，跑 pytest
# ══════════════════════════════════════════════════════════════
def 拼测试(用判分抬头, 导入语句, 正文):
    """把一份测试文件的全部零件拼起来：抬头 + 导入 + 正文。

    ⚠️ 【抬头和导入是两件事，缺一个都不行】—— 本脚本第一次跑就栽在这儿：
       抬头只把 src/ 塞进了 sys.path（负责"找得到"），可没人真的 import 那个模块。
       于是四道闸里闸①全红，3 道题一道没入库，报的是 NameError。
       这正是闸该有的样子：**它拦的不是模型的错，是我的错。**
    """
    抬头 = 判分抬头 if 用判分抬头 else 可见抬头
    return f"{抬头}\n{导入语句}\n\n{正文}"


def 跑一次(src内容, src文件名, 测试相对路径, 导入语句, 测试正文, 用判分抬头):
    """返回 (退出码, 输出)。临时目录跑完自动销毁 —— 不碰盘上的靶场。"""
    with tempfile.TemporaryDirectory() as td:
        沙箱 = Path(td) / "题目"
        (沙箱 / "src").mkdir(parents=True)
        (沙箱 / "src" / src文件名).write_text(src内容, encoding="utf-8")

        测试文件 = 沙箱 / 测试相对路径
        测试文件.parent.mkdir(parents=True, exist_ok=True)
        测试文件.write_text(拼测试(用判分抬头, 导入语句, 测试正文), encoding="utf-8")

        环境 = dict(os.environ)
        if 用判分抬头:
            环境["ARENA_SRC"] = str(沙箱 / "src")

        结果 = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=short", "--no-header",
             "-p", "no:cacheprovider", 测试相对路径],
            cwd=沙箱, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60, env=环境,
        )
        return 结果.returncode, (结果.stdout or "") + (结果.stderr or "")


def 数失败(输出):
    """从 pytest 摘要行里抠出失败/出错数，例如 '1 failed, 4 passed'。"""
    总数 = 0
    for m in re.finditer(r"(\d+) (failed|error)", 输出):
        总数 += int(m.group(1))
    return 总数


def 摘要行(输出):
    for 行 in reversed(输出.strip().splitlines()):
        if "passed" in 行 or "failed" in 行 or "error" in 行:
            return 行.strip()
    return "(没有摘要行)"


def 建一道(题号, 题):
    可见路径 = f"tests/{题['可见测试']}"
    判分路径 = f"hidden/{题['判分测试']}"
    print(f"\n[{题号}]  {题['档次']}")

    # ── 闸 ① 正解 + 可见测试 → 必须全绿
    码, 输出 = 跑一次(题["src_对"], 题["文件名"], 可见路径, 题["导入语句"], 题["tests"], False)
    if 码 != 0:
        print("   闸① 正解 + 可见测试 -> 红了  [NO]  <-- 是题坏了，不是模型的锅")
        print(输出)
        return None
    print(f"   闸① 正解 + 可见测试 -> 全绿  [OK]   {摘要行(输出)}")

    # ── 闸 ② 有 bug + 可见测试 → 必须红
    码, 输出 = 跑一次(题["src_bug"], 题["文件名"], 可见路径, 题["导入语句"], 题["tests"], False)
    if 码 == 0:
        print("   闸② 有 bug + 可见测试 -> 全绿  [NO]  <-- 死代码 bug，测试抓不到，作废")
        return None
    print(f"   闸② 有 bug + 可见测试 -> 红了  [OK]   {摘要行(输出)}")

    # ── 闸 ③ 正解 + 判分测试 → 必须全绿（验判分卷自己没写坏）
    码, 输出3 = 跑一次(题["src_对"], 题["文件名"], 判分路径, 题["导入语句"], 题["hidden"], True)
    if 码 != 0:
        print("   闸③ 正解 + 判分测试 -> 红了  [NO]  <-- 判分卷自己写坏了")
        print(输出3)
        return None
    print(f"   闸③ 正解 + 判分测试 -> 全绿  [OK]   {摘要行(输出3)}")

    # ── 闸 ④ 有 bug + 判分测试 → 记基线
    码, 输出4 = 跑一次(题["src_bug"], 题["文件名"], 判分路径, 题["导入语句"], 题["hidden"], True)
    基线 = 数失败(输出4)
    if 码 == 0:
        print("   闸④ 有 bug + 判分测试 -> 全绿  [NO]  <-- 判分卷也抓不到，作废")
        return None
    print(f"   闸④ 有 bug + 判分测试 -> 红了  [OK]   基线失败 {基线} 个用例  ({摘要行(输出4)})")

    # ── 四道闸全过 → 落盘
    这题目录 = 题目目录 / 题号
    (这题目录 / "src").mkdir(parents=True, exist_ok=True)
    (这题目录 / "tests").mkdir(parents=True, exist_ok=True)
    (这题目录 / "task.md").write_text(题["题面"], encoding="utf-8")
    # ⚠️ 只写 src_bug。src_对 是闸箱里的东西，盘上一份都不留。
    (这题目录 / "src" / 题["文件名"]).write_text(题["src_bug"], encoding="utf-8")
    (这题目录 / "tests" / 题["可见测试"]).write_text(
        拼测试(False, 题["导入语句"], 题["tests"]), encoding="utf-8")

    (判分目录 / 题号).mkdir(parents=True, exist_ok=True)
    (判分目录 / 题号 / 题["判分测试"]).write_text(
        拼测试(True, 题["导入语句"], 题["hidden"]), encoding="utf-8")

    print(f"   落盘  tasks/{题号}/  隐藏  hidden/{题号}/")
    return {"题号": 题号, "档次": 题["档次"], "基线失败": 基线}


def main():
    print("=" * 70)
    print("出题机 —— 每道题跑四道闸，全过才准入库")
    print("=" * 70)

    好的 = []
    for 题号, 题 in 题目表.items():
        结果 = 建一道(题号, 题)
        if 结果 is not None:
            好的.append(结果)

    print("\n" + "=" * 70)
    print(f"{len(好的)} / {len(题目表)} 道题入库")
    for r in 好的:
        print(f"  {r['题号']:<24} {r['档次']:<34} 基线失败 {r['基线失败']}")
    print("=" * 70)

    return 0 if len(好的) == len(题目表) else 1


if __name__ == "__main__":
    sys.exit(main())
