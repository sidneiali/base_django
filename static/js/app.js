(function () {
    function sortSelect(select) {
        Array.from(select.options)
            .sort((a, b) => a.text.localeCompare(b.text, "pt-BR"))
            .forEach((option) => select.appendChild(option));
    }

    function moveSelected(from, to) {
        Array.from(from.selectedOptions).forEach((option) => {
            option.selected = false;
            option.hidden = false;
            to.appendChild(option);
        });

        sortSelect(to);
    }

    function moveAll(from, to) {
        Array.from(from.options).forEach((option) => {
            option.hidden = false;
            option.selected = false;
            to.appendChild(option);
        });

        sortSelect(to);
    }

    function initDualLists(root) {
        root.querySelectorAll("[data-dual-list]").forEach((container) => {
            if (container.dataset.dualListInitialized === "true") {
                return;
            }

            const available = container.querySelector("[data-dual-list-available]");
            const chosen = container.querySelector("[data-dual-list-chosen]");
            const filter = container.querySelector("[data-dual-list-filter]");
            const addButton = container.querySelector("[data-dual-list-add]");
            const removeButton = container.querySelector("[data-dual-list-remove]");
            const addAllButton = container.querySelector("[data-dual-list-add-all]");
            const removeAllButton = container.querySelector("[data-dual-list-remove-all]");
            const form = container.closest("form");

            if (!available || !chosen || !filter || !form) {
                return;
            }

            container.dataset.dualListInitialized = "true";

            addButton?.addEventListener("click", function () {
                moveSelected(available, chosen);
            });

            removeButton?.addEventListener("click", function () {
                moveSelected(chosen, available);
            });

            addAllButton?.addEventListener("click", function () {
                moveAll(available, chosen);
            });

            removeAllButton?.addEventListener("click", function () {
                moveAll(chosen, available);
            });

            available.addEventListener("dblclick", function () {
                moveSelected(available, chosen);
            });

            chosen.addEventListener("dblclick", function () {
                moveSelected(chosen, available);
            });

            filter.addEventListener("input", function () {
                const query = filter.value.toLowerCase();

                Array.from(available.options).forEach((option) => {
                    option.hidden = !option.text.toLowerCase().includes(query);
                });
            });

            form.addEventListener("submit", function () {
                Array.from(chosen.options).forEach((option) => {
                    option.selected = true;
                });
            });
        });
    }

    function syncActiveNav() {
        const path = window.location.pathname;

        document.querySelectorAll("[data-nav-prefix]").forEach((link) => {
            const prefix = link.dataset.navPrefix;
            const exact = link.dataset.navExact === "true";
            const isActive = exact ? path === prefix : path.startsWith(prefix);

            link.classList.toggle("active", isActive);
        });

        const configCollapse = document.getElementById("sidebar-configuracoes");
        const configToggle = document.querySelector(
            '[aria-controls="sidebar-configuracoes"]',
        );
        const shouldOpenConfig = path.startsWith("/painel/");

        if (configCollapse) {
            configCollapse.classList.toggle("show", shouldOpenConfig);
        }

        if (configToggle) {
            configToggle.setAttribute(
                "aria-expanded",
                shouldOpenConfig ? "true" : "false",
            );
        }
    }

    function syncPageTitle(root) {
        const titleSource =
            root.querySelector("[data-page-title]") ||
            document.querySelector("#page-content [data-page-title]");

        if (titleSource?.dataset.pageTitle) {
            document.title = titleSource.dataset.pageTitle;
        }
    }

    function initPage(root) {
        initDualLists(root);
        syncActiveNav();
        syncPageTitle(root);
    }

    document.addEventListener("DOMContentLoaded", function () {
        initPage(document);
    });

    document.body.addEventListener("htmx:afterSwap", function (event) {
        initPage(event.detail.target);
    });

    document.body.addEventListener("htmx:historyRestore", function () {
        initPage(document);
    });
})();
