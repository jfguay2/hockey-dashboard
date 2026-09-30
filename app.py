import streamlit as st
import pandas as pd
import plotly.express as px
import subprocess
import os

st.set_page_config(page_title="Spordle Hockey Stats Dashboard", layout="wide")
st.title("🏒 Outaouais AA Regional Hockey Stats")

# --- SÉCURITÉ PRINCIPALE ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "hockey2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 Entrez le mot de passe de l'équipe pour accéder :", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 Entrez le mot de passe de l'équipe pour accéder :", type="password", on_change=password_entered, key="password")
        st.error("😕 Mot de passe incorrect.")
        return False
    return True

if not check_password():
    st.stop()
# ----------------------

@st.cache_data
def load_data():
    if os.path.exists('league_stats.csv'):
        return pd.read_csv('league_stats.csv')
    return pd.DataFrame()

st.sidebar.header("Commandes")

if st.sidebar.button("🔄 Rafraîchir les données"):
    with st.spinner("Téléchargement des derniers matchs..."):
        subprocess.run(["python", "scraper.py"])
        st.cache_data.clear()
        st.success("Données mises à jour !")

df_full = load_data()

if df_full.empty:
    st.warning("Aucune donnée. Cliquez sur 'Rafraîchir les données'.")
else:
    categories = [c for c in df_full['Category'].unique() if pd.notna(c)]
    categories.sort()
    selected_category = st.sidebar.selectbox("Filtre par Catégorie", ["Toutes les catégories"] + list(categories))
    
    if selected_category != "Toutes les catégories":
        df = df_full[df_full['Category'] == selected_category]
    else:
        df = df_full

    tab1, tab2 = st.tabs(["📊 Statistiques de l'Équipe", "📋 Rapport de Dépistage (Coaches)"])

    with tab1:
        if 'Player_Team' not in df.columns:
            st.warning("⚠️ Veuillez rafraîchir les données.")
        else:
            teams = [t for t in df['Player_Team'].unique() if pd.notna(t)]
            teams.sort()
            selected_team = st.selectbox("Filtre par Équipe", ["Toutes les équipes"] + list(teams))
            
            if selected_team != "Toutes les équipes":
                df_team = df[df['Player_Team'] == selected_team]
                st.subheader(f"Statistiques pour : {selected_team}")
            else:
                df_team = df
                st.subheader("Statistiques de la Ligue")

            if not df_team.empty:
                # --- TABLEAU UNIFIÉ ---
                st.markdown("**Statistiques Unifiées des Joueurs**")
                
                pivot_df = df_team.groupby(['Player', 'Number', 'Player_Team', 'Type']).size().unstack(fill_value=0).reset_index()
                
                for col in ['Goal', 'Assist', 'Penalty']:
                    if col not in pivot_df.columns:
                        pivot_df[col] = 0
                        
                pivot_df.rename(columns={'Goal': 'Buts', 'Assist': 'Passes', 'Penalty': 'Pénalités', 'Player_Team': 'Équipe'}, inplace=True)
                pivot_df['Points'] = pivot_df['Buts'] + pivot_df['Passes']
                
                pivot_df = pivot_df[['Player', 'Number', 'Équipe', 'Buts', 'Passes', 'Points', 'Pénalités']]
                pivot_df = pivot_df.sort_values(by=['Points', 'Buts'], ascending=False)
                pivot_df.set_index('Player', inplace=True)
                st.table(pivot_df)

                # --- STATS D'ÉQUIPE ---
                st.markdown("---")
                st.subheader("🥅 Statistiques d'Équipe (Défensive)")
                
                if selected_team != "Toutes les équipes":
                    team_games = df[(df['Home_Team'] == selected_team) | (df['Away_Team'] == selected_team)]['Game_ID'].unique()
                    g_against = 0
                    wins = 0
                    losses = 0
                    ties = 0
                    shutouts = 0
                    
                    for gid in team_games:
                        game_data = df[df['Game_ID'] == gid]
                        gf = len(game_data[(game_data['Player_Team'] == selected_team) & (game_data['Type'] == 'Goal')])
                        ga = len(game_data[(game_data['Player_Team'] != selected_team) & (game_data['Type'] == 'Goal')])
                        
                        g_against += ga
                        if ga == 0: shutouts += 1
                        
                        if gf > ga: wins += 1
                        elif ga > gf: losses += 1
                        else: ties += 1
                        
                    goalie_data = {
                        "Matchs Joués": [len(team_games)],
                        "Victoires": [wins],
                        "Défaites": [losses],
                        "Nuls": [ties],
                        "Buts Accordés": [g_against],
                        "Blanchissages": [shutouts]
                    }
                    st.table(pd.DataFrame(goalie_data))

    with tab2:
        # --- SÉCURITÉ ONGLET SCOUT ---
        def check_scout_password():
            if st.session_state.get("scout_pw") == "Royal142":
                return True
            pw = st.text_input("🔒 Mot de passe des entraîneurs (Scout) :", type="password", key="scout_pw_input")
            if pw == "Royal142":
                st.session_state["scout_pw"] = "Royal142"
                st.rerun()
            elif pw:
                st.error("Mot de passe incorrect.")
            return False

        if check_scout_password():
            st.header("📋 Rapport de Dépistage d'Avant-Match")
            st.markdown("Sélectionnez le **prochain adversaire**.")
            
            if 'Player_Team' in df.columns:
                teams = [t for t in df['Player_Team'].unique() if pd.notna(t)]
                teams.sort()
                opponent = st.selectbox("Prochain Adversaire", ["Sélectionnez une équipe..."] + list(teams))
                
                if opponent != "Sélectionnez une équipe...":
                    df_opp = df[df['Player_Team'] == opponent]
                    if df_opp.empty:
                        st.info(f"Aucune donnée pour {opponent}.")
                    else:
                        c1, c2, c3 = st.columns(3)
                        opp_goals = df_opp[df_opp['Type'] == 'Goal']
                        opp_pens = df_opp[df_opp['Type'] == 'Penalty']
                        
                        with c1:
                            st.markdown("**⚠️ Menaces Offensives**")
                            pts = df_opp[df_opp['Type'].isin(['Goal', 'Assist'])].groupby(['Player', 'Number']).size().reset_index(name='Pts').sort_values(by='Pts', ascending=False).head(5)
                            if not pts.empty:
                                pts.set_index('Player', inplace=True)
                                st.table(pts)
                                
                        with c2:
                            st.markdown("**⚖️ Indisciplinés**")
                            pens = opp_pens.groupby(['Player', 'Number']).size().reset_index(name='Pénalités').sort_values(by='Pénalités', ascending=False).head(5)
                            if not pens.empty:
                                pens.set_index('Player', inplace=True)
                                st.table(pens)
                                
                        with c3:
                            st.markdown("**⏱️ Buts par Période**")
                            if not opp_goals.empty:
                                per_counts = opp_goals['Period'].value_counts().reset_index()
                                per_counts.columns = ['Période', 'Buts']
                                per_counts['Période'] = per_counts['Période'].astype(str)
                                per_counts = per_counts.sort_values(by='Période')
                                per_counts.set_index('Période', inplace=True)
                                st.table(per_counts)
