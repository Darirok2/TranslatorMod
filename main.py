import os
import json
import zipfile
import shutil
import re
from deep_translator import GoogleTranslator
from time import sleep
import tempfile
from typing import List

# Настройки
MODS_FOLDER = 'mods'  # Папка с исходными модами
OUTPUT_FOLDER = 'translated_mods'  # Папка для переведенных модов
BATCH_SIZE = 50  # Размер батча для перевода (чтобы обходить лимиты)
SLEEP_BETWEEN_BATCHES = 3  # Задержка между батчами (секунды)
RETRY_SLEEP = 5  # Задержка при ошибке (секунды)


def is_localization_file(file_path: str) -> bool:
    """Проверяет, является ли файл файлом локализации."""
    try:
        if file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and any(k.startswith(
                    ('block.', 'item.', 'entity.', 'biome.', 'effect.', 'enchantment.', 'gui.', 'sound.', 'tile.',
                     'achievement.')) for k in data):
                return True
        elif file_path.endswith('.lang'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(500)  # первые 500 символов достаточно
            return '=' in content and len(content.strip()) > 10
    except Exception:
        return False
    return False


def translate_batch(texts: List[str], source_lang: str, target_lang: str, retries=3) -> List[str]:
    """Переводит батч текстов с ретраями при ошибках."""
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    for attempt in range(retries):
        try:
            return translator.translate_batch(texts)
        except Exception as e:
            print(f"Ошибка перевода: {e}. Ретрай {attempt + 1}/{retries} после паузы...")
            sleep(RETRY_SLEEP)
    raise Exception("Не удалось перевести батч после всех ретраев.")


def get_full_lang_code(short_code: str, is_legacy: bool = False) -> str:
    """
    Преобразует короткий код в полный стандартный для Minecraft.
    Примеры:
    - ru     → ru_ru (json) или RU_RU (legacy .lang)
    - uk     → uk_ua
    - pt     → pt_br или pt_pt (можно доработать)
    """
    common_mappings = {
        'ru': 'ru_ru',
        'uk': 'uk_ua',
        'be': 'be_by',
        'kk': 'kk_kz',
        'en': 'en_us',
        'de': 'de_de',
        'fr': 'fr_fr',
        'es': 'es_es',
        'pl': 'pl_pl',
        'pt': 'pt_br',  # чаще всего бразильский
        # Добавь другие по необходимости
    }

    code = common_mappings.get(short_code.lower(), short_code.lower())

    if is_legacy:
        # Для старых .lang → заглавные + подчёркивание
        return code.upper().replace('_', '_')
    else:
        # Для современных .json → строчные
        return code.lower()


def process_lang_file(lang_file: str, target_lang_short: str):
    """Обрабатывает один файл локализации (JSON или LANG) и создает переведенную версию."""
    basename = os.path.basename(lang_file).lower()
    is_json = lang_file.endswith('.json')
    is_legacy = lang_file.endswith('.lang')  # предполагаем, что если оригинал .lang → legacy формат

    # Определяем исходный язык для перевода
    source_lang = 'en' if 'en_us' in basename or 'en_gb' in basename else 'auto'

    # Получаем правильный код для целевого языка
    full_target_code = get_full_lang_code(target_lang_short, is_legacy=is_legacy)

    if is_json:
        # Чтение с fallback
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except UnicodeDecodeError:
            with open(lang_file, 'r', encoding='windows-1251', errors='replace') as f:
                data = json.load(f)

        keys = list(data.keys())
        values = list(data.values())

        # Разделяем на батчи
        translated_values = []
        for i in range(0, len(values), BATCH_SIZE):
            batch = values[i:i + BATCH_SIZE]
            translated_batch = translate_batch(batch, source_lang, target_lang_short)
            translated_values.extend(translated_batch)
            sleep(SLEEP_BETWEEN_BATCHES)

        new_data = dict(zip(keys, translated_values))

        # Сохраняем как {full_target_code}.json
        target_filename = f"{full_target_code}.json"
        target_file = os.path.join(os.path.dirname(lang_file), target_filename)
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=4)
        print(f"Переведен JSON: {lang_file} -> {target_file}")

    elif is_legacy:
        # Чтение с fallback-кодировкой (важно для старых модов)
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(lang_file, 'r', encoding='windows-1251', errors='replace') as f:
                lines = f.readlines()

        translated_lines = []
        value_idx = 0

        # Сначала собираем все значения для перевода
        values = []
        for line in lines:
            stripped = line.strip()
            if '=' in stripped and not stripped.startswith('#'):
                _, v = stripped.split('=', 1)
                values.append(v.strip())

        # Переводим батчами
        translated_values = []
        for i in range(0, len(values), BATCH_SIZE):
            batch = values[i:i + BATCH_SIZE]
            translated_batch = translate_batch(batch, source_lang, target_lang_short)
            translated_values.extend(translated_batch)
            sleep(SLEEP_BETWEEN_BATCHES)

        # Теперь собираем новый файл, заменяя только значения
        value_idx = 0
        for line in lines:
            stripped = line.strip()
            if '=' in stripped and not stripped.startswith('#'):
                k, _ = stripped.split('=', 1)
                if value_idx < len(translated_values):
                    new_line = f"{k.strip()}={translated_values[value_idx]}\n"
                    translated_lines.append(new_line)
                    value_idx += 1
                else:
                    # На всякий случай — если что-то сломалось
                    translated_lines.append(line)
                    print(f"Warning: нехватка переведённых значений для ключа {k}")
            else:
                translated_lines.append(line)

        if value_idx != len(translated_values):
            print(f"Warning: переведено {value_idx} из {len(translated_values)} строк")

        # Сохраняем как {full_target_code}.lang
        target_filename = f"{full_target_code}.lang"
        target_file = os.path.join(os.path.dirname(lang_file), target_filename)
        with open(target_file, 'w', encoding='utf-8') as f:
            f.writelines(translated_lines)
        print(f"Переведен LANG: {lang_file} -> {target_file}")


def process_mod(mod_path: str, output_path: str, target_lang_short: str):
    """Обрабатывает один мод: распаковывает, находит локализации, переводит, упаковывает обратно."""
    # Временная папка системы
    temp_dir = tempfile.mkdtemp()

    # Распаковка
    with zipfile.ZipFile(mod_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # Поиск файлов локализации везде
    lang_files = []
    for root, _, files in os.walk(temp_dir):
        for file in files:
            if file.endswith('.json') or file.endswith('.lang'):
                full_path = os.path.join(root, file)
                if is_localization_file(full_path):
                    lang_files.append(full_path)

    if not lang_files:
        print(f"Нет файлов локализации в {mod_path}. Пропуск.")
        shutil.rmtree(temp_dir)
        return

    # Если несколько, предпочитаем en_us, иначе первый
    source_files = sorted(lang_files, key=lambda f: 0 if 'en_us' in os.path.basename(f).lower() else 1)
    # Переводим каждый, если target не существует
    for source_file in source_files:
        ext = os.path.splitext(source_file)[1]
        target_filename = f"{get_full_lang_code(target_lang_short, is_legacy=ext == '.lang')}{ext}"
        target_path = os.path.join(os.path.dirname(source_file), target_filename)
        if not os.path.exists(target_path):
            process_lang_file(source_file, target_lang_short)
        else:
            print(f"Целевой файл уже существует: {target_path}. Пропуск.")

    # Упаковка обратно
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, temp_dir)
                zip_out.write(full_path, arcname)

    # Очистка
    shutil.rmtree(temp_dir)
    print(f"Мод переведен: {mod_path} -> {output_path}")


def main():
    target_lang_short = input("Введите код целевого языка (например, ru): ").strip()
    if not target_lang_short:
        target_lang_short = 'ru'
    print(f"Целевой язык: {target_lang_short}")

    if not os.path.exists(MODS_FOLDER):
        print(f"Папка {MODS_FOLDER} не найдена. Создайте её и положите моды.")
        return

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    for filename in os.listdir(MODS_FOLDER):
        if filename.endswith('.jar'):
            mod_path = os.path.join(MODS_FOLDER, filename)
            output_path = os.path.join(OUTPUT_FOLDER, filename)
            process_mod(mod_path, output_path, target_lang_short)


if __name__ == "__main__":
    main()