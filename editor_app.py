# Streamlit MVP: Финансирование по фазам + Торнадо-анализ
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
preset_names = list(presets.keys())

st.title("📋 Редактор сценариев девелопмента")

st.sidebar.header("Сценарии")
selected = st.sidebar.selectbox("Выберите сценарий", preset_names)
compare_selection = st.sidebar.multiselect("Сравнить сценарии", preset_names)

if selected:
    preset = presets[selected]
    st.subheader(f"Сценарий: {selected}")

    bgp = st.number_input("Общая площадь (BGP, м²)", value=float(preset["bgp"]))
    discount = st.number_input("Ставка дисконта", value=float(preset["discount_rate"]))
    years = st.number_input("Срок проекта (лет)", value=int(preset["years"]))

    construction_years = st.number_input("⛏️ Срок строительства (лет)", min_value=1, max_value=years, value=2)
    sales_years = st.number_input("💼 Годы продаж (лет)", min_value=1, max_value=years, value=3)

    mix = st.columns(len(preset["mix"]))
    new_mix = {}
    for i, k in enumerate(preset["mix"]):
        new_mix[k] = mix[i].slider(k, 0.0, 100.0, float(preset["mix"][k]), step=1.0)

    st.markdown("---")
    st.subheader("🔧 Параметры назначения")
    default_params = {
        "Stan": {"capex": 950, "sale_price": 2100, "parking_ratio": 1/100},
        "Hotel": {"capex": 3500, "revpar": 200, "occupancy": 0.5, "noi_margin": 0.25, "parking_ratio": 1/100},
        "Turistički objekti": {"capex": 1250, "revpar": 95, "occupancy": 0.45, "noi_margin": 0.18, "parking_ratio": 0.8/100},
        "Poslovni prostor": {"capex": 1100, "sale_price": 1800, "lease_price": 14, "noi_margin": 0.23, "parking_ratio": 1/60},
        "Restorani": {"capex": 1200, "lease_price": 18, "noi_margin": 0.28, "parking_ratio": 1/30},
    }
    parameters = preset.get("parameters", default_params)
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
        capex = sum(bgp * mix[k] / 100 * params[k]["capex"] for k in mix)
        income = sum(bgp * mix[k] / 100 * params[k].get("sale_price", 0) for k in mix)
        lease_income = sum(bgp * mix[k] / 100 * params[k].get("lease_price", 0) * 12 * params[k].get("noi_margin", 0) for k in mix)

        cashflows = []
        for y in range(1, years + 1):
            if y <= construction_years:
                cashflows.append(-capex / construction_years)
            elif y <= construction_years + sales_years:
                cf = income / sales_years + lease_income
                cashflows.append(cf)
            else:
                cashflows.append(lease_income)

        return {
            "capex": capex,
            "npv": npf.npv(discount, [-capex / construction_years] * construction_years + cashflows[construction_years:]),
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

    df_cf = pd.DataFrame({"Год": list(range(1, years+1)), "Cash Flow (€)": result['cf']})
    fig_cf = px.bar(df_cf, x="Год", y="Cash Flow (€)", title="📊 Кэшфлоу по фазам проекта")
    st.plotly_chart(fig_cf)

    # ===== 🌪 Анализ чувствительности (торнадо) =====
    st.subheader("🌪 Торнадо-анализ чувствительности NPV")
    sensitivity_data = []
    base_npv = result['npv']
    for fn, attrs in updated_params.items():
        for key in [k for k in attrs if k in ["sale_price", "capex", "noi_margin"]]:
            for delta in [-0.2, 0.2]:
                test_params = copy.deepcopy(updated_params)
                test_params[fn][key] *= 1 + delta
                res = phased_cashflow(new_mix, test_params)
                sensitivity_data.append({
                    "Параметр": f"{fn} - {key}",
                    "Изменение": f"{int(delta*100)}%",
                    "NPV": res['npv']
                })
    df_sens = pd.DataFrame(sensitivity_data)
    fig_tornado = px.bar(df_sens, x="NPV", y="Параметр", color="Изменение", orientation="h", title="Торнадо-график чувствительности NPV")
    st.plotly_chart(fig_tornado)

    st.success("Чувствительность учтена к ключевым параметрам")
