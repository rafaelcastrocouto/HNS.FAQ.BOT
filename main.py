import openai
import os
import discord
from flask import Flask
from threading import Thread

# setup openapi
openai.api_key = os.environ.get('OPENAI')


def score(e):
    return e.score

def ask(log, answer=''):

    responses = openai.Completion.create(
        engine = 'davinci',
        prompt = log, # prompt max tokens=2049
        max_tokens = 100, # response max tokens
        temperature = 0.1, # Float value controlling randomness in boltzmann distribution.The model will become deterministic at zero
        stop = '\n')

    print(log + responses.choices[0].text)
    answer += responses.choices[0].text

    if not len(answer):
        answer = "Please try at searching at our Learning center: https://learn.namebase.io."

    # remove bot name
    if answer.startswith('A: '):
        answer = answer[3:]

    return answer


# read all datasets.txt
file_names = [
  'auction', 
  'ca',
  'dns', 
  'domains', 
  'handshake', 
  'hns', 
  'miner',
  'wallets'
]
datasets = []
for file_name in file_names:
    datafile = open('datasets/' + file_name + ".txt", "r")
    datasets.append(datafile.read())

# create server
app = Flask('discord bot')


@app.route("/")
def hello_world():
    return 'SERVER RUNNING'


def start_server():
    app.run(host='0.0.0.0', port=8080)


t = Thread(target=start_server)
t.start()


# create discord bot client
CHANNEL_ID = 357574292541669377
client = discord.Client()


@client.event
async def on_ready():
    print('Logged in as ' + client.user.name)
    print(
        'https://discordapp.com/oauth2/authorize?client_id={}&scope=bot&permissions=116736'
        .format(client.user.id))


@client.event
async def on_message(message):
    if message.channel.id == CHANNEL_ID and message.author != client.user:

        log = ''
        # prompt log:
        #
        # best_history: search discord questions?
        # A: Answers.

        # best_faq: search dataset questions?
        # BOT: Answers.
        #
        # last_history: discord last questions?
        # BOT: Answers.
        #
        # last: question?
        # BOT: ...

        # get channel history
        channel_hist = []
        async for msg in message.channel.history(limit=100):
            channel_hist.append(msg)

        n = 1
        history = []
        content = ''
        for msg in reversed(channel_hist):
            if msg.author.name == client.user.name:
              content += 'A: ' + msg.content
            else:
              content += 'Q: ' + msg.content
            for embed in msg.embeds:
                content += '[' + str(embed.title) + '](' + str(embed.url) + ')'
            content += '\n'
            if msg.author.name == client.user.name:
                history.append(content)
                #print(content+ '\n');
                content = ''

        # search best in history
        result = openai.Engine("davinci").search(
            documents=history[:-n], query=message.content)

        # create zip with scores and history
        z = zip(map(score, result.data), history[:-n])

        # create new array with history sorted by score
        best_hist = [x for _,x in reversed(sorted(z))];

        # best history matches
        best_history = ''
        for msg in best_hist[:n]:
            best_history += msg
        log += best_history

        # semantic search for best faq
        result = openai.Engine("davinci").search(
            documents=datasets, query=message.content)
        # sorts by score
        result.data.sort(reverse=True, key=score)
        best_faq = datasets[result.data[0].document]

        # semantic search for best question
        best_in_faq = best_faq.split('\n\n')
        result = openai.Engine("davinci").search(
            documents=best_in_faq, query=message.content)
        # sorts by score
        result.data.sort(reverse=True, key=score)
        best_q = best_in_faq[result.data[0].document]

        log += best_q

        # last history
        last_history = ''
        for msg in history[-n:]:
            last_history += msg
        log += last_history

        msg = 'Q: ' + message.content
        if not msg in log:
            log += msg + '\n'

        log += 'A: '

        #print('## discord', msg + '\n');

        # ask openai and send response to discord
        response = ask(log)
        await message.channel.send(response)


client.run(os.environ.get('DISCORD'))
