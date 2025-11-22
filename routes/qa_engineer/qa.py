import os
import uuid
from flask import Blueprint, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, BugReport, User


qa_bp = Blueprint('qa-engineer', __name__, template_folder='templates')


@qa_bp.route('/qa-engineer')
@jwt_required()
def qa_dashboard():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    # роль 'test' или 'admin' имеет доступ
    if user.role not in ['test', 'admin']:
        return redirect(url_for('main.index'))  # или 403
    return render_template('qa-engineer/qa.html')


# Настройки загрузки (лучше вынести в config)
UPLOAD_FOLDER = 'static/uploads/bug_reports'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'txt', 'log'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@qa_bp.route('/api/bug-reports', methods=['POST'])
@jwt_required()
def create_bug_report():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in ['test', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    try:
        # Обработка ссылки
        attachment_link = request.form.get('attachment_link', '').strip()
        attachments_value = None

        if attachment_link:
            # Просто сохраняем ссылку как строку
            attachments_value = attachment_link
        else:
            # Обработка файлов
            files = request.files.getlist('attachment_files')
            saved_paths = []
            for file in files:
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4().hex}.{filename.rsplit('.', 1)[1].lower()}"
                    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                    file.save(filepath)
                    saved_paths.append(f"/{UPLOAD_FOLDER}/{unique_filename}")
            if saved_paths:
                attachments_value = ','.join(saved_paths)

        # Создание записи
        new_report = BugReport(
            title=request.form['bugTitle'],
            severity=request.form['bugSeverity'],
            status=request.form['bugStatus'],
            precondition=request.form.get('bugPrecondition') or None,
            environment=request.form['bugEnvironment'],
            steps_to_reproduce=request.form['bugSteps'],
            actual_result=request.form['bugActual'],
            expected_result=request.form['bugExpected'],
            attachments=attachments_value,
            author_id=current_user_id
        )

        db.session.add(new_report)
        db.session.commit()

        return jsonify({'message': 'Баг-репорт создан', 'id': new_report.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера'}), 500