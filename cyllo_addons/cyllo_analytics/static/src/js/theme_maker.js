/** @odoo-module **/
export class ThemeMaker {
    /**
     * Class for creating a theme for the Cyllo dashboard.
     * @param {object} theme - The theme data including colors and styles.
     */
    constructor(theme) {
        this.theme = theme
        this.themeJson = {}
    }

    /**
     * Initialize the theme by applying the specified colors and styles to the dashboard.
     * @returns {object} - The theme data with style information.
     */
    initTheme() {
        var theme = this.theme
        var root = document.querySelector(':root');
        var primary_color = theme.theme_color_ids ? theme.theme_color_ids[0] : "#000"
        root.style.setProperty('--dashboard-text-color', theme.title || "#000");
        root.style.setProperty('--dashboard-primary-color', primary_color);
        root.style.setProperty('--dashboard-background-color', theme.background || "#fff");
        let modalColor = theme.background === 'rgba(0,0,0,0)' ? 'rgba(255,255,255,1)' : theme.background?.replace(/(rgba\(.+),\s*[^)]+\)/, '$1,1)') || 'rgba(255,255,255,1)';
        root.style.setProperty('--dashboard-modal-background-color', modalColor || "#fff");
        root.style.setProperty('--dashboard--body-header-background-color', theme.body_header_background);
        root.style.setProperty('--dashboard-header-title-color', theme.header_title_color);
        root.style.setProperty('--dashboard-theme-color-2', theme.theme_color_ids[1]);
        root.style.setProperty('--dashboard-theme-color-3', theme.theme_color_ids[2]);

        return {
            "themeName": theme.name,
            "seriesCnt": 4,
            "backgroundColor": 'transparent',
            "title": {
                "textStyle": {
                    "color": theme.subtitle
                },
                "subtextStyle": {
                    "color": theme.subtitle
                }
            },
            "textColorShow": false,
            "textColor": theme.label_text,
            "markTextColor": "#eee",
            "color": theme.theme_color_ids,
            graph: {
                color: theme.theme_color_ids,
                "itemStyle": {
                    "borderWidth": theme.border_width,
                    "borderColor": theme.border_color
                },
            },
            "legend": {
                "textStyle": {
                    "color": theme.subtitle
                }
            },
        }
    }

    /**
     * Get the theme and register it in ECharts to apply it to the dashboard.
     * @returns {string} - The name Banner 2of the registered theme.
     */
    getTheme() {
        var theme = this.initTheme()
        this.themeJson = theme
        this.registerDarkMode()
        echarts.registerTheme(theme.themeName, theme)
        return theme.themeName
    }

    registerDarkMode() {
        this.themeJson = {
            ...this.themeJson,
            "themeName":`${this.theme.name}_dark`,
            "title": {
                "textStyle": {
                    "color": "white"
                },
                "subtextStyle": {
                    "color": this.theme.subtitle
                }
            },
            "legend": {
                "textStyle": {
                    "color": "white"
                }
            },

        }
        echarts.registerTheme(`${this.theme.name}_dark`, this.themeJson)
    }
}