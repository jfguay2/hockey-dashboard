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

# Formateur de nom "Joueur #Numéro"
def format_name(row):
    try:
        if pd.notna(row['Number']) and str(row['Number']).strip() != '':
            return f"{row['Player']} #{int(float(row['Number']))}"
    except:
        pass
    return str(row['Player'])

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
                
                # Appliquer le format "Nom #Numéro"
                pivot_df['Joueur'] = pivot_df.apply(format_name, axis=1)
                
                pivot_df = pivot_df[['Joueur', 'Équipe', 'Buts', 'Passes', 'Points', 'Pénalités']]
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
        # --- SÉCURITÉ ONGLET SCOUT (MULTI-USERS) ---
        def check_scout_login():
            if st.session_state.get("scout_logged_in"):
                st.sidebar.success(f"👤 Coach connecté : {st.session_state['scout_username']}")
                return True
            
            st.markdown("### 🔐 Portail des Entraîneurs")
            col1, col2 = st.columns(2)
            with col1:
                user = st.text_input("Nom d'utilisateur :")
            with col2:
                pwd = st.text_input("Mot de passe :", type="password")
                
            # Dictionnaire des entraîneurs autorisés
            valid_users = {
                "JFG": "Royal142",
                "Coach2": "Defense99",
                "Admin": "Hockey2026"
            }
            
            if st.button("Se connecter"):
                if user in valid_users and valid_users[user] == pwd:
                    st.session_state["scout_logged_in"] = True
                    st.session_state["scout_username"] = user
                    st.rerun()
                else:
                    st.error("Identifiants incorrects.")
            return False

        if check_scout_login():
            import datetime
            def log_ai_query(username, opponent):
                with open("ai_scouting_logs.txt", "a", encoding="utf-8") as f:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] Coach: {username} a généré un rapport IA pour: {opponent}\n")
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
                            
                            st.markdown("**Leurs principales menaces (Top 10) :**")
                            opp_pts = df_opp[df_opp['Type'].isin(['Goal', 'Assist'])]
                            if not opp_pts.empty:
                                pts_df = opp_pts.groupby(['Player', 'Number', 'Type']).size().unstack(fill_value=0).reset_index()
                                for col in ['Goal', 'Assist']:
                                    if col not in pts_df.columns: pts_df[col] = 0
                                pts_df['Points'] = pts_df['Goal'] + pts_df['Assist']
                                pts_df.rename(columns={'Goal': 'Buts', 'Assist': 'Passes'}, inplace=True)
                                pts_df['Joueur'] = pts_df.apply(format_name, axis=1)
                                pts_df = pts_df[['Joueur', 'Buts', 'Passes', 'Points']].sort_values(by=['Points', 'Buts'], ascending=False).head(10)
                                pts_df['Rang'] = range(1, len(pts_df) + 1)
                                pts_df.set_index('Rang', inplace=True)
                                st.table(pts_df)
                            
                                # Analyse dynamique
                                top_player = pts_df.iloc[0]
                                second_player_pts = pts_df.iloc[1]['Points'] if len(pts_df) > 1 else 0
                                
                                if top_player['Points'] >= (second_player_pts * 2) and top_player['Points'] >= 4:
                                    st.error(f"🚨 **Analyse Stratégique :** Attention absolue à **{top_player['Joueur']}** ! Il génère seul une énorme portion de leur offensive. Ne lui donnez aucun espace sur la glace.")
                                elif dependency > 60:
                                    st.warning("🎯 **Analyse Stratégique :** Équipe très dépendante d'un noyau restreint de joueurs. Concentrez votre défensive sur leurs meilleurs compteurs pour freiner leur attaque.")
                                elif dependency < 35 and len(pts_df) >= 5:
                                    st.success("🛡️ **Analyse Stratégique :** Production offensive très bien répartie parmi plusieurs joueurs. Aucune cible unique à isoler, il faudra jouer un système défensif global.")
                                else:
                                    st.info("🎯 **Analyse Stratégique :** La production est dans la moyenne de la ligue. Gardez un œil attentif sur leurs meneurs offensifs.")
                        else:
                            st.info("L'équipe adverse n'a pas encore marqué de but cette saison.")
                        
                        # --- MOMENTUM ---
                        st.markdown("---")
                        st.subheader("🔥 Le Momentum (Leurs 60 dernières minutes)")
                        opp_all_games = df[(df['Home_Team'] == opponent) | (df['Away_Team'] == opponent)][['Game_ID', 'Date']].drop_duplicates()
                        if not opp_all_games.empty:
                            opp_all_games['Date_DT'] = pd.to_datetime(opp_all_games['Date'])
                            last_game_row = opp_all_games.sort_values(by='Date_DT', ascending=False).iloc[0]
                            last_game_id = last_game_row['Game_ID']
                            last_game_date = last_game_row['Date']
                            last_game_opp_df = df_opp[df_opp['Game_ID'] == last_game_id]
                            game_info = df[df['Game_ID'] == last_game_id].iloc[0]
                            vs_team = game_info['Away_Team'] if game_info['Home_Team'] == opponent else game_info['Home_Team']
                            last_game_goals = last_game_opp_df[last_game_opp_df['Type'] == 'Goal']
                            goals_for = len(last_game_goals)
                            goals_against = len(df[(df['Game_ID'] == last_game_id) & (df['Player_Team'] == vs_team) & (df['Type'] == 'Goal')])
                            
                            st.write(f"**Dernier match :** Joué le {last_game_date} contre **{vs_team}** (Score final: {opponent} {goals_for} - {goals_against} {vs_team})")
                            
                            if goals_for > 0:
                                st.markdown("**Joueurs en feu (Points lors de ce match) :**")
                                lg_pts = last_game_opp_df[last_game_opp_df['Type'].isin(['Goal', 'Assist'])]
                                if not lg_pts.empty:
                                    lg_pts_df = lg_pts.groupby(['Player', 'Number', 'Type']).size().unstack(fill_value=0).reset_index()
                                    for col in ['Goal', 'Assist']:
                                        if col not in lg_pts_df.columns: lg_pts_df[col] = 0
                                    lg_pts_df['Points'] = lg_pts_df['Goal'] + lg_pts_df['Assist']
                                    lg_pts_df['Joueur'] = lg_pts_df.apply(format_name, axis=1)
                                    lg_pts_df = lg_pts_df[['Joueur', 'Goal', 'Assist', 'Points']].sort_values(by=['Points', 'Goal'], ascending=False).head(5)
                                    lg_pts_df.rename(columns={'Goal': 'Buts', 'Assist': 'Passes'}, inplace=True)
                                    lg_pts_df['Rang'] = range(1, len(lg_pts_df) + 1)
                                    lg_pts_df.set_index('Rang', inplace=True)
                                    st.table(lg_pts_df)
                                    
                                    top_hot = lg_pts_df.iloc[0]
                                    if top_hot['Points'] >= 3:
                                        st.warning(f"⚠️ **Attention :** {top_hot['Joueur']} a connu un match monstre récemment avec {top_hot['Points']} points. Il est en pleine confiance, surveillez-le de près.")
                            else:
                                st.info("Ils ont été blanchis lors de leur dernier match. Attendez-vous à une équipe désespérée de rebondir offensivement.")
                        else:
                            st.info("Aucun match enregistré pour cette équipe.")
                        
                        # 2. PROFIL D'INDISCIPLINE
                        st.markdown("---")
                        st.subheader("⚖️ 2. Le Profil d'Indiscipline")
                        opp_pens = df_opp[df_opp['Type'] == 'Penalty']
                        if not opp_pens.empty:
                            profil_pens = opp_pens.groupby(['Player', 'Number', 'Infraction']).size().reset_index(name='Compte').sort_values(by=['Compte', 'Player'], ascending=[False, True])
                            profil_pens['Joueur'] = profil_pens.apply(format_name, axis=1)
                            profil_pens = profil_pens[['Joueur', 'Infraction', 'Compte']]
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

                        # --- PERFORMANCE CONTRE LE TOP TIERS ---
                        st.markdown("---")
                        st.subheader("🏆 Performance contre les Puissances (Top 3)")
                        
                        # Calcul rapide du classement
                        team_points = {t: 0 for t in teams}
                        all_games = df['Game_ID'].unique()
                        for gid in all_games:
                            g_data = df[df['Game_ID'] == gid]
                            if not g_data.empty:
                                home_t = g_data.iloc[0]['Home_Team']
                                away_t = g_data.iloc[0]['Away_Team']
                                if home_t in teams and away_t in teams:
                                    home_goals = len(g_data[(g_data['Player_Team'] == home_t) & (g_data['Type'] == 'Goal')])
                                    away_goals = len(g_data[(g_data['Player_Team'] == away_t) & (g_data['Type'] == 'Goal')])
                                    if home_goals > away_goals: team_points[home_t] += 2
                                    elif away_goals > home_goals: team_points[away_t] += 2
                                    else:
                                        team_points[home_t] += 1
                                        team_points[away_t] += 1
                                        
                        sorted_teams = sorted(team_points.items(), key=lambda x: x[1], reverse=True)
                        top_tier_teams = [t[0] for t in sorted_teams[:3] if pd.notna(t[0])]
                        
                        top_tier_filtered = [t for t in top_tier_teams if t != opponent]
                        
                        if opponent in top_tier_teams:
                            st.write(f"💡 *{opponent} fait lui-même partie du Top 3 de la ligue.*")
                            
                        if len(top_tier_filtered) > 0:
                            opp_games_vs_top = df[((df['Home_Team'] == opponent) & (df['Away_Team'].isin(top_tier_filtered))) | 
                                                  ((df['Away_Team'] == opponent) & (df['Home_Team'].isin(top_tier_filtered)))]['Game_ID'].unique()
                            
                            if len(opp_games_vs_top) == 0:
                                st.info(f"Ils n'ont pas encore affronté les puissances de la ligue ({', '.join(top_tier_filtered)}).")
                            else:
                                w, l, t_tie = 0, 0, 0
                                for gid in opp_games_vs_top:
                                    g_data = df[df['Game_ID'] == gid]
                                    gf = len(g_data[(g_data['Player_Team'] == opponent) & (g_data['Type'] == 'Goal')])
                                    ga = len(g_data[(g_data['Player_Team'] != opponent) & (g_data['Type'] == 'Goal')])
                                    if gf > ga: w += 1
                                    elif ga > gf: l += 1
                                    else: t_tie += 1
                                
                                st.write(f"**Fiche contre le Top Tier ({', '.join(top_tier_filtered)}) :** {w} Victoires - {l} Défaites - {t_tie} Nuls")
                                
                                win_pct = (w + (t_tie*0.5)) / len(opp_games_vs_top)
                                if win_pct >= 0.55:
                                    st.error("🚨 **Alerte :** Cette équipe hausse son niveau de jeu contre les gros clubs de la ligue. Prenez-les extrêmement au sérieux.")
                                elif win_pct <= 0.35:
                                    st.success("🎯 **Opportunité :** Ils s'écroulent contre les bonnes équipes. Un jeu rapide et intense en début de match pourrait les casser mentalement.")
                                else:
                                    st.info("Ils se maintiennent de façon moyenne contre les meilleures équipes.")

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
                                bete_noire.rename(columns={'Goal': 'Buts', 'Assist': 'Passes'}, inplace=True)
                                
                                bete_noire['Joueur'] = bete_noire.apply(format_name, axis=1)
                                bete_noire = bete_noire[['Joueur', 'Buts', 'Passes', 'Points Contre Nous']]
                                
                                bete_noire = bete_noire.sort_values(by='Points Contre Nous', ascending=False).head(5)
                                bete_noire['Rang'] = range(1, len(bete_noire) + 1)
                                bete_noire.set_index('Rang', inplace=True)
                                st.table(bete_noire)
                        # --- ANTIGRAVITY AI SCOUTING ---
                        st.markdown("---")
                        st.subheader("🤖 Analyse Stratégique par IA (Antigravity)")
                        if st.button("Générer le rapport IA détaillé pour " + opponent):
                            log_ai_query(st.session_state['scout_username'], opponent)
                            with st.spinner("L'IA Antigravity analyse les statistiques locales en direct..."):
                                try:
                                    import asyncio
                                    from google.antigravity import Agent, LocalAgentConfig
                                    
                                    async def run_ai():
                                        async with Agent(LocalAgentConfig()) as agent:
                                            prompt = f"Tu es un entraîneur adjoint de hockey professionnel. Voici les stats de notre adversaire ({opponent}) :\n\n- Attaque:\n{df_opp[df_opp['Type'].isin(['Goal', 'Assist'])].to_dict()}\n\n- Pénalités:\n{df_opp[df_opp['Type'] == 'Penalty'].to_dict()}\n\nÉcris un rapport de dépistage ultra-percutant, liste les 3 joueurs clés à surveiller, et propose un plan de match pour les neutraliser."
                                            response = await agent.chat(prompt)
                                            return response.text
                                            
                                    ai_response = asyncio.run(run_ai())
                                    st.success("Analyse générée avec succès !")
                                    st.write(ai_response)
                                except Exception as e:
                                    st.error(f"Erreur de connexion à l'IA locale Antigravity : {e}")
