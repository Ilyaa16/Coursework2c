import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from team_selection import load_data, train_and_predict, generate_team_with_optimization, generate_random_team
from collections import defaultdict

captain_name = None
emoji = {'GK': '🧤', 'DEF': '🛡️', 'MID': '🎯', 'FWD': '⚽'}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу тебе собрать Fantasy-состав. Используй команды:\n"
        "/team <тур> <бюджет>\n"
        "/random_vs_optimal <тур> <бюджет>\n"
        "/team_players <название_команды>\n"
        "/set_captain <имя_игрока>\n"
        "/top_scorer <тур>\n"
        "/top_assistant <тур>\n"
        "/player_points <имя_игрока> <тур>"
    )


async def set_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global captain_name
    try:
        if len(context.args) != 2:
            await update.message.reply_text("⚠️ Используй команду в формате: /team <тур> <бюджет>")
            return

        target_tour = int(context.args[0])
        budget = float(context.args[1])

        data = load_data()
        predict_data = train_and_predict(data, target_tour)
        team, total_cost = generate_team_with_optimization(predict_data, budget)

        grouped = defaultdict(list)
        for player in team:
            grouped[player['position']].append(player)

        main_counts = {'GK': 1, 'DEF': 3, 'MID': 4, 'FWD': 3}
        main_squad, bench = [], []

        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            players = sorted(grouped[pos], key=lambda x: -x['predicted_points'])
            main_squad += players[:main_counts[pos]]
            bench += players[main_counts[pos]:]

        total_points = sum(p['predicted_points'] for p in team)

        message = f"🎽 <b>Состав на тур {target_tour}</b> (бюджет: {budget} млн):\n\n"
        message += "<b>🔝 Основной состав:</b>\n"
        for player in main_squad:
            pos = player['position']
            is_captain = "🧢 " if player['player_name'] == captain_name else ""
            message += f"{is_captain}{emoji[pos]} {player['player_name']} ({player['team']}) — {player['predicted_points']:.2f} очков, 💰 {player['cost']} млн\n"

        message += "\n🪑 <b>Запасные игроки:</b>\n"
        for player in bench:
            pos = player['position']
            message += f"{emoji[pos]} {player['player_name']} ({player['team']}) — {player['predicted_points']:.2f} очков, 💰 {player['cost']} млн\n"

        message += f"\n📊 <b>Итоговая стоимость:</b> {total_cost} млн\n"
        message += f"📈 <b>Сумма очков всей команды:</b> {total_points:.2f}"

        await update.message.reply_text(message, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def random_vs_optimal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 2:
            await update.message.reply_text("⚠️ Используй команду в формате: /random_vs_optimal <тур> <бюджет>")
            return

        target_tour = int(context.args[0])
        budget = float(context.args[1])

        data = load_data()
        predict_data = train_and_predict(data, target_tour)

        optimal_team, optimal_cost = generate_team_with_optimization(predict_data, budget)
        optimal_points = sum(p['predicted_points'] for p in optimal_team)

        random_team, random_cost = generate_random_team(predict_data, budget)
        random_points = sum(p['predicted_points'] for p in random_team)

        diff = optimal_points - random_points

        message = f"📊 <b>Сравнение команд на тур {target_tour} (бюджет: {budget} млн)</b>\n\n"
        message += f"✅ <b>Оптимальная команда</b>: {optimal_points:.2f} очков, 💰 {optimal_cost} млн\n"
        message += f"🎲 <b>Случайная команда</b>: {random_points:.2f} очков, 💰 {random_cost} млн\n"
        message += f"\n📉 <b>Разница:</b> {diff:+.2f} очков в пользу оптимальной команды"

        await update.message.reply_text(message, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def team_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Используй: /team_players <название_команды>")
        return

    team_name = " ".join(context.args)
    data = load_data()
    players = data[data['team'].str.lower() == team_name.lower()]['player_name'].unique()

    if len(players) == 0:
        await update.message.reply_text(f"❌ Команда '{team_name}' не найдена.")
        return

    players_list = "\n".join(players)
    await update.message.reply_text(f"📋 Игроки команды <b>{team_name}</b>:\n{players_list}", parse_mode="HTML")


async def set_captain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global captain_name
    if not context.args:
        await update.message.reply_text("⚠️ Используй: /set_captain <имя_игрока>")
        return

    name = " ".join(context.args)
    data = load_data()
    if name not in data['player_name'].values:
        await update.message.reply_text(f"❌ Игрок с именем '{name}' не найден.")
        return

    captain_name = name
    await update.message.reply_text(f"🧢 Капитан установлен: <b>{captain_name}</b>", parse_mode="HTML")


async def top_scorer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not context.args:
        await update.message.reply_text("⚠️ Используй: /top_scorer <тур>")
        return

    tour = int(context.args[0])
    tour_data = data[data['round'] == tour]
    top_players = tour_data.groupby('player_name')['goals'].sum().nlargest(3)

    message = f"⚽ <b>Топ-3 бомбардиров тура {tour}:</b>\n"
    for i, (name, goals) in enumerate(top_players.items(), 1):
        message += f"{i}. {name} — {goals} гол(ов)\n"
    await update.message.reply_text(message, parse_mode="HTML")


async def top_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not context.args:
        await update.message.reply_text("⚠️ Используй: /top_assistant <тур>")
        return

    tour = int(context.args[0])
    tour_data = data[data['round'] == tour]
    top_players = tour_data.groupby('player_name')['assists'].sum().nlargest(3)

    message = f"🎯 <b>Топ-3 ассистента тура {tour}:</b>\n"
    for i, (name, assists) in enumerate(top_players.items(), 1):
        message += f"{i}. {name} — {assists} ассист(ов)\n"
    await update.message.reply_text(message, parse_mode="HTML")


async def player_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Используй: /player_points <имя_игрока> <тур>")
        return

    name = " ".join(context.args[:-1])
    tour = int(context.args[-1])

    data = load_data()
    predict_data = train_and_predict(data, tour)
    player_row = predict_data[predict_data['player_name'].str.lower() == name.lower()]

    if player_row.empty:
        await update.message.reply_text(f"❌ Игрок '{name}' не найден.")
        return

    player = player_row.iloc[0]
    await update.message.reply_text(
        f"📈 <b>{player['player_name']}</b> ожидает {player['predicted_points']:.2f} очков в туре {tour}\n"
        f"Позиция: {player['position']}, Команда: {player['team']}, 💰 {player['cost']} млн",
        parse_mode="HTML"
    )


def main():
    app = Application.builder().token("7611819731:AAHHpINYPDyWi7IQwn-6PqiVVbdFRkjHRkc").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("team", set_team))
    app.add_handler(CommandHandler("random_vs_optimal", random_vs_optimal))
    app.add_handler(CommandHandler("team_players", team_players))
    app.add_handler(CommandHandler("set_captain", set_captain))
    app.add_handler(CommandHandler("top_scorer", top_scorer))
    app.add_handler(CommandHandler("top_assistant", top_assistant))
    app.add_handler(CommandHandler("player_points", player_points))

    app.run_polling()


if __name__ == "__main__":
    main()
