/** @odoo-module **/
import { Component, onMounted, onWillUpdateProps, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
const { DateTime } = luxon;
const COLORS = [
    "",
    "#FF9C9C",
    "#F7C698",
    "#FDE388",
    "#BBD7F8",
    "#D9A8CC",
    "#F8D6C8",
    "#89E1DB",
    "#97A6F9",
    "#FF9ECC",
    "#B7EDBE",
    "#E6DBFC"
];

export class GanttRenderer extends Component {
    setup() {
        this.archInfo = this.props.archInfo;
        this.model = this.props.list.resModel;
        this.state = useState({
            tasks: [],
            groups: [],
        });
        this.ref = useRef('root-renderer');
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.defaultGroup = this.props.list.groupBy[0] || this.archInfo.defaultGroup;
        if (this.defaultGroup && this.defaultGroup?.includes(':')) {
            this.notification.add("Date field is not supported as Group By", { type: "warning"});
            this.defaultGroup = !this.archInfo.defaultGroup.includes(':') && this.archInfo.defaultGroup;
        };
        this.relatedModel = this.defaultGroup && this.archInfo.relatedModels[this.model][this.defaultGroup]?.relation;
        this.fields = ['name', this.archInfo.startDate, this.archInfo.endDate, this.archInfo.defaultGroup, this.defaultGroup, this.archInfo.color].filter(Boolean);
        this.current_window = {
            start: DateTime.now().startOf("week"),
            end: DateTime.now().endOf("week"),
        };
        onMounted(() => {
            this.generateGantt();
            let container = this.ref.el.querySelector('#cyllo_gantt_widget');
            this.timeline = new vis.Timeline(container , [], {});
        });
        onWillUpdateProps(async (nextProps) => {
            let recordIds = nextProps.list.records.map(record => record._values.id);
            this.records = this.allRecords.filter(record => recordIds?.includes(record.id));
            if (this.defaultGroup !== nextProps.list?.groupBy[0] && !nextProps.list?.groupBy[0]?.includes(':')) {
                this.defaultGroup = nextProps.list?.groupBy[0] || this.archInfo.defaultGroup;
                this.relatedModel = this.defaultGroup && this.archInfo.relatedModels[this.model][this.defaultGroup]?.relation;
                if (this.defaultGroup && !this.allRecords[0]?.hasOwnProperty(this.defaultGroup)) {
                    let groupByRecords = await this.orm.searchRead(this.model, [], [this.defaultGroup]);
                    this.allRecords.forEach(record => {
                        record[this.defaultGroup] = groupByRecords.find(item => item.id === record.id)[this.defaultGroup];
                    });
                };
                let imageField = await this.orm.search('ir.model.fields', [['name', '=', 'image_128'], ['model_id.model', '=', this.relatedModel]]);
                let fields = ['name', ...(imageField.length > 0 ? ['image_128'] : [])];
                let result = await this.orm.searchRead(this.relatedModel, [], fields);
                this.relatedRecords = result.map(({ name, id, image_128 }) => ({ id, name, image: image_128 || null }));
                this.updateImage(this.records);
            } else if (nextProps.list?.groupBy[0]?.includes(':')) {
                this.notification.add("Date field is not supported as Group By", { type: "warning"});
                return false;
            };
            let domain = this.splitAndCreateDomain(nextProps.list._config.domain);
            if (this.showAllData && this.relatedModel && domain) {
                let data = await this.orm.search(this.relatedModel, domain);
                let result = this.relatedRecords.filter(item => data.includes(item.id));
                let records = this.records.length > 0
                          ? this.records.concat(result.filter(item => this.records.some(rec => rec[this.defaultGroup][0] !== item.id)))
                          : result;
                this.CreateGroup(records);
                this.CreateTasks(records);
            } else {
                this.CreateGroup(this.records);
                this.CreateTasks(this.records);
            };
            this.timeline.setData({
                groups: this.state.groups,
                items: this.state.tasks
            });
        });
        this.displayDate = this.current_window.start.toFormat('yyyy-MM-dd') + " - " + this.current_window.end.toFormat('yyyy-MM-dd');
    }
    /**
    * For generating the gantt
    */
    async generateGantt() {
        const date = DateTime.now();
        this.showAllData = this.archInfo.showAllData == 'True';
        let values = await this.orm.searchRead(this.model, [], this.fields);
        values?.map(data => this.convertToLocal(data));
        let records = await Promise.all(this.props.list.records.map(async (record) => {
            let id = record._values.id || record.evalContext.id;
            return {
                ...record._values,
                ...(await values.find(value => value.id === id))
            };
        }));
        let imageField = await this.orm.search('ir.model.fields', [['name', '=', 'image_128'], ['model_id.model', '=', this.relatedModel]]);
        let fields = ['name', ...(imageField.length > 0 ? ['image_128'] : [])];
        if (this.defaultGroup) {
            let result = await this.orm.searchRead(this.relatedModel, [], fields);
            result = result.map(({ name, id, image_128 }) => ({ id, name, image: image_128 || null }));
            this.relatedRecords = result;
        }
        this.updateImage = (records) => {
            records.forEach(record => {
                record.image = this.relatedRecords?.find(item => item.id === record[this.defaultGroup][0])?.image;
            });
        };
        this.updateImage(values);
        this.updateImage(records);
        this.allRecords = values;
        this.records = records;
        if (this.showAllData && this.relatedModel) {
            let domain = this.splitAndCreateDomain(this.props.list._config.domain);
            if (domain) {
                let recordIds = await this.orm.search(this.relatedModel, domain);
                let result = this.relatedRecords.filter(item => recordIds.includes(item.id));
                records = records.length > 0
                      ? records.concat(result.filter(item => records.some(rec => rec[this.defaultGroup][0] !== item.id)))
                      : result;
            };
        };
        // Calling the 'CreateGroup()' method  for getting the groups
        this.CreateGroup(records);
        // Calling the 'CreateTasks()' method  for getting the tasks
        this.CreateTasks(records);
        const { isLocked, activeActions } = this.archInfo;
        // Configure gantt options based on the current week's dates and permissions
        this.options = {
            start: date.startOf("week").toISO(),
            end: date.endOf("week").toISO(),
            zoomable: false,
            horizontalScroll: true,
            verticalScroll: true,
            orientation: 'both',
            timeAxis: { scale: 'day', step: 1 },
            editable: {
                add: isLocked !== 'True' && activeActions.create,
                updateTime: activeActions.edit,
                updateGroup: isLocked !== 'True' && activeActions.editGroup,
                remove: isLocked !== 'True' && activeActions.delete,
            },
        };
        /**
        * Opening the Wizard of the current record while double clicking on the bar
        */
        this.options.onUpdate = async (item, callback) => {
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: item.content,
                target: 'new',
                res_id: Number(item.id),
                res_model: this.model,
                views: [[false, 'form']],
            }, {
                onClose: async () => {
                    let record = await this.orm.searchRead(this.model, [['id', '=', item.id]], this.fields);
                    record?.map(data => {
                        let utcStartTime = DateTime.fromFormat(data[this.archInfo.startDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
                        let utcEndTime = DateTime.fromFormat(data[this.archInfo.endDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
                        data[this.archInfo.startDate] = utcStartTime.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
                        data[this.archInfo.endDate] = utcEndTime.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
                        data.image = this.relatedRecords?.find(item => item.id === data[this.defaultGroup][0])?.image;
                    });
                    this.allRecords = this.allRecords.map(task => task.id === record[0]?.id ? record[0] : task);
                    this.env.searchModel._notify();
                },
            });
        };
        /**
        * Creating the task while double-tapping on an empty space or just dragging on empty space
        */
        this.options.onAdd = (item, callback) => {
            let startDate = this.formatDateToString(item.start);
            let endDate = item.end ? this.formatDateToString(item.end) : startDate;
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: "New",
                target: 'new',
                res_model: this.model,
                views: [[false, 'form']],
                context: {
                    ['default_'+ this.defaultGroup]: Number(item.group),
                    ['default_'+ this.archInfo.startDate]: startDate,
                    ['default_'+ this.archInfo.endDate]: endDate,
                }
            }, {
                onClose: async () => {
                    let record = await this.orm.searchRead(this.model, [], [...this.fields]);
                    record = record.filter(item => !this.allRecords.some(({id}) => id === item.id));
                    if (record.length > 0) {
                        record.map(data => {
                            let utcStartTime = DateTime.fromFormat(data[this.archInfo.startDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
                            let utcEndTime = DateTime.fromFormat(data[this.archInfo.endDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
                            data[this.archInfo.startDate] = utcStartTime.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
                            data[this.archInfo.endDate] = utcEndTime.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
                            data.image = this.relatedRecords?.find(item => item.id === data[this.defaultGroup][0])?.image;
                        });
                        this.records.push(...record);
                        this.allRecords.push(...record);
                        this.env.searchModel._notify();
                    };
                    callback(null);
                },
            });
        };
        /**
        * Changing the time and group of the task while dragging the bar
        */
        this.options.onMove = async (item, callback) => {
            if (this.archInfo.isLocked) {
                let record = this.state.tasks.find(task => task.id === item.id);
                this.notification.add("Dragging is not allowed.", { type: "warning", sticky: false, });
                callback(record);
            } else if (this.defaultGroup) {
                let record = await this.UpdateItemOnDrag(item, this.defaultGroup);
                item.content = record.name;
                this.records.forEach(data => {
                    if (data.id === item.id) {
                        data.name = record.name;
                        if (record[this.archInfo.startDate]) {
                            let utcStartTime = DateTime.fromFormat(record[this.archInfo.startDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
                            data[this.archInfo.startDate] = utcStartTime?.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
                        };
                        if (record[this.archInfo.endDate]) {
                            let utcEndTime = DateTime.fromFormat(record[this.archInfo.endDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
                            data[this.archInfo.endDate] = utcEndTime?.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
                        };
                        if (this.defaultGroup && record[this.defaultGroup]) {
                            data[this.defaultGroup] = record[this.defaultGroup];
                        };
                    };
                });
                callback(item);
            } else {
                this.orm.write(this.model, [Number(item.id)], {
                    [this.archInfo.startDate]: this.formatDateToString(item.start),
                    [this.archInfo.endDate]: this.formatDateToString(item.end)
                });
            };
        };
        /**
        * Unlink the task while clicking the delete button
        */
        this.options.onRemove = (item, callback) => {
            this.orm.unlink(this.model, [Number(item.id)]);
            this.records = this.records.filter(record => record.id !== item.id);
            this.allRecords = this.allRecords.filter(record => record.id !== item.id);
            if (!this.showAllData) {
                this.CreateGroup(this.records);
                // Updates the view after deleting
                this.timeline.setData({
                    groups: this.state.groups,
                });
            };
            callback(item);
        };
        this.timeline.setOptions(this.options);
        // Checking if the attribute defaultGroup has a date field; if true, displaying the warning.
        if (this.default_group_is_date) {
            this.defaultGroup = false;
            this.default_group_is_date = false;
            this.notification.add("Date field is not supported to the attribute 'default_group_by'", { type: "danger", sticky: true, });
        };
        this.timeline.setData({
            groups: this.defaultGroup && this.state.groups,
            items:  new vis.DataSet(this.state.tasks),
        });
        this.ref.el.querySelector('#view-selector').value = "Week";
    };
    /**
    * For updating the items value while dragging the item
    */
    async UpdateItemOnDrag(item, group) {
        let currentRecord = this.records.find(rec => rec.id === item.id);
        let startDate = new Date(currentRecord[this.archInfo.startDate]);
        let endDate = new Date(currentRecord[this.archInfo.startDate]);
        let data = {};
        if (item.start?.getTime() !== startDate?.getTime()) {
            data[this.archInfo.startDate] = this.formatDateToString(item.start);
        };
        if (item.end?.getTime() !== endDate?.getTime()) {
            data[this.archInfo.endDate] = this.formatDateToString(item.end);
        };
        if (item.group !== currentRecord[group][0]) {
           data[group] = item.group == 'x' ? false : item.group;
        };
        let value = await this.orm.write(this.model, [Number(item.id)], data);
        let fields = ['name', ...(group ? [group] : [])];
        let record = await this.orm.searchRead(this.model, [['id', '=', item.id]], fields);
        return {...data, ...record[0]};
    }
    /**
    * For getting the records in the current model and appending to the this.state.tasks
    */
    CreateTasks(records) {
        this.state.tasks = [];
        records.forEach((vals) => {
            let color = typeof vals[this.archInfo.color] === 'number' ? COLORS[vals[this.archInfo.color]] : vals[this.archInfo.color] || '#4368FA';
            let opacity = Math.round(Math.min(Math.max(0.5 || 1, 0), 1) * 255);
            let style = "background: repeating-linear-gradient(45deg, " + color + opacity.toString(16) + " 10px," + color + " 20px); min-height: 50px; display: flex; align-items: center;";
            let startDate = vals[this.archInfo.startDate];
            let endDate = vals[this.archInfo.endDate];
            let start = startDate ? this.formatDateTime(startDate) : null;
            let end = endDate ? this.formatDateTime(endDate) : null;
            let groupField =  this.defaultGroup && vals[this.defaultGroup] || (this.showAllData ? [vals.id, vals.name, vals.image] : null);
            let group = 'x';
            if (this.defaultGroup) {
                if (Array.isArray(groupField) && groupField.length === 2 && typeof (groupField[1]) === 'string') {
                    group = groupField[0];
                } else if (typeof (groupField) === 'string') {
                    group = this.state.groups.find(groupItem => groupItem.content === groupField)?.id || 'x';
                };
            };
            const found = this.state.tasks.some(item => item.id === vals.id);
            let task = {
              style,
              content: vals.name,
              id: vals.id,
              start,
              group,
            };
            if (start && !found) {
                endDate ? (task.end = end) : (task.editable = false);
                this.state.tasks.push(task);
            } else if (this.showAll) {
                this.state.tasks.push(task);
            };
        });
    }
    // For Generating the Groups
    CreateGroup(records) {
        this.state.groups = [];
        const processGroup = (groupField) => {
            let obj = {
                content: null,
                style: 'min-width:200px; width: auto; justify-content:center; display:flex; min-height: 60px !important;',
                image: null
            };
            if (Array.isArray(groupField) && groupField.length === 3 && typeof (groupField[1]) === 'string') {
                obj.id = groupField[0];
                obj.content = groupField[1];
                obj.image = groupField[2];
                const found = this.state.groups.some(item => item.id === obj.id && item.content === obj.content);
                // Preventing duplicate entries
                if (!found) {
                    this.state.groups.push(obj);
                };
            };
        };
        records.forEach((vals) => {
            let groupField = this.defaultGroup && (vals[this.defaultGroup] ? [...vals[this.defaultGroup], vals.image] : (this.showAllData ? [vals.id, vals.name, vals.image] : null));
            if (groupField && groupField.c) {
                // Checking whether the field is a date
                this.default_group_is_date = true;
            } else {
                processGroup(groupField);
            };
        });
    }
    // Formats a DateTime object into a string representation in the format 'YYYY-MM-DDTHH:mm:ss'.
    formatDateTime(dateTime) {
        if (typeof dateTime === 'string') {
            // If dateTime is a string
            const dateParts = dateTime.split(' ');
            const date = dateParts[0];
            const time = dateParts[1] ? dateParts[1] : '00:00:00';
            return `${date}T${time}`;
        } else {
            // If dateTime is a Luxon DateTime object wrapped in a Proxy
            const { year, month, day, hour, minute, second } = dateTime.c;
            return `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}T${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}:${second.toString().padStart(2, '0')}`;
        }
    }
    /**
    * Converting the UTC formate to local time
    */
    convertToLocal(data) {
        if (data[this.archInfo.startDate]) {
            let utcStartTime = DateTime.fromFormat(data[this.archInfo.startDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
            data[this.archInfo.startDate] = utcStartTime.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
        }
        if (data[this.archInfo.endDate]) {
            let utcEndTime = DateTime.fromFormat(data[this.archInfo.endDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
            data[this.archInfo.endDate] = utcEndTime.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
        }
        return data;
    }
    /**
    * Converting the local time to UTC format for saving to database
    */
    formatDateToString(date) {
        return DateTime.fromJSDate(date, { zone: 'utc' }).toFormat('yyyy-MM-dd HH:mm:ss');
    }
    /**
    * Updating the view mode while switching the and displaying the current period of date.
    */
    updateViewMode(mode, date = DateTime.now()) {
        let startDate = date.startOf(mode);
        let endDate = date.endOf(mode);
        const timeAxisConfig = {
            'Day': { scale: 'hour', step: 1 },
            'Year': { scale: 'month', step: 1 },
            'default': { scale: 'day', step: 1 }
        };
        this.current_window.start = startDate.toISO();
        this.current_window.end = endDate.toISO();
        this.timeline.setOptions({
            timeAxis: timeAxisConfig[mode] || timeAxisConfig['default']
        });
        this.ref.el.querySelector('.currentDate').innerHTML = mode !== 'Day' ? `${startDate.toFormat('yyyy-MM-dd')} - ${endDate.toFormat('yyyy-MM-dd')}` : startDate.toFormat('yyyy-MM-dd');
        this.timeline.setWindow(this.current_window);
    }
    /**
    *  Changing the view range and displaying period while clicking the navigate buttons
    */
    UpdateDateRange(value, mode) {
        const startDateTime = DateTime.fromISO(this.current_window.start);
        const nextDate = value ? startDateTime.plus({ [mode]: 1 }) : startDateTime.minus({ [mode]: 1 });
        this.updateViewMode(mode, nextDate);
    }
    splitAndCreateDomain(domain) {
        const newDomain = [];
        for (const item of domain) {
            if (typeof item === 'object') {
                if (item[0] !== this.defaultGroup && !(newDomain.at(-1) === '|' || newDomain.at(-2) ==='|')) {
                    return false;
                } else if (item[0] === this.defaultGroup) {
                    item[0] = item[1] === 'ilike' || item[1] === 'not ilike' ? 'name' : 'id';
                    newDomain.push(item);
                };
            } else {
                newDomain.push(item);
            };
        };
        if (newDomain.length === 2 && newDomain[0] === '|') {
            newDomain.shift();
        };
        return newDomain;
    };
}
GanttRenderer.template = 'cyllo_web.GanttRenderer';