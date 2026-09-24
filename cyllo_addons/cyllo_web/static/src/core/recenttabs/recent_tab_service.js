/** @odoo-module **/

import { registry } from "@web/core/registry";

const recentTabsKey = 'recentTabs';
const numberOfPinnedTabsKey = 'numberOfPinnedTabs'

export const recentTabsService = {
    dependencies: ["router", "orm"],
    async start(env, { router, orm }) {
        const getCurrentUserRecentTab = () => {
            const user = orm.user;
            const userKey = user.db.name + user.userId;
            let recentTabsOfAllUsers = JSON.parse(sessionStorage.getItem(recentTabsKey));
            return (recentTabsOfAllUsers && recentTabsOfAllUsers[userKey]) || [];
        };
        const setCurrentUserRecentTab = (recentTabs) => {
            const user = orm.user;
            const userKey = user.db.name + user.userId;
            let recentTabsOfAllUsers = JSON.parse(sessionStorage.getItem(recentTabsKey));
            if (recentTabsOfAllUsers) {
                if (recentTabsOfAllUsers[userKey]) {
                    recentTabsOfAllUsers[userKey] = recentTabs;
                }
                else {
                    recentTabsOfAllUsers = { ...recentTabsOfAllUsers, [userKey]: [recentTabs] };
                }
                sessionStorage.setItem(recentTabsKey, JSON.stringify(recentTabsOfAllUsers));
            }
            else {
                sessionStorage.setItem(recentTabsKey, JSON.stringify({ [userKey]: [recentTabs] }));
            }
        };
        const removeTab = (data, recentTabs) => {
            const repeatedIndex = recentTabs.findIndex((tab) => {

                // Case 1: Both are Form views (have item_id)
                if (tab.item_id && data.item_id) {
                    // Duplicate only if it's the exact same record under the same action
                    return tab.item_id === data.item_id && tab.action_id === data.action_id;
                }
                // Case 2: Both are List/Kanban views (neither has item_id)
                if (!tab.item_id && !data.item_id) {
                    const matchesAction = tab.action_id && data.action_id && tab.action_id === data.action_id;
                    const matchesMenu = tab.menu_id && data.menu_id && tab.menu_id === data.menu_id;
                    return matchesAction || matchesMenu;
                }
                return false;
            });
            // If an actual duplicate is found, remove it
            if (repeatedIndex !== -1) {
                recentTabs.splice(repeatedIndex, 1);
            }
        };
        const pushToRecent = async (data) => {
            let recentTabs = getCurrentUserRecentTab();
            if (recentTabs) {
                if (recentTabs.length > 10 - parseInt(sessionStorage.getItem(numberOfPinnedTabsKey) || 0)) {
                    recentTabs.shift();
                }
                //if repeated records found it will be removed
                removeTab(data, recentTabs);
                recentTabs.push(data);
                setCurrentUserRecentTab(recentTabs)
            } else {
                setCurrentUserRecentTab([data])
            }
        };
        const handleRouteNavigation = () => {
            setTimeout(async () => {
                const currentHash = window.location.hash;
                const currentRoute = router.current;
                if (currentRoute.search.debug || currentRoute.search.studio) {
                    // not tracked while in studio/debug mode
                    return;
                }
                const now = new Date();
                const options = {
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true
                };
                let data = {
                    name: document.title,
                    tab_url: document.URL,
                    item_id: currentRoute.hash.id,
                    last_visited: now.toLocaleString('en-US', options).replace(',', ''),
                    action_id: currentRoute.hash.action,
                    company_id: parseInt(currentRoute.hash.cids.toString().split("-")[0]),
                    menu_id: currentRoute.hash.menu_id,
                    res_model: currentRoute.hash.model,
                    view_type: currentRoute.hash.view_type,
                    path_name: currentRoute.pathname,
                    hash: currentHash,
                    pinned: false,
                };
                await pushToRecent(data);
            }, 300);
        };

        async function loadTabs() {
            let pinnedTabs = await orm.searchRead('recent.tab', [['user_id', '=', orm.user.userId]]);
            sessionStorage.setItem(numberOfPinnedTabsKey, pinnedTabs.length.toString());
            let recentTabs = getCurrentUserRecentTab();
            pinnedTabs.forEach(async (tab, index) => {
                pinnedTabs[index].pinned = true;
                removeTab(pinnedTabs[index], recentTabs);
            })
            let tabs = [...pinnedTabs.reverse(), ...recentTabs.reverse()];
            if (tabs.length > 10) {
                tabs = tabs.slice(0, 10);
            }
            return tabs;
        };


        async function pinTab(tab) {
            if (sessionStorage.getItem(numberOfPinnedTabsKey) >= 3) {
                return;
            }
            let recentTabs = getCurrentUserRecentTab();
            let pinnedTabIds = await orm.create('recent.tab', [{
                name: tab.name,
                user_id: orm.user.userId,
                item_id: tab.item_id,
                tab_url: tab.tab_url,
                action_id: tab.action_id,
                company_id: tab.company_id,
                menu_id: tab.menu_id,
                last_visited: tab.last_visited,
                res_model: tab.res_model,
                view_type: tab.view_type,
                path_name: tab.path_name,
                hash: tab.hash,
            }]);
            tab.id = pinnedTabIds[0];
            tab.pinned = true;
            removeTab(tab, recentTabs);
            setCurrentUserRecentTab(recentTabs);
        };

        async function unpinTab(tab, numberOfPinnedTabs) {
            await orm.unlink('recent.tab', [tab.id]);
            sessionStorage.setItem(numberOfPinnedTabsKey, (numberOfPinnedTabs - 1).toString());
            tab.pinned = false;
            pushToRecent(tab);
        };

        async function clearTab(tab) {
            let recentTabs = getCurrentUserRecentTab();
            removeTab(tab, recentTabs);
            setCurrentUserRecentTab(recentTabs);
        };

        async function clearAllTabs() {
            setCurrentUserRecentTab([])
        };
        async function updateLastVisitedPinned(tab) {
            const now = new Date();
            const options = {
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
            };
            await orm.write('recent.tab', [tab.id], { last_visited: now.toLocaleString('en-US', options).replace(',', '') });
        };

        env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", handleRouteNavigation);

        return {
            pinTab,
            unpinTab,
            loadTabs,
            clearTab,
            clearAllTabs,
            updateLastVisitedPinned,
        };

    },
};

registry.category("services").add("recentTabsService", recentTabsService);