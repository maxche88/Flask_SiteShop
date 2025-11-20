# Добавление файла с изображением товара.

import os

from werkzeug.utils import secure_filename
import uuid
from flask import current_app


def save_product_image(image_file):
    """
    Сохраняет изображение товара с учётом настроек из конфигурации:
    - UPLOAD_FOLDER
    - ALLOWED_EXTENSIONS
    - MAX_CONTENT_LENGTH

    Возвращает URL-путь /static/img/products/новое_имя_файла
    """
    upload_folder = current_app.config['UPLOAD_FOLDER']
    allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    max_file_size = current_app.config['MAX_CONTENT_LENGTH']

    # Проверка размера файла
    # image_file — это FileStorage, он не имеет .seek() по умолчанию в multipart/form-data,
    # поэтому используем .read(), но потом нужно вернуть указатель в начало.
    image_file.stream.seek(0, os.SEEK_END)
    file_size = image_file.stream.tell()
    image_file.stream.seek(0)  # возвращаем в начало для последующего save()

    if file_size > max_file_size:
        max_mb = max_file_size / (1024 * 1024)
        raise ValueError(f"Размер файла превышает допустимый лимит ({max_mb:.1f} МБ)")

    # Безопасное имя файла
    filename = secure_filename(image_file.filename)
    if '.' not in filename:
        raise ValueError("Файл не имеет расширения")

    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        raise ValueError(f"Недопустимый формат файла. Допустимые: {', '.join(allowed_extensions)}")

    # Создание папки и сохранение
    os.makedirs(upload_folder, exist_ok=True)

    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(upload_folder, unique_filename)
    image_file.save(file_path)

    # Формирование URL-пути (относительно корня static/)
    try:
        # Получаем абсолютные пути
        static_abs = os.path.abspath(current_app.static_folder)
        upload_abs = os.path.abspath(upload_folder)

        # Пытаемся вычислить относительный путь от static к папке загрузки
        rel_to_static = os.path.relpath(upload_abs, static_abs)

        # Формируем итоговый URL: /static/.../filename
        return f"/{rel_to_static.replace(os.sep, '/')}/{unique_filename}"
    
    except ValueError:
        # Fallback: возвращаем просто имя файла (предполагается, что UPLOAD_FOLDER внутри static)
        return f"/{unique_filename}"