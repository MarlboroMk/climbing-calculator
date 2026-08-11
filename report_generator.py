"""
MD 报告生成器
对开爬坡计算报告生成，包含输入参数、中间变量、最终结果及计算原理说明
"""

from calculator import CalculationResult


def generate_report(result: CalculationResult, custom_name: str = "") -> str:
    """
    生成完整的 Markdown 格式计算报告

    Args:
        result: 计算结果
        custom_name: 用户自定义的计算名称

    Returns:
        str: Markdown 格式报告全文
    """
    p = result.params
    im = result.intermediate
    fn = result.final

    lines = []

    # ---- 标题 ----
    name = custom_name or "对开爬坡能力计算"
    lines.append(f"# {name} — 计算报告")
    lines.append("")

    # ============================================================
    # 1. 输入参数
    # ============================================================
    lines.append("## 一、输入参数")
    lines.append("")

    lines.append("### 1.1 轮胎参数")
    lines.append("")
    lines.append("| 参数 | 符号 | 数值 | 单位 |")
    lines.append("|------|------|------|------|")
    lines.append(f"| 胎宽 | B | {p.tire_width:.0f} | mm |")
    lines.append(f"| 扁平比 | C | {p.aspect_ratio:.0f} | — |")
    lines.append(f"| 轮辋直径 | D | {p.rim_diameter:.0f} | inch |")
    lines.append("")

    lines.append("### 1.2 质量与质心")
    lines.append("")
    lines.append("| 参数 | 符号 | 数值 | 单位 |")
    lines.append("|------|------|------|------|")
    lines.append(f"| 总质量 | m | {p.mass:.0f} | kg |")
    lines.append(f"| 质心高度 | h | {p.cg_height:.1f} | mm |")
    lines.append(f"| 质心到前轴距离 | a | {p.cg_to_front:.1f} | mm |")
    lines.append(f"| 轴距 | L | {p.wheelbase:.0f} | mm |")
    lines.append("")

    lines.append("### 1.3 动力系统")
    lines.append("")
    lines.append("| 参数 | 符号 | 数值 | 单位 |")
    lines.append("|------|------|------|------|")
    lines.append(f"| 后电机最大扭矩 | I_rear | {p.rear_motor:.0f} | Nm |")
    lines.append(f"| 前电机最大扭矩 | I_front | {p.front_motor:.0f} | Nm |")
    lines.append(f"| 后轴保护扭矩 | K_rear | {p.rear_protection:.0f} | Nm |")
    lines.append(f"| 前轴保护扭矩 | K_front | {p.front_protection:.0f} | Nm |")
    lines.append(f"| 后eLSD容量 | M_rear | {p.rear_elsd:.0f} | Nm |")
    lines.append(f"| 前eLSD容量 | M_front | {p.front_elsd:.0f} | Nm |")
    lines.append(f"| BTC+eLSD协同控制 | — | {p.cooperative} | — |")
    lines.append("")

    lines.append("### 1.4 路面条件")
    lines.append("")
    lines.append("| 参数 | 符号 | 数值 | 单位 |")
    lines.append("|------|------|------|------|")
    lines.append(f"| 低附侧附着系数 | μ_low | {p.low_mu:.2f} | — |")
    lines.append(f"| 高附侧附着系数 | μ_high | {p.high_mu:.2f} | — |")
    lines.append(f"| 对开坡道坡度 | i | {p.slope:.0f} | % |")
    lines.append("")

    # ============================================================
    # 2. 中间变量
    # ============================================================
    lines.append("## 二、中间变量")
    lines.append("")

    lines.append("### 2.1 几何与运动学")
    lines.append("")
    lines.append("| 符号 | 名称 | 数值 | 单位 |")
    lines.append("|------|------|------|------|")
    lines.append(f"| r | 轮胎滚动半径 | {im.rolling_radius:.4f} | m |")
    lines.append(f"| θ | 坡度角 | {fn.slope_deg:.2f} | deg |")
    lines.append(f"| a_g | 坡道重力分量加速度 | {im.gravity_component:.4f} | m/s² |")
    lines.append("")

    lines.append("### 2.2 轮荷（考虑坡道纵向载荷转移）")
    lines.append("")
    lines.append("| 符号 | 名称 | 数值 | 单位 |")
    lines.append("|------|------|------|------|")
    lines.append(f"| F_Nr | 后轮单侧法向力 | {im.rear_wheel_load:.1f} | N |")
    lines.append(f"| F_Nf | 前轮单侧法向力 | {im.front_wheel_load:.1f} | N |")
    lines.append("")

    lines.append("### 2.3 附着极限扭矩")
    lines.append("")
    lines.append("| 符号 | 名称 | 数值 | 单位 |")
    lines.append("|------|------|------|------|")
    lines.append(f"| T_r_low | 后轴低附侧最大附着扭矩 | {im.rear_low_mu_torque:.1f} | Nm |")
    lines.append(f"| T_f_low | 前轴低附侧最大附着扭矩 | {im.front_low_mu_torque:.1f} | Nm |")
    lines.append(f"| T_r_high | 后轴高附侧最大附着扭矩 | {im.rear_high_mu_torque:.1f} | Nm |")
    lines.append(f"| T_f_high | 前轴高附侧最大附着扭矩 | {im.front_high_mu_torque:.1f} | Nm |")
    lines.append("")

    lines.append("### 2.4 扭矩分配策略")
    lines.append("")
    is_coop = p.cooperative.upper() == 'Y'
    rear_candidates = [im.rear_torque_btc, im.rear_torque_elsd]
    front_candidates = [im.front_torque_btc, im.front_torque_elsd]
    if is_coop:
        rear_candidates.append(im.rear_torque_coop)
        front_candidates.append(im.front_torque_coop)
    rear_best = max(rear_candidates)
    front_best = max(front_candidates)

    lines.append("| 符号 | 策略 | 数值 | 单位 | 是否采用 |")
    lines.append("|------|------|------|------|----------|")
    lines.append(f"| T_r_BTC | 后轴-BTC | {im.rear_torque_btc:.1f} | Nm | {'✅' if im.rear_torque_btc == rear_best else ''} |")
    lines.append(f"| T_r_ELSD | 后轴-ELSD | {im.rear_torque_elsd:.1f} | Nm | {'✅' if im.rear_torque_elsd == rear_best else ''} |")
    if is_coop:
        lines.append(f"| T_r_coop | 后轴-协同 | {im.rear_torque_coop:.1f} | Nm | {'✅' if im.rear_torque_coop == rear_best else ''} |")
    lines.append(f"| T_f_BTC | 前轴-BTC | {im.front_torque_btc:.1f} | Nm | {'✅' if im.front_torque_btc == front_best else ''} |")
    lines.append(f"| T_f_ELSD | 前轴-ELSD | {im.front_torque_elsd:.1f} | Nm | {'✅' if im.front_torque_elsd == front_best else ''} |")
    if is_coop:
        lines.append(f"| T_f_coop | 前轴-协同 | {im.front_torque_coop:.1f} | Nm | {'✅' if im.front_torque_coop == front_best else ''} |")
    lines.append("")

    lines.append("### 2.5 高附利用率与总扭矩")
    lines.append("")
    rear_ok = "✅ OK" if im.rear_utilization <= 1.0 else "❌ 超限!"
    front_ok = "✅ OK" if im.front_utilization <= 1.0 else "❌ 超限!"
    lines.append("| 符号 | 名称 | 数值 | 单位 | 判定 |")
    lines.append("|------|------|------|------|------|")
    lines.append(f"| η_r | 后轴高附利用率 | {im.rear_utilization * 100:.1f} | % | {rear_ok} |")
    lines.append(f"| η_f | 前轴高附利用率 | {im.front_utilization * 100:.1f} | % | {front_ok} |")
    lines.append(f"| T_total | 总爬坡扭矩 | {im.total_torque:.1f} | Nm | — |")
    lines.append(f"| T_ramp | 坡道阻力矩 | {im.ramp_resistance_torque:.1f} | Nm | — |")
    lines.append("")

    # ============================================================
    # 3. 最终结果
    # ============================================================
    lines.append("## 三、最终结果")
    lines.append("")
    lines.append("| 符号 | 名称 | 数值 | 单位 | 判定 |")
    lines.append("|------|------|------|------|------|")
    accel_ok = fn.acceleration >= 0.8
    lines.append(f"| a | 对开起步加速度 | **{fn.acceleration:.3f}** | m/s² | {'✅ > 0.8' if accel_ok else '❌ < 0.8'} |")
    lines.append(f"| θ | 对开坡道坡度 | {fn.slope_deg:.2f} | deg | — |")
    lines.append(f"| d_5s | 理论爬坡距离 (5s) | {fn.climb_distance_5s:.2f} | m | — |")
    lines.append("")

    # ---- 警告汇总 ----
    if result.warnings:
        lines.append("### ⚠ 警告")
        lines.append("")
        for w in result.warnings:
            lines.append(f"- {w}")
        lines.append("")

    # ============================================================
    # 4. 计算原理与公式
    # ============================================================
    lines.append("---")
    lines.append("")
    lines.append("## 四、计算原理与公式")
    lines.append("")
    lines.append("### 4.1 计算假设")
    lines.append("")
    lines.append("1. 忽略动态效应和纵向载荷转移的瞬态过程，仅考虑稳态")
    lines.append("2. 差速器将扭矩平均分配到左右车轮（开式差速器特性）")
    lines.append("3. 对开路面：一侧为低附着（如冰面，μ ≈ 0.1），另一侧为高附着（如沥青，μ ≈ 0.7~1.0）")
    lines.append("4. 低附侧车轮先达到附着极限打滑，差速器限制高附侧无法获得更多扭矩")
    lines.append("5. BTC / eLSD / 协同控制可突破差速器的等扭矩分配限制")
    lines.append("")

    lines.append("### 4.2 滚动半径")
    lines.append("")
    lines.append("$$")
    lines.append("r = \\frac{D_{inch} \\times 0.0254 + 2 \\cdot B_{mm} \\cdot C \\,/\\, 100000}{2} \\quad [\\text{m}]")
    lines.append("$$")
    lines.append("")

    lines.append("### 4.3 轮荷计算（考虑坡道纵向载荷转移）")
    lines.append("")
    lines.append("上坡时，质心后移导致后轮加载、前轮减载。")
    lines.append("坡度角 $\\theta = \\arctan(i / 100)$，$i$ 为坡度百分比。")
    lines.append("")
    lines.append("$$")
    lines.append("F_{Nr} = \\frac{m g \\cos\\theta \\cdot a + m g \\sin\\theta \\cdot h}{L \\cdot 2} \\quad [\\text{N, 后轮单侧}]")
    lines.append("$$")
    lines.append("")
    lines.append("$$")
    lines.append("F_{Nf} = \\frac{m g \\cos\\theta \\cdot (L - a) - m g \\sin\\theta \\cdot h}{L \\cdot 2} \\quad [\\text{N, 前轮单侧}]")
    lines.append("$$")
    lines.append("")
    lines.append("> $m$ — 总质量 (kg)，$g = 9.8 \\ \\mathrm{m/s^2}$，$a$ — 质心到前轴距离 (mm)，$h$ — 质心高度 (mm)，$L$ — 轴距 (mm)")
    lines.append("")

    lines.append("### 4.4 附着极限扭矩")
    lines.append("")
    lines.append("各车轮能传递的最大扭矩受限于：法向力 × 附着系数 × 滚动半径")
    lines.append("")
    lines.append("$$")
    lines.append("\\begin{aligned}")
    lines.append("T_{r,low}  &= F_{Nr} \\cdot r \\cdot \\mu_{low}  \\quad &\\text{后轴低附侧} \\\\")
    lines.append("T_{f,low}  &= F_{Nf} \\cdot r \\cdot \\mu_{low}  \\quad &\\text{前轴低附侧} \\\\")
    lines.append("T_{r,high} &= F_{Nr} \\cdot r \\cdot \\mu_{high} \\quad &\\text{后轴高附侧} \\\\")
    lines.append("T_{f,high} &= F_{Nf} \\cdot r \\cdot \\mu_{high} \\quad &\\text{前轴高附侧}")
    lines.append("\\end{aligned}")
    lines.append("$$")
    lines.append("")

    lines.append("### 4.5 三种扭矩分配策略")
    lines.append("")
    lines.append("由于开式差速器将扭矩**等分**到左右车轮，低附侧打滑后高附侧也无法获得更多扭矩。")
    lines.append("以下三种策略通过不同方式突破此限制（以后轴为例，前轴同理，将 $I_{rear}$ 换为 $I_{front}$，$K_{rear}$ 换为 $K_{front}$）：")
    lines.append("")

    lines.append("**策略① — BTC（Brake Torque Control，制动扭矩控制）**")
    lines.append("")
    lines.append("对低附侧车轮施加制动力，间接让高附侧获得更多扭矩：")
    lines.append("")
    lines.append("$$")
    lines.append("T_{r,BTC} = \\min\\left(K_{rear},\\; \\min\\left(\\frac{K_{rear}}{2},\\; T_{r,high}\\right) + T_{r,low}\\right)")
    lines.append("$$")
    lines.append("")

    lines.append("**策略② — ELSD（Electronic Limited Slip Differential，电控限滑差速器）**")
    lines.append("")
    lines.append("eLSD 可主动将最多 $M_{rear}$ Nm 的扭矩从低附侧转移到高附侧：")
    lines.append("")
    lines.append("$$")
    lines.append("T_{r,ELSD} = \\min\\left(T_{r,low} + \\min\\left(T_{r,low} + M_{rear},\\; T_{r,high}\\right),\\; I_{rear}\\right)")
    lines.append("$$")
    lines.append("")

    lines.append("**策略③ — 协同控制（BTC + eLSD 同时作用）**")
    lines.append("")
    lines.append("两者叠加，扭矩分配能力最强：")
    lines.append("")
    lines.append("$$")
    lines.append("T_{r,coop} = T_{r,low} + \\min\\left(\\frac{I_{rear}}{2} + \\frac{M_{rear}}{2},\\; I_{rear} - T_{r,low},\\; T_{r,high}\\right)")
    lines.append("$$")
    lines.append("")

    lines.append("### 4.6 高附利用率")
    lines.append("")
    lines.append("高附利用率 = 实际分配到高附侧的扭矩 / 高附侧地面能承受的最大扭矩：")
    lines.append("")
    lines.append("$$")
    lines.append("\\eta_r = \\frac{\\max(T_{r,BTC},\\; T_{r,ELSD} [,\\; T_{r,coop}]) - T_{r,low}}{T_{r,high}}")
    lines.append("$$")
    lines.append("")
    lines.append("> ⚠ **判定标准 1**：若 $\\eta_r > 100\\%$ 或 $\\eta_f > 100\\%$，说明高附侧车轮也会打滑，爬坡失败。")
    lines.append("")

    lines.append("### 4.7 总爬坡扭矩与加速度")
    lines.append("")
    lines.append("前后轴各自选择扭矩最大的策略，总扭矩为两者之和：")
    lines.append("")
    lines.append("$$")
    lines.append("T_{total} = \\max(T_{rear}^{strategies}) + \\max(T_{front}^{strategies})")
    lines.append("$$")
    lines.append("")
    lines.append("对开起步加速度 = 总驱动力 / 质量 − 坡道重力分量：")
    lines.append("")
    lines.append("$$")
    lines.append("a = \\frac{T_{total}}{m \\cdot r} - a_g, \\quad a_g = g \\cdot \\sin\\theta")
    lines.append("$$")
    lines.append("")
    lines.append("理论爬坡距离（5 秒从静止起步）：")
    lines.append("")
    lines.append("$$")
    lines.append("d_{5s} = \\frac{1}{2} \\cdot a \\cdot 5^2")
    lines.append("$$")
    lines.append("")

    lines.append("### 4.8 判定标准汇总")
    lines.append("")
    lines.append("| 序号 | 条件 | 含义 |")
    lines.append("|------|------|------|")
    lines.append("| 1 | $\\eta_r \\leq 100\\%$ 且 $\\eta_f \\leq 100\\%$ | 高附侧不打滑 |")
    lines.append("| 2 | $a > 0.8 \\ \\mathrm{m/s^2}$ | 具备足够爬坡能力 |")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*报告由对开爬坡能力计算工具自动生成*")
    lines.append("")

    return "\n".join(lines)
