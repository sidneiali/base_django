(function () {
    function copyTextFallback(value) {
        const textarea = document.createElement("textarea");
        textarea.value = value;
        textarea.setAttribute("readonly", "readonly");
        textarea.className = "clipboard-fallback-textarea";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
    }

    async function copyText(value) {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(value);
            return;
        }

        copyTextFallback(value);
    }

    function initApiDocs() {
        const docsScrollContainer = document.querySelector(
            ".public-docs__card-body--content",
        );
        const sectionLinks = document.querySelectorAll("[data-section-link]");
        const endpointLinks = document.querySelectorAll("[data-endpoint-link]");
        const languageButtons = document.querySelectorAll("[data-code-lang]");

        if (!docsScrollContainer || !sectionLinks.length || !languageButtons.length) {
            return;
        }

        let highlightedExample = null;
        let currentLanguage = "curl";
        let scrollSpy = null;

        const getVisibleCodeBlock = (panel) =>
            panel.querySelector(`[data-code-sample="${currentLanguage}"]`) ||
            panel.querySelector("[data-code-sample]:not([hidden])");

        const initCodeCopyButtons = () => {
            document.querySelectorAll(".public-docs__code-panel").forEach((panel) => {
                if (panel.parentElement?.classList.contains("public-docs__code-wrap")) {
                    return;
                }

                const wrapper = document.createElement("div");
                wrapper.className = "public-docs__code-wrap";

                const button = document.createElement("button");
                button.type = "button";
                button.className =
                    "btn btn-sm btn-outline-light public-docs__copy-btn";
                button.textContent = "Copiar";

                button.addEventListener("click", async () => {
                    const codeBlock = getVisibleCodeBlock(wrapper);
                    const code = codeBlock?.querySelector("code");
                    const value =
                        code?.textContent?.trim() ||
                        codeBlock?.textContent?.trim() ||
                        "";

                    if (!value) {
                        return;
                    }

                    try {
                        await copyText(value);
                        button.textContent = "Copiado";
                        window.setTimeout(() => {
                            button.textContent = "Copiar";
                        }, 1800);
                    } catch (error) {
                        console.error("Falha ao copiar exemplo da API:", error);
                    }
                });

                panel.parentNode.insertBefore(wrapper, panel);
                wrapper.appendChild(button);
                wrapper.appendChild(panel);
            });
        };

        const setActiveLanguage = (language) => {
            currentLanguage = language;

            languageButtons.forEach((button) => {
                const isActive = button.dataset.codeLang === language;
                button.classList.toggle("active", isActive);
                button.setAttribute("aria-selected", isActive ? "true" : "false");
            });

            document.querySelectorAll("[data-code-sample]").forEach((codeBlock) => {
                const isVisible = codeBlock.dataset.codeSample === language;
                codeBlock.hidden = !isVisible;
            });

            if (scrollSpy?.refresh) {
                scrollSpy.refresh();
            }
        };

        const clearHighlight = () => {
            if (!highlightedExample) {
                return;
            }

            highlightedExample.classList.remove("is-highlighted");
            highlightedExample = null;
        };

        const scrollToTarget = (targetId) => {
            const target = document.getElementById(targetId);
            if (!target) {
                return;
            }

            target.scrollIntoView({ behavior: "smooth", block: "start" });
        };

        const scrollToEndpointExample = (endpointKey) => {
            const example = document.querySelector(
                `[data-endpoint-example="${endpointKey}"]`,
            );
            if (!example) {
                return;
            }

            scrollToTarget(endpointKey);
            clearHighlight();
            highlightedExample = example;
            example.classList.add("is-highlighted");
            window.setTimeout(clearHighlight, 1800);
        };

        const applyHashRoute = () => {
            const hash = window.location.hash.replace(/^#/, "");
            if (!hash) {
                return;
            }

            if (hash === "api-tabs-python") {
                setActiveLanguage("python");
            } else if (hash === "api-tabs-curl") {
                setActiveLanguage("curl");
            }

            if (document.querySelector(`[data-endpoint-example="${hash}"]`)) {
                window.setTimeout(() => {
                    scrollToEndpointExample(hash);
                }, 60);
                return;
            }

            const target = document.getElementById(hash);
            if (!target) {
                return;
            }

            window.setTimeout(() => {
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 60);
        };

        const initScrollSpy = () => {
            if (!window.bootstrap?.ScrollSpy) {
                return;
            }

            scrollSpy = new window.bootstrap.ScrollSpy(docsScrollContainer, {
                target: "#api-docs-nav",
                smoothScroll: true,
                offset: 24,
            });
            scrollSpy.refresh();
        };

        sectionLinks.forEach((link) => {
            link.addEventListener("click", (event) => {
                event.preventDefault();
                scrollToTarget(link.dataset.sectionLink);
            });
        });

        endpointLinks.forEach((link) => {
            link.addEventListener("click", (event) => {
                event.preventDefault();
                scrollToEndpointExample(link.dataset.endpointLink);
            });
        });

        languageButtons.forEach((button) => {
            button.addEventListener("click", () => {
                setActiveLanguage(button.dataset.codeLang);
            });
        });

        initCodeCopyButtons();
        initScrollSpy();
        setActiveLanguage(currentLanguage);
        applyHashRoute();
        window.addEventListener("hashchange", applyHashRoute);
    }

    document.addEventListener("DOMContentLoaded", initApiDocs);
})();
