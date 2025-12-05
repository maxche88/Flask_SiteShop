import os
import uuid
from typing import List, Optional
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from flask import current_app
import logging


sys_logger = logging.getLogger('app.system')


def save_uploaded_files(
    files: List[FileStorage],
    subfolder: str,
    allowed_extensions: Optional[set] = None,
    max_file_size: Optional[int] = None
) -> List[str]:
    """
    Сохраняет файлы в static/uploads/{subfolder} и возвращает URL-пути.
    Args:
        files (List[FileStorage]): Список файлов из request.files.getlist(...)
        subfolder (str): Имя подкаталога внутри static/uploads (например, 'bug_reports')
        allowed_extensions (set, optional): Разрешённые расширения (без точки, в нижнем регистре)
        max_file_size (int, optional): Макс. размер файла в байтах

    Returns:
        List[str]: Список URL-путей: ['/static/uploads/{subfolder}/uuid.png', ...]
    """
    if not files:
        return []

    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'log'}

    # Путь на диске: static/uploads/{subfolder}
    base_dir = os.path.join(current_app.root_path, 'static', 'uploads')
    target_dir = os.path.join(base_dir, subfolder)
    os.makedirs(target_dir, exist_ok=True)

    saved_urls = []

    for file in files:
        if not file or not file.filename.strip():
            continue

        # Безопасное имя и расширение
        filename = secure_filename(file.filename)
        if not filename or '.' not in filename:
            raise ValueError("Файл не имеет корректного имени или расширения")

        ext = filename.rsplit('.', 1)[1].lower()
        if ext not in allowed_extensions:
            raise ValueError(f"Недопустимый формат файла. Допустимые: {', '.join(allowed_extensions)}")

        # Проверка размера (если задан)
        if max_file_size is not None:
            file.stream.seek(0, os.SEEK_END)
            file_size = file.stream.tell()
            file.stream.seek(0)
            if file_size > max_file_size:
                max_mb = max_file_size / (1024 * 1024)
                raise ValueError(f"Размер файла превышает лимит ({max_mb:.1f} МБ)")

        # Генерируем уникальное имя и сохраняем файл
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        full_path = os.path.join(target_dir, unique_name)
        file.save(full_path)

        # Формируем публичный URL
        url_path = f"/static/uploads/{subfolder}/{unique_name}"
        saved_urls.append(url_path)

        sys_logger.debug(f"Файл сохранён: {full_path} → {url_path}")

    return saved_urls


def delete_uploaded_files(url_paths: List[str]) -> List[str]:
    """
    Удаляет физические файлы по списку URL-путей вида ['/static/uploads/...'].
    Логирует только технические события (успех/ошибка на уровне ОС).
    
    Возвращает список путей, которые не удалось удалить.
    """
    if not url_paths:
        return []

    failed_paths = []
    for url_path in url_paths:
        url_path = url_path.strip()
        if not url_path:
            continue

        # Защита: удаляем ТОЛЬКО из /static/
        if not url_path.startswith('/static/'):
            failed_paths.append(url_path)
            continue

        relative_path = url_path.lstrip('/')
        full_path = os.path.join(current_app.root_path, relative_path)

        try:
            if os.path.isfile(full_path):
                os.remove(full_path)
                sys_logger.debug(f"Файл успешно удалён: {full_path}")
            # else: файла нет — считаем успехом (идемпотентность)
        except OSError as e:
            sys_logger.error(f"Ошибка ОС при удалении файла '{full_path}': {e}")
            failed_paths.append(url_path)

    return failed_paths