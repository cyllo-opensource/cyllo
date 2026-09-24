/** @odoo-module **/
/**
 * Create a loading chart for Cyllo Analytic Dashboard.
 *
 * @param {Object} props - Properties of the loading chart.
 * @param {string} [props.text] - Text to be displayed in the center of the loading chart. Default is 'Cyllo Dashboard'.
 * @param {number} [props.fontSize] - Font size of the text. Default is 35.
 * @param {number} [props.duration] - Duration of the loading animation in milliseconds. Default is 3000.
 * @param {boolean} [props.loop] - If true, the loading animation will loop indefinitely. Default is false.
 *
 * @returns {Object} - A configuration object for the loading chart.
 */
export function loadingChart(props) {
    return {
        graphic: {
            elements: [{
                type: 'text',
                left: 'center',
                top: 'center',
                style: {
                    text: props?.text || 'Cyllo Dashboard',
                    fontSize: props?.fontSize || 20,
                    fontWeight: '400',
                    lineDash: [0, 200],
                    lineDashOffset: 0,
                    fill: 'transparent',
                    lineWidth: 1,
                },
                keyframeAnimation: {
                    duration: props?.duration ? props.duration : 1,
                    loop: props?.loop,
                    keyframes: [{
                        percent: 0.7,
                        style: {
                            fill: 'transparent',
                            lineDashOffset: 200,
                            lineDash: [200, 0]
                        }
                    },
                        {
                            // Stop for a while.
                            percent: 0.8,
                            style: {
                                fill: 'transparent'
                            }
                        },
                        {
                            percent: 1,
                            style: {
                                fill: '#989494',
                            }
                        }
                    ]
                }
            }]
        }
    };
}