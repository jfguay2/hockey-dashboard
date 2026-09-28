import streamlit as st
import pandas as pd
import plotly.express as px
import subprocess
import os

st.set_page_config(page_title="Spordle Hockey Stats Dashboard", layout="wide")

st.title("🏒 Outaouais AA Regional Hockey Stats")

@st.cache_data
def load_data():
    if os.path.exists('league_stats.csv'):
        df = pd.read_csv('league_stats.csv')
        return df
    return pd.DataFrame()

# Sidebar for controls
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
    # Get unique teams to filter
    teams = pd.concat([df['Home_Team'], df['Away_Team']]).unique()
    teams = [t for t in teams if pd.notna(t)]
    teams.sort()
    
    selected_team = st.sidebar.selectbox("Filter by Team", ["All Teams"] + list(teams))
    
    # Filter data based on selection
    if selected_team != "All Teams":
        df = df[(df['Home_Team'] == selected_team) | (df['Away_Team'] == selected_team)]
        st.subheader(f"Stats for games involving: {selected_team}")
    else:
        st.subheader("League Wide Stats")

    # Metrics
    goals_df = df[df['Type'] == 'Goal']
    assists_df = df[df['Type'] == 'Assist']
    penalties_df = df[df['Type'] == 'Penalty']
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Games Played", df['Game_ID'].nunique())
    col2.metric("Total Goals Scored", len(goals_df))
    col3.metric("Total Assists", len(assists_df))
    col4.metric("Total Penalties", len(penalties_df))
    
    st.markdown("---")
    
    # Leaderboards
    st.subheader("🏆 Player Leaderboards")
    
    col_goals, col_assists, col_points = st.columns(3)
    
    with col_goals:
        st.markdown("**Top Goal Scorers**")
        top_goals = goals_df.groupby(['Player', 'Number']).size().reset_index(name='Goals')
        top_goals = top_goals.sort_values(by='Goals', ascending=False).head(10)
        top_goals.set_index('Player', inplace=True)
        st.table(top_goals)
        
    with col_assists:
        st.markdown("**Top Playmakers (Assists)**")
        top_assists = assists_df.groupby(['Player', 'Number']).size().reset_index(name='Assists')
        top_assists = top_assists.sort_values(by='Assists', ascending=False).head(10)
        top_assists.set_index('Player', inplace=True)
        st.table(top_assists)
        
    with col_points:
        st.markdown("**Top Point Leaders**")
        points_df = df[df['Type'].isin(['Goal', 'Assist'])]
        top_points = points_df.groupby(['Player', 'Number']).size().reset_index(name='Points')
        top_points = top_points.sort_values(by='Points', ascending=False).head(10)
        top_points.set_index('Player', inplace=True)
        st.table(top_points)

    st.markdown("---")
    
    # Visualizations
    st.subheader("📈 Penalty Breakdown")
    if not penalties_df.empty:
        penalty_counts = penalties_df['Infraction'].value_counts().reset_index()
        penalty_counts.columns = ['Infraction', 'Count']
        fig = px.pie(penalty_counts, values='Count', names='Infraction', title="Types of Penalties Called")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Most Penalized Players**")
        top_penalties = penalties_df.groupby(['Player', 'Number']).size().reset_index(name='Penalties')
        top_penalties = top_penalties.sort_values(by='Penalties', ascending=False).head(10)
        top_penalties.set_index('Player', inplace=True)
        st.table(top_penalties)
        
    st.markdown("---")
    st.subheader("Raw Data Feed")
    st.dataframe(df.sort_values(by=['Date', 'Game_ID'], ascending=False), use_container_width=True)
