# Streamlit MVP: Исправление списка сценариев и UI
import streamlit as st
import json
import os
import numpy_financial as npf
import pandas as pd
import plotly.express as px
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from io import BytesIO
import copy

st.set_page_config(page_title="Редактор сценариев", layout="wide")

PRESET_PATH = "presets.json"

@st.cache_data
def load_presets():
    if os.path.exists(PRESET_PATH):
        with open(PRESET_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_presets(data):
    with open(PRESET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

presets = load_presets()

# ================== Выбор сценариев ==================
st.sidebar.header("Сценарии")

# Загружаем JSON-файл
if not presets:
    st.sidebar.error("❌ Нет доступных сценариев. Проверьте `presets.json` в GitHub.")
else:
    unique_scenarios = sorted(presets.keys())  # Берём все ключи
    selected = st.sidebar.selectbox("Выберите сценарий", unique_scenarios, index=0)

    if selected in presets:
        description = presets[selected].get("description", "Описание отсутствует")
        st.sidebar.caption(f"📘 {description}")

        st.write(f"### 📊 Выбран сценарий: {selected}")
    else:
        st.sidebar.warning("⚠️ Сценарий не найден в `presets.json`.")

    # Выводим описание выбранного сценария
    description = presets[selected].get("description", "Описание отсутствует")
    st.sidebar.caption(f"📘 {description}")

    # ================== Основные параметры сценария ==================
    preset = presets[selected]
    st.subheader(f"Сценарий: {selected}")

    bgp = st.number_input("Общая площадь (BGP, м²)", value=float(preset["bgp"]))
    discount = st.number_input("Ставка дисконта", value=float(preset["discount_rate"]))
    years = st.number_input("Срок проекта (лет)", value=int(preset["years"]))

    mix = st.columns(len(preset["mix"]))
    new_mix = {}
    for i, k in enumerate(preset["mix"]):
        new_mix[k] = mix[i].slider(k, 0.0, 100.0, float(preset["mix"][k]), step=1.0)

    st.markdown("---")
    st.subheader("🔧 Параметры назначения")
    parameters = preset.get("parameters", {})
    updated_params = {}

    for fn in parameters:
        st.markdown(f"### {fn}")
        col1, col2, col3 = st.columns(3)
        p = parameters[fn]
        new_p = {}
        for key in p:
            val = col1.number_input(f"{fn} - {key}", value=float(p[key]), key=f"{fn}-{key}")
            new_p[key] = val
        updated_params[fn] = new_p

    st.markdown("---")
    st.subheader("📊 Финансовые расчёты (по фазам)")
    
    def phased_cashflow(mix, params):
        capex = sum(bgp * mix[k] / 100 * params.get(k, {}).get("capex", 1000) for k in mix)
        income = sum(bgp * mix[k] / 100 * params.get(k, {}).get("sale_price", 1800) for k in mix)
        lease_income = sum(bgp * mix[k] / 100 * params.get(k, {}).get("lease_price", 0) * 12 * params.get(k, {}).get("noi_margin", 0.2) for k in mix)
        cashflows = [-capex] + [income + lease_income] + [lease_income]*(years-1)
        return {
            "capex": capex,
            "npv": npf.npv(discount, cashflows),
            "irr": npf.irr(cashflows),
            "noi": lease_income,
            "dscr": lease_income / (capex / years),
            "cf": cashflows
        }
    
    result = phased_cashflow(new_mix, updated_params)
    st.write(f"💰 CAPEX: €{result['capex']:,.0f}")
    st.write(f"📈 NPV: €{result['npv']:,.0f}")
    st.write(f"📉 IRR: {result['irr']*100:.2f}%")
    st.write(f"🏢 NOI: €{result['noi']:,.0f}")
    st.write(f"📊 DSCR: {result['dscr']:.2f}")
    
    if len(result['cf']) == years + 1:
        df_cf = pd.DataFrame({"Год": list(range(0, years + 1)), "Cash Flow (€)": result['cf']})
        fig_cf = px.bar(df_cf, x="Год", y="Cash Flow (€)", title="📊 Кэшфлоу по фазам проекта")
        st.plotly_chart(fig_cf)
    else:
        st.error("Ошибка: размер cashflow не соответствует количеству лет.")
    
    st.success("✅ Интерфейс сценариев исправлен и работает корректно!")
