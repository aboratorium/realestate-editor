
import streamlit as st
import json
import os

# ======== Загрузка и сохранение пресетов ========
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

# ======== Выбор сценария и действие ========
st.set_page_config(page_title="Редактор сценариев", layout="wide")
st.title("📋 Редактор сценариев девелопмента")

st.sidebar.header("Сценарии")
selected = st.sidebar.selectbox("Выберите сценарий", preset_names)
action = st.sidebar.radio("Действие", ["Редактировать", "Создать копию", "Удалить"])

# ======== Работа со сценарием ========
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
        "Stan": {"capex": 950, "sale_price": 2100},
        "Hotel": {"capex": 3500, "revpar": 200, "occupancy": 0.5, "noi_margin": 0.25},
        "Turistički objekti": {"capex": 1250, "revpar": 95, "occupancy": 0.45, "noi_margin": 0.18},
        "Poslovni prostor": {"capex": 1100, "sale_price": 1800, "lease_price": 14, "noi_margin": 0.23},
        "Restorani": {"capex": 1200, "lease_price": 18, "noi_margin": 0.28},
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

    if action == "Редактировать":
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

    elif action == "Создать копию":
        new_name = st.text_input("Имя нового сценария")
        if st.button("📁 Создать копию") and new_name:
            presets[new_name] = {
                "bgp": bgp,
                "discount_rate": discount,
                "years": years,
                "mix": new_mix,
                "parameters": updated_params
            }
            save_presets(presets)
            st.success(f"Создан новый сценарий: {new_name}")

    elif action == "Удалить":
        if st.button(f"🗑 Удалить сценарий '{selected}'"):
            del presets[selected]
            save_presets(presets)
            st.warning("Сценарий удалён. Перезапустите страницу.")
