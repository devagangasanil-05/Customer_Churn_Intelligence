/* -------------------------------------------------------------
   IMMEDIATE THEME SYNC (Prevents flash of wrong theme on load)
------------------------------------------------------------- */
const savedTheme = localStorage.getItem("churniq-theme") || "dark";
document.documentElement.setAttribute("data-theme", savedTheme);

if (savedTheme === "light") {
    document.documentElement.classList.add("light-mode");
    if (document.body) document.body.classList.add("light-mode");
}

document.addEventListener("DOMContentLoaded", function () {
    if (savedTheme === "light") {
        document.body.classList.add("light-mode");
    }

    /* -------------------------------------------------------------
       CAPSULE THEME SWITCH
    ------------------------------------------------------------- */
    const themeToggle = document.getElementById("themeToggle");

    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            const isCurrentlyLight = document.documentElement.getAttribute("data-theme") === "light" ||
                                     document.body.classList.contains("light-mode");

            const newTheme = isCurrentlyLight ? "dark" : "light";

            document.documentElement.setAttribute("data-theme", newTheme);
            document.documentElement.classList.toggle("light-mode", newTheme === "light");
            document.body.classList.toggle("light-mode", newTheme === "light");

            localStorage.setItem("churniq-theme", newTheme);
        });
    }

    /* -------------------------------------------------------------
       NAVIGATION ACTIVE STATE
    ------------------------------------------------------------- */
    const navLinks = document.querySelectorAll(".nav-links a");

    navLinks.forEach(function (link) {
        link.addEventListener("click", function () {
            navLinks.forEach(function (item) {
                item.classList.remove("active");
            });
            this.classList.add("active");
        });
    });

    /* -------------------------------------------------------------
       REVEAL ANIMATION
    ------------------------------------------------------------- */
    const revealElements = document.querySelectorAll(
        ".metric, .analysis-card, .insight-row, .key-finding"
    );

    const observer = new IntersectionObserver(
        function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("visible");
                    observer.unobserve(entry.target);
                }
            });
        },
        {
            threshold: 0.12
        }
    );

    revealElements.forEach(function (element) {
        element.classList.add("reveal");
        observer.observe(element);
    });
});