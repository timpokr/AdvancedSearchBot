import logging
from configparser import RawConfigParser
from pathlib import Path

from fuzzywuzzy import fuzz
from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.types import Message

from similar_msgs import get_similar_msgs

logging.basicConfig(level=logging.INFO)

config = RawConfigParser()
config.read('../config.ini')

api_id = config['api']['id']
api_hash = config['api']['hash']
bot_token = config['bot']['token']
phone = config['user']['phone']
password = config['user']['password']

workdir = Path(__file__).parent.parent / 'sessions'
workdir.mkdir(exist_ok=True)
user = Client('user', api_id=api_id, api_hash=api_hash, phone_number=phone, password=password, workdir=str(workdir))
bot = Client('src', api_id=api_id, api_hash=api_hash, bot_token=bot_token, workdir=str(workdir))


def title_similarity(query, title):
    return fuzz.partial_token_sort_ratio(query, title) / 100


def format_answer_block(msg):
    text = msg.text or msg.caption
    if len(text) > 100:
        text = text[:100] + '...'
    return f'{msg.link}\n{text}'


@bot.on_message()
async def handle_message(client: Client, msg: Message):
    req_dialog, req_text = msg.text.split('\n')

    chats = [dialog.chat async for dialog in user.get_dialogs()
             if dialog.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)]

    chat = max([(c, title_similarity(req_dialog, c.title))
                for c in chats], key=lambda i: i[1])

    if chat[1] < 0.7:
        await msg.reply_text('Диалог не найден')
        return
    chat = chat[0]

    msgs = [msg async for msg in user.get_chat_history(chat.id, limit=1000)]
    similar_msgs = get_similar_msgs(req_text, msgs, 10)

    if len(similar_msgs) == 0:
        await msg.reply_text('Сообщения не найдены')
        return

    reply_msgs = '\n-----\n'.join(format_answer_block(m) for m in similar_msgs)

    await msg.reply_text(f'Похожие сообщения в группе {chat.title}:\n\n{reply_msgs}')


user.start()
bot.run()
