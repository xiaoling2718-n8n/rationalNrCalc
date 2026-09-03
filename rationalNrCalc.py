import streamlit as st
import random
import re
from fractions import Fraction
import math
from decimal import Decimal, ROUND_HALF_UP

# 页面配置
st.set_page_config(
    page_title="数学闯关·有理数计算",
    page_icon="⚔️",
    layout="centered"
)

# ---------- 初始化 session 状态 ----------
if "stage" not in st.session_state:
    st.session_state.stage = 0
if "question" not in st.session_state:
    st.session_state.question = None
if "steps" not in st.session_state:
    st.session_state.steps = []
if "current_step_index" not in st.session_state:
    st.session_state.current_step_index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "monster_defeated" not in st.session_state:
    st.session_state.monster_defeated = False
if "feedback" not in st.session_state:
    st.session_state.feedback = ""
if "done" not in st.session_state:
    st.session_state.done = False
if "penalty" not in st.session_state:
    st.session_state.penalty = False
if "total_steps" not in st.session_state:
    st.session_state.total_steps = 0
if "original_expr" not in st.session_state:
    st.session_state.original_expr = ""
if "expected_steps" not in st.session_state:
    st.session_state.expected_steps = []
if "final_result" not in st.session_state:
    st.session_state.final_result = None
if "numbers" not in st.session_state:
    st.session_state.numbers = []
if "operators" not in st.session_state:
    st.session_state.operators = []
if "difficulty" not in st.session_state:
    st.session_state.difficulty = 1
if "difficulty_name" not in st.session_state:
    st.session_state.difficulty_name = "🌟 基础运算"
if "display_expr" not in st.session_state:
    st.session_state.display_expr = ""

# ---------- 难度级别配置 ----------
DIFFICULTY_LEVELS = {
    1: {
        "name": "🌟 基础运算",
        "icon": "➕",
        "description": "正负混合 · 整数 · 分数 · 小数加减运算",
        "color": "#4CAF50"
    },
    2: {
        "name": "🔥 绝对值运算",
        "icon": "｜｜",
        "description": "含绝对值的加减混合运算",
        "color": "#FF9800"
    },
    3: {
        "name": "⚡ 乘除运算",
        "icon": "✖️",
        "description": "含乘除法的四则运算",
        "color": "#2196F3"
    },
    4: {
        "name": "🚀 乘方运算",
        "icon": "💪",
        "description": "含乘方运算 · 科学计数法",
        "color": "#9C27B0"
    },
    5: {
        "name": "🏆 综合运算",
        "icon": "🏅",
        "description": "含小括号的四则混合运算",
        "color": "#F44336"
    }
}

# ---------- 格式化函数 ----------
def format_fraction(value):
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"

def fraction_to_mixed(value):
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    sign = "-" if value < 0 else ""
    value = abs(value)
    whole = value.numerator // value.denominator
    remainder = value.numerator % value.denominator
    if whole == 0:
        return f"{sign}{remainder}/{value.denominator}"
    if remainder == 0:
        return f"{sign}{whole}"
    return f"{sign}{whole} {remainder}/{value.denominator}"

def fraction_to_decimal(value, places=3):
    try:
        return round(float(value), places)
    except:
        return float(value)

def contains_decimal(expr):
    if not expr:
        return False
    expr = str(expr)
    pattern = r'(?<![\w.])-?(?:\d+\.\d+|\.\d+)'
    return re.search(pattern, expr) is not None

def round_decimal_3(value):
    try:
        return Decimal(str(float(value))).quantize(
            Decimal("0.001"),
            rounding=ROUND_HALF_UP
        )
    except:
        return Decimal(str(value)).quantize(
            Decimal("0.001"),
            rounding=ROUND_HALF_UP
        )

def contains_absolute(expr):
    return '|' in str(expr)

# ---------- LaTeX 渲染函数 ----------
def to_latex(expr):
    """
    将表达式转换为 LaTeX 格式
    支持：分数、带分数、乘方、科学计数法、绝对值
    """
    # 先处理带括号的带分数（如 (-3 1/4)，通常紧跟在运算符后面）
    # 整体替换为 \left(-整数\frac{分子}{分母}\right)——负号必须放在括号里面，
    # 否则渲染出来会变成 "÷ -\left(...\right)"，负号又跑到括号外面紧贴前一个运算符，
    # 看起来还是"两个运算符相连"
    def replace_wrapped_mixed(match):
        whole = match.group(1)
        num = match.group(2)
        den = match.group(3)
        if whole.startswith('-'):
            whole_abs = whole[1:]
            return f"\\left(-{whole_abs}\\frac{{{num}}}{{{den}}}\\right)"
        else:
            return f"\\left({whole}\\frac{{{num}}}{{{den}}}\\right)"

    expr = re.sub(r'\((-?\d+)\s+(\d+)/(\d+)\)', replace_wrapped_mixed, expr)

    # 再处理未加括号的带分数：整数 分子/分母 -> 整数\frac{分子}{分母}（不加"+"，
    # 避免与前后的加减号混在一起导致带分数在视觉上"消失"/拆散）。
    # 如果是负数，同样把负号放进 \left( \right) 里面，理由同上。
    def replace_mixed(match):
        whole = match.group(1)
        num = match.group(2)
        den = match.group(3)
        if whole.startswith('-'):
            whole_abs = whole[1:]
            return f"\\left(-{whole_abs}\\frac{{{num}}}{{{den}}}\\right)"
        else:
            return f"{whole}\\frac{{{num}}}{{{den}}}"
    
    # 匹配带分数：整数 分子/分母
    expr = re.sub(r'(-?\d+)\s+(\d+)/(\d+)', replace_mixed, expr)
    
    # 处理普通分数：分子/分母 -> \frac{分子}{分母}
    def replace_fraction(match):
        num = match.group(1)
        den = match.group(2)
        return f"\\frac{{{num}}}{{{den}}}"
    
    # 匹配分数，但跳过已经处理的带分数部分
    expr = re.sub(r'(?<!\d)(\d+)/(\d+)', replace_fraction, expr)
    
    # 处理乘方：a^b -> a^{b}
    # 注意：不要重复替换已经处理过的
    def replace_power(match):
        base = match.group(1)
        exp = match.group(2)
        return f"{base}^{{{exp}}}"
    
    # 先处理带括号的底数：(-3)^2 -> (-3)^{2}
    expr = re.sub(r'\((-?\d+)\)\^(\d+)', r'(\1)^{\2}', expr)
    # 再处理普通底数：3^2 -> 3^{2}
    expr = re.sub(r'(\d+)\^(\d+)', r'\1^{\2}', expr)
    
    # 处理科学计数法：a×10^b -> a \times 10^{b}
    expr = re.sub(r'(\d+)×10\^(\d+)', r'\1 \\times 10^{\2}', expr)
    
    # 处理乘号和除号
    expr = expr.replace('×', ' \\times ')
    expr = expr.replace('÷', ' \\div ')
    
    # 处理空格
    expr = re.sub(r'\s+', ' ', expr)
    
    return expr

def to_latex_simple(expr):
    """
    简单转换，用于显示步骤
    """
    # 处理分数
    expr = re.sub(r'(\d+)/(\d+)', r'\\frac{\1}{\2}', expr)
    # 处理乘号
    expr = expr.replace('×', ' \\times ')
    expr = expr.replace('÷', ' \\div ')
    # 处理绝对值
    expr = expr.replace('|', '\\left|').replace('|', '\\right|')
    return expr

# ---------- 带分数处理函数 ----------
def is_mixed_number(expr):
    expr = expr.strip()
    pattern = r'^-?\d+\s+\d+/\d+$'
    return bool(re.match(pattern, expr))

def convert_mixed_to_improper(expr):
    expr = expr.strip()
    if not is_mixed_number(expr):
        return None, "不是带分数格式"
    parts = expr.split()
    if len(parts) != 2:
        return None, "格式错误"
    try:
        whole = int(parts[0])
        num, den = parts[1].split('/')
        num = int(num)
        den = int(den)
        if den <= 0:
            return None, "分母必须大于0"
        if num < 0:
            return None, "带分数的分子不能为负数"
        if num >= den:
            return None, f"{num}/{den} 不是真分数"
        if whole >= 0:
            result = Fraction(whole * den + num, den)
        else:
            result = Fraction(-(abs(whole) * den + num), den)
        return result, f"{expr} = {result}"
    except ValueError as e:
        return None, f"数字格式错误：{e}"

def replace_mixed_numbers(expr):
    pattern = re.compile(r'(?<![\w.)])(-?\d+)\s+(\d+)\s*/\s*(\d+)(?![\w.(])')
    def mixed_to_fraction(match):
        whole = int(match.group(1))
        numerator = int(match.group(2))
        denominator = int(match.group(3))
        if denominator == 0:
            raise ValueError("分母不能为 0")
        sign = -1 if whole < 0 else 1
        whole_abs = abs(whole)
        numerator_total = whole_abs * denominator + numerator
        numerator_total *= sign
        return f"({numerator_total}/{denominator})"
    while pattern.search(expr):
        expr = pattern.sub(mixed_to_fraction, expr)
    return expr

def calculate_value(expr):
    """计算表达式的值 - 使用 power_parse 算法处理幂指数"""
    try:
        # 处理绝对值
        has_abs = '|' in expr
        if has_abs:
            def replace_abs(match):
                inner = match.group(1)
                val = calculate_value(inner)
                if val is None:
                    return "0"
                return str(abs(float(val)))
            expr = re.sub(r'\|([^|]*)\|', replace_abs, expr)
        
        # 关键修复：将中文乘除符号转换为 Python 可识别的 * 和 /
        # 否则表达式中一旦出现 × 或 ÷（如含乘方的题目里常见），eval 会直接报语法错误，
        # calculate_value 返回 None，导致这些步骤（包括乘方结果）永远无法被判定为正确
        expr = expr.replace('×', '*').replace('÷', '/')
        
        expr_without_mixed = replace_mixed_numbers(expr)
        namespace = {'Fraction': Fraction}
        
        def replace_fraction(match):
            num = int(match.group(1))
            den = int(match.group(2))
            return f"Fraction({num}, {den})"
        
        expr_eval = re.sub(r'(\d+)/(\d+)', replace_fraction, expr_without_mixed)
        expr_eval = re.sub(r'\s+', '', expr_eval)
        
        # ---------- 使用 power_parse 算法处理幂指数 ----------
        # 处理乘方：a^b -> a**b
        # 处理负底数：(-3)^2 -> (-3)**2
        expr_eval = re.sub(r'\((-?\d+)\)\^(\d+)', r'((\1)**(\2))', expr_eval)
        # 处理普通底数：3^2 -> 3**2
        expr_eval = re.sub(r'(\d+)\^(\d+)', r'((\1)**(\2))', expr_eval)
        
        # 注：科学计数法 a×10^b 中的 × 已在函数开头被转换为 *，
        # "10^b" 会被上面的通用乘方正则处理为 10**(b)，无需再单独匹配 "×10^"
        
        result = eval(expr_eval, namespace)
        if isinstance(result, Fraction):
            result = result.limit_denominator()
        return result
    except Exception as e:
        try:
            expr_clean = re.sub(r'\s+', '', expr)
            result = eval(expr_clean)
            return result
        except:
            return None

def get_value_from_expr(expr):
    expr = expr.strip()
    return calculate_value(expr)

def is_equal(value1, value2, accept_rounding=True):
    if value1 is None or value2 is None:
        return False
    try:
        if isinstance(value1, (int, Fraction)) and isinstance(value2, (int, Fraction)):
            return value1 == value2
        if accept_rounding:
            v1 = round_decimal_3(value1)
            v2 = round_decimal_3(value2)
            return v1 == v2
        return abs(float(value1) - float(value2)) < 1e-3
    except Exception:
        return False

def is_pure_number(expr):
    expr_clean = expr.strip()
    pattern = r'^\-?\d+(\.\d+)?$|^\-?\d+/\d+$|^\-?\d+\s+\d+/\d+$'
    return bool(re.match(pattern, expr_clean))

def is_fraction_simplified(frac_str):
    if ' ' in frac_str:
        parts = frac_str.split()
        if len(parts) == 2:
            frac_part = parts[1]
            if '/' in frac_part:
                frac_parts = frac_part.split('/')
                if len(frac_parts) == 2:
                    try:
                        num = abs(int(frac_parts[0]))
                        den = int(frac_parts[1])
                        from math import gcd
                        return gcd(num, den) == 1
                    except:
                        pass
        return True
    if frac_str.startswith('-'):
        frac_str = frac_str[1:]
    if '/' not in frac_str:
        return True
    parts = frac_str.split('/')
    if len(parts) != 2:
        return False
    try:
        num = abs(int(parts[0].strip()))
        den = int(parts[1].strip())
        if den == 0:
            return False
        from math import gcd
        return gcd(num, den) == 1
    except:
        return False

# ---------- 辅助函数：格式化负数 ----------
def format_number_for_display(num):
    """格式化数字用于显示，负数加括号"""
    if isinstance(num, Fraction):
        if num < 0:
            return f"({format_fraction(num)})"
        return format_fraction(num)
    elif isinstance(num, float):
        if num < 0:
            return f"({num})"
        return str(num)
    else:
        if num < 0:
            return f"({num})"
        return str(num)

def build_expression_safe(numbers, operators):
    """安全构建表达式，确保负数加括号，运算符不连续"""
    parts = []
    
    for i, num in enumerate(numbers):
        if isinstance(num, str):
            formatted = num
        else:
            formatted = format_number_for_display(num)
        
        parts.append(formatted)
        
        if i < len(operators):
            parts.append(operators[i])
    
    return " ".join(parts)

def generate_question(difficulty):
    """根据难度生成题目"""
    if difficulty == 1:
        return generate_question_level1()
    elif difficulty == 2:
        return generate_question_level2()
    elif difficulty == 3:
        return generate_question_level3()
    elif difficulty == 4:
        return generate_question_level4()
    elif difficulty == 5:
        return generate_question_level5()

def generate_number(difficulty, allow_negative=True):
    """生成随机数"""
    num_type = random.choice(['int', 'fraction', 'decimal'])
    
    if difficulty >= 3:
        max_val = 20 if difficulty >= 4 else 15
    else:
        max_val = 12
    
    if num_type == 'int':
        val = random.randint(1 if not allow_negative else -max_val, max_val)
        while val == 0:
            val = random.randint(1 if not allow_negative else -max_val, max_val)
        return val
    elif num_type == 'fraction':
        den = random.randint(2, 8)
        num = random.randint(1, den - 1)
        if allow_negative and random.random() > 0.5:
            num = -num
        return Fraction(num, den)
    else:  # decimal
        val = random.randint(1, max_val) + random.randint(1, 99) / 100
        if allow_negative and random.random() > 0.5:
            val = -val
        return round(val, 2)

def generate_exponent_number(difficulty):
    """生成乘方运算的底数和指数"""
    max_base = 5 if difficulty >= 5 else 4
    if difficulty >= 5:
        max_exp = 4
    elif difficulty >= 4:
        max_exp = 3
    else:
        max_exp = 2
    
    base = random.randint(1, max_base)
    exp = random.randint(2, max_exp)
    return base, exp

def generate_scientific_notation():
    """生成科学计数法题目"""
    num = random.randint(1, 9)
    exp = random.randint(1, 6)
    return num, exp

def generate_question_level1():
    """第一级：有理数加减运算"""
    num_count = random.randint(3, 5)
    numbers = []
    operators = []
    
    for i in range(num_count):
        num = generate_number(1)
        numbers.append(num)
        if i < num_count - 1:
            operators.append(random.choice(['+', '-']))
    
    return build_expression_safe(numbers, operators)

def generate_question_level2():
    """第二级：含绝对值的加减运算"""
    num_count = random.randint(3, 5)
    numbers = []
    operators = []
    
    has_abs = False
    for i in range(num_count):
        if not has_abs and random.random() > 0.4:
            val = generate_number(2)
            val_str = format_number_for_display(val)
            numbers.append(f"|{val_str}|")
            has_abs = True
        else:
            numbers.append(generate_number(2))
        if i < num_count - 1:
            operators.append(random.choice(['+', '-']))
    
    if not has_abs:
        idx = random.randint(0, len(numbers) - 1)
        val = generate_number(2)
        val_str = format_number_for_display(val)
        numbers[idx] = f"|{val_str}|"
    
    return build_expression_safe(numbers, operators)

def generate_question_level3():
    """第三级：含乘除法的运算"""
    num_count = random.randint(3, 5)
    numbers = []
    operators = []
    
    for i in range(num_count):
        if random.random() > 0.4:
            whole = random.randint(1, 5)
            den = random.randint(2, 6)
            num = random.randint(1, den - 1)
            if random.random() > 0.5:
                val = f"(-{whole} {num}/{den})"
            else:
                val = f"{whole} {num}/{den}"
            numbers.append(val)
        else:
            numbers.append(generate_number(3))
        if i < num_count - 1:
            operators.append(random.choice(['+', '-', '×', '÷']))
    
    return build_expression_safe(numbers, operators)

def generate_question_level4():
    """第四级：含乘方运算"""
    num_count = random.randint(3, 4)
    numbers = []
    operators = []
    
    has_exponent = False
    for i in range(num_count):
        if not has_exponent and random.random() > 0.4:
            base, exp = generate_exponent_number(4)
            if random.random() > 0.5:
                base_str = f"({-base})"
            else:
                base_str = str(base)
            numbers.append(f"{base_str}^{exp}")
            has_exponent = True
        elif random.random() > 0.6 and not has_exponent:
            num, exp = generate_scientific_notation()
            numbers.append(f"{num}×10^{exp}")
            has_exponent = True
        else:
            numbers.append(generate_number(4))
        if i < num_count - 1:
            operators.append(random.choice(['+', '-']))
    
    if not has_exponent:
        idx = random.randint(0, len(numbers) - 1)
        base, exp = generate_exponent_number(4)
        if random.random() > 0.5:
            base_str = f"({-base})"
        else:
            base_str = str(base)
        numbers[idx] = f"{base_str}^{exp}"
    
    return build_expression_safe(numbers, operators)

def generate_question_level5():
    """第五级：含小括号的四则混合运算"""
    num_count = random.randint(4, 6)
    numbers = []
    operators = []
    
    for i in range(num_count):
        if random.random() > 0.5:
            whole = random.randint(1, 5)
            den = random.randint(2, 6)
            num = random.randint(1, den - 1)
            if random.random() > 0.5:
                val = f"(-{whole} {num}/{den})"
            else:
                val = f"{whole} {num}/{den}"
            numbers.append(val)
        elif random.random() > 0.6:
            base, exp = generate_exponent_number(5)
            if random.random() > 0.5:
                base_str = f"({-base})"
            else:
                base_str = str(base)
            numbers.append(f"{base_str}^{exp}")
        else:
            numbers.append(generate_number(5))
        if i < num_count - 1:
            operators.append(random.choice(['+', '-', '×', '÷']))
    
    expr = build_expression_with_parentheses_safe(numbers, operators)
    return expr

def build_expression_with_parentheses_safe(numbers, operators):
    """构建带括号的表达式，确保负数加括号"""
    if len(numbers) < 3:
        return build_expression_safe(numbers, operators)
    
    parts = []
    for i, num in enumerate(numbers):
        if isinstance(num, str):
            parts.append(num)
        else:
            parts.append(format_number_for_display(num))
        if i < len(operators):
            parts.append(operators[i])
    
    if len(numbers) >= 4:
        start = random.randint(1, len(numbers) - 2)
        end = random.randint(start + 1, len(numbers) - 1)
        
        new_parts = []
        for i, num in enumerate(numbers):
            if i == start:
                new_parts.append("(")
            if isinstance(num, str):
                new_parts.append(num)
            else:
                new_parts.append(format_number_for_display(num))
            if i == end:
                new_parts.append(")")
            if i < len(operators):
                new_parts.append(operators[i])
        
        return " ".join(new_parts)
    
    return " ".join(parts)

def calculate_final_result(expr, difficulty):
    """计算最终结果"""
    expr_clean = expr
    
    expr_clean = expr_clean.replace('×', '*').replace('÷', '/')
    expr_clean = re.sub(r'\(?(-?\d+)\)?\^(\d+)', r'(\1)**(\2)', expr_clean)
    expr_clean = re.sub(r'(\d+)×10\^(\d+)', r'(\1)*10**(\2)', expr_clean)
    expr_clean = replace_mixed_numbers(expr_clean)
    
    if '|' in expr_clean:
        def replace_abs(match):
            inner = match.group(1)
            val = calculate_value(inner)
            if val is None:
                return "0"
            return str(abs(float(val)))
        expr_clean = re.sub(r'\|([^|]*)\|', replace_abs, expr_clean)
    
    try:
        namespace = {'Fraction': Fraction}
        def replace_fraction(match):
            num = int(match.group(1))
            den = int(match.group(2))
            return f"Fraction({num}, {den})"
        
        expr_eval = re.sub(r'(\d+)/(\d+)', replace_fraction, expr_clean)
        expr_eval = re.sub(r'\s+', '', expr_eval)
        
        result = eval(expr_eval, namespace)
        if isinstance(result, Fraction):
            result = result.limit_denominator()
        return result
    except:
        return None

# ---------- 游戏逻辑 ----------
def reset_game():
    st.session_state.stage = 0
    st.session_state.question = None
    st.session_state.steps = []
    st.session_state.current_step_index = 0
    st.session_state.score = 0
    st.session_state.monster_defeated = False
    st.session_state.feedback = ""
    st.session_state.done = False
    st.session_state.penalty = False
    st.session_state.total_steps = 0
    st.session_state.original_expr = ""
    st.session_state.expected_steps = []
    st.session_state.final_result = None
    st.session_state.numbers = []
    st.session_state.operators = []
    st.session_state.display_expr = ""

def new_question():
    expr = generate_question(st.session_state.difficulty)
    st.session_state.original_expr = expr
    
    # 生成 LaTeX 显示
    st.session_state.display_expr = to_latex(expr)
    
    final_result = calculate_final_result(expr, st.session_state.difficulty)
    st.session_state.final_result = final_result
    
    st.session_state.steps = []
    st.session_state.current_step_index = 0
    st.session_state.done = False
    st.session_state.feedback = ""
    st.session_state.penalty = False
    st.session_state.monster_defeated = False
    st.session_state.stage = 1
    st.session_state.prev_expression = expr

def validate_step(step_str, prev_expression, final_result, steps_so_far):
    """验证学生的计算步骤"""
    step_str = step_str.strip()
    if not step_str:
        return False, "请输入计算结果，例如：= 5/6", False
    if not step_str.startswith("="):
        return False, "每一步只填写等号右边的内容，请从 '=' 开始", False
    if step_str.count("=") != 1:
        return False, "每一步只能有一个等号", False
    
    right_side = step_str[1:].strip()
    if not right_side:
        return False, "等号后面不能为空", False
    
    # 检查两个运算符是否直接相连，例如 "× -3" 或 "+ -5"（负数没有加括号）。
    # 扩展到 +-×÷ 任意两个运算符组合，而不仅仅是 +/- 组合。
    if re.search(r'[\+\-×÷]\s*[\+\-×÷]', right_side):
        return False, "两个运算符不能直接相连，负数请用括号括起来，如 (-3)+(-5) 或 5×(-3)", False
    
    if steps_so_far:
        last_step = steps_so_far[-1].strip()
        if last_step.startswith("="):
            previous_value_expr = last_step[1:].strip()
        else:
            previous_value_expr = last_step.strip()
        current_left_expr = previous_value_expr
    else:
        current_left_expr = prev_expression
    
    left_value = get_value_from_expr(current_left_expr)
    if left_value is None:
        return False, f"无法计算上一结果：{current_left_expr}", False
    
    right_value = get_value_from_expr(right_side)
    if right_value is None:
        return False, f"无法识别你的计算结果：{right_side}", False
    
    use_rounding = contains_decimal(current_left_expr) or contains_decimal(right_side)
    
    if not is_equal(left_value, right_value, use_rounding):
        return False, f"计算错误！\n上一结果：{fraction_to_mixed(left_value)}\n你的结果：{fraction_to_mixed(right_value)}", False
    
    if is_pure_number(right_side):
        use_rounding = contains_decimal(right_side)
        if not is_equal(right_value, final_result, use_rounding):
            return False, f"最终结果错误。\n正确答案：{fraction_to_mixed(final_result)}", False
        
        if "/" in right_side:
            if not is_fraction_simplified(right_side):
                simplified = format_fraction(right_value)
                mixed = fraction_to_mixed(right_value)
                return True, f"数值正确！但分数还没有约分到最简。\n请继续约分为：{simplified}", False
        
        return True, "🎉 最终结果正确！", True
    
    if "/" in right_side:
        if not is_fraction_simplified(right_side):
            simplified = format_fraction(right_value)
            return True, f"步骤正确！可以继续约分为：{simplified}", False
    
    return True, "✅ 步骤正确！", False

def submit_step():
    user_input = st.session_state.get('step_input', '').strip()
    if not user_input:
        st.session_state.feedback = "请输入计算步骤！"
        return
    
    if st.session_state.done:
        st.session_state.feedback = "这道题已经完成了！请挑战下一只怪物"
        return
    
    prev_expr = st.session_state.steps[-1] if st.session_state.steps else st.session_state.original_expr
    
    result = validate_step(
        user_input,
        prev_expr,
        st.session_state.final_result,
        st.session_state.steps
    )
    
    if len(result) == 3:
        is_valid, message, is_final = result
    else:
        is_valid, message = result
        is_final = False
    
    if is_valid:
        st.session_state.steps.append(user_input)
        st.session_state.current_step_index += 1
        st.session_state.feedback = message
        st.session_state.penalty = False
        
        if is_final:
            st.session_state.done = True
            st.session_state.score += 1
            st.session_state.monster_defeated = True
            st.session_state.feedback = "🎉 恭喜！你击败了怪物！获得1分！"
    else:
        st.session_state.feedback = f"❌ {message}"
        st.session_state.penalty = True
        st.session_state.score -= 1
    
    st.session_state.step_input = ""

# ---------- 显示界面 ----------
def main():
    st.title("⚔️ 数学闯关 · 有理数计算")
    
    # 难度选择
    st.markdown("---")
    st.subheader("🎯 选择难度级别")
    
    cols = st.columns(5)
    for i in range(1, 6):
        level = DIFFICULTY_LEVELS[i]
        with cols[i-1]:
            if st.button(
                f"{level['icon']}\n{level['name']}",
                key=f"diff_{i}",
                use_container_width=True,
                type="primary" if st.session_state.difficulty == i else "secondary"
            ):
                st.session_state.difficulty = i
                st.session_state.difficulty_name = level['name']
                reset_game()
                st.rerun()
    
    current_level = DIFFICULTY_LEVELS[st.session_state.difficulty]
    st.info(f"**{current_level['icon']} 当前难度：{current_level['name']}** — {current_level['description']}")
    st.markdown("---")
    
    with st.sidebar:
        st.header("🏆 战绩")
        st.metric("打倒怪物", st.session_state.score)
        
        st.markdown(f"**📊 当前难度：** {current_level['icon']} {current_level['name']}")
        
        if st.session_state.steps:
            st.progress(min(1.0, len(st.session_state.steps) / 8))
            st.caption(f"已写 {len(st.session_state.steps)} 步")
        
        if st.session_state.monster_defeated:
            st.success("💥 怪物被击败！")
        if st.session_state.penalty:
            st.error("💢 怪物反击！")
        if st.session_state.score >= 5:
            st.balloons()
            st.success("🌟 你太棒了！继续挑战！")
        
        st.markdown("---")
        st.caption("💡 点击上方的难度按钮切换级别")
        st.caption("📌 规则：负数用括号括起来，如 (-3)")
    
    if st.session_state.stage == 0:
        st.info("👋 准备好了吗？点击下方按钮开始挑战！")
        if st.button("⚔️ 召唤怪物（生成题目）"):
            new_question()
            st.rerun()
    else:
        st.subheader("📝 当前题目")
        
        # 使用 LaTeX 显示题目
        display_expr = st.session_state.get("display_expr", "")
        if display_expr:
            st.latex(display_expr)
        else:
            original_expr = st.session_state.get("original_expr", "")
            st.write(f"**计算：** `{original_expr}`")
        
        st.caption("💡 提示：逐步化简，每一步都要合理，最后得到结果")
        
        # 显示题目类型提示
        difficulty_hints = {
            1: "📌 加减运算 · 注意符号变化 · 负数加括号",
            2: "📌 含绝对值 · 先算绝对值再运算 · 负数加括号",
            3: "📌 乘除运算 · 注意运算顺序（先乘除后加减）· 负数加括号",
            4: "📌 乘方运算 · 注意乘方的优先级 · 负数底数加括号",
            5: "📌 四则混合 · 注意括号优先级 · 负数加括号"
        }
        st.info(difficulty_hints.get(st.session_state.difficulty, ""))
        
        if st.session_state.steps:
            st.write("**✅ 你的步骤：**")
            for i, step in enumerate(st.session_state.steps):
                # 显示步骤（尝试用 LaTeX 渲染）
                step_display = step
                if step.startswith("="):
                    step_content = step[1:].strip()
                    try:
                        step_latex = to_latex_simple(step_content)
                        st.success(f"第{i+1}步: $= {step_latex}$")
                    except:
                        st.success(f"第{i+1}步: {step}")
                else:
                    st.success(f"第{i+1}步: {step}")
        
        if st.session_state.feedback:
            if "✅" in st.session_state.feedback or "🎉" in st.session_state.feedback:
                st.success(st.session_state.feedback)
            elif "❌" in st.session_state.feedback:
                st.error(st.session_state.feedback)
            else:
                st.info(st.session_state.feedback)
        
        if not st.session_state.done:
            with st.form(key="step_form"):
                step_input = st.text_input(
                    "输入下一步的计算过程（以 = 开头）：",
                    placeholder="例如：= (-3)+(-5)+2 或 = 5/6",
                    key="step_input_widget"
                )
                st.caption("💡 提示：负数请加括号，如 (-3)；两个运算符不能直接相连")
                submitted = st.form_submit_button("提交步骤")
                if submitted:
                    st.session_state.step_input = step_input
                    submit_step()
                    st.rerun()
            
            if not st.session_state.steps:
                st.info("💡 第1步示例：可以先去括号、去绝对值，或通分合并")
            else:
                st.info("💡 继续化简，每一步都从上一结果继续")
        else:
            st.balloons()
            st.success("🎊 所有步骤完成！怪物已倒！")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⚔️ 挑战下一只怪物", use_container_width=True):
                    new_question()
                    st.rerun()
            with col2:
                if st.button("🔄 重新开始", use_container_width=True):
                    reset_game()
                    st.rerun()
        
        if st.button("🔄 重置游戏 (清空分数)", use_container_width=True):
            reset_game()
            st.rerun()

if __name__ == "__main__":
    main()