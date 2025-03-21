# Streamlit MVP: Улучшенный выбор сценария с описанием и сортировкой по NPV
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

# ========== Предрасчёт NPV по всем сценариям ==========
@st.cache_data
def sorted_scenarios():
    scores = []
    for name, scenario in presets.items():
        mix = scenario["mix"]
        params = scenario.get("parameters", {})
        bgp = scenario["bgp"]
        years = scenario["years"]
        discount = scenario["discount_rate"]

        def quick_cashflow():
            capex = sum(bgp * mix[k] / 100 * params.get(k, {}).get("capex", 1000) for k in mix)
            income = sum(bgp * mix[k] / 100 * params.get(k, {}).get("sale_price", 1800) for k in mix)
            lease_income = sum(bgp * mix[k] / 100 * params.get(k, {}).get("lease_price", 0) * 12 * params.get(k, {}).get("noi_margin", 0.2) for k in mix)
            cashflows = [-capex] + [income + lease_income] + [lease_income]*(years-1)
            return npf.npv(discount, cashflows)

        try:
            score = quick_cashflow()
        except:
            score = 0
        scores.append((name, presets[name].get("description", ""), score))
    scores.sort(key=lambda x: -x[2])
    return scores

# ========== UI выбор ==========
st.sidebar.header("Сценарии")
sorted_presets = sorted_scenarios()
options = [f"{name} — NPV: €{npv:,.0f}" for name, desc, npv in sorted_presets]
selected_label = st.sidebar.selectbox("Выберите сценарий", options)
selected = selected_label.split(" — ")[0]
compare_selection = st.sidebar.multiselect("Сравнить сценарии", [s[0] for s in sorted_presets])

# Показываем описание выбранного сценария
if selected in presets:
    desc = presets[selected].get("description", "Описание отсутствует")
    st.caption(f"📘 {desc}")

# Далее весь основной код как прежде...
# (оставлен без изменений, начиная с загрузки параметров и расчётов)
