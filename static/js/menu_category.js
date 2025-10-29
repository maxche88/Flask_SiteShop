document.addEventListener("DOMContentLoaded", function () {
    
    const categoryButton = document.getElementById("categories-button");
    const categoryMenu = document.getElementById("categories-menu");

    if (categoryButton && categoryMenu) {
        let isCategoryOpen = false;

        categoryButton.addEventListener("click", function (e) {
            e.preventDefault();
            isCategoryOpen = !isCategoryOpen;
            this.setAttribute("aria-expanded", isCategoryOpen);
            categoryMenu.style.display = isCategoryOpen ? "block" : "none";
        });

        categoryMenu.addEventListener("mouseleave", function () {
            isCategoryOpen = false;
            categoryButton.setAttribute("aria-expanded", false);
            categoryMenu.style.display = "none";
        });

        document.addEventListener("click", function (e) {
            if (!categoryButton.contains(e.target) && !categoryMenu.contains(e.target)) {
                isCategoryOpen = false;
                categoryButton.setAttribute("aria-expanded", false);
                categoryMenu.style.display = "none";
            }
        });
    }
});