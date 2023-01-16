import logging
from configparser import RawConfigParser

from fuzzywuzzy import fuzz
from pymorphy2 import MorphAnalyzer
from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.types import Message

from similar_msgs import get_similar_msgs

logging.basicConfig(level=logging.INFO)

config = RawConfigParser()
config.read('config.ini')

api_id = config['api']['id']
api_hash = config['api']['hash']
bot_token = config['bot']['token']
phone = config['user']['phone']
password = config['user']['password']

user = Client('user', api_id=api_id, api_hash=api_hash, phone_number=phone, password=password, workdir='sessions')
bot = Client('bot', api_id=api_id, api_hash=api_hash, bot_token=bot_token, workdir='sessions')

morph = MorphAnalyzer()


def title_similarity(query, title):
    return fuzz.partial_token_sort_ratio(query, title) / 100


@bot.on_message()
async def handle_message(client: Client, msg: Message):
    req_title, req_text = msg.text.split('\n')

    chats = [dialog.chat
             async for dialog
             in user.get_dialogs()
             if dialog.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)]

    chat = max([(c, title_similarity(req_title, c.title))
                for c in chats], key=lambda i: i[1])

    if chat[1] < 0.7:
        await msg.reply_text('Группа не найдена')
        return
    chat = chat[0]

    similar_msgs = await get_similar_msgs(req_text, user.get_chat_history(chat.id, limit=1000), 10)

    if len(similar_msgs) == 0:
        await msg.reply_text('Сообщения не найдены')
        return

    reply_msgs = '\n-----\n'.join(f'{m.link}\n{m.text}' for m in similar_msgs)

    await msg.reply_text(f'Похожие сообщения в группе {chat.title}:\n\n{reply_msgs}')


user.start()
bot.run()
