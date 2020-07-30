import openai
import os
import discord
from flask import Flask
from threading import Thread

# setup openapi
openai.api_key = os.environ.get('OPENAI')


def score(e):
    return e.score


def ask(name, log, answer=''):
    responses = openai.Completion.create(
        engine = 'davinci',
        prompt = log, # prompt max tokens=2049
        max_tokens = 100, # response max tokens
        temperature = 0.1, # Float value controlling randomness in boltzmann distribution.The model will become deterministic at zero
        stop = '\n')

    print('openai', responses.choices[0].text)
    answer += responses.choices[0].text

    if not len(answer):
        answer = 'Sorry I could not understand. Please try at searching at our [Learning center](https://learn.namebase.io).'

    # keep asking until it ends the sentence
    if not answer.endswith('.'):
        answer = ask(name, log, answer)

    # remove bot name
    if answer.startswith(name):
        answer = answer[2 + len(name):]

    return answer


# read all datasets.txt
file_names = ['auction', 'dns', 'domains', 'handshake', 'hns', 'wallets']
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
        # build prompt log

        # semantic search for best faq
        # get discord channel history

        # best faq: questions?
        # BOT: Answers.
        #
        # history: questions?
        # BOT: Answers.
        #
        # last: question?
        # BOT: ...

        log = 'The following is a respectful conversation between a very polite attendant and a customer.\n\n'

        # semantic search for best faq
        result = openai.Engine("davinci").search(
            documents=datasets, query=message.content)
        # sorts by score
        result.data.sort(reverse=True, key=score)
        best_faq = datasets[result.data[0].document]
        log += best_faq

        # get channel history
        history = []
        async for old_msg in message.channel.history(limit=5):
            content = old_msg.author.name + ': ' + old_msg.content
            for embed in old_msg.embeds:
                content += '[' + str(embed.title) + '](' + str(embed.url) + ')'
            if old_msg.author.name == client.user.name:
                content += '\n'
            history.append(content + '\n')
        # reverse and convert to string
        history_string = ''
        for msg in reversed(history):
            history_string += msg
        log += history_string
        msg = message.author.name + ': ' + message.content
        if not msg in log:
            log += msg

        print('discord', msg);

        # ask openai and send response to discord
        response = ask(client.user.name, log)
        await message.channel.send(response)


client.run(os.environ.get('DISCORD'))
