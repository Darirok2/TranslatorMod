import zipfile
import os
import json
from googletrans import Translator
import time

translator = Translator()
language = input("Язык для перевода например: en, uk...\nВведите: ")
path = "./"
files = os.listdir(path)
filtered_files = [file for file in files if file.endswith(".jar")]
# print(filtered_files)

try:
    for i in range(0, len(filtered_files)):
        print("Начло перевода: " + filtered_files[i])
        src_file = path + filtered_files[i]
        print(src_file)
        archive = zipfile.ZipFile(filtered_files[i], "r")
        paths = archive.namelist()
        paths_copy = paths[:]
        for path in paths_copy:
            if path.find('assets') == -1:
                paths.remove(path)
        print(paths)
        paths_copy = paths[:]
        for path in paths_copy:
            if path.find('lang') == -1:
                paths.remove(path)
        print(paths)
        if paths != []:
            paths_copy = paths[:]
            for path in paths_copy:
                if path.find(language) == -1:
                    paths.remove(path)
            print(paths)
            if paths != []:
                ru_path = ""
                ru_path_temp = ""
                for path in paths:
                    ru_path = path.split('/')
                    ru_path.remove(ru_path[len(ru_path) - 1])
                    ru_path_str = ""
                    for j in range(0, len(ru_path)):
                        ru_path_str = ru_path_str + str(ru_path[j]) + "/"
                    ru_path_temp = ru_path_str
                    ru_path = ru_path_str + "ru_ru.json"
                archive.extract(path, "./mods/" + filtered_files[i].split(".jar")[0] + "/")
                # print("./" + filtered_files[i] + "/" + ru_path_temp)
                if os.path.exists("./mods/" + filtered_files[i].split(".jar")[0] + "/" + ru_path):
                    print(filtered_files[i] + " Уже переведён!")
                else:
                    with open("./mods/" + filtered_files[i].split(".jar")[0] + "/" + path, 'r+',
                              encoding='utf-8') as file:
                        file_content = file.read()
                        file.close()
                    json_file = json.loads(file_content)
                    time.sleep(3)
                    translated_json = {key: translator.translate(value, dest='ru').text for key, value in
                                       json_file.items()}
                    os.remove("./mods/" + filtered_files[i].split(".jar")[0] + "/" + path)
                    print(json_file)
                    print(translated_json)
                    with open("./mods/" + filtered_files[i].split(".jar")[0] + "/" + ru_path, 'w+',
                              encoding='utf-8') as output_file:
                        json.dump(translated_json, output_file, ensure_ascii=False)
                        output_file.close()
                    # with zipfile.ZipFile(filtered_files[i], "w") as archive:
                    #     archive.write(ru_path)
                    # print(ru_path)
                    print("Перевод: " + ru_path + " Закончен!")
                    print("Файл с переводом сохранён по пути: " + ru_path)
            else:
                print("Не чего переводить :(")
except Exception:
    print("Ошибка: " + Exception)
    