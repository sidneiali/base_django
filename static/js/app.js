(function () {
    let autoRefreshTimer = null;
    let autoRefreshInFlight = false;
    let shellMetricsFrame = null;

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

    function initForms(root) {
        root.querySelectorAll("form").forEach((form) => {
            if (form.dataset.formStateInitialized === "true") {
                return;
            }

            form.dataset.formStateInitialized = "true";
            form.dataset.formDirty = "false";

            form.addEventListener("input", function () {
                form.dataset.formDirty = "true";
            });

            form.addEventListener("change", function () {
                form.dataset.formDirty = "true";
            });

            form.addEventListener("submit", function () {
                form.dataset.formSubmitting = "true";
            });
        });
    }

    function initRefreshPreferenceControls(root) {
        root.querySelectorAll("form").forEach((form) => {
            const toggle = form.querySelector("[data-auto-refresh-toggle]");
            const intervalInput = form.querySelector(
                "[data-auto-refresh-interval-input]",
            );

            if (!toggle || !intervalInput) {
                return;
            }

            const syncState = function () {
                const enabled = toggle.checked;

                intervalInput.readOnly = !enabled;
                intervalInput.tabIndex = enabled ? 0 : -1;
                intervalInput.classList.toggle("bg-light", !enabled);
                intervalInput.setAttribute(
                    "aria-disabled",
                    enabled ? "false" : "true",
                );
            };

            syncState();

            if (toggle.dataset.autoRefreshToggleInitialized === "true") {
                return;
            }

            toggle.dataset.autoRefreshToggleInitialized = "true";
            toggle.addEventListener("change", syncState);
        });
    }

    async function copyText(value) {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(value);
            return;
        }

        const textarea = document.createElement("textarea");
        textarea.value = value;
        textarea.setAttribute("readonly", "readonly");
        textarea.style.position = "absolute";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
    }

    function resolveCopyValue(button) {
        const selector = button.dataset.copyTarget;
        if (!selector) {
            return button.dataset.copyText || "";
        }

        const target = document.querySelector(selector);
        if (!target) {
            return "";
        }

        if ("value" in target && typeof target.value === "string") {
            return target.value;
        }

        return target.textContent?.trim() || "";
    }

    function initCopyButtons(root) {
        root.querySelectorAll("[data-copy-target], [data-copy-text]").forEach((button) => {
            if (button.dataset.copyInitialized === "true") {
                return;
            }

            button.dataset.copyInitialized = "true";
            const defaultLabel =
                button.dataset.copyLabelDefault || button.textContent.trim();
            const successLabel = button.dataset.copyLabelSuccess || "Copiado";

            button.addEventListener("click", async function () {
                const value = resolveCopyValue(button);

                if (!value) {
                    return;
                }

                try {
                    await copyText(value);
                    button.textContent = successLabel;
                    window.setTimeout(() => {
                        button.textContent = defaultLabel;
                    }, 1800);
                } catch (error) {
                    console.error("Falha ao copiar conteúdo:", error);
                }
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
    }

    function syncPageTitle(root) {
        const titleSource =
            root.querySelector("[data-page-title]") ||
            document.querySelector("#page-content [data-page-title]");

        if (titleSource?.dataset.pageTitle) {
            document.title = titleSource.dataset.pageTitle;

            const layoutTitle = document.querySelector("[data-layout-page-title]");

            if (layoutTitle) {
                layoutTitle.textContent = titleSource.dataset.pageTitle;
            }
        }
    }

    function scrollPageBodyToTop() {
        const pageBody = document.querySelector(".page-body");

        if (pageBody) {
            pageBody.scrollTop = 0;
        }
    }

    function applyShellMetrics() {
        const root = document.documentElement;
        const topbar = document.querySelector(".app-topbar-shell");
        const footer = document.querySelector(".footer-app");
        const topbarHeight = Math.ceil(topbar?.offsetHeight || 0);
        const footerHeight = Math.ceil(footer?.offsetHeight || 0);

        if (topbarHeight > 0) {
            root.style.setProperty("--app-topbar-height", `${topbarHeight}px`);
        }

        if (footerHeight > 0) {
            root.style.setProperty("--app-footer-height", `${footerHeight}px`);
        }
    }

    function syncShellMetrics() {
        window.cancelAnimationFrame(shellMetricsFrame);
        shellMetricsFrame = window.requestAnimationFrame(applyShellMetrics);
    }

    function getAutoRefreshConfig() {
        const container = document.getElementById("page-content");

        if (!container || container.dataset.autoRefresh === "off") {
            return null;
        }

        const parsedInterval = Number.parseInt(
            container.dataset.autoRefreshInterval || "15000",
            10,
        );

        return {
            container,
            interval: Number.isFinite(parsedInterval) && parsedInterval >= 30
                ? parsedInterval * 1000
                : 30000,
        };
    }

    function hasInteractiveFocus(container) {
        const activeElement = document.activeElement;

        return Boolean(
            activeElement &&
            container.contains(activeElement) &&
            activeElement.matches("input, select, textarea, [contenteditable='true']"),
        );
    }

    function shouldPauseAutoRefresh(container) {
        if (document.hidden || !navigator.onLine) {
            return true;
        }

        if (autoRefreshInFlight) {
            return true;
        }

        if (
            container.querySelector("form:not([method]), form[method='post']") ||
            container.querySelector("form[data-form-dirty='true']") ||
            container.querySelector("[data-auto-refresh='off']")
        ) {
            return true;
        }

        if (hasInteractiveFocus(container)) {
            return true;
        }

        return Boolean(
            document.querySelector(".dropdown-menu.show, .modal.show, .offcanvas.show"),
        );
    }

    async function refreshPageContent() {
        const config = getAutoRefreshConfig();

        if (!config || shouldPauseAutoRefresh(config.container)) {
            scheduleAutoRefresh();
            return;
        }

        const requestUrl = window.location.pathname + window.location.search;
        autoRefreshInFlight = true;

        try {
            const response = await fetch(requestUrl, {
                headers: {
                    "HX-Request": "true",
                    "HX-Target": "page-content",
                    "X-Requested-With": "XMLHttpRequest",
                },
                credentials: "same-origin",
            });

            if (response.redirected) {
                window.location.href = response.url;
                return;
            }

            if (!response.ok || response.status === 204) {
                return;
            }

            if (requestUrl !== window.location.pathname + window.location.search) {
                return;
            }

            config.container.innerHTML = await response.text();
            initPage(config.container);
        } catch (error) {
            console.error("Falha no auto refresh da pagina:", error);
        } finally {
            autoRefreshInFlight = false;
            scheduleAutoRefresh();
        }
    }

    function scheduleAutoRefresh() {
        window.clearTimeout(autoRefreshTimer);

        const config = getAutoRefreshConfig();

        if (!config) {
            return;
        }

        autoRefreshTimer = window.setTimeout(refreshPageContent, config.interval);
    }

    function initPage(root) {
        initForms(root);
        initRefreshPreferenceControls(root);
        initCopyButtons(root);
        initDualLists(root);
        syncActiveNav();
        syncPageTitle(root);
        syncShellMetrics();
        scheduleAutoRefresh();
    }

    document.addEventListener("DOMContentLoaded", function () {
        initPage(document);
    });

    document.body.addEventListener("htmx:afterSwap", function (event) {
        if (event.detail.target?.id === "page-content") {
            scrollPageBodyToTop();
        }
        initPage(event.detail.target);
    });

    document.body.addEventListener("htmx:historyRestore", function () {
        scrollPageBodyToTop();
        initPage(document);
    });

    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) {
            scheduleAutoRefresh();
        }
    });

    window.addEventListener("focus", function () {
        scheduleAutoRefresh();
    });

    window.addEventListener("online", function () {
        scheduleAutoRefresh();
    });

    window.addEventListener("resize", function () {
        syncShellMetrics();
    });
})();
