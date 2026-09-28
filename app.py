import streamlit as st
import pandas as pd
import plotly.express as px
import subprocess
import os

st.set_page_config(page_title="Spordle Hockey Stats Dashboard", layout="wide")
st.title("🏒 Outaouais AA Regional Hockey Stats")
# --- SECURITY CHECK ---
def check_password():
    def password_entered():
        # YOU CAN CHANGE "hockey2026" TO WHATEVER PASSWORD YOU WANT
        if st.session_state["password"] == "hockey2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 Please enter the team password to access the dashboard:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 Please enter the team password to access the dashboard:", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect. Please try again.")
        return False
    return True

if not check_password():
    st.stop() # Stops anyone without the password from seeing the rest of the page!
# ----------------------
@st.cache_data
def load_data():
    if os.path.exists('league_stats.csv'):
        return pd.read_csv('league_stats.csv')
    return pd.DataFrame()

st.sidebar.header("Dashboard Controls")

if st.sidebar.button("🔄 Refresh Data from Spordle"):
    with st.spinner("Fetching latest games and scoresheets..."):
        subprocess.run(["python", "scraper.py"])
        st.cache_data.clear()
        st.success("Data refreshed successfully!")

df = load_data()

if df.empty:
    st.warning("No data found. Please click 'Refresh Data' to pull the latest stats.")
else:
    # Category Filter
    categories = [c for c in df['Category'].unique() if pd.notna(c)]
    categories.sort()
    selected_category = st.sidebar.selectbox("Filter by Category / Age Group", ["All Categories"] + list(categories))
    
    if selected_category != "All Categories":
        df = df[df['Category'] == selected_category]

    # Team Filter
    if 'Player_Team' not in df.columns:
        st.warning("⚠️ Please update your league_stats.csv file to apply specific team filters.")
    else:
        teams = [t for t in df['Player_Team'].unique() if pd.notna(t)]
        teams.sort()
        
        selected_team = st.sidebar.selectbox("Filter by Team", ["All Teams"] + list(teams))
        
        if selected_team != "All Teams":
            df = df[df['Player_Team'] == selected_team]
            st.subheader(f"Stats for: {selected_team} ({selected_category})")
        else:
            st.subheader(f"League Wide Stats ({selected_category})")

        goals_df = df[df['Type'] == 'Goal']
        assists_df = df[df['Type'] == 'Assist']
        penalties_df = df[df['Type'] == 'Penalty']
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Goals", len(goals_df))
        col2.metric("Total Assists", len(assists_df))
        col3.metric("Total Points", len(goals_df) + len(assists_df))
        col4.metric("Total Penalties", len(penalties_df))
        
        st.markdown("---")
        st.subheader("🏆 Player Leaderboards")
        
        col_goals, col_assists, col_points = st.columns(3)
        
        with col_goals:
            st.markdown("**Top Goal Scorers**")
            top_goals = goals_df.groupby(['Player', 'Number']).size().reset_index(name='Goals').sort_values(by='Goals', ascending=False).head(10)
            if not top_goals.empty:
                top_goals.set_index('Player', inplace=True)
                st.table(top_goals)
            
        with col_assists:
            st.markdown("**Top Playmakers (Assists)**")
            top_assists = assists_df.groupby(['Player', 'Number']).size().reset_index(name='Assists').sort_values(by='Assists', ascending=False).head(10)
            if not top_assists.empty:
                top_assists.set_index('Player', inplace=True)
                st.table(top_assists)
            
        with col_points:
            st.markdown("**Top Point Leaders**")
            points_df = df[df['Type'].isin(['Goal', 'Assist'])]
            top_points = points_df.groupby(['Player', 'Number']).size().reset_index(name='Points').sort_values(by='Points', ascending=False).head(10)
            if not top_points.empty:
                top_points.set_index('Player', inplace=True)
                st.table(top_points)

        st.markdown("---")
        st.subheader("📈 Penalty Breakdown")
        if not penalties_df.empty:
            penalty_counts = penalties_df['Infraction'].value_counts().reset_index()
            penalty_counts.columns = ['Infraction', 'Count']
            st.plotly_chart(px.pie(penalty_counts, values='Count', names='Infraction', title="Types of Penalties Called"), use_container_width=True)

            st.markdown("**Most Penalized Players**")
            top_penalties = penalties_df.groupby(['Player', 'Number']).size().reset_index(name='Penalties').sort_values(by='Penalties', ascending=False).head(10)
            if not top_penalties.empty:
                top_penalties.set_index('Player', inplace=True)
                st.table(top_penalties)
