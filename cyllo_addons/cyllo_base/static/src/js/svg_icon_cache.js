/** @odoo-module **/

// App icon SVG markup keyed by path, shared by every sidebar variant
// (Studio's MenuSideBar and the regular simple sidebar both show the same
// installed apps) — fetch each one at most once per session instead of
// once per component instance.
const svgIconCache = new Map();

export function getCachedSvgText(svgPath) {
    const iconSvgPath = `${svgPath.split(',')[0]}/${svgPath.split(',')[1]}`;
    if (!svgIconCache.has(iconSvgPath)) {
        svgIconCache.set(
            iconSvgPath,
            fetch(iconSvgPath).then((res) => {
                if (!res.ok) {
                    // Don't cache a failed response — a transient failure
                    // (e.g. during the fullscreen mount/unmount churn of
                    // Shop Floor) would otherwise poison the cache with
                    // `null` forever, leaving that icon permanently blank.
                    svgIconCache.delete(iconSvgPath);
                    return null;
                }
                return res.text();
            })
        );
    }
    return svgIconCache.get(iconSvgPath).catch((error) => {
        svgIconCache.delete(iconSvgPath);
        console.error('Error fetching SVG:', error);
        return null;
    });
}
