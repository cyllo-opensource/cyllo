/** @odoo-module **/

const { useState, useEffect, useRef } = owl

export function useResize(refName, resizeFunc = () => { }) {
    const state = useState({ width: 0, height: 0 });
    const ref = useRef(refName);

    useEffect(() => {
        const handleResize = () => {
            if (ref.el) {
                const { width, height } = ref.el.getBoundingClientRect();
                state.width = width;
                state.height = height;
            }
            resizeFunc(state.width, state.height, ref);
        };
        handleResize();
        window.addEventListener('resize', handleResize);
        return () => {
            window.removeEventListener('resize', handleResize);
        };
    }, () => []);
}