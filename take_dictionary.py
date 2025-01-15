import random
import os
import sqlite3
import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import messagebox, simpledialog
import subprocess
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import pytz

# データベース接続
conn = sqlite3.connect('leaderboard.db')
c = conn.cursor()

# テーブル作成
c.execute('''CREATE TABLE IF NOT EXISTS leaderboard (
    username TEXT PRIMARY KEY,
    score INTEGER DEFAULT 0,
    words_looked_up INTEGER DEFAULT 0,
    flashcards_used INTEGER DEFAULT 0,
    quizzes_done INTEGER DEFAULT 0,
    activity_date TEXT DEFAULT CURRENT_TIMESTAMP
)''')

# ユーザーのアクティビティを記録するための新しいテーブルを作成
c.execute('''CREATE TABLE IF NOT EXISTS user_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    activity TEXT,
    activity_date TEXT DEFAULT CURRENT_TIMESTAMP
)''')

conn.commit()

# Merriam-Websterから単語の定義を取得する関数
def get_merriam_webster_definition(word):
    try:
        url = f"https://www.merriam-webster.com/dictionary/{word.replace(' ', '-')}"

        response = requests.get(url)
        response.raise_for_status()
        definitions = []
        soup = BeautifulSoup(response.text, 'html.parser')
        definitions = [definition.get_text(strip=True) for definition in soup.find_all('span', class_='dtText')]
        if not definitions:
            return None  # 定義が取得できなかった場合
        return definitions
    except requests.exceptions.RequestException as e:
        print(f"Error fetching definition for {word}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# 単語や熟語の定義を取得する関数
def get_definition(word):
    definitions = get_merriam_webster_definition(word)
    return definitions

# 学習した単語をファイルから読み込む
def load_learned_words(filename='learned_words.txt'):
    if not os.path.exists(filename):
        return []
    with open(filename, 'r') as f:
        return [line.strip() for line in f.readlines()]

# 学習した単語を保存
def save_word(word, definition):
    with open('learned_words.txt', 'a') as f:
        f.write(f"{word}:{definition}\n")  # 定義も一緒に保存

# フラッシュカードを起動する関数
def start_flashcards():
    subprocess.Popen(['python3', 'take_flashcard.py'])  # フラッシュカードシステムの実行
    update_user_activity(username_entry.get(), 'flashcards_used')  # フラッシュカード使用数を更新

# クイズ機能を実装
def start_quiz():
    username = username_entry.get()
    learned_words = load_learned_words()
    if not learned_words:
        messagebox.showinfo("Info", "No learned words found.")
        return

    # 定義をランダムに選ぶ
    word_definition_pairs = []
    for pair in learned_words:
        word, definition = pair.split(':', 1)
        word_definition_pairs.append((word, definition))

    chosen_word, chosen_definition = random.choice(word_definition_pairs)

    # 定義を表示してユーザーに回答を求める
    user_answer = simpledialog.askstring("Quiz", f"What word does the following definition describe?\n\n{chosen_definition}")

    if user_answer:
        if user_answer.strip().lower() == chosen_word.lower():
            messagebox.showinfo("Quiz Result", "Correct! 🎉")
            update_leaderboard(username, 1)  # 正解したらスコアを1加算
            update_user_activity(username, 'quizzes_done')  # クイズ数を更新
        else:
            messagebox.showinfo("Quiz Result", f"Wrong! The correct answer was '{chosen_word}'.")
    else:
        messagebox.showinfo("Info", "You did not enter an answer.")

# ユーザーのアクティビティを更新
def update_user_activity(username, activity):
    # 新しいアクティビティレコードを挿入
    c.execute("INSERT INTO user_activity (username, activity) VALUES (?, ?)", (username, activity))

    if activity == 'words_looked_up':
        c.execute("UPDATE leaderboard SET words_looked_up = words_looked_up + 1 WHERE username = ?", (username,))
    elif activity == 'flashcards_used':
        c.execute("UPDATE leaderboard SET flashcards_used = flashcards_used + 1 WHERE username = ?", (username,))
    elif activity == 'quizzes_done':
        c.execute("UPDATE leaderboard SET quizzes_done = quizzes_done + 1 WHERE username = ?", (username,))

    conn.commit()

# リーダーボードを更新する関数
def update_leaderboard(username, score_increment):
    # ユーザーのスコアを更新
    c.execute("INSERT INTO leaderboard (username, score) VALUES (?, ?) ON CONFLICT(username) DO UPDATE SET score = score + ?",
              (username, score_increment, score_increment))
    conn.commit()

# アクティビティを日別に集計する関数
def get_daily_activity(username):
    # 日本時間を取得
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    today = now.strftime('%Y-%m-%d')  # 今日の日付を取得

    c.execute('''SELECT activity, DATE(activity_date, 'localtime'), COUNT(*)
                 FROM user_activity
                 WHERE username = ?
                 GROUP BY activity, DATE(activity_date, 'localtime')''', (username,))
    return c.fetchall()

# 日別アクティビティの可視化
def visualize_daily_activity(username):
    daily_activity = get_daily_activity(username)

    if not daily_activity:
        messagebox.showinfo("Info", f"No daily activity data found for {username}.")
        return

    # 日付ごとのカウントを集計
    activity_counts = {}
    for activity, date, count in daily_activity:
        if date not in activity_counts:
            activity_counts[date] = {'words_looked_up': 0, 'flashcards_used': 0, 'quizzes_done': 0}
        activity_counts[date][activity] += count

    # データをプロットする
    dates = list(activity_counts.keys())
    words_looked_up_counts = [activity_counts[date]['words_looked_up'] for date in dates]
    flashcards_used_counts = [activity_counts[date]['flashcards_used'] for date in dates]
    quizzes_done_counts = [activity_counts[date]['quizzes_done'] for date in dates]

    bar_width = 0.25
    x = np.arange(len(dates))

    plt.figure(figsize=(10, 6))
    plt.bar(x - bar_width, words_looked_up_counts, width=bar_width, label='Words Looked Up', color='blue')
    plt.bar(x, flashcards_used_counts, width=bar_width, label='Flashcards Used', color='orange')
    plt.bar(x + bar_width, quizzes_done_counts, width=bar_width, label='Quizzes Done', color='green')

    # 各バーの上に数値を表示
    for i in range(len(dates)):
        plt.text(x[i] - bar_width, words_looked_up_counts[i], str(words_looked_up_counts[i]), ha='center', va='bottom', fontsize=9, color='blue')
        plt.text(x[i], flashcards_used_counts[i], str(flashcards_used_counts[i]), ha='center', va='bottom', fontsize=9, color='orange')
        plt.text(x[i] + bar_width, quizzes_done_counts[i], str(quizzes_done_counts[i]), ha='center', va='bottom', fontsize=9, color='green')

    plt.xlabel('Date')
    plt.ylabel('Count')
    plt.title(f'Daily Activity Summary for {username}')
    plt.xticks(x, dates, rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.grid(axis='y')  # Y軸にグリッドを追加
    plt.show()

# メインメニュー
def main():
    global username_entry  # グローバル変数として定義
    root = tk.Tk()
    root.title("Dictionary App")

    def look_up_word():
        username = username_entry.get()
        word = simpledialog.askstring("Input", "Enter an English word:")
        definitions = get_definition(word)
        if definitions:
            # 複数の定義をリストで表示し、ユーザーに選ばせる
            definition_choice = simpledialog.askinteger("Definitions", f"Choose the best definition for '{word}':\n" +
                                                        "\n".join([f"{i+1}: {definition}" for i, definition in enumerate(definitions)]))
            if definition_choice is not None and 1 <= definition_choice <= len(definitions):
                selected_definition = definitions[definition_choice - 1]
                save_word(word, selected_definition)  # 学習した単語を保 存
                update_user_activity(username, 'words_looked_up')  # アクティビティを更新
                messagebox.showinfo("Definition", f"{word}: {selected_definition}")
            else:
                messagebox.showwarning("Warning", "Invalid choice.")
        else:
            messagebox.showerror("Error", f"No definition found for '{word}'.")

    username_entry = tk.Entry(root)
    username_entry.pack(pady=10)

    look_up_button = tk.Button(root, text="Look Up Word", command=look_up_word)
    look_up_button.pack(pady=5)

    flashcard_button = tk.Button(root, text="Start Flashcards", command=start_flashcards)
    flashcard_button.pack(pady=5)

    quiz_button = tk.Button(root, text="Start Quiz", command=start_quiz)
    quiz_button.pack(pady=5)

    visualize_button = tk.Button(root, text="Visualize Activity", command=lambda: visualize_daily_activity(username_entry.get()))
    visualize_button.pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()
