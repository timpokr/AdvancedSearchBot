import itertools
import re
from functools import lru_cache
from typing import AsyncGenerator

import nltk
import requests
from bs4 import BeautifulSoup
from pymorphy2 import MorphAnalyzer
from pyrogram import types
from fuzzywuzzy import fuzz

morph = MorphAnalyzer()

forbidden_tags = ['PREP', 'CONJ', 'PRCL', 'INTJ', 'PNCT', 'NPRO', 'COMP']


def remove_parentheses(text):
    ret = ''
    skip = 0
    for i in text:
        if i == '(':
            skip += 1
        elif i == ')' and skip > 0:
            skip -= 1
        elif skip == 0:
            ret += i
    return ret


def word_tokenize(text):
    text = bytes(text, 'utf-8').decode('utf-8', 'ignore')
    return nltk.word_tokenize(text, 'russian')


@lru_cache
def synonyms(word):
    request = requests.get(f'http://www.synonymizer.ru/index.php?sword={word}')
    soup = BeautifulSoup(request.text, "html.parser")
    try:
        syns = soup.find('h2', text='База синонимов 1:').parent.select_one(':nth-last-child(1)').text
    except AttributeError:
        return []
    syns = remove_parentheses(syns)
    syns = re.sub(r'[\s,]+', ' ', syns).split()
    syns = list(map(str.lower, syns))
    return syns


def get_normalized_words(text):
    words = [morph.normal_forms(word)
             for word
             in word_tokenize(text)]

    return set(itertools.chain.from_iterable(words))


def is_similar(request, req_synonyms, text):
    if fuzz.partial_token_sort_ratio(request, text) >= 90:
        print('partial')
        return True

    msg_words = get_normalized_words(text)
    n = 0
    for syns in req_synonyms:
        if any(syn in msg_words for syn in syns):
            n += 1
    score = n / len(req_synonyms)
    return score >= 0.8


async def get_similar_msgs(request, msgs: AsyncGenerator[types.Message, None], max_count):
    req_synonyms = []
    for word in word_tokenize(request):
        word_synonyms = set()
        for p in morph.parse(word):
            if all(forbidden_tag not in p.tag for forbidden_tag in forbidden_tags):
                word_synonyms.add(p.normal_form)
                word_synonyms.update(synonyms(p.normal_form))
        if word_synonyms:
            req_synonyms.append(word_synonyms)

    print(request, req_synonyms)

    if len(req_synonyms) == 0:
        return []

    result = []
    async for msg in msgs:
        if msg.text is None:
            continue
        if is_similar(request, req_synonyms, msg.text):
            result.append(msg)
            print(msg.text)
        if len(result) >= max_count:
            break
    return result
