import zipfile
import os
import json
from googletrans import Translator
import time
import shutil

def translate_mod_files():
    translator = Translator()
    target_language = 'ru_ru'
    mods_path = "./mods/"
    complete_path = "./complete/"
    temp_path = "./temp/"
    files = os.listdir(mods_path)
    filtered_files = [file for file in files if file.endswith(".jar")]

    os.makedirs(complete_path, exist_ok=True)

    try:
        for mod_file in filtered_files:
            print(f"Начало перевода: {mod_file}")
            src_file = os.path.join(mods_path, mod_file)
            print(src_file)

            with zipfile.ZipFile(src_file, "r") as archive:
                paths = [p for p in archive.namelist() if 'assets' in p and 'lang' in p]

                if not paths:
                    print("Нет файлов для перевода в этом моде.")
                    continue

                lang_paths = [p for p in paths if p.endswith('.json')]
                target_lang_path = None

                for lang_path in lang_paths:
                    if 'en_us.json' in lang_path:
                        target_lang_path = lang_path
                        break
                    elif 'en' in lang_path:
                        target_lang_path = lang_path

                if not target_lang_path:
                    print("Не найдено подходящих файлов для перевода.")
                    continue

                ru_path = target_lang_path.replace(target_lang_path.split('/')[-1], f'{target_language}.json')
                extract_dir = os.path.join(temp_path, mod_file.split(".jar")[0])
                extract_path = os.path.join(extract_dir, target_lang_path)
                ru_file_path = os.path.join(extract_dir, ru_path)

                # Убедимся, что директория существует перед извлечением
                os.makedirs(os.path.dirname(extract_path), exist_ok=True)
                archive.extract(target_lang_path, extract_dir)

                if os.path.exists(ru_file_path):
                    print(f"{mod_file} уже переведён!")
                    continue

                try:
                    with open(extract_path, 'r', encoding='utf-8') as file:
                        file_content = file.read()

                    if not file_content:
                        print(f"Файл {extract_path} пустой или не удалось прочитать содержимое.")
                        continue

                    json_file = json.loads(file_content)

                    translated_json = {}
                    for key, value in json_file.items():
                        attempts = 3
                        while attempts > 0:
                            try:
                                if value.strip():
                                    translated_value = translator.translate(value, dest=target_language).text
                                else:
                                    translated_value = value
                                translated_json[key] = translated_value
                                break
                            except Exception as e:
                                attempts -= 1
                                time.sleep(3)
                                if attempts == 0:
                                    print(f"Ошибка перевода '{value}': {e}")
                                    translated_json[key] = value

                    os.makedirs(os.path.dirname(ru_file_path), exist_ok=True)
                    with open(ru_file_path, 'w', encoding='utf-8') as output_file:
                        json.dump(translated_json, output_file, ensure_ascii=False)

                    print(f"Перевод: {ru_path} закончен!")

                    # Сохранение нового JAR файла с переводом
                    complete_mod_path = os.path.join(complete_path, mod_file)
                    shutil.copy(src_file, complete_mod_path)

                    with zipfile.ZipFile(complete_mod_path, 'a') as complete_archive:
                        complete_archive.write(ru_file_path, ru_path)

                    print(f"Файл с переводом сохранён по пути: {complete_mod_path}")

                except Exception as e:
                    print(f"Ошибка обработки файла {target_lang_path}: {e}")

    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    translate_mod_files()
