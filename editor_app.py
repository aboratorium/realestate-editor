# Streamlit MVP: Полный финанализ + Экспорт + Торнадо
import streamlit as st
import json
import os
import numpy_financial as npf
import pandas as pd
import plotly.express as px
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from io import BytesIO

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
    st.subheader("📊 Финансовые расчёты")

    def calc_metrics(mix, params):
        capex = sum(bgp * mix[k] / 100 * params[k]["capex"] for k in mix)
        income = sum(bgp * mix[k] / 100 * params[k].get("sale_price", 0) for k in mix)
        lease_income = sum(bgp * mix[k] / 100 * params[k].get("lease_price", 0) * 12 * params[k].get("noi_margin", 0) for k in mix)
        op_income = lease_income
        cashflows = [-capex] + [income + lease_income] + [lease_income]*(years-1)
        return {
            "capex": capex,
            "npv": npf.npv(discount, cashflows),
            "irr": npf.irr(cashflows),
            "noi": lease_income,
            "dscr": lease_income / (capex / years),
            "cf": cashflows
        }

    result = calc_metrics(new_mix, updated_params)
    st.write(f"💰 CAPEX: €{result['capex']:,.0f}")
    st.write(f"📈 NPV: €{result['npv']:,.0f}")
    st.write(f"📉 IRR: {result['irr']*100:.2f}%")
    st.write(f"🏢 NOI: €{result['noi']:,.0f}")
    st.write(f"📊 DSCR: {result['dscr']:.2f}")

    total_parking = sum(bgp * new_mix[k] / 100 * updated_params[k]["parking_ratio"] for k in new_mix)
    st.write(f"🚗 Парковка: всего {total_parking:.0f} мест")

    df_cf = pd.DataFrame({"Год": list(range(years+1)), "Cash Flow (€)": result['cf']})
    fig_cf = px.bar(df_cf, x="Год", y="Cash Flow (€)", title="Кэшфлоу по годам")
    st.plotly_chart(fig_cf)

    # ====== 📦 Экспорт в Excel ======
    if st.button("📤 Скачать Excel"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_cf.to_excel(writer, sheet_name="Cashflow", index=False)
            mix_df = pd.DataFrame(list(new_mix.items()), columns=["Функция", "%"])
            mix_df.to_excel(writer, sheet_name="Mix", index=False)
        st.download_button("📥 Скачать файл", output.getvalue(), file_name="scenario_export.xlsx")

    # ====== 🌪 Торнадо-диаграмма ======
    st.markdown("---")
    st.subheader("🌪 Чувствительность NPV к параметрам")
    base_npv = result['npv']
    tornado_data = []
    for key in updated_params:
        val = updated_params[key]
        if "sale_price" in val:
            for delta in [-0.2, 0.2]:
                changed = updated_params.copy()
                changed[key] = val.copy()
                changed[key]["sale_price"] *= (1 + delta)
                test = calc_metrics(new_mix, changed)
                tornado_data.append({"Фактор": f"{key} (sale_price)", "Δ": f"{int(delta*100)}%", "NPV": test['npv']})
    df_tornado = pd.DataFrame(tornado_data)
    fig_tornado = px.bar(df_tornado, x="NPV", y="Фактор", color="Δ", orientation="h", title="Торнадо-анализ NPV")
    st.plotly_chart(fig_tornado)

    # Сравнение сценариев — прежнее поведение
    if compare_selection:
        st.subheader("📊 Сравнение сценариев")
        df_compare = []
        for name in compare_selection:
            p = presets[name]
            m = calc_metrics(p["mix"], p.get("parameters", default_params))
            df_compare.append({"Сценарий": name, "NPV": m["npv"], "IRR": m["irr"]*100, "CAPEX": m["capex"], "DSCR": m["dscr"]})
        df = pd.DataFrame(df_compare)
        st.dataframe(df.style.format({"NPV": "€{:.0f}", "IRR": "{:.2f}%", "CAPEX": "€{:.0f}", "DSCR": "{:.2f}"}))
        fig = px.bar(df, x="Сценарий", y="NPV", color="Сценарий", title="Сравнение по NPV")
        st.plotly_chart(fig)

    if st.button("💾 Сохранить изменения"):
        presets[selected] = {
            "bgp": bgp,
            "discount_rate": discount,
            "years": years,
            "mix": new_mix,
            "parameters": updated_params
        }
        save_presets(presets)
        st.success("Сценарий обновлён")
