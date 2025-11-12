from flask import request, render_template, jsonify

def render_or_json(template_name=None, context=None, json_data=None, status_code=200, is_success=True):
    """
    Возвращает HTML-страницу или JSON в зависимости от Accept-заголовка.
    
    :param template_name: имя шаблона (для HTML)
    :param context: словарь с данными для шаблона
    :param json_data: данные для JSON-ответа
    :param status_code: HTTP-статус
    :param is_success: если True — использует 'message', иначе 'error' в контексте шаблона
    """
    context = context or {}
    json_data = json_data or {}

    if 'text/html' in request.accept_mimetypes:
        if template_name is None:
            raise ValueError("Для HTML-ответа необходимо указать template_name")
        # В шаблоне ожидается либо 'message', либо 'error'
        key = 'message' if is_success else 'error'
        # Берём сообщение из json_data или context
        message = json_data.get('message') or context.get(key)
        render_context = {key: message}
        return render_template(template_name, **render_context), status_code
    else:
        # JSON-ответ
        response_data = {
            'success': is_success,
            'message': json_data.get('message') or context.get('message') or context.get('error')
        }
        return jsonify(response_data), status_code