import pandas as pd
import random
from sklearn.ensemble import RandomForestRegressor
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpBinary


def load_data():
    path = "/Users/baggggggg/PycharmProjects/курсач/.venv/ucl_fantasy_modified.csv"
    return pd.read_csv(path)


def train_and_predict(data: pd.DataFrame, target_tour: int) -> pd.DataFrame:
    features = ['goals', 'assists', 'shots', 'tackles', 'minutes']
    target = 'fantasy_points'

    train_data = data[data['round'] < target_tour].copy()
    if train_data.empty:
        raise ValueError(f"Недостаточно данных для обучения на тур {target_tour}")

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(train_data[features], train_data[target])

    predict_data = data[data['round'] == target_tour - 1].copy()
    if predict_data.empty:
        raise ValueError(f"Нет данных для предсказания на тур {target_tour - 1}")

    predict_data['predicted_points'] = model.predict(predict_data[features])
    predict_data['cost'] = predict_data['cost'].fillna(5)
    return predict_data


def generate_team_with_optimization(data: pd.DataFrame, budget: float = 100.0):
    required_counts = {
        'GK': 2,
        'DEF': 4,
        'MID': 5,
        'FWD': 4
    }
    total_players = sum(required_counts.values())

    player_vars = {}
    model = LpProblem("FantasyTeamSelection", LpMaximize)

    for idx, row in data.iterrows():
        var = LpVariable(f"player_{idx}", cat=LpBinary)
        player_vars[idx] = var

    model += lpSum([player_vars[idx] * row['predicted_points'] for idx, row in data.iterrows()])
    model += lpSum([player_vars[idx] * row['cost'] for idx, row in data.iterrows()]) <= budget

    for pos, count in required_counts.items():
        model += lpSum([player_vars[idx] for idx, row in data.iterrows() if row['position'] == pos]) == count

    model += lpSum([player_vars[idx] for idx in data.index]) == total_players
    model.solve()

    selected_rows = []
    total_cost = 0.0

    for idx, var in player_vars.items():
        if var.value() == 1:
            selected_rows.append(data.loc[idx])
            total_cost += data.loc[idx, 'cost']

    return selected_rows, round(total_cost, 2)


def generate_random_team(data: pd.DataFrame, budget: float = 100.0):
    required_counts = {
        'GK': 2,
        'DEF': 4,
        'MID': 5,
        'FWD': 4
    }

    attempt = 0
    while attempt < 1000:
        team = []
        for pos, count in required_counts.items():
            players = data[data['position'] == pos].sample(n=count, replace=False, random_state=random.randint(1, 9999))
            team.extend(players.to_dict('records'))

        total_cost = sum(p['cost'] for p in team)
        if total_cost <= budget:
            return team, round(total_cost, 2)

        attempt += 1

    raise Exception("Не удалось собрать случайную команду с заданным бюджетом.")
