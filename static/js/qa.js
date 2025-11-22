document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('bugReportModalBackdrop');
    const openBtn = document.getElementById('openBugReportModalBtn');
    const cancelBtn = document.getElementById('cancelBugReportBtn');
    const form = document.getElementById('createBugReportForm');
    const copyTemplateBtn = document.getElementById('copyTemplateBtn');
    const pasteTemplateBtn = document.getElementById('pasteTemplateBtn');
    const toggleBtn = document.getElementById('toggleAttachmentType');
    const linkInput = document.getElementById('bugAttachmentInput');
    const fileInput = document.getElementById('bugAttachmentFile');
    const clearFormBtn = document.getElementById('clearFormBtn');
    const detectEnvBtn = document.getElementById('detectEnvBtn');

    // Определение окружения
    function detectEnvironment() {
        const ua = navigator.userAgent;
        let os = 'Unknown OS';
        let browser = 'Unknown Browser';

        // Определение ОС с версией
        if (ua.includes('Windows')) {
            if (ua.includes('Windows NT 10.0')) os = 'Windows 10';
            else if (ua.includes('Windows NT 6.3')) os = 'Windows 8.1';
            else if (ua.includes('Windows NT 6.2')) os = 'Windows 8';
            else if (ua.includes('Windows NT 6.1')) os = 'Windows 7';
            else os = 'Windows';
        } else if (ua.includes('Mac OS X')) {
            const match = ua.match(/Mac OS X (\d+)[._](\d+)(?:[._](\d+))?/);
            if (match) {
            const major = match[1];
            const minor = match[2];
            os = `macOS ${major}.${minor}`;
            } else {
            os = 'macOS';
            }
        } else if (ua.includes('Linux')) {
            os = 'Linux';
        } else if (ua.includes('Android')) {
            const match = ua.match(/Android ([\d.]+)/);
            os = match ? `Android ${match[1]}` : 'Android';
        } else if (ua.includes('iPhone') || ua.includes('iPad')) {
            const match = ua.match(/OS (\d+)_(\d+)_?(\d+)?/);
            if (match) {
            os = `iOS ${match[1]}.${match[2]}`;
            } else {
            os = 'iOS';
            }
        }

        // Определение браузера с версией
        if (ua.includes('Chrome') && !ua.includes('Edg') && !ua.includes('OPR')) {
            const match = ua.match(/Chrome\/([\d.]+)/);
            browser = match ? `Chrome ${match[1].split('.')[0]}` : 'Chrome';
        } else if (ua.includes('Firefox')) {
            const match = ua.match(/Firefox\/([\d.]+)/);
            browser = match ? `Firefox ${match[1].split('.')[0]}` : 'Firefox';
        } else if (ua.includes('Safari') && !ua.includes('Chrome') && !ua.includes('Chromium')) {
            const match = ua.match(/Version\/([\d.]+)/);
            browser = match ? `Safari ${match[1].split('.')[0]}` : 'Safari';
        } else if (ua.includes('Edg')) {
            const match = ua.match(/Edg\/([\d.]+)/);
            browser = match ? `Edge ${match[1].split('.')[0]}` : 'Edge';
        } else if (ua.includes('OPR')) {
            const match = ua.match(/OPR\/([\d.]+)/);
            browser = match ? `Opera ${match[1].split('.')[0]}` : 'Opera';
        }

        return `${browser}, ${os}`;
    }

    // Кнопка определения окружения
    if (detectEnvBtn) {
        detectEnvBtn.addEventListener('click', () => {
            const envInput = document.getElementById('bugEnvironment');
            if (envInput) {
                envInput.value = detectEnvironment();
            }
        });
    }

    // Переключение режима вложений
    if (toggleBtn && linkInput && fileInput) {
        toggleBtn.addEventListener('click', () => {
            if (fileInput.style.display === 'none' || fileInput.style.display === '') {
                fileInput.style.display = 'block';
                linkInput.value = '';
                toggleBtn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M15 22a1 1 0 0 1-1-1V3a1 1 0 0 1 2 0v18a1 1 0 0 1-1 1z"></path>
                        <path d="M10 19a1 1 0 0 1-1-1V6a1 1 0 0 1 2 0v12a1 1 0 0 1-1 1z"></path>
                        <path d="M5 16a1 1 0 0 1-1-1V9a1 1 0 0 1 2 0v6a1 1 0 0 1-1 1z"></path>
                    </svg>
                `;
            } else {
                fileInput.style.display = 'none';
                fileInput.value = '';
                toggleBtn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4-4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                `;
            }
        });
    }

    const getFormDataAsJSON = () => {
        if (!form) {
            return {
                title: "",
                severity: "medium",
                status: "open",
                precondition: "",
                environment: "",
                steps_to_reproduce: "",
                actual_result: "",
                expected_result: "",
                attachments: []
            };
        }

        return {
            title: form.bugTitle?.value || "",
            severity: form.bugSeverity?.value || "medium",
            status: form.bugStatus?.value || "open",
            precondition: form.bugPrecondition?.value || "",
            environment: form.bugEnvironment?.value || "",
            steps_to_reproduce: form.bugSteps?.value || "",
            actual_result: form.bugActual?.value || "",
            expected_result: form.bugExpected?.value || "",
            attachments: []
        };
    };

    copyTemplateBtn?.addEventListener('click', async () => {
        const data = getFormDataAsJSON();
        const jsonStr = JSON.stringify(data, null, 2);
        try {
            await navigator.clipboard.writeText(jsonStr);
        } catch (err) {
            console.warn('Не удалось скопировать:', err);
        }
    });

    pasteTemplateBtn?.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            const data = JSON.parse(text);

            if (typeof data !== 'object' || data === null) return;

            const fieldMap = {
                'title': 'bugTitle',
                'severity': 'bugSeverity',
                'status': 'bugStatus',
                'precondition': 'bugPrecondition',
                'environment': 'bugEnvironment',
                'steps_to_reproduce': 'bugSteps',
                'actual_result': 'bugActual',
                'expected_result': 'bugExpected'
            };

            for (const [jsonKey, fieldId] of Object.entries(fieldMap)) {
                const el = document.getElementById(fieldId);
                if (el && data.hasOwnProperty(jsonKey)) {
                    el.value = data[jsonKey] ?? '';
                }
            }
        } catch (err) {
            console.warn('Вставка не удалась:', err);
        }
    });

    clearFormBtn?.addEventListener('click', () => {
        if (form) form.reset();
        const fileInput = document.getElementById('bugAttachmentFile');
        const toggleBtn = document.getElementById('toggleAttachmentType');
        if (fileInput && toggleBtn) {
            fileInput.style.display = 'none';
            fileInput.value = '';
            toggleBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4-4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
            `;
        }
    });

    if (!modal || !openBtn || !cancelBtn || !form) {
        console.warn('Один из элементов модального окна не найден');
        return;
    }

    const closeModal = () => {
        modal.classList.remove('is-open');
    };

    openBtn.addEventListener('click', () => {
        modal.classList.add('is-open');
    });

    cancelBtn.addEventListener('click', closeModal);

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const linkInput = document.getElementById('bugAttachmentInput');
        const fileInput = document.getElementById('bugAttachmentFile');
        const formData = new FormData();

        const fields = [
            'bugTitle', 'bugSeverity', 'bugStatus', 'bugPrecondition',
            'bugEnvironment', 'bugSteps', 'bugActual', 'bugExpected'
        ];
        fields.forEach(name => {
            const el = document.getElementById(name);
            if (el) formData.append(name, el.value);
        });

        const linkValue = linkInput?.value.trim() || '';
        const files = fileInput?.files || [];

        if (linkValue) {
            formData.append('attachment_link', linkValue);
        } else if (files.length > 0) {
            for (let file of files) {
                formData.append('attachment_files', file);
            }
        }

        try {
            const response = await fetch('/api/bug-reports', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                alert('Баг-репорт успешно создан!');
                form.reset();
                closeModal();
            } else {
                const msg = result.error || 'Неизвестная ошибка при создании баг-репорта';
                alert('Ошибка: ' + msg);
                console.error('Ошибка API:', result);
            }
        } catch (err) {
            alert('Ошибка сети: не удалось отправить баг-репорт');
            console.error('Ошибка сети:', err);
        }
    });
});