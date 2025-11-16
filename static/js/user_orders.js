document.addEventListener("DOMContentLoaded", function () {
    const selectAllCheckbox = document.getElementById('select-all-orders');
    const itemCheckboxes = document.querySelectorAll('.order-item-checkbox');

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function () {
            const isChecked = this.checked;
            itemCheckboxes.forEach(cb => {
                cb.checked = isChecked;
            });
        });
    }

    itemCheckboxes.forEach(cb => {
        cb.addEventListener('change', function () {
            if (selectAllCheckbox && !this.checked) {
                selectAllCheckbox.checked = false;
            }
        });
    });
});