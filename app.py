import streamlit as st
import pandas as pd
import io
from datetime import datetime
import numpy as np

st.set_page_config(page_title="DISPO Planas", layout="wide")
st.title("DISPO PLANAS redagavimo įrankis")

# 1. ĮKĖLIMO BLOKAS
uploaded_file = st.file_uploader("Įkelk Excel failą:", type=["xlsx"])

if uploaded_file:
    excel = pd.ExcelFile(uploaded_file)
    sheet_names = excel.sheet_names

    # 2. PASIRINKTI LAPĄ
    sheet = st.selectbox("Pasirink lapą:", sheet_names)
    df = excel.parse(sheet)

    st.markdown("### Duomenų filtras")

    # Filtravimas pagal tekstinius stulpelius su nedaug reikšmių
    filter_cols = [col for col in df.columns if df[col].dtype == object and df[col].nunique() < 100]
    filters = {}
    for col in filter_cols:
        options = df[col].dropna().unique().tolist()
        selected = st.multiselect(f"Filtruoti pagal: {col}", options)
        if selected:
            filters[col] = selected

    # Pritaikome filtrus
    filtered_df = df.copy()
    for col, values in filters.items():
        filtered_df = filtered_df[filtered_df[col].isin(values)]

    st.markdown("### Stulpelių pasirinkimas")
    selected_columns = st.multiselect("Pasirink stulpelius, kuriuos rodyti:", options=df.columns.tolist(), default=filtered_df.columns.tolist())
    visible_df = filtered_df[selected_columns]

    # Validacija (skaitiniai stulpeliai ir datos)
    def validate_data(df, cols):
        for col in cols:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].apply(lambda x: max(x, 0) if pd.notnull(x) else x)
            elif pd.api.types.is_object_dtype(df[col]) and "date" in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
                except:
                    pass
        return df

    visible_df = validate_data(visible_df, visible_df.columns)

    st.markdown("### Redaguojama lentelė")
    st.caption("*Neigiami skaičiai automatiškai keičiami į 0, datos konvertuojamos jei įmanoma*")

    # Spalvinimas pagal reikšmes
    def highlight_values(val, col_name):
        if isinstance(val, (int, float)) and pd.notnull(val):
            if "income" in col_name.lower() and val < 100:
                return "background-color: #ffcccc"
            elif "km" in col_name.lower() and val == 0:
                return "background-color: #ffffcc"
        return ""

    styled_df = visible_df.style.applymap(lambda v: highlight_values(v, col_name=visible_df.columns[visible_df.columns.get_loc(v.name)]), subset=pd.IndexSlice[:, visible_df.select_dtypes(include=[np.number]).columns])

    st.dataframe(styled_df, use_container_width=True)

    edited_df = st.data_editor(visible_df, num_rows="dynamic", use_container_width=True)

    if st.button("💾 Atsisiųsti redaguotą failą"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for name in sheet_names:
                temp_df = excel.parse(name)
                if name == sheet:
                    unchanged_df = df[~df.index.isin(edited_df.index)]
                    final_df = pd.concat([unchanged_df, edited_df]).sort_index()
                    final_df.to_excel(writer, sheet_name=name, index=False)
                else:
                    temp_df.to_excel(writer, sheet_name=name, index=False)

        st.download_button(
            label="📅 Atsisiųsti naują Excel",
            data=output.getvalue(),
            file_name="Redaguotas_Planning2.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
