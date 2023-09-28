import django
django.setup()
import typer
import csv
from tqdm import tqdm
import random
from sefaria.model import *
from util.general import get_raw_ref_text, get_by_xml_tag

import langchain
from langchain.cache import SQLiteCache
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain import PromptTemplate
from langchain.schema import HumanMessage
langchain.llm_cache = SQLiteCache(database_path=".langchain.db")

random.seed(26)


def translate_segment(tref: str):
    oref = Ref(tref)
    text = get_raw_ref_text(oref, 'he')
    identity_message = HumanMessage(content="You are a Jewish scholar knowledgeable in all Torah and Jewish texts. Your "
                                         "task is to translate the Hebrew text wrapped in <input> tags. Output "
                                            "translation wrapped in <translation> tags.")
    task_message = HumanMessage(content=f"<input>{text}</input>")
    llm = ChatAnthropic(model="claude-2", temperature=0)
    response_message = llm([identity_message, task_message])
    translation = get_by_xml_tag(response_message.content, 'translation')
    if translation is None:
        print(response_message.content)
        return response_message.content
    return translation


def randomly_translate_book(title: str, n: int = 30):
    segment_orefs = library.get_index(title).all_segment_refs()
    random_segment_orefs = random.sample(segment_orefs, n)
    rows = []
    for oref in tqdm(random_segment_orefs, desc='randomly translating'):
        tref = oref.normal()
        rows += [{
            "Ref": tref,
            "Hebrew": get_raw_ref_text(oref, 'he'),
            "English": translate_segment(tref),
        }]
    with open('output/random_mb_translations.csv', 'w') as fout:
        cout = csv.DictWriter(fout, ['Ref', 'Hebrew', 'English'])
        cout.writeheader()
        cout.writerows(rows)


if __name__ == '__main__':
    typer.run(randomly_translate_book)
