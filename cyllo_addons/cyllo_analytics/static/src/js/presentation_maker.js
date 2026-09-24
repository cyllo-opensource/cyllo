/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { useRef, onMounted, useState, onWillStart, Component, onWillDestroy, useEffect } = owl;
import { GraphTile } from "./presentation/components/graph_tile"
import { browser } from "@web/core/browser/browser";
import { ThemeMaker } from "./theme_maker";
import { useSaveContext } from "@cyllo_analytics/js/useSaveContext";
import { Table } from "@cyllo_analytics/js/table/table";

let isPlaying = false;

try {
    Reveal.configure({
        keyboard: {
            32: () => {
                const playbackElement = document.querySelector(".playback");
                if (playbackElement) {
                    const clickEvent = new Event('click');
                    isPlaying ? (isPlaying = false) : (isPlaying = true);
                    if (isPlaying) {
                        playbackElement.dispatchEvent(clickEvent);
                    }
                }
            }
        }
    });
} catch {
    console.warn("Internet connection is not available")
}

class PresentationMaker extends Component {
    /** Class for creating a presentation maker component. */
    setup() {
        this.actionService = useService("action")
        this.orm = useService("orm")
        const { type } = this.props.action.context;
        this.chartData = useState({ data: [], style: null, theme: null, themeData: {} });
        this.state = useState({ exit: type ? false : true, warning: false, darkMode: false })
        this.type = type;
        this.ref = useRef('root')
        const { id } = useSaveContext()
        this.id = id
        onWillDestroy(() => this.env.bus.trigger("PN:RLD"))
        // Execute actions on component setup
        onWillStart(async () => {
            this.state.darkMode = await this.orm.call('res.users', 'get_active', [])
            await this.fetchData()
            if (this.chartData.themeData) {
                var theme_maker = new ThemeMaker(this.chartData.themeData)
                theme_maker.getTheme()
            }
        })
        // Execute actions after the component is mounted
        onMounted(async () => {
            try {
                this.reveal = await Reveal.initialize({
                    controls: true,
                    hash: false,
                    transition: 'slide',
                    transitionSpeed: 'default',
                    autoSlide: (type || this.type) === 'play' ? this.autoSlideTime * 1000 : false
                })
            } catch (e) {
                console.warn("Internet connection is not available")
            }

            this.navBar = document.body.querySelector('.o_navbar');
            this.sideBar = document.body.querySelector('.cy-left-sidebar');
            this.sideBar2 = document.body.querySelector('.cy-submenu-box');
            const actionManager = document.querySelector('.o_action_manager');
            let el = this.ref.el;
            while (el && el.parentElement !== actionManager) {
                el = el.parentElement;
            }
            this.actionWrapper = el;

            document.addEventListener('webkitfullscreenchange', this.exitHandler.bind(this), false);
            document.addEventListener('mozfullscreenchange', this.exitHandler.bind(this), false);
            document.addEventListener('fullscreenchange', this.exitHandler.bind(this), false);
            document.addEventListener('MSFullscreenChange', this.exitHandler.bind(this), false);

            this.fullScreen = true;
            this.toggleSideAndHeader();
        })
    }

    /**
     * Fetch data for the presentation.
     */
    async fetchData() {
        var data = this.props.action?.context?.rec_id && this.props.action.context
        if (!data) {
            try {
                data = await this.orm.read("dashboard.presentation", [this.id], [])
                if (!data.length) {
                    this.state.warning = true
                    return;
                }
            } catch {
                this.state.warning = true
                return;
            }
            data = data[0]
        }

        const {
            chart_data, style_json, type, theme, theme_json, auto_slide, auto_slide_time,
            title_page, title_page_heading, title_page_subheading
        } = data
        this.chartData.data = chart_data
        this.chartData.style = { ...(style_json || {}), height: '85vh', width: '85vw', 'margin-top': '0' }
        this.type = type
        this.autoSlideTime = auto_slide_time
        this.autoSlide = auto_slide
        this.titlePage = title_page
        this.heading = title_page_heading
        this.subheading = title_page_subheading
        this.chartData.theme = theme
        this.chartData.themeData = theme_json
    }

    /**
     * Toggle the visibility of the sidebar and header in full-screen mode.
     */
    toggleSideAndHeader() {
        let val = this.fullScreen ? 'none' : 'block';
        this.navBar.style.display = this.fullScreen ? 'none' : 'flex';
        if (this.fullScreen) {
            document.body.classList.add('cy-presentation-active');
        } else {
            document.body.classList.remove('cy-presentation-active');
        }
        if (this.actionWrapper) {
            if (this.fullScreen) {
                this.actionWrapper.style.setProperty('margin-left', '0', 'important');
                this.actionWrapper.style.setProperty('width', '100%', 'important');
            } else {
                this.actionWrapper.style.removeProperty('margin-left');
                this.actionWrapper.style.removeProperty('width');
            }
        }
    }

    /**
     * Handle the exit from full-screen mode.
     */
    exitHandler() {
        if (!document.webkitIsFullScreen && !document.mozFullScreen && !document.msFullscreenElement) {
            this.state.exit = true;
        }
    }

    /**
     * Exit the presentation mode and navigate to the original dashboard.
     */
    async exitPresentation() {
        this.fullScreen = false;
        await this.toggleSideAndHeader()
        browser.history.go(-1)
    }

    /**
     * Trigger full-screen mode for the presentation.
     */
    triggerFullScreen() {
        document.documentElement.requestFullscreen();
        this.state.exit = false;
        this.fullScreen = true
        this.toggleSideAndHeader();
    }
}

// Define the template for the PresentationMaker component
PresentationMaker.template = "cyllo_analytics.PresentationMaker"
PresentationMaker.components = {
    GraphTile, Table
}
// Register the PresentationMaker component in the actions category
registry.category("actions").add("presentation_maker", PresentationMaker);