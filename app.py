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
                # --- TABLEAU UNIFIÉ AVEC RANG ET NUMÉRO ---
                st.markdown("**Statistiques Unifiées des Joueurs**")
                
                pivot_df = df_team.groupby(['Player', 'Number', 'Type']).size().unstack(fill_value=0).reset_index()
                
                for col in ['Goal', 'Assist', 'Penalty']:
                    if col not in pivot_df.columns:
                        pivot_df[col] = 0
                        
                pivot_df.rename(columns={'Goal': 'Buts', 'Assist': 'Passes', 'Penalty': 'Pénalités'}, inplace=True)
                pivot_df['Points'] = pivot_df['Buts'] + pivot_df['Passes']
                
                pivot_df = pivot_df[['Player', 'Number', 'Buts', 'Passes', 'Points', 'Pénalités']]
                pivot_df.rename(columns={'Player': 'Joueur', 'Number': 'No'}, inplace=True)
                pivot_df = pivot_df.sort_values(by=['Points', 'Buts'], ascending=False)
                
                pivot_df['Rang'] = range(1, len(pivot_df) + 1)
                pivot_df.set_index('Rang', inplace=True)
                
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
            st.header("📋 Rapport de Dépistage (Scouting Avancé)")
            
            if 'Player_Team' in df.columns:
                teams = [t for t in df['Player_Team'].unique() if pd.notna(t)]
                teams.sort()
                
                col_us, col_them = st.columns(2)
                with col_us:
                    us_team = st.selectbox("Notre Équipe", ["ROYAL OUTAOUAIS"] + [t for t in teams if t != "ROYAL OUTAOUAIS"])
                with col_them:
                    opponent = st.selectbox("Prochain Adversaire", ["Sélectionnez une équipe..."] + [t for t in teams if t != us_team])
                
                if opponent != "Sélectionnez une équipe...":
                    df_opp = df[df['Player_Team'] == opponent]
                    
                    if df_opp.empty:
                        st.info(f"Aucune donnée pour {opponent} jusqu'à présent.")
                    else:
                        st.markdown("---")
                        
                        # 1. PROFONDEUR OFFENSIVE
                        st.subheader("📊 1. Profondeur Offensive (Dépendance)")
                        opp_goals = df_opp[df_opp['Type'] == 'Goal']
                        total_goals = len(opp_goals)
                        if total_goals > 0:
                            top_3_goals = opp_goals.groupby('Player').size().sort_values(ascending=False).head(3).sum()
                            dependency = (top_3_goals / total_goals) * 100
                            st.metric("Dépendance offensive au Top 3", f"{dependency:.1f}%", f"{top_3_goals} buts sur {total_goals} marqués par leurs 3 meilleurs buteurs", delta_color="inverse")
                            if dependency > 60:
                                st.warning("🎯 **Analyse Stratégique :** Cette équipe est très dépendante de ses vedettes. Neutralisez leur premier trio et leur attaque s'effondrera.")
                            else:
                                st.success("🎯 **Analyse Stratégique :** Attaque très équilibrée. Le danger vient de tous les trios, il faudra une défensive hermétique constante.")
                        else:
                            st.info("L'équipe adverse n'a pas encore marqué de but cette saison.")
                        
                        # 2. PROFIL D'INDISCIPLINE
                        st.markdown("---")
                        st.subheader("⚖️ 2. Le Profil d'Indiscipline")
                        opp_pens = df_opp[df_opp['Type'] == 'Penalty']
                        if not opp_pens.empty:
                            profil_pens = opp_pens.groupby(['Player', 'Number', 'Infraction']).size().reset_index(name='Compte').sort_values(by=['Compte', 'Player'], ascending=[False, True])
                            profil_pens.rename(columns={'Player': 'Joueur', 'Number': 'No'}, inplace=True)
                            profil_pens['Rang'] = range(1, len(profil_pens) + 1)
                            profil_pens.set_index('Rang', inplace=True)
                            st.table(profil_pens.head(10))
                        else:
                            st.info("Équipe très disciplinée, aucune pénalité enregistrée.")

                        # 3. VULNÉRABILITÉ DÉFENSIVE
                        st.markdown("---")
                        st.subheader("🚨 3. Vulnérabilité Défensive (Buts Accordés)")
                        opp_games = df[(df['Home_Team'] == opponent) | (df['Away_Team'] == opponent)]['Game_ID'].unique()
                        goals_against = df[(df['Game_ID'].isin(opp_games)) & (df['Player_Team'] != opponent) & (df['Type'] == 'Goal')]
                        
                        if not goals_against.empty:
                            vuln_counts = goals_against['Period'].value_counts().reset_index()
                            vuln_counts.columns = ['Période', 'Buts Accordés']
                            vuln_counts['Période'] = vuln_counts['Période'].astype(str)
                            vuln_counts = vuln_counts.sort_values(by='Période')
                            vuln_counts.set_index('Période', inplace=True)
                            st.table(vuln_counts)
                            
                            worst_period = vuln_counts.idxmax()['Buts Accordés']
                            st.info(f"💡 **À noter :** Ils ont tendance à accorder le plus de buts en **Période {worst_period}**.")
                        else:
                            st.info("Aucun but accordé par cet adversaire jusqu'à présent.")

                        # 4. LA BÊTE NOIRE
                        st.markdown("---")
                        st.subheader(f"⚔️ 4. La Bête Noire (Historique contre {us_team})")
                        h2h_games = df[
                            ((df['Home_Team'] == us_team) & (df['Away_Team'] == opponent)) | 
                            ((df['Home_Team'] == opponent) & (df['Away_Team'] == us_team))
                        ]['Game_ID'].unique()
                        
                        if len(h2h_games) == 0:
                            st.info(f"Aucun affrontement préalable entre {opponent} et {us_team} dans la base de données actuelle.")
                        else:
                            h2h_opp_pts = df[(df['Game_ID'].isin(h2h_games)) & (df['Player_Team'] == opponent) & (df['Type'].isin(['Goal', 'Assist']))]
                            if h2h_opp_pts.empty:
                                st.success(f"Magnifique ! Aucun joueur de {opponent} n'a réussi à récolter de point contre vous cette saison.")
                            else:
                                bete_noire = h2h_opp_pts.groupby(['Player', 'Number', 'Type']).size().unstack(fill_value=0).reset_index()
                                for col in ['Goal', 'Assist']:
                                    if col not in bete_noire.columns: bete_noire[col] = 0
                                bete_noire['Points Contre Nous'] = bete_noire['Goal'] + bete_noire['Assist']
                                bete_noire.rename(columns={'Player': 'Joueur', 'Number': 'No', 'Goal': 'Buts', 'Assist': 'Passes'}, inplace=True)
                                bete_noire = bete_noire[['Joueur', 'No', 'Buts', 'Passes', 'Points Contre Nous']]
                                bete_noire = bete_noire.sort_values(by='Points Contre Nous', ascending=False).head(5)
                                bete_noire['Rang'] = range(1, len(bete_noire) + 1)
                                bete_noire.set_index('Rang', inplace=True)
                                st.table(bete_noire)
