import streamlit as st
import pandas as pd
import plotly.express as px
from utils.mongo_utils import get_mongo_db

st.set_page_config(page_title="Dashboard Educativo de México", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #fdf6fa; }
    .block-container { padding-top: 2rem; }
    h1, h2, h3, h4 { color: #6a1b9a; }
    table td:nth-child(1) { font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

db = get_mongo_db()
df_uni = pd.DataFrame(list(db["processed_hipolabs"].find()))
df_matri = pd.DataFrame(list(db["processed_worldbank"].find()))
pais = db["processed_worldbank_country"].find_one()

# ================== TÍTULO ==================
st.title("🎓 Dashboard Educativo de México")
st.markdown("Explora datos sobre universidades y matrícula en educación superior de forma clara y directa.")

# ================== PERFIL DEL PAÍS ==================
st.header("🇲🇽 Perfil educativo de México")

if pais:
    col1, col2, col3 = st.columns(3)
    col1.metric("Nivel de ingreso", pais.get("income_level", {}).get("value", "—"))
    col2.metric("Región", pais.get("region", {}).get("value", "—"))
    col3.metric("Código ISO", pais.get("id", "—").upper())

    ingreso = pais.get("income_level", {}).get("value", "").lower()
    if "middle" in ingreso:
        st.info("México es un país de ingreso medio. Esto influye en el acceso a educación superior.")
else:
    st.warning("No se encontró información del país.")

# ================== UNIVERSIDADES ==================
st.header("🏛️ Universidades activas")

if not df_uni.empty:
    df_uni["country"] = df_uni["country"].fillna("Sin país")
    df_uni["num_domains"] = df_uni["domains"].apply(lambda x: len(x) if isinstance(x, list) else 0)

    total_uni = df_uni.shape[0]
    dominios = df_uni["domains"].explode().nunique()

    col1, col2 = st.columns(2)
    col1.metric("Total de universidades", f"{total_uni}")
    col2.metric("Dominios únicos", f"{dominios}")

    # --- Buscador y tabla ordenada ---
    st.subheader("🔎 Buscar universidades y dominios")
    query = st.text_input("Escribe parte del nombre de la universidad:")

    df_filter = df_uni.copy()
    if query:
        df_filter = df_filter[df_filter["name"].str.contains(query, case=False)]

    df_filter = df_filter.sort_values("num_domains", ascending=False).reset_index(drop=True)
    df_filter.index += 1

    st.markdown("### 🏆 Mejores universidades con los dominios más comunes")
    st.caption("Universidades ordenadas según cuántos dominios tienen registrados (ej. .edu.mx, .org.mx, etc.)")

    for i, row in df_filter.head(10).iterrows():
        badge = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔹"
        st.markdown(
            f"{badge} **{row['name']}** — `{row['num_domains']} dominio(s)`  \n"
            f"[🌐 {row['web_pages'][0]}]({row['web_pages'][0]})  \n"
            f"**Dominios:** {', '.join(row['domains']) if isinstance(row['domains'], list) else '—'}"
        )

    with st.expander("🔽 Ver todas las universidades"):
        st.dataframe(df_filter[["name", "domains", "web_pages", "num_domains"]], use_container_width=True)
else:
    st.warning("No hay datos disponibles de universidades.")

st.markdown("---")

# ================== MAPA: Mejores universidades del país (con coordenadas fijas) ==================
st.header("🌟 Mapa de las mejores universidades del país")

universidades_destacadas = [
    {"name": "Universidad Anáhuac (Sur)", "lat": 19.3344, "lon": -99.2446},
    {"name": "Universidad de La Salle Bajío", "lat": 21.1370, "lon": -101.6834},
    {"name": "BUAP", "lat": 19.0414, "lon": -98.2063},
    {"name": "UG Campus León", "lat": 21.1222, "lon": -101.6821},
    {"name": "CETI (Colomos)", "lat": 20.7016, "lon": -103.3777},
    {"name": "CETYS Universidad", "lat": 32.6235, "lon": -115.4523},
    {"name": "CEU Monterrey", "lat": 25.6880, "lon": -100.3179},
    {"name": "Centro Universitario Ixtlahuaca", "lat": 19.5646, "lon": -99.7553},
    {"name": "Universidad Xochicalco", "lat": 31.8667, "lon": -116.5960},
    {"name": "Universidad Champagnat", "lat": 20.6247, "lon": -103.3844}
]

df_top = pd.DataFrame(universidades_destacadas)
df_top["size"] = 5
fig_top = px.scatter_mapbox(
    df_top,
    lat="lat", lon="lon",
    hover_name="name",
    size="size",
    zoom=4,
    height=500,
    title="📍 Mapa de universidades destacadas",
    color_discrete_sequence=["#8e24aa"]
)

fig_top.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":50,"l":0,"b":0})
st.plotly_chart(fig_top, use_container_width=True)


# ================== INSIGHTS BANCO MUNDIAL ==================
st.subheader("📍 Insights rápidos sobre la matrícula en educación superior")

if not df_matri.empty:
    df_matri = df_matri[df_matri["value"].notnull()]
    df_matri["date"] = pd.to_datetime(df_matri["date"], errors="coerce")
    df_matri = df_matri.sort_values("date")
    df_matri["year"] = df_matri["date"].dt.year

    # Año con mayor y menor tasa
    max_row = df_matri.loc[df_matri["value"].idxmax()]
    min_row = df_matri.loc[df_matri["value"].idxmin()]

    # Promedio por década
    df_matri["decada"] = (df_matri["year"] // 10) * 10
    df_decada = df_matri.groupby("decada")["value"].mean().reset_index()

    # Variación respecto al año anterior
    df_matri["delta"] = df_matri["value"].diff()
    ult = df_matri.iloc[-1]
    delta = ult["delta"]

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label=f"Tasa actual ({ult['year']})",
            value=f"{ult['value']:.2f}%",
            delta=f"{delta:+.2f}% respecto al año anterior"
        )
    with col2:
        st.info(f"""
📈 Año con mayor tasa: **{max_row['year']}** → **{max_row['value']:.2f}%**  
📉 Año con menor tasa: **{min_row['year']}** → **{min_row['value']:.2f}%**
""")

    fig_dec = px.bar(df_decada, x="decada", y="value",
                     labels={"decada": "Década", "value": "Promedio (%)"},
                     title="📊 Promedio de matrícula por década",
                     color_discrete_sequence=["#ab47bc"])
    st.plotly_chart(fig_dec, use_container_width=True)
else:
    st.warning("No hay datos disponibles para generar insights.")

# ================== MATRÍCULA ==================
st.header("📈 Evolución de la matrícula en Educación Superior")

if not df_matri.empty:
    rango = st.slider("Selecciona el rango de años:",
                      int(df_matri["year"].min()),
                      int(df_matri["year"].max()),
                      (2010, 2022))

    df_f = df_matri[df_matri["year"].between(rango[0], rango[1])]
    fig_line = px.line(df_f, x="date", y="value", markers=True,
                       labels={"date": "Año", "value": "Tasa (%)"},
                       title="📈 Evolución de la matrícula (%)",
                       color_discrete_sequence=["#6a1b9a"])
    st.plotly_chart(fig_line, use_container_width=True)

    with st.expander("🔍 Ver datos crudos"):
        st.dataframe(df_f, use_container_width=True)
else:
    st.warning("No hay datos de matrícula disponibles.")


st.markdown("---")
st.markdown("<h4 style='text-align: center; color: #a46fb4;'>Hecho con 💜 y mucha dedicación para el futuro de México</h4>", unsafe_allow_html=True)
