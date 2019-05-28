import os
from bs4 import BeautifulSoup
from natasha import NamesExtractor
import json
extractor = NamesExtractor()
import re
#регулярка для имён
fio = re.compile("[А-ЯЁ][а-яё]+ [А-ЯЁ]\.[А-ЯЁ]\.")
import pandas as pd


def parse_xml(path):  # парсим xml
    meta_data = {'number': path.split("/")[-1], 'court': 'not_found', 'judge': 'not_found', 'prosecutor': 'not_found',
                 'advocate': 'not_found', 'secretary': 'not_found', 'accused': 'not_found', 'result': 'not_found',
                 'category': 'not_found'}
    with open(path, 'r', encoding='utf-8')as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        meta_data['court'] = soup.court.string  # добавляем в метаданные то, что имеется в разметке
        meta_data['judge'] = soup.judge.string
        meta_data['result'] = soup.result.string
        meta_data['category'] = soup.category.string

        html = []
        for line in soup.body:
            line = line.replace('[', '')
            line = line.replace(']', '')
            html.append(line)
        true_html = ' '.join(html)

        html_soup = BeautifulSoup(true_html, 'html.parser')
    return meta_data, html_soup.get_text()

def open_with_xml(path):
    text = ""
    with open(path, 'r', encoding='utf-8')as f:
        for line in f.readlines():
            text += line
    return text

def get_parts(text):    # делим на части
    lines = [line for line in text.split('\n')]
    beg, end = 0, 0
    for num, line in enumerate(lines):
        if 'установил' in line.lower() or 'у с т а н о в и л' in line.lower():
            beg = num + 1
        if 'приговорил' in line.lower() or 'п р и г о в о р и л' in line.lower() or 'определил' in line.lower() or 'о п р е д е л и л' in line.lower()  or 'решил' in line.lower() or 'р е ш и л' in line.lower() or "постановил" in line.lower() or "п о с т а н о в и л" in line.lower():
            end = num + 1
        if beg and end:
            beginning = [stroka.strip() for stroka in lines[:beg]]
            main_part = [stroka.strip() for stroka in lines[beg:end]]
            ending = [stroka.strip() for stroka in lines[end:]]
    return [' '.join(main_part), '\n'.join(beginning), '\n'.join(ending)]

def get_names(line):
    name = ""
    matches = extractor(line)
    for match in matches:
        fact = match.fact.as_json
        name = fact["first"]+"."+fact["middle"]+". "+fact["last"].capitalize()
    return name

def splitting_text(path):
    lines = []
    trouble_counter = 0
    text = get_parts(parse_xml(path)[1])[1]
    text = text.split("с участием")
    for part in text:
        lines += [line for line in part.split("\n") if line.strip()]
    for line in lines:
        if len(fio.findall(line)) > 1:
            trouble_counter += 1
    if trouble_counter != 0:
        for part in text:
            lines = [line for line in part.split(",") if line.strip()]
    return lines  

def meta_lines(path):
    lines = splitting_text(path) 
    add_meta = []
    for i, line in enumerate(lines):  
        if "защитник" in line.lower() or "адвокат" in line.lower(): 
            if fio.findall(line):
                add_meta.append(("advocate", line)) 
            else:
                add_meta.append(("advocate", line+lines[i+1])) 
        if "прокурор" in line.lower() or "обвинител" in line.lower():  
            if fio.findall(line):
                add_meta.append(("prosecutor", line)) 
            else:
                add_meta.append(("prosecutor", line+lines[i+1]))  
        if "секретар" in line.lower():
            if fio.findall(line):
                add_meta.append(("secretary", line)) 
            else:
                add_meta.append(("secretary", line+lines[i+1])) 
        if "подсудим" in line.lower() or "в отношении" in line.lower():
            if fio_cifer.findall(line):
                add_meta.append(("accused", line)) 
            elif fio.findall(line):
                add_meta.append(("accused", line)) 
            else:
                if i+1 < len(lines):
                    add_meta.append(("accused", line+lines[i+1])) 
    return add_meta

def get_meta_names(meta_lines):
    meta_names = []
    for line in meta_lines:         
        matches = extractor(line[1]) 
        if line[0] == "accused":
            if fio_cifer.findall(line[1]):
                meta_names.append((line[0], fio_cifer.findall(line[1])[0]))
            elif matches:
                try:
                    for match in matches:
                        fact = match.fact.as_json 
                        meta_names.append((line[0], (fact["last"].capitalize()+" "+fact["first"]+"."+fact["middle"]+".")))
                except KeyError:
                    if fio.findall(line[1]): 
                        meta_names.append((line[0], fio.findall(line[1])[0]))
            elif fio.findall(line[1]): 
                meta_names.append((line[0], fio.findall(line[1])[0]))
        else:
            if matches:
                try:
                    for match in matches:
                        fact = match.fact.as_json 
                        meta_names.append((line[0], (fact["last"].capitalize()+" "+fact["first"]+"."+fact["middle"]+".")))
                except KeyError:
                    if fio.findall(line[1]): 
                        meta_names.append((line[0], fio.findall(line[1])[0]))
            elif fio.findall(line[1]): 
                meta_names.append((line[0], fio.findall(line[1])[0]))
    return meta_names

def names_to_meta(path):
    meta_data = parse_xml(path)[0]
    updated_names = []
    unique_names = list(set(get_meta_names(meta_lines(path))))
    unique_names.sort()
    #объединение кортежей с одинаковыми нулевыми значениями
    for i, name in enumerate(unique_names):
        if i+1 < len(unique_names):
            if name[0] == unique_names[i+1][0]:
                updated_names.append((name[0], name[1]+", "+unique_names[i+1][1]))
            elif name[0] != unique_names[i-1][0] or i == 0:
                updated_names.append((name[0], name[1]))
        elif i+1 >= len(unique_names) and name[0] != unique_names[i-1][0]:
            updated_names.append((name[0], name[1]))
        elif len(unique_names) == 1:
            updated_names.append((name[0], name[1]))

    for name in updated_names:
        meta_data[name[0]] = name[1]
    return meta_data





