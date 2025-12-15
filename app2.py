import streamlit as st
import pandas as pd
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import plotly.express as px
# ------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ------------------------------------------------------
st.set_page_config(page_title="Visualizador Acuerdos UBPD", layout="wide")

# ------------------------------------------------------
# FUNCIÓN PARA LEER GOOGLE SHEETS VIA OAUTH
# ------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SPREADSHEET_ID = "1CLXO542URTaZOjOaZnMP_BkQYbXVoCVIM0AQEciMqiU"
RANGE = "Hoja1!A:Z"

def read_sheet():

    # --- OAuth usando Streamlit Secrets ---
    if "google_creds" not in st.session_state:

        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": st.secrets["google"]["client_id"],
                    "client_secret": st.secrets["google"]["client_secret"],
                    "auth_uri": st.secrets["google"]["auth_uri"],
                    "token_uri": st.secrets["google"]["token_uri"],
                }
            },
            SCOPES,
        )

        creds = flow.run_local_server(port=0)

        # Guardar token en sesión (NO archivo)
        st.session_state["google_creds"] = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }

    else:
        creds = Credentials.from_authorized_user_info(
            st.session_state["google_creds"], SCOPES
        )

    # --- Lectura Google Sheets ---
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()

    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE
    ).execute()

    values = result.get("values", [])

    if not values:
        return pd.DataFrame()

    return pd.DataFrame(values[1:], columns=values[0])

# ------------------------------------------------------
# CARGA DE DATOS
# ------------------------------------------------------
df = read_sheet()  # <<< AQUÍ SE CARGA TODO DESDE GOOGLE SHEETS
df.columns = df.columns.str.strip()

# ------------------------------------------------------
# Encabezado
# ------------------------------------------------------
st.markdown(
    """
    <style>
        .header-container {
            background-color: #8E44AD;  /* Morado UBPD aproximado */
            padding: 15px 0;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .header-container img {
            height: 90px;                     /* Tamaño base */
            transform: scale(1.5);            /* 1.5 veces su tamaño */
            transform-origin: center center;  /* Centrar la ampliación */
        }
    </style>

    <div class="header-container"> 
        <img src="https://unidadbusqueda.gov.co/wp-content/themes/ubpd-portal-web/assets/ubpd_white_logo.svg"/>
    </div>
    """,
    unsafe_allow_html=True
)

# ------------------------------------------------------
# MENÚ SUPERIOR
# ------------------------------------------------------
# ---- MENÚ ESTILO UBPD ----
st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] {
    background-color: #057B8D;
    display: flex;
    justify-content: center;
    gap: 80px;
    padding-top: 4px;
    padding-bottom: 4px;
}

.stTabs [data-baseweb="tab"] {
    font-size: 18px;
    color: white;
    font-weight: bold;
    font-family: Arial, sans-serif;
}

.stTabs [aria-selected="true"] {
    background-color: #045A64;
    border-radius: 6px;
}
</style>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["generalidades", "detalles"])


# ------------------------------------------------------
# ------------------   PÁGINA 1 ------------------------
# ------------------ GENERALIDADES ---------------------
# ------------------------------------------------------
with tab1:

    st.title("📌 Generalidades de los acuerdos")

    # ---- FILTROS ----
    colA, colB = st.columns(2)

    with colA:
        filtro_tipo_entidad = st.multiselect(
            "Filtrar por Tipo de Entidad:",
            options=df["Tipo de entidad"].unique()
        )

    with colB:
        filtro_tipo_acuerdo = st.multiselect(
            "Filtrar por Tipo de Acuerdo:",
            options=df["Tipo de acuerdo"].unique()
        )

    # APLICAR FILTROS
    df_g = df.copy()

    if filtro_tipo_entidad:
        df_g = df_g[df_g["Tipo de entidad"].isin(filtro_tipo_entidad)]
    if filtro_tipo_acuerdo:
        df_g = df_g[df_g["Tipo de acuerdo"].isin(filtro_tipo_acuerdo)]

    # ---- RESUMEN ----
    st.subheader("📊 Resumen")

    total = len(df_g)
    priv = len(df_g[df_g["Tipo de entidad"] == "Privada"])
    pub = len(df_g[df_g["Tipo de entidad"] == "Pública"])

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Total entidades", total)
    with c2:
        st.metric("Entidades privadas", priv)
    with c3:
        st.metric("Entidades públicas", pub)

    # ---- GRÁFICO PIE ----
    st.subheader("📈 Distribución por tipo de acuerdo")

    if len(df_g) > 0:
        pie = px.pie(
            df_g,
            names="Tipo de acuerdo",
            title="Tipo de acuerdo",
            hole=0.3
        )
        st.plotly_chart(pie, use_container_width=True)
    else:
        st.info("No hay datos para graficar con los filtros seleccionados.")

    # ---- MATRIZ ----
    st.subheader("📄 Matriz filtrada")

    columnas = [
        "Entidad", "Tipo de entidad", "Tipo de acuerdo",
        "Estado", "Vigencia del acuerdo"
    ]

    st.dataframe(df_g[columnas], use_container_width=True)

# ------------------------------------------------------
# ------------------   PÁGINA 2 ------------------------
# ---------------- DETALLES DE LA GESTIÓN --------------
# ------------------------------------------------------
with tab2:

    st.title("📑 Detalles de la gestión por entidad")

    # ---- FILTRO POR ENTIDAD ----
    entidades = df["Entidad"].unique()

    entidad_sel = st.selectbox(
        "Selecciona una entidad:",
        options=entidades
    )

    df_d = df[df["Entidad"] == entidad_sel].iloc[0]

    # ---- CABECERA LOGO + INFO ----
    colL, colR = st.columns([1, 3])

    with colL:
        st.image(df_d["Logos"], width=140)

    with colR:
        st.markdown(f"""
        ### **{df_d['Entidad']}**
        - **Tipo de acuerdo:** {df_d['Tipo de acuerdo']}
        - **Estado:** {df_d['Estado']}
        - **Vigencia del acuerdo:** {df_d['Vigencia del acuerdo']}
        """)

    st.markdown("---")

    # ---- SECCIÓN DOBLE ----
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📄 Tipo de información a la que la UBPD tiene acceso")
        st.info(df_d["Tipo de información a la que la UBPD tiene acceso"])

    with c2:
        st.subheader("👤 Quién tiene acceso a la información")
        st.info(df_d["Quién tiene el acceso a la info"])

    # ---- CONSULTA ----
    st.subheader("📬 ¿Cómo consulto o solicito la información?")
    st.warning(df_d["¿Cómo consulto o solicito la información?"])
