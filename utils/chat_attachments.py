"""
Модуль для безопасной обработки и сохранения вложений из чата (изображений).

Использует Pillow для валидации реального содержимого файла.
Автоматически создаёт директорию при первом обращении.
Поддерживает только разрешённые форматы изображений (JPEG, PNG, GIF и др.).
Возвращает относительный путь для сохранения в БД.
"""
import os
from werkzeug.utils import secure_filename
import uuid
from flask import current_app
from PIL import Image  # Pillow для надёжной валидации изображений
from datetime import datetime, timezone


def save_chat_attachment(uploaded_file):
    """
    Сохраняет файл вложения из чата с полной валидацией через Pillow.

    Поддерживает ТОЛЬКО изображения, разрешённые в CHAT_ALLOWED_IMAGE_FORMATS.
    Возвращает относительный путь от корня приложения для сохранения в БД.

    Args:
        uploaded_file (FileStorage): файл из request.files

    Returns:
        str: относительный путь (например, 'uploads/chat/2025/11/uuid.jpg')

    Raises:
        ValueError: при нарушении правил валидации
    """

    # Загрузка настроек из конфига
    upload_base = current_app.config.get('CHAT_UPLOAD_FOLDER')
    allowed_formats = current_app.config.get('CHAT_ALLOWED_IMAGE_FORMATS', {'JPEG', 'PNG', 'GIF'})
    max_file_size = current_app.config.get('CHAT_MAX_FILE_SIZE', 5 * 1024 * 1024)

    if not upload_base:
        raise ValueError("CHAT_UPLOAD_FOLDER не настроен в конфигурации")

    # Проверка размера
    uploaded_file.stream.seek(0, os.SEEK_END)
    file_size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)

    if file_size > max_file_size:
        max_mb = max_file_size / (1024 * 1024)
        raise ValueError(f"Размер файла превышает допустимый лимит ({max_mb:.1f} МБ)")

    # Безопасное имя и расширение
    original_filename = secure_filename(uploaded_file.filename)
    if '.' not in original_filename:
        raise ValueError("Файл не имеет расширения")

    ext = original_filename.rsplit('.', 1)[1].lower()
    # Сопоставление расширений и форматов Pillow
    ext_to_format = {
        'jpg': 'JPEG',
        'jpeg': 'JPEG',
        'png': 'PNG',
        'gif': 'GIF',
    }
    expected_format = ext_to_format.get(ext)
    if expected_format is None or expected_format not in allowed_formats:
        allowed_exts = [k for k, v in ext_to_format.items() if v in allowed_formats]
        raise ValueError(
            f"Недопустимый формат файла. Допустимые расширения: {', '.join(allowed_exts)}"
        )

    # ВАЛИДАЦИЯ ЧЕРЕЗ PILLOW
    try:
        with Image.open(uploaded_file.stream) as img:
            img.verify()  # Проверяет целостность файла
        # После verify() поток "сломан", поэтому сбрасываем
        uploaded_file.stream.seek(0)
    except Exception as e:
        raise ValueError("Файл не является корректным изображением") from e

    # Повторное открытие для определения реального формата
    try:
        with Image.open(uploaded_file.stream) as img:
            actual_format = img.format
        uploaded_file.stream.seek(0)
    except Exception as e:
        raise ValueError("Не удалось определить формат изображения") from e

    if actual_format not in allowed_formats:
        raise ValueError(f"Формат изображения '{actual_format}' не разрешён")

    # Определяем расширение по реальному формату
    format_to_ext = {
        'JPEG': 'jpg',
        'PNG': 'png',
        'GIF': 'gif',
    }
    final_ext = format_to_ext.get(actual_format, 'jpg')  # fallback на jpg

    # Генерация пути с подкаталогами по году/месяцу 
    now = datetime.now(timezone.utc)
    year_month = f"{now.year}/{now.month:02d}"
    upload_dir = os.path.join(upload_base, year_month)
    os.makedirs(upload_dir, exist_ok=True)

    # Уникальное имя
    unique_filename = f"{uuid.uuid4().hex}.{final_ext}"
    full_path = os.path.join(upload_dir, unique_filename)

    # Сохранение
    uploaded_file.save(full_path)

    # Относительный путь от root_path
    rel_path = os.path.relpath(full_path, start=current_app.root_path)
    return rel_path.replace(os.sep, '/')


def get_attachment_absolute_path(relative_path):
    """
    Преобразует относительный путь (из БД) в абсолютный путь на диске.
    """
    return os.path.join(current_app.root_path, relative_path)