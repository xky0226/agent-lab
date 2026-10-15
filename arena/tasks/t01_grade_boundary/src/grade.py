def grade(score):
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
