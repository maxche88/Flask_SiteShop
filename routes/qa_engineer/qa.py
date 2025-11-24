import os
import uuid
from flask import current_app, Blueprint, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, BugReport, User
from sqlalchemy import case


qa_bp = Blueprint('qa-engineer', __name__, template_folder='templates')


@qa_bp.route('/qa-engineer')
@jwt_required()
def qa_dashboard():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    # роль 'tester' или 'admin' имеет доступ
    if user.role not in ['tester', 'admin']:
        return redirect(url_for('main.index'))
    return render_template('qa-engineer/qa.html')


@qa_bp.route('/api/bug-reports', methods=['POST'])
@jwt_required()
def create_bug_report():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    # Получаем настройки из конфига
    upload_folder = current_app.config['BUG_REPORT_UPLOAD_FOLDER']
    allowed_extensions = current_app.config['BUG_REPORT_ALLOWED_EXTENSIONS']

    # Создаём папку, если не существует
    os.makedirs(upload_folder, exist_ok=True)

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

    try:
        # Обработка ссылки
        attachment_link = request.form.get('attachment_link', '').strip()
        attachments_value = None

        if attachment_link:
            # Cохраняем ссылку как строку
            attachments_value = attachment_link
        else:
            # Обработка файлов
            files = request.files.getlist('attachment_files')
            saved_paths = []
            for file in files:
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4().hex}.{filename.rsplit('.', 1)[1].lower()}"
                    filepath = os.path.join(upload_folder, unique_filename)
                    file.save(filepath)
                    saved_paths.append(f"/static/uploads/bug_reports/{unique_filename}")
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



@qa_bp.route('/api/bug-reports', methods=['GET'])
@jwt_required()
def get_bug_reports():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    # Определяем порядок severity для сортировки в PostgreSQL
    severity_order = case(
        (BugReport.severity == 'critical', 1),
        (BugReport.severity == 'high', 2),
        (BugReport.severity == 'medium', 3),
        (BugReport.severity == 'low', 4),
        else_=5
    )

    reports = BugReport.query.order_by(
        severity_order,
        BugReport.updated_at.desc()
    ).all()

    result = [
        {
            'id': r.id,
            'author_id': r.author_id,
            'title': r.title,
            'severity': r.severity,
            'status': r.status,
            'updated_at': r.updated_at.isoformat() if r.updated_at else None
        }
        for r in reports
    ]

    return jsonify(result), 200

@qa_bp.route('/api/bug-reports/bulk-update-status', methods=['PATCH'])
@jwt_required()
def bulk_update_bug_status():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    data = request.get_json()
    ids = data.get('ids')
    new_status = data.get('status')

    if not ids or not isinstance(ids, list) or not new_status:
        return jsonify({'error': 'Некорректные данные'}), 400

    if new_status not in ['new', 'open', 'in_progress', 'resolved', 'closed']:
        return jsonify({'error': 'Недопустимый статус'}), 400

    # Обновляем только свои баг-репорты (или все, если admin)
    query = BugReport.query.filter(BugReport.id.in_(ids))
    if user.role != 'admin':
        query = query.filter(BugReport.author_id == current_user_id)

    reports = query.all()
    if not reports:
        return jsonify({'error': 'Нет доступных баг-репортов для обновления'}), 400

    for report in reports:
        report.status = new_status

    db.session.commit()
    return jsonify({'message': f'Обновлено {len(reports)} записей'}), 200


@qa_bp.route('/api/bug-reports/<int:bug_id>', methods=['GET'])
@jwt_required()
def get_bug_report(bug_id):
    """
    Получение деталей конкретного баг-репорта по его ID.
    
    Доступ разрешён только:
      - Администраторам (могут читать любые репорты)
    
    Возвращает 403 при недостатке прав, 404 если репорт не найден.
    """
    # Получаем ID текущего пользователя из JWT-токена
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    # Проверяем, существует ли пользователь и имеет ли допустимую роль
    if not user or user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    # Ищем баг-репорт по переданному ID
    report = BugReport.query.get(bug_id)

    if not report:
        return jsonify({'error': 'Баг-репорт не найден'}), 404

    # Возвращаем данные репорта в стандартизированном формате
    return jsonify({
        'id': report.id,
        'author_id': report.author_id,
        'title': report.title,
        'severity': report.severity,
        'status': report.status,
        'precondition': report.precondition,
        'environment': report.environment,
        'steps_to_reproduce': report.steps_to_reproduce,
        'actual_result': report.actual_result,
        'expected_result': report.expected_result,
        'attachments': report.attachments,
        'created_at': report.created_at.isoformat() if report.created_at else None,
        'updated_at': report.updated_at.isoformat() if report.updated_at else None
    }), 200