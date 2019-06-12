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
import pandas as pd

def get_paths(folder_path):
    paths = []
    for root, dirs, files in os.walk(folder_path):
        for _file in files:
            if 'xml' in _file:
                res = os.path.join(os.path.abspath(root), _file)
                paths.append(res)
    return paths

def parse_xml(path):  # парсим xml
    meta_data = {'number': path.split("/")[-1], 'court': 'not found', 'judge': 'not found', 'prosecutor': 'not found',
                 'advocate': 'not found', 'secretary': 'not found', 'accused': 'not found', 'result': 'not found',
                 'category': 'not found'}
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
    # Объявляем здесь переменные, чтобы в return не ругался на возврат локальных
    beginning, main_part, ending = [], [], []
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
    trouble_counter = 0
    text = get_parts(parse_xml(path)[1])[1]
    lines = [line for line in text.split(",") if line.strip()]
    for line in lines:
        if len(fio.findall(line)) > 1:
            trouble_counter += 1
    if trouble_counter != 0:
        lines = [line for line in text.split("\n") if line.strip()]
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
            elif fio_short.findall(line):
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
            elif fio_short.findall(line[1]):
                meta_names.append((line[0], fio_short.findall(line[1])[0]))
            elif matches:
                try:
                    for match in matches:
                        fact = match.fact.as_json
                        meta_names.append((line[0], (fact["last"].capitalize()+" "+fact["first"][0].upper()+"."+fact["middle"][0].upper()+".")))
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
                        meta_names.append((line[0], (fact["last"].capitalize()+" "+fact["first"][0].upper()+"."+fact["middle"][0].upper()+".")))
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

def killing_doubles(path):
    names_dict = names_to_meta(path)
    no_doubles_dict = {}
    for role in names_dict:
        if type(names_dict[role]) == str:
            names_list = names_dict[role].split(",")
            if "," in names_dict[role]:
                for n, name in enumerate(names_list):
                    if fio.findall(name):
                        if n > 0 and name.split()[1] == names_list[n-1].split()[1]  and name.split()[0][:len(name.split()[0])-2] == names_list[n-1].split()[0][0:len(name.split()[0])-2]:
                            names_list.pop(n)
            no_doubles_dict[role] = names_list
        else:
            no_doubles_dict[role] = [names_dict[role]]
    return no_doubles_dict

def final_meta(path):
    dict_with_lists = killing_doubles(path)
    final_meta_dict = {}
    for role in dict_with_lists:
        if len(dict_with_lists[role]) == 1:
            final_meta_dict[role] = dict_with_lists[role][0]
        else:
            final_meta_dict[role] = ",".join(dict_with_lists[role])
    return final_meta_dict





