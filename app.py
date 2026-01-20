import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from ortools.sat.python import cp_model
import math
import io

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Logi-Flow Team Balancer", page_icon="⚽", layout="wide")

st.title("⚽ Logi-Flow Japan: Fair Team Allocator")
st.markdown("""
**The Goal:** Upload your player list, and this engine will use **Constraint Programming** to generate perfectly balanced teams based on Age, Skill, and Position.
""")

# --- 2. LOGIC: DATA CLEANING & SCORING ---
def clean_and_score_data(df):
    # Standardize Column Names
    column_mapping = {
        'Full Name': 'name',
        'Date of Birth': 'dob',
        'Primary Playing Position': 'position',
        'Secondary Playing Position (Optional)': 'position_2',
        'Years of Competitive Soccer Experience': 'years_exp', 
        'Please list your previous two competitive teams and the highest level you played (e.g., U17 Premier, High School Varsity)': 'history_text'
    }
    # Rename if columns exist (flexible)
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    # Lowercase everything for safety
    df.columns = df.columns.str.lower()

    cols_to_drop = [c for c in df.columns if 'column' in c or 'unnamed' in c]
    df = df.drop(columns=cols_to_drop, errors='ignore')
    
    # Drop PII
    cols_to_drop = ['timestamp', 'contact email', 'phone number', 'cleaned email']
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors='ignore')

    # Fill NaNs
    df['position_2'] = df['position_2'].fillna('None')
    df['years_exp'] = df['years_exp'].fillna(0)
    
    # Position Normalization
    position_cleanup = {
        'Goalkeeper (GK)': 'GK', 'GK': 'GK',
        'Defender (Left Back/Right Back)': 'DEF', 'Center Back (CB)': 'DEF',
        'Midfielder (Defensive Mid/Center Mid)': 'MID', 'Winger (Left Wing/Right Wing)': 'MID',
        'Forward (Striker/Center Forward)': 'FWD'
    }
    df['position'] = df['position'].map(position_cleanup).fillna(df['position']) # map allows keeping original if not found? No, better use replace logic or careful map
    # Safer replace logic:
    for key, val in position_cleanup.items():
        df.loc[df['position'] == key, 'position'] = val
    df['position'] = df['position'].str.upper()

    # Age Calculation
    def calculate_age(dob):
        try:
            if isinstance(dob, (datetime, pd.Timestamp)):
                birth_date = dob
            else:
                birth_date = pd.to_datetime(dob)
            today = datetime.now()
            return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except:
            return 0 
    
    # Birth Year & Age
    df['age'] = df['dob'].apply(calculate_age)
    df['birth_year'] = df['dob'].apply(lambda x: x.year if isinstance(x, (datetime, pd.Timestamp)) else pd.to_datetime(x).year)

    # Cohort Assignment
    def assign_cohort(year):
        if year <= 2007: return 'Group_2007_Earlier'
        elif 2008 <= year <= 2009: return 'Group_2008_2009'
        else: return 'Group_2010_Plus'
    df['category'] = df['birth_year'].apply(assign_cohort)

    # Skill Calculation
    def calculate_skill(row):
        score = row['years_exp'] * 2
        text = str(row['history_text']).lower()
        if 'premier' in text or 'academy' in text or 'club' in text: score += 50 
        elif 'varsity' in text or 'high school' in text: score += 30 
        elif 'ayso' in text or 'aysa' in text: score += 20
        elif 'jv' in text or 'rec' in text: score += 10 
        else: score += 15 
        return score

    df['skill_score'] = df.apply(calculate_skill, axis=1).astype(int)

    # GHOST INJECTION (The Fix for 2010)
    # Check 2010 GK count
    gks_2010 = df[(df['category'] == 'Group_2010_Plus') & (df['position'] == 'GK')]
    if len(gks_2010) == 1:
        st.warning("👻 Auto-Detected: Only 1 GK in 2010 Group. Injecting 'Ghost GK' to enable matching.")
        ghost = {
            'name': 'GHOST_GK_PLACEHOLDER',
            'dob': datetime(2010, 1, 1),
            'birth_year': 2010,
            'position': 'GK', 'position_2': 'None',
            'years_exp': 3, 'history_text': 'Generated',
            'skill_score': 50,
            'category': 'Group_2010_Plus', 'age': 14
        }
        df = pd.concat([df, pd.DataFrame([ghost])], ignore_index=True)

    return df

# --- 3. LOGIC: THE SOLVER ENGINE (V2) ---
def solve_cohort_v2(cohort_name, df_cohort):
    players = df_cohort.to_dict('records')
    num_players = len(players)
    num_teams = 2 
    all_players = range(num_players)
    all_teams = range(num_teams)
    
    model = cp_model.CpModel()
    x = {}
    
    # Variables
    for p in all_players:
        for t in all_teams:
            x[p, t] = model.NewBoolVar(f'p{p}_t{t}')

    # Constraints
    # 1. One Team per Player
    for p in all_players:
        model.Add(sum(x[p, t] for t in all_teams) == 1)

    # 2. Equal Size
    target = num_players // num_teams
    for t in all_teams:
        model.Add(sum(x[p, t] for p in all_players) >= target)
        model.Add(sum(x[p, t] for p in all_players) <= target + 1)

    # 3. Position Loop
    unique_positions = set(p['position'] for p in players)
    for pos in unique_positions:
        pos_indices = [i for i, p in enumerate(players) if p['position'] == pos]
        count = len(pos_indices)
        min_per_team = count // num_teams
        # Force min per team
        for t in all_teams:
            model.Add(sum(x[p, t] for p in pos_indices) >= min_per_team)
            # Optional: Add Max to prevent hoarding
            model.Add(sum(x[p, t] for p in pos_indices) <= math.ceil(count / num_teams))

    # Objective: Minimize Skill Diff
    t_scores = [sum(players[p]['skill_score'] * x[p, t] for p in all_players) for t in all_teams]
    diff = model.NewIntVar(0, 100000, 'diff')
    model.AddAbsEquality(diff, t_scores[0] - t_scores[1])
    model.Minimize(diff)

    # Solve
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        rosters = {0: [], 1: []}
        for p in all_players:
            for t in all_teams:
                if solver.Value(x[p, t]) == 1:
                    player_data = players[p]
                    player_data['Assigned_Team'] = f"{cohort_name}_Team_{t+1}"
                    rosters[t].append(player_data)
        return rosters, solver.Value(diff)
    else:
        return None, None

# --- 4. THE UI ---
uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])

if uploaded_file:
    # A. Process Data
    raw_df = pd.read_excel(uploaded_file, engine='openpyxl')
    st.write(f"✅ Loaded {len(raw_df)} rows.")
    
    with st.spinner("Cleaning & Scoring Data..."):
        df = clean_and_score_data(raw_df)
    
    st.dataframe(df.head())

    # B. Optimize Button
    if st.button("🚀 Optimize Teams"):
        final_roster = []
        
        # Tabs for result display
        cohorts = sorted(df['category'].unique())
        tabs = st.tabs(cohorts)
        
        for i, cohort in enumerate(cohorts):
            with tabs[i]:
                cohort_data = df[df['category'] == cohort].copy()
                st.subheader(f"Analyzing: {cohort}")
                
                # Check Inventory
                inventory = cohort_data['position'].value_counts()
                st.text("Player Pool:")
                st.write(inventory.to_dict())
                
                # Run Solver
                result, skill_diff = solve_cohort_v2(cohort, cohort_data)
                
                if result:
                    st.success(f"✅ Optimized! Skill Difference: {skill_diff}")
                    
                    # Flatten for this cohort
                    cohort_final = []
                    for t_id in result:
                        cohort_final.extend(result[t_id])
                    
                    c_df = pd.DataFrame(cohort_final)
                    final_roster.extend(cohort_final)
                    
                    # Visuals
                    col1, col2 = st.columns(2)
                    
                    # Chart 1: Structure
                    fig1 = plt.figure(figsize=(6, 4))
                    sns.countplot(data=c_df, x='position', hue='Assigned_Team', palette='viridis')
                    plt.title("Position Balance")
                    col1.pyplot(fig1)
                    
                    # Chart 2: Skill
                    fig2 = plt.figure(figsize=(6, 4))
                    sns.boxplot(data=c_df, x='Assigned_Team', y='skill_score', palette='coolwarm')
                    plt.title("Skill Distribution")
                    col2.pyplot(fig2)
                    
                    st.dataframe(c_df[['name', 'Assigned_Team', 'position', 'skill_score']])
                    
                else:
                    st.error("❌ No Feasible Solution. Check constraints (e.g., trying to split 1 player).")

        # C. Download Final
        if final_roster:
            final_df = pd.DataFrame(final_roster)
            final_df = final_df.sort_values(['category', 'Assigned_Team', 'position'])
            
            # Create Excel in Memory
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                final_df.to_excel(writer, index=False, sheet_name='Balanced_Teams')
                
            st.download_button(
                label="📥 Download Final Excel",
                data=buffer,
                file_name="Logi_Flow_Final_Teams.xlsx",
                mime="application/vnd.ms-excel"
            )