function showNotification(message) {
    const notification = document.getElementById('custom-notification');
    const messageEl = document.getElementById('notification-message');

    if (!notification || !messageEl) {
        console.warn('Элемент уведомления не найден в DOM');
        return;
    }

    messageEl.textContent = message;
    notification.classList.remove('hidden');

    const hideNotification = () => {
        notification.classList.add('hidden');
    };

    const autoHideTimer = setTimeout(hideNotification, 5000);

    const handleClickOutside = (e) => {
        if (e.target === notification) {
            hideNotification();
            clearTimeout(autoHideTimer);
            document.removeEventListener('click', handleClickOutside);
        }
    };

    document.addEventListener('click', handleClickOutside);
}

// Делаем функцию доступной глобально (не обязательно, но удобно)
window.showNotification = showNotification;