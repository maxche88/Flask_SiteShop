import os
import uuid
from flask import current_app, Blueprint, render_template, redirect, url_for, g, request, jsonify
from werkzeug.utils import secure_filename
from models import BugReport, Checklist
from extensions import db
from sqlalchemy import case


qa_bp = Blueprint('qa-engineer', __name__, template_folder='templates')


@qa_bp.route('/qa-engineer')
def qa_dashboard():
    user = g.current_user
    if user.role not in ['tester', 'admin']:
        return redirect(url_for('main.index'))
    return render_template('qa-engineer/qa_bug_reports.html')


#  ЧЕК-ЛИСТЫ
# === Страница чек-листов ===
@qa_bp.route('/checklists')
def checklists_page():
    user = g.current_user
    if user.role not in ['tester', 'admin']:
        return redirect(url_for('main.index'))
    return render_template('qa-engineer/checklists.html')


# === GET: все чек-листы текущего пользователя ===
@qa_bp.route('/api/checklists', methods=['GET'])
def get_checklists():
    user = g.current_user
    if user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    checklists = Checklist.query.filter_by(author_id=g.current_user_id).order_by(Checklist.created_at.desc()).all()

    result = []
    for cl in checklists:
        items = cl.items
        total = len(items)
        completed = sum(1 for item in items if item.get('is_done'))
        result.append({
            'id': cl.id,
            'title': cl.title,
            'author_id': cl.author_id,
            'total_items': total,
            'completed_items': completed,
            'created_at': cl.created_at.isoformat()
        })

    return jsonify(result), 200


# === POST: создать чек-лист ===
@qa_bp.route('/api/checklists', methods=['POST'])
def create_checklist():
    user = g.current_user
    if user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    data = request.get_json()
    title = (data.get('title') or '').strip()
    raw_items = data.get('items', [])

    if not title:
        return jsonify({'error': 'Требуется название'}), 400
    if not isinstance(raw_items, list):
        return jsonify({'error': 'Пункты должны быть массивом'}), 400

    # Валидация и фильтрация пунктов
    items = []
    for idx, item in enumerate(raw_items):
        action_name = (item.get('action_name') or '').strip()
        if action_name:
            items.append({
                'id_item': idx + 1,
                'action_name': action_name,
                'result': None,
                'comment': '',
            })

    if not items:
        return jsonify({'error': 'Нет валидных пунктов'}), 400

    try:
        new_cl = Checklist(
            title=title,
            author_id=g.current_user_id
        )
        new_cl.items = items  # вызывает setter → JSON
        db.session.add(new_cl)
        db.session.commit()

        return jsonify({'message': 'Чек-лист создан', 'id': new_cl.id}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка создания чек-листа: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500

# === GET: один чек-лист ===
@qa_bp.route('/api/checklists/<int:checklist_id>', methods=['GET'])
def get_checklist(checklist_id):
    user = g.current_user
    if user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    cl = Checklist.query.filter_by(id=checklist_id, author_id=g.current_user_id).first()
    if not cl:
        return jsonify({'error': 'Чек-лист не найден'}), 404

    return jsonify({
        'id': cl.id,
        'title': cl.title,
        'author_id': cl.author_id,
        'items': cl.items,
        'created_at': cl.created_at.isoformat(),
        'updated_at': cl.updated_at.isoformat()
    }), 200


# === PATCH: полное редактирование чек-листа с пересчётом ===
@qa_bp.route('/api/checklists/<int:checklist_id>', methods=['PATCH'])
def update_checklist_full(checklist_id):
    user = g.current_user
    if user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    cl = Checklist.query.filter_by(id=checklist_id, author_id=g.current_user_id).first()
    if not cl:
        return jsonify({'error': 'Чек-лист не найден'}), 404

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'Ожидается объект'}), 400

    changed = False

    # Обновляем title
    if 'title' in data:
        title = (data['title'] or '').strip()
        if not title:
            return jsonify({'error': 'Название не может быть пустым'}), 400
        cl.title = title
        changed = True

    # Обновляем пункты
    if 'items' in data:
        raw_items = data['items']
        if not isinstance(raw_items, list):
            return jsonify({'error': 'Пункты должны быть массивом'}), 400

        old_items = cl.items or []
        new_items = []

        for idx, item_update in enumerate(raw_items):
            if not isinstance(item_update, dict):
                return jsonify({'error': 'Каждый пункт должен быть объектом'}), 400

            action_name = (item_update.get('action_name') or '').strip()
            if not action_name:
                return jsonify({'error': 'Название действия обязательно'}), 400

            # Сопоставляем по индексу: если индекс в пределах старого массива — берём данные
            if idx < len(old_items):
                old_item = old_items[idx]
                result = old_item.get('result')
                comment = old_item.get('comment', '')
            else:
                result = None
                comment = ''

            new_items.append({
                'id_item': idx + 1,
                'action_name': action_name,
                'result': result,
                'comment': comment
            })

        cl.items = new_items
        changed = True

    if not changed:
        return jsonify({'error': 'Нечего обновлять'}), 400

    try:
        db.session.commit()
        return jsonify({'message': 'Чек-лист обновлён'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка обновления чек-листа {checklist_id}: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500


# === PATCH: обновить отдельный пункт чек-листа по индексу ===
@qa_bp.route('/api/checklists/<int:checklist_id>/items/<int:index>', methods=['PATCH'])
def update_checklist_item(checklist_id, index):
    user = g.current_user
    if user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    cl = Checklist.query.filter_by(id=checklist_id, author_id=g.current_user_id).first()
    if not cl:
        return jsonify({'error': 'Чек-лист не найден'}), 404

    items = cl.items
    if not isinstance(items, list) or index < 0 or index >= len(items):
        return jsonify({'error': 'Неверный индекс пункта'}), 400

    data = request.get_json()
    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'Ожидается объект с полями для обновления'}), 400

    item = items[index]
    valid_results = {'passed', 'failed', 'blocked', 'skipped'}
    updated = False

    # Обновляем action_name
    if 'action_name' in data:
        action_name = (data['action_name'] or '').strip()
        if not action_name:
            return jsonify({'error': 'Название действия не может быть пустым'}), 400
        item['action_name'] = action_name
        updated = True

    # Обновляем result
    if 'result' in data:
        result = data['result']
        if result is not None and result not in valid_results:
            return jsonify({'error': 'Недопустимое значение result'}), 400
        item['result'] = result
        updated = True

    # Обновляем comment
    if 'comment' in data:
        comment = data['comment']
        if not isinstance(comment, str):
            return jsonify({'error': 'Комментарий должен быть строкой'}), 400
        item['comment'] = comment.strip()
        updated = True

    if not updated:
        return jsonify({'error': 'Нечего обновлять в пункте'}), 400

    try:
        cl.items = items
        db.session.commit()
        return jsonify({'message': 'Пункт обновлён'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка обновления пункта {index} в чек-листе {checklist_id}: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500


# === PATCH: отметить все пункты как выполненные (result = 'passed') ===
@qa_bp.route('/api/checklists/<int:checklist_id>/mark-all-done', methods=['PATCH'])
def mark_all_items_done(checklist_id):
    user = g.current_user
    if user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    cl = Checklist.query.filter_by(id=checklist_id, author_id=g.current_user_id).first()
    if not cl:
        return jsonify({'error': 'Чек-лист не найден'}), 404

    try:
        items = cl.items
        if not isinstance(items, list):
            return jsonify({'error': 'Некорректная структура пунктов'}), 500

        for item in items:
            item['result'] = 'passed'

        cl.items = items
        db.session.commit()
        return jsonify({'message': 'Все пункты отмечены как выполненные'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка отметки всех пунктов: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500


# === DELETE: удалить чек-лист ===
@qa_bp.route('/api/checklists/<int:checklist_id>', methods=['DELETE'])
def delete_checklist(checklist_id):
    user = g.current_user
    if user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    # Админ может удалять любой чек-лист, tester — только свой
    if user.role == 'admin':
        cl = Checklist.query.get(checklist_id)
    else:  # tester
        cl = Checklist.query.filter_by(id=checklist_id, author_id=user.id).first()

    if not cl:
        return jsonify({'error': 'Чек-лист не найден или недоступен'}), 404

    try:
        db.session.delete(cl)
        db.session.commit()
        return jsonify({'message': 'Чек-лист удалён'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка удаления чек-листа {checklist_id}: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500


#  БАГ-РЕПОРТЫ
@qa_bp.route('/api/bug-reports', methods=['POST'])
def create_bug_report():
    user = g.current_user
    
    if user.role not in ['tester', 'admin']:
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
            author_id=g.current_user_id
        )

        db.session.add(new_report)
        db.session.commit()

        return jsonify({'message': 'Баг-репорт создан', 'id': new_report.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера'}), 500



@qa_bp.route('/api/bug-reports', methods=['GET'])
def get_bug_reports():
    user = g.current_user
    
    if user.role not in ['tester', 'admin']:
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


@qa_bp.route('/api/bug-reports/update-status', methods=['PATCH'])
def update_bug_status():
    user = g.current_user
    
    if user.role not in ['tester', 'admin']:
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
        query = query.filter(BugReport.author_id == g.current_user_id)

    reports = query.all()
    if not reports:
        return jsonify({'error': 'Нет доступных баг-репортов для обновления'}), 400

    for report in reports:
        report.status = new_status

    db.session.commit()
    return jsonify({'message': f'Обновлено {len(reports)} записей'}), 200


@qa_bp.route('/api/bug-reports/<int:bug_id>', methods=['GET'])
def get_bug_report(bug_id):
    """
    Получение деталей конкретного баг-репорта по его ID.
    
    Доступ разрешён только:
      - Администраторам (могут читать любые репорты)
    
    Возвращает 403 при недостатке прав, 404 если репорт не найден.
    """
    user = g.current_user

    if user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    # Ищем баг-репорт по переданному ID
    report = db.session.get(BugReport, bug_id)

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


@qa_bp.route('/api/bug-reports/delete-selected', methods=['DELETE'])
def delete_selected_bug_reports():
    user = g.current_user
    if user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    data = request.get_json()
    ids = data.get('ids')
    if not ids or not isinstance(ids, list):
        return jsonify({'error': 'Некорректные данные'}), 400

    # Формируем запрос
    query = BugReport.query.filter(BugReport.id.in_(ids))
    if user.role == 'tester':
        # tester может удалять только свои
        query = query.filter(BugReport.author_id == g.current_user_id)

    reports_to_delete = query.all()
    if not reports_to_delete:
        return jsonify({'error': 'Нет доступных баг-репортов для удаления'}), 400

    deleted_ids = [r.id for r in reports_to_delete]
    for report in reports_to_delete:
        db.session.delete(report)

    db.session.commit()
    return jsonify({
        'message': 'Удалено успешно',
        'deleted_count': len(deleted_ids),
        'deleted_ids': deleted_ids
    }), 200