import os
import discord
import requests
import random
import html

import sqlite3

from discord.ext import commands
from dotenv import load_dotenv

db = sqlite3.connect("triviapoor.db")
db.execute("""
    CREATE TABLE IF NOT EXISTS user_stats (
        user_id TEXT PRIMARY KEY,
        correct_answers INTEGER NOT NULL DEFAULT 0,
        wrong_answers INTEGER NOT NULL DEFAULT 0
    )
""")
db.commit()

base_url = "https://opentdb.com/api.php?"

def question(category = None, difficulty = None):
    category = category_dict[category]
    url = f"{base_url}amount=1&category={category}&difficulty={difficulty}&type=multiple"
    response = requests.get(url)

    if response.status_code == 200:
        question_data = response.json()
        return question_data
    else:
        print(f"Failed to retrieve data {response.status_code}")

def format_question(question):
    correct_answer = question['results'][0]['correct_answer']
    answers = [correct_answer, question['results'][0]['incorrect_answers'][0], question['results'][0]['incorrect_answers'][1], question['results'][0]['incorrect_answers'][2]]
    random_answers = []
    for i in range (4):
        next_answer = random.choice(answers)
        random_answers.append(next_answer)
        answers.pop(answers.index(next_answer))
    return html.unescape(question['results'][0]['question']), random_answers, correct_answer

category_dict = {
    'general': '9',
    'books': '10',
    'film': '11',
    'music': '12',
    'television': '14',
    'video games': '15',
    'science': '17',
    'comp sci': '18',
    'mathematics': '19',
    'mythology': '20',
    'sports': '21',
    'geography': '22',
    'history': '23',
    'politics': '24',
    'art': '25',
    'celebrities': '26',
    'animals': '27',
    'vehicles': '28',
    'anime & manga': '31',
    'cartoon & animation': '32',
}

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} is on')

@bot.command()
async def points(ctx, user: discord.User = None):
    user = user or ctx.author

    row = db.execute(
        "SELECT correct_answers, wrong_answers FROM user_stats WHERE user_id = ?",
        (str(user.id),)
    ).fetchone()

    correct, wrong = row if row else (0, 0)

    await ctx.send(
        f"{user.display_name} has {correct} correct answer(s) "
        f"and {wrong} wrong answer(s)."
    )
        

@bot.command()
async def trivia(ctx, category=None, difficulty=None):
    def check(msg):
        if msg.author == ctx.author and msg.channel == ctx.channel:
            return msg.content in category_dict

    def diff_check(msg):
        if msg.author == ctx.author and msg.channel == ctx.channel:
            if msg.content == 'easy' or msg.content == 'medium' or msg.content == 'hard':
                return msg.content

    def answer_check(msg):
        return (
            msg.author == ctx.author
            and msg.channel == ctx.channel
            and msg.content in answers
        )
            
    category_missing = False
    difficulty_missing = False
    if category == None:
        await ctx.send("Which category?")
        msg = await bot.wait_for("message", check=check)
        category_missing = True

    if difficulty == None:
        await ctx.send("Which difficulty?")
        diff_msg = await bot.wait_for("message", check=diff_check)
        difficulty_missing = True

    if category_missing and difficulty_missing:    
        question_data = question(msg.content, diff_msg.content)

    elif category_missing:
        question_data = question(msg.content, difficulty)

    elif difficulty_missing:
        question_data = question(category, diff_msg.content)

    else:
        question_data = question(category, difficulty)

    question_text, answers, correct_answer = format_question(question_data)

    question_output = f"{question_text}\n{"\n".join(answers)}"
    await ctx.send(question_output)
    answer = await bot.wait_for("message", check=answer_check)
    if answer.content == correct_answer:
        db.execute("""
            INSERT INTO user_stats (user_id, correct_answers)
            VALUES (?, 1)
            ON CONFLICT(user_id)
            DO UPDATE SET correct_answers = correct_answers + 1
        """, (str(answer.author.id),))
        db.commit()
        await ctx.send("Correct")
    else:
        db.execute("""
            INSERT INTO user_stats (user_id, wrong_answers)
            VALUES (?, 1)
            ON CONFLICT(user_id)
            DO UPDATE SET wrong_answers = wrong_answers + 1
        """, (str(answer.author.id),))
        db.commit()
        await ctx.send(f"Wrong, the correct answer is ||{correct_answer}||")


bot.run(TOKEN)