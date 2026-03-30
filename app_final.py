import streamlit as st
import plotly.express as px
import pandas as pd

# ---------------------------------------------------------
# 0. 基礎設定與資料結構
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="人生花費預算 vs 實際支出")
st.title("📊 人生花費結構：預算 vs 實際支出 終極儀表板")

# 定義你指定的大項與子項目
spending_menu = {
    "房屋與居住": ["房價與房貸利息", "房屋裝修", "房屋稅與地價稅", "水電瓦斯", "管理費"],
    "飲食與生活": ["三餐外食", "買菜下廚", "日用品", "服飾與理髮", "其他雜費"],
    "子女養育": ["保母與托嬰", "教育學費", "才藝班與補習", "生活用品與玩具"],
    "交通與通訊": ["買車與車貸", "油錢與充電", "車輛保養與稅金", "大眾運輸", "手機與網路費"],
    "醫療與保險": ["看診與醫藥費", "人身保險(壽險/醫療險)", "保健食品"],
    "休閒與娛樂": ["國內外旅遊", "聚餐慶生", "個人嗜好與娛樂", "運動健身"],
    "退休預備金": ["純養老生活費", "看護與長期照顧預備金"]
}

# 預設比例 (總和為 100)
default_ratios = {
    "房屋與居住": 35.0,
    "飲食與生活": 20.0,
    "子女養育": 15.0,
    "交通與通訊": 10.0,
    "醫療與保險": 10.0,
    "休閒與娛樂": 5.0,
    "退休預備金": 5.0
}

# 初始化 Session State：儲存左欄預算百分比
for key, val in default_ratios.items():
    if key not in st.session_state:
        st.session_state[key] = val

# 初始化 Session State：儲存右欄實際支出金額（每月）
if 'actual_expenses' not in st.session_state:
    st.session_state.actual_expenses = {key: 0.0 for key in spending_menu.keys()}

# ---------------------------------------------------------
# 1. 核心魔法：連動等比例扣除（左欄拉桿專用）
# ---------------------------------------------------------
def calculate_linked_ratios():
    changed_key = None
    for key in default_ratios.keys():
        current_slider_val = st.session_state.get(f"slider_{key}")
        if current_slider_val is not None and current_slider_val != st.session_state[key]:
            changed_key = key
            break
            
    if not changed_key:
        return
        
    new_val = st.session_state[f"slider_{changed_key}"]
    
    if new_val >= 100.0:
        for key in default_ratios.keys():
            st.session_state[key] = 100.0 if key == changed_key else 0.0
        return

    remaining_pool = 100.0 - new_val
    other_keys = [k for k in default_ratios.keys() if k != changed_key]
    other_sum_before = sum(st.session_state[k] for k in other_keys)
    
    if other_sum_before == 0:
        avg_val = remaining_pool / len(other_keys)
        for k in other_keys:
            st.session_state[k] = round(avg_val, 2)
    else:
        for k in other_keys:
            scale_ratio = st.session_state[k] / other_sum_before
            st.session_state[k] = round(remaining_pool * scale_ratio, 2)
            
    st.session_state[changed_key] = new_val
    
    current_sum = sum(st.session_state[k] for k in default_ratios.keys())
    if current_sum != 100.0:
        diff = 100.0 - current_sum
        for k in other_keys:
            st.session_state[k] = round(st.session_state[k] + diff, 2)
            break

# 先計算完比例，再去渲染前端 Slider
calculate_linked_ratios()

# ---------------------------------------------------------
# 2. 頂部全局設定：月薪與時間視角
# ---------------------------------------------------------
col_top1, col_top2 = st.columns(2)
with col_top1:
    monthly_income = st.number_input("💰 請輸入你的預估「月薪」 (元)", min_value=0, value=50000, step=1000)
with col_top2:
    view_type = st.radio("🔍 顯示時間視角", ["每月金額", "每年金額"], horizontal=True)

multiplier = 1 if view_type == "每月金額" else 12
st.markdown("---")

# ---------------------------------------------------------
# 3. 雙欄設計：左欄（預算比例）與 右欄（實際支出）
# ---------------------------------------------------------
col_left, col_right = st.columns(2)

# ==================== 左欄：預算規劃 (100% 自動平衡) ====================
with col_left:
    st.header("👈 預算比例規劃 (理想)")
    st.caption("當你調大某一項，其他項會按比例自動縮小，永遠維持 100%！")
    
    # 迴圈動態生成 7 個連動拉桿
    for key in default_ratios.keys():
        st.session_state[f"slider_{key}"] = float(st.session_state[key])
        st.slider(
            f"{key} (%)",
            min_value=0.0,
            max_value=100.0,
            step=0.5,
            key=f"slider_{key}"
        )
        
    # 根據計算後的比例與月薪，算出絕對預算金額
    budget_data = {}
    for key in default_ratios.keys():
        budget_data[key] = (monthly_income * st.session_state[key] / 100) * multiplier

# ==================== 右欄：實際支出填寫 (動態多階選單) ====================
with col_right:
    st.header("👉 實際支出填寫 (現實)")
    st.caption("輸入你真實的開銷，系統會自動換算為統一週期。")
    
    # 階層連動下拉選單
    main_cat = st.selectbox("1️⃣ 選擇消費大項", list(spending_menu.keys()))
    sub_cat = st.selectbox("2️⃣ 選擇子項目", spending_menu[main_cat])
    period = st.selectbox("3️⃣ 選擇記帳週期", ["每日", "每週", "每月", "每年"])
    amount = st.number_input("4️⃣ 輸入金額 (元)", min_value=0.0, value=100.0, step=100.0)
    
    # 週期轉換魔法
    monthly_calc = 0.0
    if period == "每日":
        monthly_calc = amount * 30
    elif period == "每週":
        monthly_calc = amount * 4.35
    elif period == "每月":
        monthly_calc = amount
    elif period == "每年":
        monthly_calc = amount / 12
        
    # 按鈕：新增支出
    if st.button("➕ 新增/更新 此筆支出"):
        st.session_state.actual_expenses[main_cat] += monthly_calc
        st.toast(f"已將【{sub_cat}】換算後加入【{main_cat}】大項中！", icon="✅")

    # 顯示目前累積的實際支出金額
    st.markdown("##### 📌 目前累計實際支出 (每月)")
    df_actual = pd.DataFrame(
        list(st.session_state.actual_expenses.items()), 
        columns=["消費大項", "每月金額"]
    )
    st.dataframe(df_actual.set_index("消費大項"), height=180)
    
    if st.button("🗑️ 清空實際支出數據"):
        st.session_state.actual_expenses = {key: 0.0 for key in spending_menu.keys()}
        st.rerun()

# ---------------------------------------------------------
# 4. 底部：動態圓餅圖對照呈現 (支援新版 Streamlit)
# ---------------------------------------------------------
st.markdown("---")
st.subheader(f"📊 【{view_type}】圓餅圖視覺化對比")

col_chart1, col_chart2 = st.columns(2)

# --- 圖表 1：預算規劃圖 ---
with col_chart1:
    st.markdown("#### 👈 理想預算分配")
    df_budget_plot = pd.DataFrame(list(budget_data.items()), columns=["類別", "金額"])
    
    fig_budget = px.pie(
        df_budget_plot, 
        values='金額', 
        names='類別', 
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_budget.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_budget, width="stretch")

# --- 圖表 2：實際支出圖 ---
with col_chart2:
    st.markdown("#### 👉 實際支出分配")
    
    # 將 Session State 中的每月金額轉換為當前視角（每月或每年）
    actual_data = {k: v * multiplier for k, v in st.session_state.actual_expenses.items()}
    df_actual_plot = pd.DataFrame(list(actual_data.items()), columns=["類別", "金額"])
    
    # 避免全部為 0 時圖表出錯
    if df_actual_plot['金額'].sum() == 0:
        st.info("ℹ️ 請在右上方輸入資料並按下『新增此筆支出』，圓餅圖將會在此呈現。")
    else:
        fig_actual = px.pie(
            df_actual_plot, 
            values='金額', 
            names='類別', 
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_actual.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_actual, width="stretch")
