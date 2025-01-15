import tkinter as tk
import os
import random
import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pytz

# 日本標準時 (JST) のタイムゾーン設定
jst = pytz.timezone('Asia/Tokyo')

# JSTの日付のみを取得する関数
def current_date_jst():
    return datetime.datetime.now(jst).date()

# 学習した単語と定義を保持するクラス
class FlashCard:
    def __init__(self, word, definitions):
        self.word = word
        self.definitions = definitions  # 定義をリストで保持
        self.last_reviewed = None  # 最後に復習した日付
        self.interval = 1  # 初回の復習間隔
        self.understood = False  # 単語が理解されたかどうか

    def update_review(self):
        self.last_reviewed = datetime.datetime.now(jst)
        self.interval *= 2  # 次回の復習間隔を倍にする

    def mark_understood(self):
        self.understood = True  # 単語を理解したとマークする

    def mark_not_understood(self):
        self.understood = False  # 単語を理解していないとマークする

# 学習した単語と定義をロードする
def load_flashcards(filename='learned_words.txt'):
    cards = []
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        word, definition_str = parts
                        definitions = definition_str.split(';')
                        cards.append(FlashCard(word, [defn.strip() for defn in definitions]))
                    else:
                        print(f"Warning: Line is not in the correct format: {line}")
    return cards

def save_flashcards(cards, filename='learned_words.txt'):
    with open(filename, 'w') as f:
        for card in cards:
            definitions = "; ".join(card.definitions)
            f.write(f"{card.word}:{definitions}\n")

def load_daily_activity(filename='daily_activity.txt'):
    activity = defaultdict(float)
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            for line in f:
                date_str, duration = line.strip().split(':')
                activity[date_str] = float(duration)
    return activity

def save_daily_activity(activity, filename='daily_activity.txt'):
    with open(filename, 'w') as f:
        for date_str, duration in activity.items():
            f.write(f"{date_str}:{duration}\n")

class FlashCardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Flashcard App")
        self.cards = load_flashcards()
        self.current_card = None
        self.activity_log = []  # アクティビティログを保持するリスト
        self.daily_activity = load_daily_activity()  # 日別の勉強時間をロード
        self.start_time = None  # セッション開始時間を記録

        # 日別の勉強時間を表示するラベル
        self.activity_label = tk.Label(self.root, text="Today's Study Duration: 0 minutes", font=("Helvetica", 16))
        self.activity_label.pack(pady=10)

        self.create_widgets()

    def create_widgets(self):
        self.word_label = tk.Label(self.root, text="", font=("Helvetica", 24))
        self.word_label.pack(pady=20)

        self.definition_label = tk.Label(self.root, text="", font=("Helvetica", 18))
        self.definition_label.pack(pady=20)

        self.show_definition_button = tk.Button(self.root, text="Show Definition", command=self.show_definition)
        self.show_definition_button.pack(pady=10)

        self.understood_button = tk.Button(self.root, text="Know", command=self.mark_understood)
        self.understood_button.pack(pady=10)

        self.not_understood_button = tk.Button(self.root, text="Don't know", command=self.mark_not_understood)
        self.not_understood_button.pack(pady=10)

        self.next_button = tk.Button(self.root, text="Next Card", command=self.next_card)
        self.next_button.pack(pady=10)

        self.delete_button = tk.Button(self.root, text="Delete Card", command=self.delete_card)
        self.delete_button.pack(pady=10)

        self.start_button = tk.Button(self.root, text="Start", command=self.start_flashcards)
        self.start_button.pack(pady=10)

        self.end_button = tk.Button(self.root, text="End", command=self.end_flashcards)  # 終了ボタンを追加
        self.end_button.pack(pady=10)

       # self.visualize_button = tk.Button(self.root, text="Visualize Activity", command=self.visualize_daily_activity)
        #self.visualize_button.pack(pady=10)

    def log_activity(self):
        """ アクティビティをログに記録する """
        if self.start_time:
            end_time = datetime.datetime.now(jst)
            duration = (end_time - self.start_time).total_seconds() / 60
            date_str = current_date_jst().isoformat()  # 修正された日付を取得
            self.daily_activity[date_str] += duration
            self.update_activity_label(date_str)

    def update_activity_label(self, date_str):
        total_duration = self.daily_activity[date_str]
        self.activity_label.config(text=f"Today's Study time: {total_duration:.1f} minutes")

    def visualize_daily_activity(self):
        # 今日と過去に学習した日付をフィルタリング
        dates = [date for date in self.daily_activity if self.daily_activity[date] > 0]
        durations = [self.daily_activity[date] for date in dates]

        # 日付をdatetimeに変換
        dates = [datetime.datetime.strptime(date, '%Y-%m-%d') for date in dates]

        plt.bar(dates, durations)
        plt.xlabel("Date")
        plt.ylabel("Study time (minutes)")
        plt.title("Daily Study time")
        plt.xticks(rotation=45)

        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator())

        for i, duration in enumerate(durations):
            plt.text(dates[i], duration + 0.1, f"{duration:.1f}", ha='center')

        plt.tight_layout()
        plt.show()

    def start_flashcards(self):
        random.shuffle(self.cards)
        self.start_time = datetime.datetime.now(jst)
        self.next_card()

    def end_flashcards(self):
        self.log_activity()
        self.save_progress()
        self.visualize_daily_activity()

    def save_progress(self):
        save_daily_activity(self.daily_activity)

    def next_card(self):
        if not self.cards:
            self.word_label.config(text="No flashcards available.")
            self.definition_label.config(text="")
            return

        not_understood_cards = [card for card in self.cards if not card.understood]
        if not_understood_cards:
            self.current_card = random.choice(not_understood_cards)
        else:
            self.current_card = random.choice(self.cards)

        self.word_label.config(text=self.current_card.word)
        self.definition_label.config(text="")

    def show_definition(self):
        if self.current_card:
            definition = random.choice(self.current_card.definitions)
            self.definition_label.config(text=definition)

    def mark_understood(self):
        if self.current_card:
            self.current_card.mark_understood()
            self.current_card.update_review()
            self.next_card()
            save_flashcards(self.cards)

    def mark_not_understood(self):
        if self.current_card:
            self.current_card.mark_not_understood()
            self.next_card()

    def delete_card(self):
        if self.current_card:
            self.cards.remove(self.current_card)
            self.next_card()
            save_flashcards(self.cards)

root = tk.Tk()
app = FlashCardApp(root)
root.mainloop()
