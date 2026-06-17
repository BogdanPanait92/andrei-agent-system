"""Streamlit web dashboard for Andrei AI Agent System."""

import streamlit as st

from src.crew.main_crew import run_crew
from src.jobs.alerts import run_smart_alerts
from src.jobs.daily_briefing import run_daily_briefing
from src.jobs.weekly_review import run_weekly_review
from src.utils.config import settings

st.set_page_config(
    page_title="Andrei AI Agents",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Andrei AI Agent System")
st.caption("Multi-agent crew: CEO · Content · Tasks · Family · Reflector")

with st.sidebar:
    st.header("Navigare")
    page = st.radio(
        "Pagină",
        ["Dashboard", "Daily Briefing", "Weekly Review", "Crew Query", "Alerts"],
    )
    st.divider()
    st.markdown(f"**Env:** {settings.app_env}")
    st.markdown(f"**Timezone:** {settings.timezone}")

if page == "Dashboard":
    st.header("Status Sistem")
    col1, col2, col3 = st.columns(3)
    col1.metric("Agenți activi", "5")
    col2.metric("LLM Principal", "Grok")
    col3.metric("Memory", settings.memory_provider.title())

    st.subheader("Agenți")
    agents_info = {
        "CEO Agent": "Strategie, prioritizare, briefing-uri",
        "Content Creator": "Idei, posting plan, pipeline creativ",
        "Task Manager": "Task-uri, deadlines, clienți",
        "Family Balance": "Echilibru, anti-burnout, timp calitate",
        "Reflector": "Jurnal, reflecții, stabilitate vs sens",
    }
    for name, desc in agents_info.items():
        st.markdown(f"**{name}** — {desc}")

elif page == "Daily Briefing":
    st.header("🌅 Daily Briefing")
    if st.button("Generează Daily Briefing", type="primary"):
        with st.spinner("Crew-ul lucrează..."):
            result = run_daily_briefing()
        st.markdown(result)

elif page == "Weekly Review":
    st.header("📊 Weekly Review")
    if st.button("Generează Weekly Review", type="primary"):
        with st.spinner("Analiză săptămânală în curs..."):
            result = run_weekly_review()
        st.markdown(result)

elif page == "Crew Query":
    st.header("💬 Interogare Crew")
    query = st.text_area(
        "Ce vrei să analizeze crew-ul?",
        placeholder='ex: "analizeaza saptamana" sau "ce prioritati am azi?"',
        height=100,
    )
    mode = st.selectbox("Mod", ["custom", "daily", "weekly"])
    if st.button("Rulează Crew", type="primary") and query:
        with st.spinner("Agenții colaborează..."):
            result = run_crew(query=query, mode=mode)
        st.markdown(result)

elif page == "Alerts":
    st.header("🔔 Smart Alerts")
    if st.button("Verifică Alerte", type="primary"):
        with st.spinner("Verificare deadlines și echilibru..."):
            result = run_smart_alerts()
        st.json(result)