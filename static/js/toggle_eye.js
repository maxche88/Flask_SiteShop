function togglePassword(id, icon) {
    const input = document.getElementById(id);
    const eyeOpen = icon.closest('.password_item').querySelector('.eye_open');
    const eyeClose = icon.closest('.password_item').querySelector('.eye_close');

    if (input.type === "password") {
        input.type = "text";
        eyeOpen.style.display = "inline";
        eyeClose.style.display = "none";
    } else {
        input.type = "password";
        eyeOpen.style.display = "none";
        eyeClose.style.display = "inline";
    }
}
