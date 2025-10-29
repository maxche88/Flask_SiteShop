# Добавление файла с изображением товара.

import os
from werkzeug.utils import secure_filename

import uuid

def save_product_image(image_file, upload_folder='static/img/products', allowed_extensions={'jpg', 'jpeg', 'png'}):
    filename = secure_filename(image_file.filename)
    if '.' not in filename:
        raise ValueError("Файл не имеет расширения")
    
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        raise ValueError("Недопустимый формат файла")
    
    os.makedirs(upload_folder, exist_ok=True)
    
    # Уникальное имя
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(upload_folder, unique_filename)
    image_file.save(file_path)
    
    return f"/img/products/{unique_filename}"