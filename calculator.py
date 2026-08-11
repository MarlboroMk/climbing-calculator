"""
对开爬坡能力计算引擎
Split-μ Climbing Performance Calculator

基于差速器保护限制的理论对开爬坡/加速性能计算
参考: MS11 -1 -5 -U 对开坡性能指标论证
"""

import math
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class VehicleParams:
    """车辆输入参数"""
    # 轮胎参数
    tire_width: float       # mm, 胎宽
    aspect_ratio: float     # -, 扁平比
    rim_diameter: float     # inch, 轮辋直径

    # 质量与质心
    mass: float             # kg, 总质量
    cg_height: float        # mm, 质心高度
    cg_to_front: float      # mm, 质心到前轴距离
    wheelbase: float        # mm, 轴距

    # 动力系统
    rear_motor: float       # Nm, 后电机最大扭矩
    front_motor: float      # Nm, 前电机最大扭矩
    rear_protection: float  # Nm, 后轴保护扭矩
    front_protection: float # Nm, 前轴保护扭矩
    rear_elsd: float        # Nm, 后eLSD容量
    front_elsd: float       # Nm, 前eLSD容量
    cooperative: str        # Y/N, eLSD+BTC协同控制

    # 路面条件
    low_mu: float           # -, 低附侧附着系数
    high_mu: float          # -, 高附侧附着系数
    slope: float            # %, 对开坡道坡度


@dataclass
class IntermediateResults:
    """中间变量计算结果"""
    rolling_radius: float = 0.0          # S: 滚动半径 (m)
    gravity_component: float = 0.0       # T: 坡道重力分量加速度 (m/s²)
    rear_wheel_load: float = 0.0         # V: 后轮单轮轮荷 (N)
    front_wheel_load: float = 0.0        # W: 前轮单轮轮荷 (N)
    rear_low_mu_torque: float = 0.0      # X: 后轴低附最大附着扭矩 (Nm)
    front_low_mu_torque: float = 0.0     # Y: 前轴低附最大附着扭矩 (Nm)
    rear_high_mu_torque: float = 0.0     # Z: 后轴高附最大附着扭矩 (Nm)
    front_high_mu_torque: float = 0.0    # AA: 前轴高附最大附着扭矩 (Nm)
    rear_torque_btc: float = 0.0         # AB: 后轴最大扭矩-BTC策略 (Nm)
    rear_torque_elsd: float = 0.0        # AC: 后轴最大扭矩-ELSD策略 (Nm)
    rear_torque_coop: float = 0.0        # AD: 后轴最大扭矩-协同策略 (Nm)
    rear_utilization: float = 0.0        # AE: 后轴高附利用率 (% as decimal)
    front_torque_btc: float = 0.0        # AF: 前轴最大扭矩-BTC策略 (Nm)
    front_torque_elsd: float = 0.0       # AG: 前轴最大扭矩-ELSD策略 (Nm)
    front_torque_coop: float = 0.0       # AH: 前轴最大扭矩-协同策略 (Nm)
    front_utilization: float = 0.0       # AI: 前轴高附利用率 (% as decimal)
    total_torque: float = 0.0            # AJ: 总爬坡扭矩 (Nm)
    ramp_resistance_torque: float = 0.0  # AK: 坡道阻力矩 (Nm)


@dataclass
class FinalResults:
    """最终结果"""
    model_name: str = ""                 # AL: 车型名称
    slope_percent: float = 0.0           # AM: 对开坡道坡度 (%)
    acceleration: float = 0.0            # AN: 对开起步加速度 (m/s²)
    slope_deg: float = 0.0               # AO: 对开坡道坡度 (deg)
    climb_distance_5s: float = 0.0       # AP: 理论爬坡距离-5秒 (m)


@dataclass
class CalculationResult:
    """完整计算结果"""
    params: VehicleParams
    intermediate: IntermediateResults
    final: FinalResults
    effective_rear_strategy: str = ""    # 后轴实际采用的策略
    effective_front_strategy: str = ""   # 前轴实际采用的策略
    warnings: list = field(default_factory=list)


def calculate(params: VehicleParams) -> CalculationResult:
    """
    执行对开爬坡能力计算

    Args:
        params: 车辆输入参数

    Returns:
        CalculationResult: 包含所有中间变量和最终结果
    """
    im = IntermediateResults()
    warnings = []

    g = 9.8  # 重力加速度 (m/s²)

    # ---- S: 滚动半径 ----
    # S = (D_inch * 0.0254 + 2 * B_mm * C / 100000) / 2
    im.rolling_radius = (params.rim_diameter * 0.0254
                         + 2 * params.tire_width * params.aspect_ratio / 100000) / 2

    # ---- 坡度角 ----
    slope_rad = math.atan(params.slope / 100)
    cos_slope = math.cos(slope_rad)
    sin_slope = math.sin(slope_rad)

    # ---- T: 坡道重力分量加速度 ----
    im.gravity_component = sin_slope * g

    # ---- V: 后轮单轮轮荷 ----
    # V = [E * g * cosθ * G + E * g * sinθ * F] / H / 2
    weight_force = params.mass * g
    normal_force_rear_total = (weight_force * cos_slope * params.cg_to_front
                               + weight_force * sin_slope * params.cg_height) / params.wheelbase
    im.rear_wheel_load = normal_force_rear_total / 2

    # ---- W: 前轮单轮轮荷 ----
    # W = [E * g * cosθ * (H - G) - E * g * sinθ * F] / H / 2
    normal_force_front_total = (weight_force * cos_slope * (params.wheelbase - params.cg_to_front)
                                - weight_force * sin_slope * params.cg_height) / params.wheelbase
    im.front_wheel_load = max(normal_force_front_total / 2, 0)  # 防止负值

    # ---- X, Y, Z, AA: 附着极限扭矩 ----
    # X = V * S * P  (后轴低附)
    im.rear_low_mu_torque = im.rear_wheel_load * im.rolling_radius * params.low_mu
    # Y = W * S * P  (前轴低附)
    im.front_low_mu_torque = im.front_wheel_load * im.rolling_radius * params.low_mu
    # Z = V * S * Q  (后轴高附)
    im.rear_high_mu_torque = im.rear_wheel_load * im.rolling_radius * params.high_mu
    # AA = W * S * Q  (前轴高附)
    im.front_high_mu_torque = im.front_wheel_load * im.rolling_radius * params.high_mu

    # ---- 后轴三种扭矩分配策略 ----
    # AB: BTC = MIN(K, MIN(K/2, Z) + X)
    im.rear_torque_btc = min(
        params.rear_protection,
        min(params.rear_protection / 2, im.rear_high_mu_torque) + im.rear_low_mu_torque
    )

    # AC: ELSD = MIN(X + MIN(X + M, Z), I)
    im.rear_torque_elsd = min(
        im.rear_low_mu_torque + min(im.rear_low_mu_torque + params.rear_elsd, im.rear_high_mu_torque),
        params.rear_motor
    )

    # AD: 协同 = X + MIN(I/2 + M/2, I - X, Z)
    im.rear_torque_coop = im.rear_low_mu_torque + min(
        params.rear_motor / 2 + params.rear_elsd / 2,
        params.rear_motor - im.rear_low_mu_torque,
        im.rear_high_mu_torque
    )

    # ---- 前轴三种扭矩分配策略 ----
    # AF: BTC = MIN(L, MIN(L/2, AA) + Y)
    im.front_torque_btc = min(
        params.front_protection,
        min(params.front_protection / 2, im.front_high_mu_torque) + im.front_low_mu_torque
    )

    # AG: ELSD = MIN(Y + MIN(Y + N, AA), J)
    im.front_torque_elsd = min(
        im.front_low_mu_torque + min(im.front_low_mu_torque + params.front_elsd, im.front_high_mu_torque),
        params.front_motor
    )

    # AH: 协同 = Y + MIN(J/2 + N/2, J - Y, AA)
    im.front_torque_coop = im.front_low_mu_torque + min(
        params.front_motor / 2 + params.front_elsd / 2,
        params.front_motor - im.front_low_mu_torque,
        im.front_high_mu_torque
    )

    # ---- 确定有效策略 ----
    is_coop = (params.cooperative.upper() == 'Y')

    if is_coop:
        rear_candidates = [im.rear_torque_btc, im.rear_torque_elsd, im.rear_torque_coop]
        front_candidates = [im.front_torque_btc, im.front_torque_elsd, im.front_torque_coop]
    else:
        rear_candidates = [im.rear_torque_btc, im.rear_torque_elsd]
        front_candidates = [im.front_torque_btc, im.front_torque_elsd]

    rear_best = max(rear_candidates)
    front_best = max(front_candidates)

    # 记录实际采用的策略
    rear_strategies = ["BTC", "ELSD", "协同"]
    front_strategies = ["BTC", "ELSD", "协同"]
    if is_coop:
        rear_idx = rear_candidates.index(rear_best)
        front_idx = front_candidates.index(front_best)
    else:
        rear_idx = rear_candidates.index(rear_best)
        front_idx = front_candidates.index(front_best)
    effective_rear = rear_strategies[rear_idx]
    effective_front = front_strategies[front_idx]

    # ---- AE: 后轴高附利用率 ----
    if im.rear_high_mu_torque > 0:
        im.rear_utilization = (rear_best - im.rear_low_mu_torque) / im.rear_high_mu_torque
    else:
        im.rear_utilization = 0

    # ---- AI: 前轴高附利用率 ----
    if im.front_high_mu_torque > 0:
        im.front_utilization = (front_best - im.front_low_mu_torque) / im.front_high_mu_torque
    else:
        im.front_utilization = 0

    # ---- AJ: 总爬坡扭矩 ----
    im.total_torque = rear_best + front_best

    # ---- AK: 坡道阻力矩 ----
    im.ramp_resistance_torque = params.mass * g * sin_slope * im.rolling_radius

    # ---- 检查警告 ----
    if im.rear_utilization > 1.0:
        warnings.append(f"⚠ 后轴高附利用率 = {im.rear_utilization * 100:.1f}%，超过100%，高附侧后轮将打滑！")
    if im.front_utilization > 1.0:
        warnings.append(f"⚠ 前轴高附利用率 = {im.front_utilization * 100:.1f}%，超过100%，高附侧前轮将打滑！")

    # ---- 最终结果 ----
    final = FinalResults()
    final.model_name = ""  # 由外部设置
    final.slope_percent = params.slope

    # AN = AJ / (E * S) - T
    if params.mass > 0 and im.rolling_radius > 0:
        final.acceleration = im.total_torque / (params.mass * im.rolling_radius) - im.gravity_component
    else:
        final.acceleration = 0

    # AO = ATAN(slope/100) in degrees
    final.slope_deg = math.degrees(slope_rad)

    # AP = 0.5 * AN * 5²
    final.climb_distance_5s = 0.5 * final.acceleration * 25  # 5² = 25

    if final.acceleration < 0.8:
        warnings.append(f"⚠ 对开起步加速度 = {final.acceleration:.2f} m/s²，低于 0.8 m/s² 阈值！")

    return CalculationResult(
        params=params,
        intermediate=im,
        final=final,
        effective_rear_strategy=effective_rear,
        effective_front_strategy=effective_front,
        warnings=warnings,
    )


def calculate_heatmap(
    params: VehicleParams,
    front_step: float = 200,
    rear_step: float = 200,
) -> Dict:
    """
    生成前/后轴保护扭矩 vs 加速度的二维热力图数据

    Args:
        params: 基础车辆参数（front_protection 和 rear_protection 将被遍历覆盖）
        front_step: 前轴保护扭矩步长 (Nm)
        rear_step: 后轴保护扭矩步长 (Nm)

    Returns:
        Dict with keys: front_vals, rear_vals, accel_matrix, utilization_matrix
    """
    front_max = max(params.front_motor, 1)   # 至少有一个步长
    rear_max = max(params.rear_motor, 1)

    # 生成遍历点
    num_front = max(int(front_max / front_step), 1) + 1
    num_rear = max(int(rear_max / rear_step), 1) + 1

    front_vals = [i * front_step for i in range(num_front)]
    # 确保最大值包含在内
    if front_vals[-1] < front_max:
        front_vals.append(front_max)
    front_vals = [min(v, front_max) for v in front_vals]

    rear_vals = [i * rear_step for i in range(num_rear)]
    if rear_vals[-1] < rear_max:
        rear_vals.append(rear_max)
    rear_vals = [min(v, rear_max) for v in rear_vals]

    # 遍历计算
    accel_matrix = []
    rear_util_matrix = []
    front_util_matrix = []

    for rear_prot in rear_vals:
        accel_row = []
        rear_util_row = []
        front_util_row = []
        for front_prot in front_vals:
            test_params = VehicleParams(
                tire_width=params.tire_width,
                aspect_ratio=params.aspect_ratio,
                rim_diameter=params.rim_diameter,
                mass=params.mass,
                cg_height=params.cg_height,
                cg_to_front=params.cg_to_front,
                wheelbase=params.wheelbase,
                rear_motor=params.rear_motor,
                front_motor=params.front_motor,
                rear_protection=rear_prot,
                front_protection=front_prot,
                rear_elsd=params.rear_elsd,
                front_elsd=params.front_elsd,
                cooperative=params.cooperative,
                low_mu=params.low_mu,
                high_mu=params.high_mu,
                slope=params.slope,
            )
            result = calculate(test_params)
            accel_row.append(round(result.final.acceleration, 4))
            rear_util_row.append(round(result.intermediate.rear_utilization * 100, 2))
            front_util_row.append(round(result.intermediate.front_utilization * 100, 2))
        accel_matrix.append(accel_row)
        rear_util_matrix.append(rear_util_row)
        front_util_matrix.append(front_util_row)

    return {
        "front_vals": [round(v, 1) for v in front_vals],
        "rear_vals": [round(v, 1) for v in rear_vals],
        "accel_matrix": accel_matrix,
        "rear_util_matrix": rear_util_matrix,
        "front_util_matrix": front_util_matrix,
    }
