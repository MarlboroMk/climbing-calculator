"""
对开爬坡能力计算 — Streamlit 可视化工具
Split-μ Climbing Performance Calculator with Visualization
"""

import json
import math
import os
import copy
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from calculator import VehicleParams, calculate, calculate_heatmap
from report_generator import generate_report

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="对开爬坡能力计算工具",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 常量
# ============================================================
PRESET_PATH = Path(__file__).parent / "presets.json"

# 车辆参数（预设影响）
VEHICLE_KEYS = [
    "tire_width", "aspect_ratio", "rim_diameter",
    "mass", "cg_height", "cg_to_front", "wheelbase",
    "rear_motor", "front_motor", "rear_protection", "front_protection",
    "rear_elsd", "front_elsd", "cooperative",
]
# 路面条件（独立于预设）
ROAD_KEYS = ["low_mu", "high_mu", "slope"]
# 全部参数
PARAM_KEYS = VEHICLE_KEYS + ROAD_KEYS

# 默认值（中性值，用户需自行填写）
DEFAULT_VALUES = {
    "tire_width": 245.0, "aspect_ratio": 45.0, "rim_diameter": 20.0,
    "mass": 2000.0, "cg_height": 500.0, "cg_to_front": 1500.0, "wheelbase": 3000.0,
    "rear_motor": 3000.0, "front_motor": 3000.0,
    "rear_protection": 2000.0, "front_protection": 2000.0,
    "rear_elsd": 0.0, "front_elsd": 0.0,
    "cooperative": "N", "low_mu": 0.1, "high_mu": 0.7, "slope": 15.0,
}

# session_state 中非数值键
META_KEYS = [
    "active_preset", "preset_selector",
    "show_save_dialog", "save_preset_name",
    "presets_data", "preset_names",
    "heatmap_data",
]


# ============================================================
# 工具函数
# ============================================================
def load_presets_file():
    """从文件读取预设，文件不存在时返回空列表"""
    if not PRESET_PATH.exists():
        return []
    with open(PRESET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_presets_file(data):
    """写入预设文件"""
    with open(PRESET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def init_session_state():
    """初始化 session_state"""
    # 加载预设列表
    if "presets_data" not in st.session_state:
        st.session_state["presets_data"] = load_presets_file()
    if "preset_names" not in st.session_state:
        st.session_state["preset_names"] = [p["name"] for p in st.session_state["presets_data"]]

    # 参数默认值
    for key in PARAM_KEYS:
        if key not in st.session_state:
            st.session_state[key] = DEFAULT_VALUES[key]

    # 元数据
    if "active_preset" not in st.session_state:
        st.session_state["active_preset"] = "(自定义)"
    if "preset_selector" not in st.session_state:
        st.session_state["preset_selector"] = "(自定义)"
    if "show_save_dialog" not in st.session_state:
        st.session_state["show_save_dialog"] = False
    if "save_preset_name" not in st.session_state:
        st.session_state["save_preset_name"] = ""


def get_preset_map():
    """返回预设名 → 预设数据的映射"""
    return {p["name"]: p for p in st.session_state["presets_data"]}


def current_params_match_preset(preset_name: str) -> bool:
    """检查当前车辆参数是否与指定预设一致（仅比较车辆参数，忽略路面条件）"""
    preset_map = get_preset_map()
    if preset_name not in preset_map:
        return False
    preset = preset_map[preset_name]
    for key in VEHICLE_KEYS:
        sv = st.session_state[key]
        pv = preset.get(key)
        if key == "cooperative":
            if str(sv).upper() != str(pv).upper():
                return False
        elif isinstance(sv, float) and isinstance(pv, (int, float)):
            if abs(sv - float(pv)) > 0.001:
                return False
        else:
            if sv != pv:
                return False
    return True


def find_matching_preset():
    """查找与当前车辆参数匹配的预设（仅比较车辆参数）"""
    for preset in st.session_state["presets_data"]:
        match = True
        for key in VEHICLE_KEYS:
            sv = st.session_state[key]
            pv = preset.get(key)
            if key == "cooperative":
                if str(sv).upper() != str(pv).upper():
                    match = False
                    break
            elif isinstance(sv, float) and isinstance(pv, (int, float)):
                if abs(sv - float(pv)) > 0.001:
                    match = False
                    break
            else:
                if sv != pv:
                    match = False
                    break
        if match:
            return preset["name"]
    return None


# ============================================================
# 回调函数
# ============================================================
def on_preset_select():
    """预设下拉框变化时的回调：仅加载车辆参数，不影响路面条件"""
    name = st.session_state["preset_selector"]
    if name == "(自定义)":
        st.session_state["active_preset"] = "(自定义)"
        return
    preset_map = get_preset_map()
    if name in preset_map:
        preset = preset_map[name]
        for key in VEHICLE_KEYS:
            st.session_state[key] = preset.get(key, DEFAULT_VALUES.get(key))
        st.session_state["active_preset"] = name


def on_param_change():
    """任意参数变化时检测是否脱离预设"""
    if st.session_state.get("active_preset", "(自定义)") == "(自定义)":
        return
    if not current_params_match_preset(st.session_state["active_preset"]):
        st.session_state["active_preset"] = "(自定义)"
        st.session_state["preset_selector"] = "(自定义)"


# ============================================================
# 初始化
# ============================================================
init_session_state()

# ============================================================
# 标题
# ============================================================
st.title("🚗 对开爬坡能力计算工具")
st.caption("受差速器保护限制的理论对开爬坡/加速性能计算 | 参考: MS11 -1 -5 -U 对开坡性能指标论证")

# ============================================================
# 侧边栏 - 输入参数
# ============================================================
with st.sidebar:
    st.header("📋 参数设置")

    # ---- 预设选择 + 保存 ----
    st.subheader("预设车型")
    preset_options = ["(自定义)"] + st.session_state["preset_names"]

    # 尝试找到与当前 session_state 匹配的预设作为 selectbox 默认值
    current_idx = 0
    active = st.session_state.get("active_preset", "(自定义)")
    if active != "(自定义)" and active in preset_options:
        current_idx = preset_options.index(active)

    st.selectbox(
        "选择预设车型",
        preset_options,
        index=current_idx,
        key="preset_selector",
        on_change=on_preset_select,
        help="从内置车型配置中加载参数，修改任意参数后自动切换为「自定义」",
    )

    # 预设状态提示
    active_preset = st.session_state.get("active_preset", "(自定义)")
    if active_preset != "(自定义)":
        st.success(f"✅ 当前预设: {active_preset}")
    else:
        st.info("📝 当前为自定义参数")

    # 保存为预设按钮（仅在本地可写时显示）
    if os.access(PRESET_PATH.parent, os.W_OK):
        col_save1, col_save2 = st.columns([1, 1])
        with col_save1:
            if st.button("💾 保存为预设", width="stretch", key="btn_show_save"):
                st.session_state["show_save_dialog"] = True

        if st.session_state.get("show_save_dialog"):
            with st.container():
                save_name = st.text_input(
                    "预设名称",
                    placeholder="输入预设名称...",
                    key="save_preset_name_input",
                )
                col_ok, col_cancel = st.columns(2)
                with col_ok:
                    if st.button("✅ 确认保存", width="stretch"):
                        name = st.session_state.get("save_preset_name_input", "").strip()
                        if not name:
                            st.error("名称不能为空")
                        elif name == "(自定义)":
                            st.error("名称不能为「(自定义)」")
                        elif name in st.session_state["preset_names"]:
                            st.error(f"预设「{name}」已存在，请换一个名称")
                        else:
                            new_preset = {key: st.session_state[key] for key in VEHICLE_KEYS}
                            new_preset["name"] = name
                            st.session_state["presets_data"].append(new_preset)
                            save_presets_file(st.session_state["presets_data"])
                            st.session_state["preset_names"] = [p["name"] for p in st.session_state["presets_data"]]
                            st.session_state["active_preset"] = name
                            st.session_state["preset_selector"] = name
                            st.session_state["show_save_dialog"] = False
                            st.success(f"预设「{name}」已保存!")
                            st.rerun()
                with col_cancel:
                    if st.button("❌ 取消", width="stretch"):
                        st.session_state["show_save_dialog"] = False
                        st.rerun()
    else:
        st.caption("☁ 云端模式：预设只读")

    st.divider()

    # ---- 轮胎参数 ----
    st.subheader("🛞 轮胎参数")
    col_b, col_c, col_d = st.columns(3)
    with col_b:
        tire_width = st.number_input(
            "胎宽 (mm)", min_value=0.0, max_value=500.0, step=5.0,
            key="tire_width", on_change=on_param_change,
        )
    with col_c:
        aspect_ratio = st.number_input(
            "扁平比", min_value=0.0, max_value=100.0, step=5.0,
            key="aspect_ratio", on_change=on_param_change,
        )
    with col_d:
        rim_diameter = st.number_input(
            "轮辋直径 (inch)", min_value=0.0, max_value=30.0, step=1.0,
            key="rim_diameter", on_change=on_param_change,
        )

    # ---- 质量与质心 ----
    st.subheader("⚖ 质量与质心")
    col_e, col_f = st.columns(2)
    with col_e:
        mass = st.number_input(
            "总质量 (kg)", min_value=0.0, max_value=10000.0, step=10.0,
            key="mass", on_change=on_param_change,
        )
    with col_f:
        cg_height = st.number_input(
            "质心高度 h (mm)", min_value=0.0, max_value=2000.0, step=1.0,
            key="cg_height", on_change=on_param_change,
        )
    col_g, col_h = st.columns(2)
    with col_g:
        cg_to_front = st.number_input(
            "质心-前轴距 a (mm)", min_value=0.0, max_value=5000.0, step=1.0,
            key="cg_to_front", on_change=on_param_change,
        )
    with col_h:
        wheelbase = st.number_input(
            "轴距 L (mm)", min_value=0.0, max_value=6000.0, step=10.0,
            key="wheelbase", on_change=on_param_change,
        )

    # ---- 动力系统 ----
    st.subheader("⚡ 动力系统")
    col_i, col_j = st.columns(2)
    with col_i:
        rear_motor = st.number_input(
            "后电机最大扭矩 (Nm)", min_value=0.0, max_value=20000.0, step=50.0,
            key="rear_motor", on_change=on_param_change,
        )
    with col_j:
        front_motor = st.number_input(
            "前电机最大扭矩 (Nm)", min_value=0.0, max_value=20000.0, step=50.0,
            key="front_motor", on_change=on_param_change,
        )
    col_k, col_l = st.columns(2)
    with col_k:
        rear_protection = st.number_input(
            "后轴保护扭矩 (Nm)", min_value=0.0, max_value=20000.0, step=50.0,
            key="rear_protection", on_change=on_param_change,
        )
    with col_l:
        front_protection = st.number_input(
            "前轴保护扭矩 (Nm)", min_value=0.0, max_value=20000.0, step=50.0,
            key="front_protection", on_change=on_param_change,
        )
    col_m, col_n = st.columns(2)
    with col_m:
        rear_elsd = st.number_input(
            "后eLSD容量 (Nm)", min_value=0.0, max_value=5000.0, step=50.0,
            key="rear_elsd", on_change=on_param_change,
        )
    with col_n:
        front_elsd = st.number_input(
            "前eLSD容量 (Nm)", min_value=0.0, max_value=5000.0, step=50.0,
            key="front_elsd", on_change=on_param_change,
        )

    cooperative = st.selectbox(
        "eLSD + BTC 协同控制",
        ["N", "Y"],
        key="cooperative",
        on_change=on_param_change,
        help="是否启用 BTC 与 eLSD 协同控制模式",
    )

    # ---- 路面条件 ----
    st.subheader("🛣 路面条件")
    col_p, col_q, col_r = st.columns(3)
    with col_p:
        low_mu = st.number_input(
            "低附系数 μ_low", min_value=0.0, max_value=2.0, step=0.05, format="%.2f",
            key="low_mu",
        )
    with col_q:
        high_mu = st.number_input(
            "高附系数 μ_high", min_value=0.0, max_value=2.0, step=0.05, format="%.2f",
            key="high_mu",
        )
    with col_r:
        slope = st.number_input(
            "对开坡度 (%)", min_value=0.0, max_value=100.0, step=1.0,
            key="slope",
        )

    # ---- 附着系数参考 ----
    with st.expander("📖 附着系数参考"):
        st.markdown("""
        | 路面类型 | μ 范围 |
        |---------|--------|
        | 冰面 | 0.1 |
        | 雪地胎水泥地 | 0.7~0.9 |
        | 四季胎水泥地 | 0.8~1.0 |
        | 湿滑沥青 | 0.7~1.0 |
        | 干燥沥青 | 0.9~1.2 |
        """)

    st.divider()

    # ---- 计算按钮 ----
    calculate_btn = st.button("🚀 开始计算", type="primary", width="stretch")

# ============================================================
# 构建参数对象
# ============================================================
params = VehicleParams(
    tire_width=st.session_state["tire_width"],
    aspect_ratio=st.session_state["aspect_ratio"],
    rim_diameter=st.session_state["rim_diameter"],
    mass=st.session_state["mass"],
    cg_height=st.session_state["cg_height"],
    cg_to_front=st.session_state["cg_to_front"],
    wheelbase=st.session_state["wheelbase"],
    rear_motor=st.session_state["rear_motor"],
    front_motor=st.session_state["front_motor"],
    rear_protection=st.session_state["rear_protection"],
    front_protection=st.session_state["front_protection"],
    rear_elsd=st.session_state["rear_elsd"],
    front_elsd=st.session_state["front_elsd"],
    cooperative=st.session_state["cooperative"],
    low_mu=st.session_state["low_mu"],
    high_mu=st.session_state["high_mu"],
    slope=st.session_state["slope"],
)

# ============================================================
# 主区域 - 两个 Tab
# ============================================================
tab_calc, tab_heatmap = st.tabs(["📊 单点计算 & 报告", "🔥 轴保护力矩-加速度热图"])

# ============================================================
# Tab 1: 单点计算 & 报告
# ============================================================
with tab_calc:
    if calculate_btn:
        with st.spinner("计算中..."):
            result = calculate(params)

        # ---- 结果摘要卡片 ----
        st.subheader("📈 结果摘要")
        col1, col2, col3, col4 = st.columns(4)

        accel = result.final.acceleration
        accel_status = "✅ 达标" if accel >= 0.8 else "❌ 不达标"

        with col1:
            st.metric(
                label="对开起步加速度",
                value=f"{accel:.3f} m/s²",
                delta=accel_status,
                delta_color="normal" if accel >= 0.8 else "inverse",
            )
        with col2:
            rear_util_pct = result.intermediate.rear_utilization * 100
            rear_ok = rear_util_pct <= 100
            st.metric(
                label="后轴高附利用率",
                value=f"{rear_util_pct:.1f}%",
                delta="✅ OK" if rear_ok else "❌ 超限",
                delta_color="normal" if rear_ok else "inverse",
            )
        with col3:
            front_util_pct = result.intermediate.front_utilization * 100
            front_ok = front_util_pct <= 100
            st.metric(
                label="前轴高附利用率",
                value=f"{front_util_pct:.1f}%",
                delta="✅ OK" if front_ok else "❌ 超限",
                delta_color="normal" if front_ok else "inverse",
            )
        with col4:
            st.metric(
                label="理论爬坡距离 (5s)",
                value=f"{result.final.climb_distance_5s:.2f} m",
            )

        # ---- 策略信息 ----
        st.info(
            f"**后轴策略**: {result.effective_rear_strategy} | "
            f"**前轴策略**: {result.effective_front_strategy} | "
            f"**总爬坡扭矩**: {result.intermediate.total_torque:.1f} Nm"
        )

        # ---- 警告 ----
        if result.warnings:
            for w in result.warnings:
                st.warning(w)

        # ---- 中间变量详情 ----
        with st.expander("📋 中间变量详情", expanded=False):
            im = result.intermediate
            fn = result.final
            is_coop = params.cooperative.upper() == 'Y'
            rear_best = max([im.rear_torque_btc, im.rear_torque_elsd] + ([im.rear_torque_coop] if is_coop else []))
            front_best = max([im.front_torque_btc, im.front_torque_elsd] + ([im.front_torque_coop] if is_coop else []))

            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown("**几何与运动学**")
                st.write(f"滚动半径 r: {im.rolling_radius:.4f} m")
                st.write(f"坡度角 θ: {fn.slope_deg:.2f}°")
                st.write(f"坡道重力分量 a_g: {im.gravity_component:.4f} m/s²")

                st.markdown("**轮荷**（单侧法向力）")
                st.write(f"后轮 F_Nr: {im.rear_wheel_load:.1f} N")
                st.write(f"前轮 F_Nf: {im.front_wheel_load:.1f} N")

                st.markdown("**附着极限扭矩**")
                st.write(f"后轴低附侧 T_r_low: {im.rear_low_mu_torque:.1f} Nm")
                st.write(f"前轴低附侧 T_f_low: {im.front_low_mu_torque:.1f} Nm")
                st.write(f"后轴高附侧 T_r_high: {im.rear_high_mu_torque:.1f} Nm")
                st.write(f"前轴高附侧 T_f_high: {im.front_high_mu_torque:.1f} Nm")

            with col_right:
                st.markdown("**后轴扭矩策略**")
                st.write(f"BTC:  {im.rear_torque_btc:.1f} Nm {'✅' if im.rear_torque_btc == rear_best else ''}")
                st.write(f"ELSD: {im.rear_torque_elsd:.1f} Nm {'✅' if im.rear_torque_elsd == rear_best else ''}")
                if is_coop:
                    st.write(f"协同: {im.rear_torque_coop:.1f} Nm {'✅' if im.rear_torque_coop == rear_best else ''}")

                st.markdown("**前轴扭矩策略**")
                st.write(f"BTC:  {im.front_torque_btc:.1f} Nm {'✅' if im.front_torque_btc == front_best else ''}")
                st.write(f"ELSD: {im.front_torque_elsd:.1f} Nm {'✅' if im.front_torque_elsd == front_best else ''}")
                if is_coop:
                    st.write(f"协同: {im.front_torque_coop:.1f} Nm {'✅' if im.front_torque_coop == front_best else ''}")

                st.markdown("**汇总**")
                st.write(f"后轴高附利用率 η_r: {im.rear_utilization * 100:.1f}%")
                st.write(f"前轴高附利用率 η_f: {im.front_utilization * 100:.1f}%")
                st.write(f"总爬坡扭矩 T_total: {im.total_torque:.1f} Nm")
                st.write(f"坡道阻力矩 T_ramp: {im.ramp_resistance_torque:.1f} Nm")

        # ---- 计算原理简要说明 ----
        with st.expander("📐 计算原理简要", expanded=False):
            st.markdown(r"""
            **核心步骤**：
            1. 计算滚动半径 $r = (D_{inch} \times 0.0254 + 2 B_{mm} C / 100000) / 2$
            2. 根据坡度角 $\theta$ 计算前后轮荷（含纵向载荷转移）
            3. 轮荷 × 附着系数 × 滚动半径 → 各侧附着极限扭矩
            4. 分别用 BTC / ELSD / 协同三种策略计算每轴可输出的最大扭矩
            5. 驱动力 − 坡道阻力 → 起步加速度 $a$
            """)

        # ---- 报告预览与下载 ----
        st.divider()
        st.subheader("📝 计算报告")

        preset_label = st.session_state.get("active_preset", "")
        if preset_label == "(自定义)":
            preset_label = ""
        report_text = generate_report(result, custom_name=preset_label)

        with st.expander("📄 报告预览", expanded=True):
            st.markdown(report_text)

        report_bytes = report_text.encode("utf-8")
        file_label = preset_label if preset_label else "自定义"
        st.download_button(
            label="📥 下载 MD 报告",
            data=report_bytes,
            file_name=f"对开爬坡计算报告_{file_label}.md",
            mime="text/markdown",
        )
        st.caption(
            "💡 导入飞书：点击「上传及导入 → 导入为在线文档 → "
            "选择 Markdown → 选择下载的 .md 文件」，公式即可正确渲染。"
        )

    else:
        st.info("👈 在左侧设置参数后，点击「🚀 开始计算」按钮")
        st.markdown("""
        ### 使用说明
        1. **选择预设车型**（可选），参数会自动填充
        2. 修改任意参数后自动切换为「自定义」状态
        3. 点击「💾 保存为预设」将当前参数保存为新预设
        4. 点击「🚀 开始计算」查看结果
        5. 在「📄 报告预览」中查看完整报告，点击下载保存
        6. 切换到「🔥 轴保护力矩-加速度热图」Tab 查看保护扭矩灵敏度分析
        """)

# ============================================================
# Tab 2: 轴保护力矩-加速度热图
# ============================================================
with tab_heatmap:
    st.subheader("🔥 保护扭矩 → 加速度 热力图")
    st.caption("固定其他参数，遍历前/后轴保护扭矩，观察对开起步加速度的变化")

    col_hs, col_hd = st.columns([1, 3])
    with col_hs:
        heatmap_step = st.selectbox(
            "保护扭矩步长 (Nm)",
            [100, 200, 500],
            index=1,
            key="heatmap_step_select"
        )
        custom_step = st.number_input(
            "自定义步长 (Nm, 0=使用上选值)",
            min_value=0, max_value=2000,
            value=0, step=50,
            key="heatmap_custom_step"
        )
        effective_step = custom_step if custom_step > 0 else float(heatmap_step)

        st.caption(f"当前步长: **{effective_step:.0f} Nm**")
        st.caption(f"前轴范围: 0 ~ {params.front_motor:.0f} Nm")
        st.caption(f"后轴范围: 0 ~ {params.rear_motor:.0f} Nm")

        show_util = st.checkbox("显示高附利用率热力图", value=False, key="show_util_check")

    # 计算触发条件：主计算按钮、首次使用、步长变化
    step_changed = (st.session_state.get("_last_heatmap_step") != effective_step)
    if calculate_btn or ("heatmap_data" not in st.session_state) or step_changed:
        with st.spinner("生成热力图..."):
            hm_data = calculate_heatmap(params, front_step=effective_step, rear_step=effective_step)
            st.session_state["heatmap_data"] = hm_data
            st.session_state["_last_heatmap_step"] = effective_step

    hm_data = st.session_state.get("heatmap_data")
    if hm_data is None:
        st.info("调整步长后热力图将自动更新，或点击「🚀 开始计算」生成")
    else:
        front_vals = hm_data["front_vals"]
        rear_vals = hm_data["rear_vals"]

        if show_util:
            data_matrix = []
            for ri in range(len(rear_vals)):
                row = []
                for ci in range(len(front_vals)):
                    row.append(max(
                        hm_data["rear_util_matrix"][ri][ci],
                        hm_data["front_util_matrix"][ri][ci],
                    ))
                data_matrix.append(row)
            title_text = "最大高附利用率 (%) — 前后轴取大值"
            color_scheme = "RdYlGn_r"
            hover_tmpl = "前轴保护: %{x:.0f} Nm<br>后轴保护: %{y:.0f} Nm<br>最大利用率: %{z:.1f}%<extra></extra>"
            zmid_val = 100
        else:
            data_matrix = hm_data["accel_matrix"]
            title_text = "对开起步加速度 (m/s²)"
            color_scheme = "RdYlGn"
            hover_tmpl = "前轴保护: %{x:.0f} Nm<br>后轴保护: %{y:.0f} Nm<br>加速度: %{z:.3f} m/s²<extra></extra>"
            zmid_val = 0.8

        fig = go.Figure(data=go.Heatmap(
            z=data_matrix,
            x=front_vals,
            y=rear_vals,
            colorscale=color_scheme,
            colorbar=dict(title=title_text),
            hovertemplate=hover_tmpl,
            zmid=zmid_val,
        ))

        fig.update_layout(
            title=title_text,
            xaxis_title="前轴保护扭矩 (Nm)",
            yaxis_title="后轴保护扭矩 (Nm)",
            height=550,
            margin=dict(l=60, r=40, t=60, b=60),
        )

        if not show_util:
            try:
                fig.add_trace(go.Contour(
                    z=data_matrix,
                    x=front_vals,
                    y=rear_vals,
                    contours=dict(start=0.8, end=0.8, size=0.01, coloring='lines', showlabels=True),
                    line=dict(width=2, color='white', dash='dash'),
                    showscale=False,
                    name='0.8 m/s² 阈值',
                    hoverinfo='skip',
                ))
            except Exception:
                pass

        st.plotly_chart(fig, width="stretch")

        # 统计
        accel_flat = [v for row in hm_data["accel_matrix"] for v in row]
        valid_accel = [v for v in accel_flat if v >= 0.8]

        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("扫描点总数", len(accel_flat))
        with col_s2:
            st.metric("达标点数 (≥0.8 m/s²)", len(valid_accel))
        with col_s3:
            st.metric("达标率", f"{len(valid_accel) / len(accel_flat) * 100:.1f}%" if accel_flat else "N/A")

        with st.expander("📊 查看原始数据表格", expanded=False):
            df = pd.DataFrame(
                data_matrix,
                index=[f"后 {v:.0f}" for v in rear_vals],
                columns=[f"前 {v:.0f}" for v in front_vals],
            )
            st.dataframe(df, width="stretch")
