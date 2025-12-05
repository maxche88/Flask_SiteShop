from flask import current_app, Blueprint, render_template, redirect, url_for, g, request, jsonify
from models import BugReport, Checklist
from extensions import db
from sqlalchemy import case
from utils.file_utils import save_uploaded_files, delete_uploaded_files
import logging


qa_bp = Blueprint('qa-engineer', __name__, template_folder='templates')
sys_logger = logging.getLogger('app.system')


@qa_bp.route('/qa-engineer')
def qa_dashboard():
    user = g.current_user
    if user.role not in ['tester', 'admin']:
        return redirect(url_for('main.index'))
    return render_template('qa-engineer/qa_bug_reports.html')


#  Страница с чек-листами
@qa_bp.route('/checklists')
def checklists_page():
    user = g.current_user
    if user.role not in ['tester', 'admin']:
        return redirect(url_for('main.index'))
    return render_template('qa-engineer/checklists.html')


# Все чек-листы текущего пользователя
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


# Создать чек-лист
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

# Один чек-лист
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


# Полное редактирование чек-листа
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


# Обновить отдельный пункт чек-листа по индексу
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


# Отметить все пункты как выполненные (result = 'passed')
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


# Удалить чек-лист
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
    if not user or user.role not in ['tester', 'admin']:
        return jsonify({'error': 'Доступ запрещён'}), 403

    try:
        # Получаем внешнюю ссылку (если есть)
        attachment_link = request.form.get('attachment_link', '').strip()

        attachments_value = None

        # Если есть внешняя ссылка — используем её
        if attachment_link:
            # Базовая валидация (например, что это URL)
            if attachment_link.startswith(('http://', 'https://')):
                attachments_value = attachment_link
            else:
                return jsonify({'error': 'Некорректный формат ссылки. Укажите полный URL.'}), 400

        # Иначе — проверяем, загружены ли файлы
        else:
            files = request.files.getlist('attachment_files')
            # Фильтруем "пустые" файлы
            actual_files = [f for f in files if f and f.filename]
            
            if actual_files:
                # Сохраняем файлы через универсальную функцию
                saved_urls = save_uploaded_files(
                    files=request.files.getlist('attachment_files'),
                    subfolder='bug_reports',
                    allowed_extensions=current_app.config.get('BUG_REPORTS_ALLOWED_EXTENSIONS'),
                    max_file_size=current_app.config.get('BUG_REPORTS_MAX_FILE_SIZE')
                )
                if saved_urls:
                    attachments_value = ','.join(saved_urls)

        # 4. Создаём баг-репорт
        new_report = BugReport(
            title=request.form['bugTitle'].strip(),
            severity=request.form['bugSeverity'],
            status=request.form['bugStatus'],
            precondition=request.form.get('bugPrecondition') or None,
            environment=request.form['bugEnvironment'].strip(),
            steps_to_reproduce=request.form['bugSteps'].strip(),
            actual_result=request.form['bugActual'].strip(),
            expected_result=request.form['bugExpected'].strip(),
            attachments=attachments_value,
            author_id=user.id
        )

        db.session.add(new_report)
        db.session.commit()

        return jsonify({
            'message': 'Баг-репорт создан',
            'id': new_report.id
        }), 201

    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except KeyError as e:
        # Отсутствует обязательное поле в form
        db.session.rollback()
        return jsonify({'error': f'Отсутствует поле: {e.args[0]}'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка при создании баг-репорта: {e}")
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
    Доступ разрешён только пользователям с ролью: admin и tester
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
        sys_logger.warning(f"Попытка удаления баг-репортов без прав: user_id={user.id}, role={user.role}")
        return jsonify({'error': 'Доступ запрещён'}), 403

    data = request.get_json()
    ids = data.get('ids')

    if not ids or not isinstance(ids, list):
        sys_logger.warning(f"Некорректные данные при удалении баг-репортов от user_id={user.id}: {data}")
        return jsonify({'error': 'Некорректные данные'}), 400

    query = BugReport.query.filter(BugReport.id.in_(ids))

    if user.role == 'tester':
        query = query.filter(BugReport.author_id == user.id)

    reports_to_delete = query.all()
    
    if not reports_to_delete:
        sys_logger.info(f"Попытка удаления несуществующих или чужих баг-репортов: user_id={user.id}, ids={ids}")
        return jsonify({'error': 'Нет доступных баг-репортов для удаления'}), 400

    # Собираем файлы
    all_local_paths = []
    for report in reports_to_delete:
        att = report.attachments
        if att and not att.startswith(('http://', 'https://')):
            paths = [p.strip() for p in att.split(',') if p.strip()]
            all_local_paths.extend(paths)

    # Логируем намерение удалить файлы
    if all_local_paths:
        sys_logger.info(
            f"Пользователь user_id={user.id} удаляет {len(reports_to_delete)} баг-репортов "
            f"с {len(all_local_paths)} вложениями: {all_local_paths}"
        )
        failed_paths = delete_uploaded_files(all_local_paths)
        if failed_paths:
            sys_logger.warning(
                f"Не удалось удалить {len(failed_paths)} файлов при удалении баг-репортов "
                f"пользователем user_id={user.id}: {failed_paths}"
            )
    else:
        sys_logger.info(f"Пользователь user_id={user.id} удаляет {len(reports_to_delete)} баг-репортов без вложений")

    # Удаляем из БД
    deleted_ids = [r.id for r in reports_to_delete]
    for report in reports_to_delete:
        db.session.delete(report)
    db.session.commit()

    sys_logger.info(f"Успешно удалено {len(deleted_ids)} баг-репортов: {deleted_ids} (user_id={user.id})")

    return jsonify({
        'message': 'Удалено успешно',
        'deleted_count': len(deleted_ids),
        'deleted_ids': deleted_ids
    }), 200