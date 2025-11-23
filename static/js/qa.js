document.addEventListener('DOMContentLoaded', () => {
    // === Элементы DOM ===
    const modal = document.getElementById('bugReportModalBackdrop');
    const openBtn = document.getElementById('openBugReportModalBtn');
    const cancelBtn = document.getElementById('cancelBugReportBtn');
    const form = document.getElementById('createBugReportForm');
    const clearFormBtn = document.getElementById('clearFormBtn');
    const detectEnvBtn = document.getElementById('detectEnvBtn');
    const triggerBtn = document.getElementById('toggleAttachmentType');
    const linkInput = document.getElementById('bugAttachmentInput');
    const fileInput = document.getElementById('bugAttachmentFile');
    const filePreview = document.getElementById('filePreview');
    const tableBody = document.getElementById('bugReportsTableBody');
    const errorDiv = document.getElementById('bugReportsError');
    const selectAll = document.getElementById('selectAllReports');
    const editStatusBtn = document.getElementById('editBugReportStatusBtn');
    const statusDropdown = document.getElementById('statusDropdown');
    const viewModal = document.getElementById('viewBugReportModalBackdrop');
    const closeViewBtn = document.getElementById('closeViewModalBtn');

    // === Вспомогательные функции ===
    const escapeHtml = (text) => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };

    const formatDateTime = (isoString) => {
        if (!isoString) return '—';
        return new Date(isoString).toLocaleString('ru-RU', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const handleSelectAll = () => {
        const checkboxes = document.querySelectorAll('.report-checkbox');
        checkboxes.forEach(cb => cb.checked = selectAll.checked);
    };

    // === Загрузка баг-репортов ===
    const loadBugReports = async () => {
        if (!tableBody) return;

        try {
            const response = await fetch('api/bug-reports');
            if (!response.ok) throw new Error('Ошибка загрузки');

            const reports = await response.json();
            tableBody.innerHTML = '';

            const template = document.getElementById('bug-report-row-template');
            reports.forEach(report => {
                const row = template.content.cloneNode(true);
                const container = row.querySelector('.bug-report-row');

                container.querySelector('.report-checkbox').dataset.id = report.id;
                container.querySelector('.id-cell').textContent = report.id;
                container.querySelector('.author-id-cell').textContent = report.author_id;
                container.querySelector('.title-cell').textContent = escapeHtml(report.title);

                const severityCell = container.querySelector('.severity-cell');
                severityCell.textContent = report.severity;
                severityCell.dataset.severity = report.severity;

                container.querySelector('.status-cell').textContent = report.status;
                container.querySelector('.updated-at-cell').textContent = formatDateTime(report.updated_at);

                tableBody.appendChild(container);
            });

            if (selectAll) {
                selectAll.checked = false;
                selectAll.removeEventListener('change', handleSelectAll);
                selectAll.addEventListener('change', handleSelectAll);
            }

            if (errorDiv) errorDiv.style.display = 'none';
        } catch (err) {
            console.error('Ошибка загрузки баг-репортов:', err);
            if (errorDiv) {
                errorDiv.textContent = 'Не удалось загрузить список баг-репортов';
                errorDiv.style.display = 'block';
            }
        }
    };

    // === Модалка просмотра баг-репорта ===
    if (closeViewBtn && viewModal) {
        closeViewBtn.addEventListener('click', () => {
            viewModal.classList.remove('is-open');
        });
    }

    if (tableBody) {
        tableBody.addEventListener('click', async (e) => {
            const titleCell = e.target.closest('.title-cell');
            if (!titleCell) return;

            const row = titleCell.closest('.bug-report-row');
            const bugId = row.querySelector('.report-checkbox').dataset.id;

            try {
                const response = await fetch(`api/bug-reports/${bugId}`);
                if (!response.ok) throw new Error('Баг-репорт не найден');

                const report = await response.json();
                renderViewModal(report);
                viewModal.classList.add('is-open');
            } catch (err) {
                alert('Ошибка загрузки баг-репорта');
                console.error(err);
            }
        });
    }

    const renderViewModal = (report) => {
        document.getElementById('viewBugId').textContent = report.id;

        const content = `
            <div class="view-field">
                <span class="view-label">Title / Заголовок</span>
                <span class="view-value">${escapeHtml(report.title)}</span>
            </div>
            <div class="view-field">
                <span class="view-label">Severity / Критичность</span>
                <span class="view-value view-severity ${report.severity}">${report.severity}</span>
            </div>
            <div class="view-field">
                <span class="view-label">Status / Статус</span>
                <span class="view-value">${report.status}</span>
            </div>
            <div class="view-field">
                <span class="view-label">Author ID</span>
                <span class="view-value">${report.author_id}</span>
            </div>
            <div class="view-field">
                <span class="view-label">Environment / Окружение</span>
                <span class="view-value ${!report.environment ? 'empty' : ''}">${report.environment || '—'}</span>
            </div>
            <div class="view-field">
                <span class="view-label">Precondition / Предусловия</span>
                <span class="view-value ${!report.precondition ? 'empty' : ''}">${report.precondition || '—'}</span>
            </div>
            <div class="view-field">
                <span class="view-label">Steps to reproduce / Шаги воспроизведения</span>
                <span class="view-value">${escapeHtml(report.steps_to_reproduce)}</span>
            </div>
            <div class="view-field">
                <span class="view-label">Actual result / Фактический результат</span>
                <span class="view-value">${escapeHtml(report.actual_result)}</span>
            </div>
            <div class="view-field">
                <span class="view-label">Expected result / Ожидаемый результат</span>
                <span class="view-value">${escapeHtml(report.expected_result)}</span>
            </div>
            <div class="view-field">
                <span class="view-label">Attachments / Вложения</span>
                <div class="view-attachments">
                    ${renderAttachments(report.attachments)}
                </div>
            </div>
            <div class="view-field">
                <span class="view-label">Created</span>
                <span class="view-value">${formatDateTime(report.created_at)}</span>
            </div>
            <div class="view-field">
                <span class="view-label">Updated</span>
                <span class="view-value">${formatDateTime(report.updated_at)}</span>
            </div>
        `;

        document.getElementById('viewBugContent').innerHTML = content;
    };

    const renderAttachments = (attachments) => {
        if (!attachments) return '<span class="empty">—</span>';
        if (attachments.startsWith('http')) {
            return `<a href="${escapeHtml(attachments)}" target="_blank" rel="noopener">Открыть ссылку</a>`;
        }
        const paths = attachments.split(',');
        return paths.map(path => {
            const filename = path.split('/').pop();
            return `<a href="${escapeHtml(path)}" target="_blank" rel="noopener">${escapeHtml(filename)}</a>`;
        }).join('<br>');
    };

    // === Массовое изменение статуса ===
    if (editStatusBtn && statusDropdown) {
        const positionDropdown = () => {
            const rect = editStatusBtn.getBoundingClientRect();
            statusDropdown.style.top = `${rect.bottom + window.scrollY + 4}px`;
            statusDropdown.style.left = `${rect.left + window.scrollX}px`;
            statusDropdown.style.display = 'block';
        };

        const hideDropdown = () => {
            statusDropdown.style.display = 'none';
        };

        editStatusBtn.addEventListener('click', () => {
            const checked = document.querySelectorAll('.report-checkbox:checked');
            if (checked.length === 0) {
                alert('Выберите хотя бы один баг-репорт.');
                return;
            }
            positionDropdown();
        });

        document.addEventListener('click', (e) => {
            if (!statusDropdown.contains(e.target) && e.target !== editStatusBtn) {
                hideDropdown();
            }
        });

        statusDropdown.addEventListener('click', async (e) => {
            const option = e.target.closest('.status-option');
            if (!option) return;

            const newStatus = option.dataset.status;
            const reportIds = Array.from(document.querySelectorAll('.report-checkbox:checked'))
                                   .map(cb => cb.dataset.id);

            const statusLabels = {
                new: 'New / Новый',
                open: 'Open / Открыт',
                in_progress: 'In Progress / В работе',
                resolved: 'Resolved / Исправлен',
                closed: 'Closed / Закрыт'
            };

            if (!confirm(`Вы действительно хотите изменить статус на "${statusLabels[newStatus]}" у ${reportIds.length} баг-репорт(ов)?`)) {
                hideDropdown();
                return;
            }

            try {
                const res = await fetch('api/bug-reports/bulk-update-status', {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ids: reportIds, status: newStatus })
                });

                if (res.ok) {
                    alert('Статус успешно обновлён.');
                    loadBugReports();
                } else {
                    const err = await res.json();
                    alert('Ошибка: ' + (err.error || 'не удалось обновить'));
                }
            } catch (err) {
                console.error('Ошибка обновления:', err);
                alert('Ошибка сети');
            } finally {
                hideDropdown();
            }
        });
    }

    // === Окружение ===
    if (detectEnvBtn) {
        detectEnvBtn.addEventListener('click', () => {
            const envInput = document.getElementById('bugEnvironment');
            if (envInput) envInput.value = (function detectEnv() {
                const ua = navigator.userAgent;
                let os = 'Unknown OS', browser = 'Unknown Browser';

                if (ua.includes('Windows')) {
                    if (ua.includes('Windows NT 10.0')) os = 'Windows 10';
                    else if (ua.includes('Windows NT 6.3')) os = 'Windows 8.1';
                    else if (ua.includes('Windows NT 6.2')) os = 'Windows 8';
                    else if (ua.includes('Windows NT 6.1')) os = 'Windows 7';
                    else os = 'Windows';
                } else if (ua.includes('Mac OS X')) {
                    const m = ua.match(/Mac OS X (\d+)[._](\d+)/);
                    os = m ? `macOS ${m[1]}.${m[2]}` : 'macOS';
                } else if (ua.includes('Linux')) {
                    os = 'Linux';
                } else if (ua.includes('Android')) {
                    const m = ua.match(/Android ([\d.]+)/);
                    os = m ? `Android ${m[1]}` : 'Android';
                } else if (ua.includes('iPhone') || ua.includes('iPad')) {
                    const m = ua.match(/OS (\d+)_(\d+)/);
                    os = m ? `iOS ${m[1]}.${m[2]}` : 'iOS';
                }

                if (ua.includes('Chrome') && !ua.includes('Edg') && !ua.includes('OPR')) {
                    browser = ua.match(/Chrome\/(\d+)/)?.[1] ? `Chrome ${ua.match(/Chrome\/(\d+)/)[1]}` : 'Chrome';
                } else if (ua.includes('Firefox')) {
                    browser = ua.match(/Firefox\/(\d+)/)?.[1] ? `Firefox ${ua.match(/Firefox\/(\d+)/)[1]}` : 'Firefox';
                } else if (ua.includes('Safari') && !ua.includes('Chrome')) {
                    browser = ua.match(/Version\/(\d+)/)?.[1] ? `Safari ${ua.match(/Version\/(\d+)/)[1]}` : 'Safari';
                } else if (ua.includes('Edg')) {
                    browser = ua.match(/Edg\/(\d+)/)?.[1] ? `Edge ${ua.match(/Edg\/(\d+)/)[1]}` : 'Edge';
                } else if (ua.includes('OPR')) {
                    browser = ua.match(/OPR\/(\d+)/)?.[1] ? `Opera ${ua.match(/OPR\/(\d+)/)[1]}` : 'Opera';
                }

                return `${browser}, ${os}`;
            })();
        });
    }

    // === Вложения ===
    if (triggerBtn && fileInput) {
        triggerBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => {
            const files = fileInput.files;
            if (files.length > 0) {
                const names = Array.from(files).map(f => f.name).join(', ');
                if (filePreview) filePreview.textContent = `Выбраны файлы: ${names}`;
                if (linkInput) linkInput.value = '';
            } else if (filePreview) {
                filePreview.textContent = '';
            }
        });
    }

    // === Форма ===
    if (clearFormBtn) {
        clearFormBtn.addEventListener('click', () => {
            if (form) form.reset();
            if (fileInput) fileInput.value = '';
            if (filePreview) filePreview.textContent = '';
        });
    }

    if (openBtn && modal) openBtn.addEventListener('click', () => modal.classList.add('is-open'));
    if (cancelBtn && modal) cancelBtn.addEventListener('click', () => modal.classList.remove('is-open'));

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData();

            ['bugTitle', 'bugSeverity', 'bugStatus', 'bugPrecondition', 'bugEnvironment', 'bugSteps', 'bugActual', 'bugExpected']
                .forEach(name => {
                    const el = document.getElementById(name);
                    if (el) formData.append(name, el.value);
                });

            const linkValue = linkInput?.value.trim() || '';
            const files = fileInput?.files || [];

            if (linkValue) {
                formData.append('attachment_link', linkValue);
            } else if (files.length > 0) {
                for (const file of files) formData.append('attachment_files', file);
            }

            try {
                const response = await fetch('api/bug-reports', { method: 'POST', body: formData });
                if (response.ok) {
                    alert('Баг-репорт успешно создан!');
                    form.reset();
                    if (fileInput) fileInput.value = '';
                    if (filePreview) filePreview.textContent = '';
                    modal.classList.remove('is-open');
                    loadBugReports();
                } else {
                    const result = await response.json();
                    alert('Ошибка: ' + (result.error || 'неизвестная'));
                }
            } catch (err) {
                alert('Ошибка сети');
                console.error(err);
            }
        });
    }

    // === Загрузка при старте ===
    loadBugReports();
});