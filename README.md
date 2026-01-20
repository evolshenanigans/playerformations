# ⚽ Logi-Flow: Fair Team Optimization Engine

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://YOUR_STREAMLIT_APP_URL_HERE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![OR-Tools](https://img.shields.io/badge/Solver-Google%20OR--Tools-red)](https://developers.google.com/optimization)

### 🚀 Live Demo
**[Click here to try the App](https://playerformations.streamlit.app/)** *(Note: No real player data is stored. Upload your own Excel file to test.)*

---

## 🧐 The Problem
Youth sports leagues often face a logistical nightmare: manually sorting hundreds of players into teams. 
* **The Constraint:** Teams must be balanced by skill level.
* **The Bottleneck:** Every team needs exactly one Goalkeeper (GK).
* **The Reality:** "Park Soccer" data is messy, with inconsistent text inputs and missing values.

Manual sorting takes hours and often results in lopsided games (10-0 blowouts) or invalid rosters (no Goalkeeper).

## 💡 The Solution
I built a **Logistic Optimization Engine** using **Constraint Programming (CP)**. 
Instead of guessing, the engine uses the **Google OR-Tools** solver to mathematically guarantee the "Fairness" of the roster.

### Key Features
* **Automated Data Cleaning:** Normalizes messy inputs (e.g., "Left Back", "LB", "Defender") into standard positions.
* **Skill Scoring Algorithm:** assigning weighted points based on experience (Varsity vs. Rec) and history text.
* **Dynamic "Ghost" Injection:** Automatically detects if a cohort has an odd number of Goalkeepers and injects a "Placeholder" to allow the solver to function.
* **The "Fair-Partition" Algorithm:** * **Objective:** Minimize the difference in Total Skill Score between Team A and Team B.
    * **Constraint 1:** Every player must be on exactly one team.
    * **Constraint 2:** Every team must have exactly 1 Goalkeeper.
    * **Constraint 3:** Position Parity (Defenders/Midfielders must be distributed evenly).

## 🛠️ Tech Stack
* **Frontend:** Streamlit (Web Interface)
* **Backend:** Python
* **Optimization:** Google OR-Tools (CP-SAT Solver)
* **Data Processing:** Pandas, NumPy
* **Visualization:** Matplotlib, Seaborn

### 1. Structural Balance Check
*Ensuring every team has the right number of Defenders and Forwards.*
<img width="861" height="630" alt="image" src="https://github.com/user-attachments/assets/c7b664ab-5920-4032-b090-ebbbc96e3fca" />


### 2. Skill Parity Check
*Proving that the teams have equal average skill levels.*
<img width="852" height="619" alt="image" src="https://github.com/user-attachments/assets/7a6749ff-3313-4d34-98f9-89a99c07de31" />


---

## 💻 How to Run Locally

1. **Clone the repo**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/soccer-team-balancer.git](https://github.com/YOUR_USERNAME/soccer-team-balancer.git)
   cd soccer-team-balancer
