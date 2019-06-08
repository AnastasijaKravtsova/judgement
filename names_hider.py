import os
from bs4 import BeautifulSoup
from natasha import NamesExtractor
import json
extractor = NamesExtractor()
import re
#регулярка для имён
fio = re.compile("[А-ЯЁ][а-яё]+ [А-ЯЁ]\.[А-ЯЁ]\.")
fio_cifer = re.compile("[А-ЯЁ][а-яё]+ ФИО[0-9]{1,3}")
fio_short = re.compile("ФИО[0-9]{1,3}")

from meta_extraction import names_to_meta
from meta_extraction import get_parts, parse_xml

persons_meta = ["judge", "prosecutor", "advocate", "accused", "secretary"]


#прячет отдельную "роль" -- адвоката, обвиняемого и т.п.
def person_hider(path, text, role):
    names = [name.strip(" ") for name in names_to_meta(path)[role].split(",")]
    for name in names:
        role_word = role.upper()
        name_to_split = name.split(" ")
        name_variations = name_to_split[0][0:-2] + r"[a-яё]{1,5}" + " " + name_to_split[1]
        text = re.sub(name_variations, role_word, text)
    return text

#прячет все роли из ролей в тексте
def all_persons_hider(path, text, roles):
    text = text
    for person in roles:
        text = person_hider(path, text, person)
    return text