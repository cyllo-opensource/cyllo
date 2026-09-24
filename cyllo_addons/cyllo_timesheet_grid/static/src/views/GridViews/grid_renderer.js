/** @odoo-module **/
import { onMounted, Component, useState, useRef, onPatched, useEffect, useExternalListener, onWillDestroy, onWillStart } from "@odoo/owl";
import { View } from "@web/views/view";
import { GridFloatTimeField } from './grid_float_time'
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Field } from "@web/views/fields/field";
import { Record } from "@web/model/record";
import { ViewScaleSelector } from "@web/views/view_components/view_scale_selector";
import { session } from "@web/session";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";
export class GridRenderer extends Component {
    /*
        GridRenderer component is created to render the
        timesheet template
    */
    async setup() {
        onWillDestroy(() => {
            clearInterval(this.counterInterval)
        })
        useExternalListener(window, 'keydown', this.keyDownEvent)
        this.activeElementId = '';
        this.isGrouped = this.props.list.isGrouped || false;
        this.counterInterval;  // Timer value is stored in this variable
        this.grid = useState({ record : [] ,runningTime:false, time: 0})
        this.orm = useService("orm");
        const { block, unblock } = this.env.services.ui
        this.block = block;
        this.unblock = unblock;
        this.project = useState({ projectVal: {} })
        this.projectRef = useRef('project-project')
        this.MainGridRenderer = useRef('MainGridRenderer')
        this.taskRef = useRef('project-task')
        this.task = useState({ taskVal: {} })
        this.timerStartsRunning = useState({timer:false})
        const searchArray = ['user_id','=',session.uid]
        this.myTimeSheet = this.props.domain.some(arr => Array.isArray(arr) && arr.join(',') === searchArray.join(','))
        this.viewDay = useState({ currentViewDate: new Date(), currentMonth:'',currentWeek: new Date() })
        this.element = useRef("renderer");
        this.action = useService("action");
        this.table = useState({
                    tableHead : [],
                    tableBody : [],
                    employeeWorkHour: 0.0,
                    week:false,
                    employees: [],
                    cssFoot:'',
                    employeeHead:'',
                    selectedMod: 'Day'
                })
        this.selectedPeriod = useRef("nextDate")
        this.selectedPeriodValue;
        this.state = useState({
            records: this.props.list.records
        })
        /**
         * Update the component's state with new records from props and refresh the data display.
         */
         useEffect((ev) => {
            this.isGrouped = this.props.list.isGrouped || false;
            // Update the component state with new records from props
            this.state.records = this.props.list.records;
            this.closeDrop();
            // Update the table header
            this.updateTableHead();
            // Refresh the data display based on search criteria
            this.getDataSearch().then(()=>{
                this.unblock()
            });

         }, ()=>[this.props.list, this.props.list?.records]);
         /**
         * Callback function triggered after a patch operation.
         * Updates various UI elements and applies necessary styles.
         */
        onPatched(async () => {
            this.selectedPeriodValue = this.selectedPeriod.el.value
            // Select date container elements
            this.dataContainer = this.element.el.querySelectorAll('.date-container');
            // Select data container body elements
            this.dataBodyContainer = this.element.el.querySelectorAll('.data-container-body');
            // Select serial number elements
            this.serialIds = this.element.el.querySelectorAll('.serial-number');
            // Store and select data records for the record tree
            this.recordTree = this.element.el.querySelectorAll('.data-container-body');
            // Apply hover opacity effects
            this.hoverOpacityDiv();
            // Select and highlight add-a-line hours element
            this.dataAddLineDivHighlight = this.element.el.querySelectorAll('.add-a-line-hours');
            // Apply custom CSS styles to the component
            await this.cssFoot();
        });
        /**
         * Callback function triggered before the component's initialization.
         * Retrieves employee work hour data for overtime calculation and checks for day-hour conditions.
         */
        onWillStart(async () => {
            // Retrieve employee work hour data for overtime calculation

            this.table.employeeWorkHour = await this.orm.call('timesheet.grid', 'overtime_work', [session.uid]);
            // Check for day-hour conditions by invoking the day_hour_check method
            this.isDay = await this.orm.call('timesheet.grid', 'day_hour_check', []).then((result) => {
                return result;
            });
        });
        /**
         * Callback function triggered when the component is mounted.
         * Retrieves cached data from local storage, initializes timer state, and starts the timer if necessary.
         * Removes cached data from local storage after processing.
         * @returns {Promise<void>}
         */
        onMounted(async () => {
            // Retrieve cached values from local storage for initial timer setup
            let values = JSON.parse(browser.localStorage.getItem('AnalyticCache') || '{}');
            if (values?.projectId?.projectId && values?.time) {
                this.timerStartsRunning.timer = true;
                this.project.projectVal = {
                    id: values.projectId.projectId,
                    display_name: values.projectId.projectName
                };
                this.task.taskVal = {
                    id: values.taskId.taskId,
                    display_name: values.taskId.taskName
                };
                const timeDiff = Math.abs(new Date() - new Date(values.storeTime)) / 1000;
                this.grid.time = values.time + (timeDiff / 3600);
                this.activeElementId = values.activeElementId
                setTimeout(() => { owl.status(this) !== "destroyed" && this.onclickStart() }, 500)
            }
            // Retrieve cached values from local storage for timer resumption
            let cacheVal = JSON.parse(browser.localStorage.getItem('AnalyticCacheResume') || '{}');

            if (cacheVal && cacheVal.time > 0) {
                this.timerStartsRunning.timer = true;
                this.project.projectVal = {
                    id: cacheVal.projectId.projectId,
                    display_name: cacheVal.projectId.projectName
                };
                this.task.taskVal = {
                    id: cacheVal.taskId.taskId,
                    display_name: cacheVal.taskId.taskName
                };
                const storedTime = new Date(cacheVal.storeTime);
                this.grid.time = cacheVal.time + (timeDiff / 3600);
                this.activeElementId = cacheVal.activeElementId
                setTimeout(() => { owl.status(this) !== "destroyed" && this.onclickStart() }, 500)

            }
            // Remove cached data from local storage
            if (this.myTimeSheet){
             browser.localStorage.removeItem('AnalyticCache');
             browser.localStorage.removeItem('AnalyticCacheResume');
            }

        });
        /**
         * Creates a new project record with the given search query and parameters.
         * Updates the project and task values accordingly.
         * @param {string} searchQuery - The search query for the new project.
         * @param {object} params - Additional parameters for creating the project.
         */
        this.quickCreate = async (searchQuery, params) => {
            // Create a new project record with the given search query and parameters
            const newRecord = await this.orm.call('project.project', 'create', [{
                name: searchQuery,
                allow_timesheets: true
            }]);
            // Update the project value
            this.project.projectVal = { id: newRecord, display_name: searchQuery };
            // Clear the task value
            this.task.taskVal = {};
        };
        /**
         * Creates a new task record with the given search query and parameters.
         * Updates the task value and associates it with a project and analytic account.
         * @param {string} searchQuery - The search query for the new task.
         * @param {object} params - Additional parameters for creating the task.
         */
        this.quickCreateTask = async (searchQuery, params) => {
            // Retrieve project_id and analytic_id from the dataset of the projectRef element
            const project_id = this.projectRef.el?.dataset.projectId;
            const analytic_id = this.projectRef.el?.dataset.analytic;
            // Prepare task data with name and optional project_id
            let taskData = {
                name: searchQuery,
            };
            taskData = project_id ? { ...taskData, project_id: parseInt(project_id) } : taskData;
            // Create a new task record
            const newRecord = await this.orm.call('project.task', 'create', [taskData]);
            // Associate the task with the project and analytic account
            const analytic = await this.orm.call('account.analytic.line', 'write_task', [{
                analytic_account_id: parseInt(analytic_id),
                project_id: parseInt(project_id),
                task_id: newRecord
            }]);
            // Update the task value
            this.task.taskVal = { id: newRecord, display_name: searchQuery };
        };
    }
    async closeDrop(){
        const self = this
        window.addEventListener('click', function (event) {
            const recordContainer = self.MainGridRenderer.el?.querySelector('#recordContainer');
            const recordLink = self.MainGridRenderer.el?.querySelector('#recordLink');
            // Check if the clicked element is outside the dropdown or the button
            if (!recordContainer?.contains(event.target) && !recordLink?.contains(event.target)) {
                // Hide the dropdown by removing 'show' class
                if (recordContainer?.classList?.contains('show')) {
                    recordContainer?.classList?.remove('show')
                }
            }
        });
    }
    /**
     * Starts counting time from a specified starting point and updates the time grid accordingly.
     * Also, manages caching of time-related data in local storage.
     * @param {number} start - The starting point for time counting.
     * @returns {Promise<void>}
     */
    async startCountingTime() {
        // Initialize the count based on grid time or set it to 0
        let count = this.grid.time * 3600 || 0;
        // Remove any existing cached data related to time
        await browser.localStorage.removeItem('AnalyticCache');
        if(this.myTimeSheet){
        // Prepare project and task data for caching
        const project = {
            projectId: parseInt(this.projectRef.el.dataset.projectId),
            projectName: this.projectRef.el.dataset.projectName
        };
        const task = {
            taskId: parseInt(this.task.taskVal.id),
            taskName: this.task.taskVal.display_name
        };
        // Prepare values for caching
        let activeElement = (typeof this.activeElementId !== 'string' ) ? this.activeElementId.getAttribute('id') : this.activeElementId
        const values = {
            projectId: project,
            taskId: task,
            time: this.grid.time,
            storeTime: new Date(),
            activeElementId: activeElement
        };
        // Cache values if no previous cache exists
        if (!browser.localStorage.getItem('AnalyticCache')){
            await browser.localStorage.setItem('AnalyticCache', JSON.stringify(values));
        }
        // Retrieve cached data
        let cache = JSON.parse(browser.localStorage.getItem('AnalyticCache') || '{}');
        if (activeElement){
            let elementId = this.element.el.querySelector(`#${activeElement}`)
            let stopSpan = elementId.querySelector('.serial-stop')
            let activeElementId = elementId.querySelector('.active')
            if (activeElementId.classList.contains('serial-alphabet')){
                activeElementId.classList.remove('active')
                stopSpan.classList.add('active')
                elementId.parentElement.classList.remove('play')
            }
        }
        // Start the interval to update time
        this.counterInterval = setInterval(async () => {
            count++;
            this.grid.time = count / 3600;
            cache.time = count / 3600;
            cache.storeTime = new Date()
            if (this.project.projectVal) {
                cache.projectId.projectId = this.project.projectVal.id
                cache.projectId.projectName = this.project.projectVal.display_name
            }
            if (this.task.taskVal) {
                cache.taskId.taskId = this.task.taskVal.id
                cache.taskId.taskName = this.task.taskVal.display_name
            }
            // Update the cached data
            await browser.localStorage.setItem('AnalyticCache', JSON.stringify(cache));
        }, 1000); // The counter will increment every 1000ms (1 second)
    }}
    /**
     * Handles the key down event, specifically checking for the Enter key (keyCode 13).
     * If the Enter key is pressed, triggers the '
     ' function asynchronously.
     * @param {Event} ev - The key down event object.
     * @returns {Promise<void>}
     */
    async keyDownEvent(ev) {
        //Function to start the timer on press ENTER
        if (ev.keyCode === 13) {
            await this.onclickStart();
        }
    }
     /**
     * Sums the numeric values within an array or returns 0 if the input is not an array.
     * @param {Array|number} data - An array of numeric values or a single numeric value.
     * @returns {number} - The sum of the numeric values in the input array, or 0 if the input is not an array.
     */
    sumUnit(data) {
    //Function to get total hours of employee in week and month all timesheet
        return (Array.isArray(data)) ? data.reduce((acc, val) => acc + val, 0) : 0;
    }
    /**
     * Adjusts CSS properties for the table's footer and employee head based on the current view date.
     * Changes the background color of the footer and the text color of the employee head if the current view date matches today's date.
     * Otherwise, clears the CSS properties.
     */
    cssFoot() {
        //Function to add background color in add line tr if it is today in day wise
        // Determine if the current view date matches today's date
        const isCurrentDate = (
            this.viewDay.currentViewDate.getDate() === new Date().getDate() &&
            this.viewDay.currentViewDate.getMonth() === new Date().getMonth() &&
            this.viewDay.currentViewDate.getYear() === new Date().getYear()
        );
        // Set the CSS properties for the table's footer and employee head based on the current date match
        this.table.cssFoot = isCurrentDate ? '#e7e9ed !important' : '';
        this.table.employeeHead = isCurrentDate ? '#ebedca !important' : '';
    }
    //Function to set the mouse hover for week and month horizontal and vertical styling
    /**
     * Performs mouse-related actions on the specified selectable element in the timesheet grid table.
     * Changes the background color of the cells and displays the overtime hour div based on the event.
     * @param {string} selectable - The index of the selectable element.
     * @param {string} event - The mouse event ('mouseenter' or 'mouseleave').
     */
    doMouseActions(selectable, event) {
        const tBody = this.element.el.querySelector('.timesheet-grid-table');
        let elements = tBody.querySelectorAll("[data-index=" + selectable + "]");
        const today = new Date();
        let indexValue;
        // Iterate through elements to apply mouse actions
        elements.forEach((el) => {
            if (parseInt(el.dataset.dayObj) === today.getDate() &&
                parseInt(el.dataset.monthObj) === today.getMonth() &&
                parseInt(el.dataset.yearObj) === today.getYear()) {
                indexValue = el.dataset.index;
            }
            if (el.dataset.index !== indexValue) {
                if (el.className !='date-container'){
                el.style.background = (event === 'mouseenter' ) ? '#f9faf0' : 'unset';}
            }
        });
        // Handle overtime cell and div display
        const overTimeCell = tBody.querySelector("[data-index=final_" + selectable + "]");
        let overTimeDiv = overTimeCell?.querySelector('.overtime-hour');
        if (overTimeDiv) {
            overTimeDiv.style.display = (event === 'mouseenter') ? 'block' : 'none';
        }
    }
    /**
     * Handles the mouseenter event for a selectable element in the timesheet grid table.
     * Calls 'doMouseActions' with the 'mouseenter' event.
     * @param {Event} ev - The mouseenter event object.
     */
    mouseEnter(ev) {
        const selectable = ev.srcElement.dataset.index;
        this.doMouseActions(selectable, 'mouseenter');
    }
    /**
     * Handles the mouseleave event for a selectable element in the timesheet grid table.
     * Calls 'doMouseActions' with the 'mouseleave' event.
     * @param {Event} ev - The mouseleave event object.
     */
    mouseLeave(ev) {
        const selectable = ev.srcElement.dataset.index;
        this.doMouseActions(selectable, 'mouseleave');
    }
    /**
     * Applies hover opacity and italic styling to specific elements within the data body container.
     * Adjusts the opacity and styling on mouseenter and mouseleave events based on specific conditions.
     */
    hoverOpacityDiv() {
        // To change the opacity of the unit amount on hovering
        if (this.dataBodyContainer) {
            // Iterate through elements in the data body container
            for (let element of this.dataBodyContainer) {
                let spanElement = element.querySelectorAll('.time-format');
                // Iterate through span elements within the element
                for (let span of spanElement) {
                    // Apply hover opacity and italic styling for specific conditions
                    if (this.isDay ? span?.dataset.time === '0.00' : span?.dataset.time === '00:00') {
                        span.classList.add('text-opacity-25');
                        // Attach event listeners for mouseenter and mouseleave
                        element.addEventListener('mouseenter', function() {
                            span.classList.remove('text-opacity-25');
                            span.classList.remove('data-time-italic');
                        });
                        element.addEventListener('mouseleave', function() {
                            if (span?.dataset.time === '00:00' || span?.dataset.time === '0.00') {
                                span.classList.add('data-time-italic');
                                span.classList.add('text-opacity-25');
                            }
                        });
                    } else {
                        span.classList.remove('text-opacity-25');
                    }
                }
            }
        }
    }
    /**
     * Formats a decimal value representing time into a human-readable time format.
     * The formatting differs based on whether it represents working hours in a day or not.
     * @param {number} decimalValue - The decimal value representing time.
     * @returns {string} - The formatted time in hours and minutes (HH:mm) or in a decimal format.
     */
    formatTime(decimalValue) {
        //Function to format the float unit amount in to HH:MM format
        let result;
        if (this.isDay) {
            // Calculate time in a day and format as a decimal
            result = (decimalValue / this.table.employeeWorkHour).toFixed(2);
        } else {
            let negToPositive, hours, minutes, formattedHours, formattedMinutes, formattedTime, operator;
            negToPositive = (decimalValue < 0) ? Math.abs(decimalValue) : decimalValue;
            hours = Math.floor(negToPositive);
            minutes = Math.round((negToPositive % 1) * 60);
            formattedHours = String(hours).padStart(2, '0');
            formattedMinutes = String(minutes).padStart(2, '0');
            operator = (decimalValue < 0) ? '-' : '';
            result = operator + formattedHours + ':' + formattedMinutes;
        }
        return result;
    }
    isIterable(variable){
        return Symbol.iterator in Object(variable)
    }
    /**
     * Retrieves and updates timesheet data based on the selected view mode (Day, Week, Month).
     * Depending on the view mode, filters and displays timesheet records accordingly.
     * Also updates the employee work hours and applies hover opacity styling to specific elements.
     * @returns {Promise<void>}
     */
    async getDataSearch() {
    //Function to fetch the datas to day,week and month
        // Get the selected view mode
        const selected = this.element.el.querySelector('#view-selector').value;
        // Initialize domain and date information
        let domain = this.env.searchModel.globalDomain;
        let date = new Date(this.viewDay.currentViewDate);
        var formattedDate = date.toISOString().split('T')[0];
        let result = this.state.records;
        let tableBody = []
        // Iterate through result records and create date objects
        for (let data of result) {
            let dateObject = new Date(
                data.data.date.c.year,
                data.data.date.c.month - 1,
                data.data.date.c.day,
                data.data.date.c.hour,
                data.data.date.c.minute,
                data.data.date.c.second,
                data.data.date.c.millisecond
            );
            data.dateObj = dateObject;
        }
        // Handle different view modes
        if (selected === 'Day') {
            this.table.week = false;
            domain = domain.filter(([fieldName]) => fieldName !== 'date');
            domain.push(['date', '=', formattedDate]);
            this.env.searchModel.globalDomain = domain;
            tableBody = await this.filteredResultXML(this.filterData(result));
        } else if (selected === 'Week') {
            this.table.week = true;
            let weekDate = new Date(date);
            weekDate.setDate(weekDate.getDate() + 7);
            let newFormatted = weekDate.toISOString().split('T')[0];
            domain = domain.filter(([fieldName]) => fieldName !== 'date');
            domain.push(['date', '>=', formattedDate]);
            domain.push(['date', '<', newFormatted]);
            this.env.searchModel.globalDomain = domain;
            tableBody = await this.filteredResultXML(this.filterData(result), selected);
            this.table.employeeWorkHour = await this.orm.call('timesheet.grid', 'overtime_work', [session.uid]);
        } else {
            this.table.week = true;
            const dateObj = new Date(date);
            const currentYear = dateObj.getFullYear();
            const currentMonth = dateObj.getMonth();
            const startDate = new Date(currentYear, currentMonth, 1);
            const endDate = new Date(currentYear, currentMonth + 1, 0);
            let newFormattedMonth = startDate.toISOString().split('T')[0];
            let newFormattedMonthEnd = endDate.toISOString().split('T')[0];
            domain = domain.filter(([fieldName]) => fieldName !== 'date');
            domain.push(['date', '>', newFormattedMonth], ['date', '<', newFormattedMonthEnd]);
            this.env.searchModel.globalDomain = domain;
            tableBody = await this.filteredResultXML(this.filterData(result), selected);
            this.table.employeeWorkHour = await this.orm.call('timesheet.grid', 'overtime_work', [session.uid]);
        }
        if(this.isGrouped){
            this.table.tableBody = this.makeGroup()
        }
        else {
            this.table.tableBody = tableBody
        }
        // Apply hover opacity styling to specific elements
        this.hoverOpacityDiv();
    }
    makeGroup(){
        let tableBody = []
        let count = 0
        const today = new Date()
        this.props.list.groups.forEach((group,index) => {
            let recs = this.filterData(group.records)
            let item = {
                display_name: group.displayName,
                css:((this.viewDay.currentViewDate.getDate() === today.getDate()) && (this.viewDay.currentViewDate.getMonth() === today.getMonth()) && (this.viewDay.currentViewDate.getYear() === today.getYear())) ? '#F5F6E6;':'',
                task_id: [false, ''],
                employee_id: [false, false],
                rec_id: false,
            }
            if(recs.length){
                let def_rec = recs[0]
                item.project_id = def_rec.data.project_id
                item.date = def_rec.dateObj
                let unit_amount = this.sumUnit(recs.map(rec => rec.data.unit_amount))
                item.unit_amount = this.formatTime(unit_amount)
                item.unitAmountUnformat = unit_amount
                item.dataWeek = this.weekDataResult(recs.filter(subData => (subData.data.task_id[0] === def_rec.data.task_id[0]) && (subData.data.employee_id[0] === def_rec.data.employee_id[0] && (subData.data.project_id[0] === def_rec.data.project_id[0]) )))
                item.serialNumber = this.serialNumber(count)
                count++;
                tableBody.push(item)
            }
        })
        tableBody.totalUnitAmount = this.sumUnit(tableBody.map(rec => rec.unitAmountUnformat))
        return tableBody
    }
    /**
     * Filters and formats timesheet data based on the selected view mode (Day, Week, Month).
     * Returns the formatted result that includes calculated unit amounts and relevant details.
     * @param {Array} filteredResult - The filtered timesheet data for the selected view mode.
     * @param {string} selected - The selected view mode (Day, Week, Month).
     * @returns {Array} - The formatted timesheet data with calculated unit amounts and details.
     */
    async filteredResultXML(filteredResult,selected){
    //Function to filter the data
        let formattedResult;
        const today = new Date()
        var mapped_data = filteredResult.map( data => data.data.task_id[0])
        var remainingHoursForTasks = await this.orm.call("timesheet.grid", 'fetch_remaining_hours' ,[mapped_data])
        const keys = ['id', 'remaining_hours', 'allocated_hours', 'effective_hours'];
        // Convert each tuple into an object with specified keys
        remainingHoursForTasks = remainingHoursForTasks.map(values => {
                    return keys.reduce((obj, key, index) => {
                        obj[key] = values[index];
                        return obj;
                    }, {});
                });

        if (selected === 'Week'){
            // Format timesheet data for the Week view mode
            let formatted = filteredResult.map((data,index)=>({
                date : data.dateObj,
                timesheet_id:data.data.id,
                employee_id:data.data.employee_id,
                unit_amount: this.formatTime(data.data.unit_amount),
                unitAmountUnformat:data.data.unit_amount,
                project_id: data.data.project_id,
                task_id: data.data.task_id,
                rec_id: data.resId,
                display_name : data.data.display_name,
                planned_hour : remainingHoursForTasks.filter(taskData => data.data.task_id[0] === taskData.id)[0]?.allocated_hours || 0,
                effective_hour : remainingHoursForTasks.filter(taskData => data.data.task_id[0] === taskData.id)[0]?.effective_hours || 0,
                task_remaining_time: remainingHoursForTasks.filter(taskData => taskData.allocated_hours != 0 && data.data.task_id[0] === taskData.id)[0]?.remaining_hours || 0,
                dataWeek : this.weekDataResult(filteredResult.filter(subData => (subData.data.task_id[0] === data.data.task_id[0]) && (subData.data.employee_id[0] === data.data.employee_id[0] && (subData.data.project_id[0] === data.data.project_id[0]) )))
           }))
            const recordList = formatted.map(subData =>
                subData.dataWeek.map(data => data.unFormattedUnitAmount)
            );
            //mapping the footer total value of each date
            const uniqueListsMap = {};
            const resultRecordList = recordList.reduce((acc, curr) => {
                const currString = JSON.stringify(curr);
                if (!uniqueListsMap[currString]) {
                    uniqueListsMap[currString] = true;
                    curr.forEach((num, index) => {
                      acc[index] = (acc[index] || 0) + num;
                    });
                }
                return acc;
            }, []);
            let weeklyData = Array.from(new Set(formatted.map(item => JSON.stringify({
                    task_id: item.task_id,
                    project_id: item.project_id
                }))))
                .map(taskAndProject => JSON.parse(taskAndProject))
                .map(taskAndProject => formatted.find(item => JSON.stringify(item.task_id) === JSON.stringify(taskAndProject.task_id) && JSON.stringify(item.project_id) === JSON.stringify(taskAndProject.project_id)));
            formattedResult = this.myTimeSheet ? weeklyData : this.allTimesheetEmployee(formatted);
            formattedResult.forEach((item, index) => {
                item.serialNumber = this.serialNumber(index);
            });
            formattedResult['resultRecordList'] =(resultRecordList.length != 0)? resultRecordList: Array.from({ length:7 },() => 0);
            formattedResult['overTime'] = formattedResult['resultRecordList'].map(result => result - this.table.employeeWorkHour );
        }
        else if(selected === 'Month'){
            let formatted = filteredResult.map((data, index) => ({
                date : data.dateObj,
                timesheet_id:data.data.id,
                employee_id:data.data.employee_id,
                unit_amount: this.formatTime(data.data.unit_amount),
                unitAmountUnformat:data.data.unit_amount,
                project_id: data.data.project_id,
                task_id: data.data.task_id,
                rec_id: data.resId,
                display_name : data.data.display_name,
                planned_hour : remainingHoursForTasks.filter(taskData => data.data.task_id[0] === taskData.id)[0]?.allocated_hours || 0,
                effective_hour : remainingHoursForTasks.filter(taskData => data.data.task_id[0] === taskData.id)[0]?.effective_hours || 0,
                task_remaining_time: remainingHoursForTasks.filter(taskData => taskData.allocated_hours != 0 && data.data.task_id[0] === taskData.id)[0]?.remaining_hours || 0,
                dataWeek : this.weekDataResult(filteredResult.filter(subData => (subData.data.task_id[0] === data.data.task_id[0]) && (subData.data.employee_id[0] === data.data.employee_id[0] && (subData.data.project_id[0] === data.data.project_id[0]) ))),
            }))
            const recordList = formatted.map(subData =>
                subData.dataWeek.map(data => data.unFormattedUnitAmount)
            );
            //mapping the footer total value of each date
            const uniqueListsMap = {};
            const resultRecordList = recordList.reduce((acc, curr) => {
              const currString = JSON.stringify(curr);
              if (!uniqueListsMap[currString]) {
                uniqueListsMap[currString] = true;
                curr.forEach((num, index) => {
                  acc[index] = (acc[index] || 0) + num;
                });
              }
              return acc;
            }, []);
            const MonthData = Array.from(new Set(formatted.map(item => JSON.stringify({
                task_id: item.task_id,
                project_id: item.project_id
            }))))
            .map(taskAndProject => JSON.parse(taskAndProject))
            .map(taskAndProject => {
                const {
                    task_id,
                    project_id
                } = taskAndProject;
                const taskRecords = formatted.filter(item => JSON.stringify(item.task_id) === JSON.stringify(task_id) && JSON.stringify(item.project_id) === JSON.stringify(project_id));
                const unitAmountSum = taskRecords.reduce((sum, item) => sum + parseFloat(item.unitAmountUnformat), 0);
                return {
                    ...taskRecords[0],
                    unit_amount: this.formatTime(unitAmountSum)
                };
            });
            formattedResult = this.myTimeSheet ? MonthData : this.allTimesheetEmployee(formatted) ;
            formattedResult.forEach((item, index) => {
                item.serialNumber = this.serialNumber(index);
            });
            const monthData = this.weekMonthCount()
            formattedResult['resultRecordList'] =(resultRecordList.length != 0)? resultRecordList: Array.from({ length: monthData[monthData.length -1] },() => 0);
            formattedResult['overTime'] = formattedResult['resultRecordList'].map(result => result - this.table.employeeWorkHour );
        }
        else{
            let formatted = filteredResult.map((data, index) => ({
                employee_id:data.data.employee_id,
                date : data.dateObj,
                timesheet_id:data.data.id,
                unit_amount: this.formatTime(data.data.unit_amount),
                unitAmountUnformat:data.data.unit_amount,
                project_id: data.data.project_id,
                task_id: data.data.task_id,
                rec_id: data.resId,
                css:((this.viewDay.currentViewDate.getDate() === today.getDate()) && (this.viewDay.currentViewDate.getMonth() === today.getMonth()) && (this.viewDay.currentViewDate.getYear() === today.getYear())) ? '#F5F6E6;':'',
                display_name : data.data.display_name,
                planned_hour : remainingHoursForTasks.filter(taskData => data.data.task_id[0] === taskData.id)[0]?.allocated_hours || 0,
                effective_hour : remainingHoursForTasks.filter(taskData => data.data.task_id[0] === taskData.id)[0]?.effective_hours || 0,
                task_remaining_time: remainingHoursForTasks.filter(taskData => taskData?.allocated_hours != 0 && data.data.task_id[0] === taskData.id)[0]?.remaining_hours || 0,
            }))
            let dailyData = Array.from(new Set(formatted.map(item => JSON.stringify({ task_id: item.task_id, project_id: item.project_id }))))
              .map(taskAndProject => JSON.parse(taskAndProject))
              .map(taskAndProject => {
                const { task_id, project_id } = taskAndProject;
                const taskRecords = formatted.filter(item => JSON.stringify(item.task_id) === JSON.stringify(task_id) && JSON.stringify(item.project_id) === JSON.stringify(project_id));
                const unitAmountSum = taskRecords.reduce((sum, item) => sum + parseFloat(item.unitAmountUnformat), 0);
                return {
                  ...taskRecords[0],
                  unit_amount: this.formatTime(unitAmountSum),
                  unitAmountUnformat: unitAmountSum
                  };
                  });
                dailyData['totalUnitAmount'] = dailyData.map(data => data.unitAmountUnformat).reduce((sum, item) => sum + parseFloat(item), 0)
            formattedResult = this.myTimeSheet ? dailyData : this.allEmployeeData(formatted)
            formattedResult.forEach((item, index) => {
                item.serialNumber = this.serialNumber(index);
            });
        }
        return formattedResult
    }
    /**
     * Fetches and organizes all timesheet data for each employee, grouping by employee and task/project.
     * @param {Array} formatted - The formatted timesheet data for a specific view mode.
     * @returns {Array} - An array of dictionaries containing grouped timesheet data for each employee.
     */
    allEmployeeData(formatted){
    // Function to fetch Day wise All timesheet data
        const employees = Array.from(new Set(formatted.map(data => data.employee_id).map(JSON.stringify)),JSON.parse)
        const filteredData = {};
        employees.forEach(employee => {
            const employeeDataFiltered = formatted.filter(data => {
                return JSON.stringify(data.employee_id) === JSON.stringify(employee);
            });
            const taskMap = new Map();
            employeeDataFiltered.forEach((dict) => {
                const taskAndProject = JSON.stringify({
                    task_id: dict.task_id,
                    project_id: dict.project_id
                }); // Convert the task_id and project_id to a string for Map key
                if (taskMap.has(taskAndProject)) {
                    taskMap.get(taskAndProject).unitAmountUnformat += dict.unitAmountUnformat;
                    taskMap.get(taskAndProject).unit_amount = this.formatTime(taskMap.get(taskAndProject).unitAmountUnformat);
                    // If duplicate task_id and project_id, add unitAmount
                } else {
                    taskMap.set(taskAndProject, {
                        ...dict
                    }); // If not duplicate, set the dictionary in the Map
                }
            });
            // Convert the Map values back to an array to get the filtered and combined dictionaries
            const filteredListOfDicts = Array.from(taskMap.values());
            filteredData[JSON.stringify(employee)] = {
                employee: employee,
                employee_data: filteredListOfDicts,
                sumUnitTime: filteredListOfDicts.map(data => data.unitAmountUnformat).reduce((sum, item) => sum + parseFloat(item), 0)
            };
        });
        // Convert the filteredData dictionary to an array of grouped employee timesheet data
        const result = Object.values(filteredData);
        return result
    }
    /**
     * Organizes timesheet data for each employee, grouping by employee and task/project, and calculating total time sums.
     * @param {Array} formatted - The formatted timesheet data for a specific view mode.
     * @returns {Array} - An array of dictionaries containing grouped timesheet data for each employee.
     */
    allTimesheetEmployee(formatted){
    //Function to fetch AllTimesheet Weekly and monthly data
        const employees = Array.from(new Set(formatted.map(data => data.employee_id).map(JSON.stringify)),JSON.parse)
        const filteredData = {};
        employees.forEach(employee => {
            const employeeDataFiltered = formatted.filter(data => {
                return JSON.stringify(data.employee_id) === JSON.stringify(employee);
            });
            const taskMap = new Map();
            employeeDataFiltered.forEach((dict) => {
                const taskAndProject = JSON.stringify({
                    task_id: dict.task_id,
                    project_id: dict.project_id
                }); // Convert the task_id and project_id to a string for Map key
                if (taskMap.has(taskAndProject)) {
                    taskMap.get(taskAndProject).unitAmountUnformat += dict.unitAmountUnformat;
                    taskMap.get(taskAndProject).unit_amount = this.formatTime(taskMap.get(taskAndProject).unitAmountUnformat);
                    // If duplicate task_id and project_id, add unitAmount
                } else {
                    taskMap.set(taskAndProject, {
                        ...dict
                    }); // If not duplicate, set the dictionary in the Map
                }
            });
            // Convert the Map values back to an array to get the filtered and combined dictionaries
            const filteredListOfDicts = Array.from(taskMap.values());
            filteredData[JSON.stringify(employee)] = {
                employee: employee,
                employee_data: filteredListOfDicts,
                sumUnitTime: this.arraySum(filteredListOfDicts.map(item => item.dataWeek)),
                css: filteredListOfDicts[0].dataWeek.map(item => item.css )
            };
        });
        // Convert the filteredData dictionary to an array of grouped employee timesheet data
        const result = Object.values(filteredData);
        // Calculate total sum of unit time across all employees
        result['totalSumUnit'] = result.map(item => item.sumUnitTime).reduce((acc, arr) => { arr.forEach((num, index) => {
                        acc[index] = (acc[index] || 0) + num;
                    })
                    return acc}, [])
        return result
    }
    //Function to get the sum of hours for each employees in the corresponding index in week and month all timesheet
    arraySum(data){
    let result = data.map(innerArray => {
        return innerArray.map(dict => dict.unFormattedUnitAmount)
    }).reduce((acc, arr) => { arr.forEach((num, index) => {
        acc[index] = (acc[index] || 0) + num;
    })
    return acc}, [])
    return result
    }
    //Function to get the weekly and monthly timesheet on each date
    weekDataResult(filteredResult){
        const result = [];
        //Month Data
        let date = this.viewDay.currentViewDate
        const selected = this.element.el.querySelector('#view-selector').value
        const dateObj = new Date(date)
        const currentYear = dateObj.getFullYear();
        const currentMonth = dateObj.getMonth();
        const startDate = new Date(currentYear, currentMonth, 1);
        const endDate = new Date(currentYear, currentMonth + 1, 0)
        let daysInMonth = endDate.getDate();
        let startDateNew = new Date(startDate)
        const iterations = selected === 'Week' ? 7 : daysInMonth;
        const uniqueDates = filteredResult.reduce((unique, data) => {
            if (!unique.some(item => item.getDate() === data.dateObj.getDate() && item.getMonth() === data.dateObj.getMonth() )) {
                unique.push(data.dateObj);
            }
            return unique;
        }, []);
        let weekDate = new Date(this.viewDay.currentViewDate.getTime())
        const today = new Date()
        for (let i = 0; i < iterations; i++) {
            if (i < uniqueDates.length) {
                const filteredObj = filteredResult.filter(filtered => filtered.dateObj.getDate() === uniqueDates[i].getDate())
                const unitAmountList = filteredObj.map(data => data.data.unit_amount)
                const sumUnitAmount = unitAmountList.reduce((acc, val) => acc + val, 0)
                let value = (filteredObj.length === 1)? filteredObj[0].data.id : null
                let css = (uniqueDates[i].getDate() === today.getDate() && uniqueDates[i].getMonth() === today.getMonth() && uniqueDates[i].getYear() === today.getYear()) ? '#F5F6E6;':''
                result.push({
                        timesheet_id: value,
                        unFormattedUnitAmount: sumUnitAmount,
                        unit_amount: this.formatTime(sumUnitAmount),
                        date: uniqueDates[i],
                        css:css,
                });
            }
            else {
                if(selected === 'Week'){
            // Handle the case when filteredResult does not have enough elements for all iterations
            let loopDate = this.dateCheck(uniqueDates,new Date(weekDate))
            let loopInnerDate = new Date(loopDate)
            let css = (loopInnerDate.getDate() === today.getDate() && loopInnerDate.getMonth() === today.getMonth() && loopInnerDate.getYear() === today.getYear()) ? '#F5F6E6;':''
                result.push({
                    timesheet_id: 0,
                    unFormattedUnitAmount: 0,
                    unit_amount: this.isDay?'0.00':'00:00',
                    date : loopInnerDate,
                    css: css
                });
                weekDate = loopDate.setDate(loopDate.getDate() +1)
            }
            else{
                let loopDate = this.dateCheck(uniqueDates,new Date(startDateNew))
                let innerDate = new Date(loopDate)
                let css = (innerDate.getDate() === today.getDate() && innerDate.getMonth() === today.getMonth() && innerDate.getYear() === today.getYear()) ? '#F5F6E6;':''
                result.push({
                    timesheet_id: 0,
                    unFormattedUnitAmount: 0,
                    unit_amount: this.isDay?'0.00':'00:00',
                    date : innerDate,
                    css: css
                });
                startDateNew = loopDate.setDate(loopDate.getDate() +1)
            }
            }
        }
        return result.sort((first, second) => {
            const dateA = first.date;
            const dateB = second.date;
        // Compare years
            const yearDiff = dateA.getFullYear() - dateB.getFullYear();
            if (yearDiff !== 0) {
                return yearDiff;
            }
        // If years are the same, compare months
            const monthDiff = dateA.getMonth() - dateB.getMonth();
                if (monthDiff !== 0) {
                return monthDiff;
            }
        // If months are the same, compare dates
            return dateA.getDate() - dateB.getDate();
        });
    }
    /**
     * Calculates the sum of unformatted unit amounts from an array of totalData objects.
     * @param {Array} totalData - An array of objects containing unformatted unit amounts.
     * @returns {number} - The sum of unformatted unit amounts.
     */
    sumHours(totalData) {
    // Function to get sum of hours
        return totalData.map(data => data.unFormattedUnitAmount).reduce((acc, val) => acc + val, 0);
    }
    /**
     * Checks and adds remaining dates to the timesheet with a unit amount of 0 to ensure all dates are included.
     * @param {Date[]} uniqueDates - An array of unique dates already present in the timesheet.
     * @param {Date} loopDate - The date to be checked and potentially added to the timesheet.
     * @returns {Date} - The adjusted date, ensuring it is not already present in the uniqueDates array.
     */
    dateCheck(uniqueDates, loopDate) {
        if (uniqueDates.some(date => date.getDate() === loopDate.getDate())) {
            loopDate.setDate(loopDate.getDate() + 1);
            return this.dateCheck(uniqueDates, new Date(loopDate));
        } else {
            return loopDate;
        }
    }
    /**
     * Generates serial numbers for items in a timesheet based on a numbering system using letters of the alphabet.
     * @param {number} number - The numerical value for which a serial number is to be generated.
     * @returns {string} - The generated serial number.
     */
    serialNumber(number) {
        const letters = "abcdefghijklmnopqrstuvwxyz";
        let result = "";
        while (number >= 0) {
            const remainder = number % 26;
            result = letters[remainder] + result;
            number = Math.floor(number / 26) - 1;
        }
        return result;
    }
    /**
     * Filters timesheet records based on the selected view (Day, Week, or Month) and the corresponding date domain.
     * @param {Array} result - The array of timesheet records to be filtered.
     * @returns {Array} - The filtered array of timesheet records according to the selected view and date domain.
     */
    filterData(result) {
        let filteredResult;
        const selected = this.element.el.querySelector('#view-selector').value;
        const date = this.viewDay.currentViewDate;
        const currentYear = date.getFullYear();
        const currentMonth = date.getMonth();
        if (selected === 'Day') {
            filteredResult = result.filter(record =>
                (record.dateObj.getDate() === date.getDate()) && (record.dateObj.getMonth() === date.getMonth()) &&
                (record.dateObj.getYear() === date.getYear())
            );
        } else if (selected === 'Week') {
            let weekDate = new Date(date);
            weekDate.setDate(weekDate.getDate() + 7);
            const dateObjWeek = this.table.tableHead.map(data => data.dateObj).map((date) => ({
                year: date.getFullYear(),
                month: date.getMonth(),
                date: date.getDate(),
            }));
            filteredResult = result.filter(record => {
                const dataDate = record.dateObj;
                const dataYear = dataDate.getFullYear();
                const dataMonth = dataDate.getMonth();
                const dataDay = dataDate.getDate();
                return dateObjWeek.some(
                    (targetDate) =>
                        targetDate.year === dataYear && targetDate.month === dataMonth && targetDate.date === dataDay
                );
            });
        } else {
            let monthDateStart = new Date(currentYear, currentMonth, 1);
            let monthDateEnd = new Date(currentYear, currentMonth + 1, 0);
            filteredResult = result.filter(record =>
                (record.dateObj.getDate() >= monthDateStart.getDate() && record.dateObj.getDate() <= monthDateEnd.getDate()) &&
                (record.dateObj.getMonth() === monthDateStart.getMonth()) && (record.dateObj.getYear() === monthDateStart.getYear())
            );
        }
        return filteredResult;
    }
    /**
     * Click function to redirect to the corresponding timesheet tree view based on the selected data.
     * @param {Event} ev - The event object triggered by the click action.
     */
    clickSearchIcon(ev) {
        const selectedData = ev.target.dataset;
        this.env.services['action'].doAction({
            type: 'ir.actions.act_window',
            name: _t(selectedData.name),
            res_model: 'account.analytic.line',
            views: [[false, 'tree']],
            domain: [
                ['task_id', '=', parseInt(selectedData.taskId)],
                ['date', '=', this.changeDateObject(selectedData.date)],
                ['employee_id', '=', parseInt(selectedData.employee)]
            ],
            context: {
                'tree_view_ref': this.myTimeSheet ? 'hr_timesheet.hr_timesheet_line_tree' : 'hr_timesheet.timesheet_view_tree_user'
            }
        });
    }
    /**
     * Function to make the unit amount span editable by setting the 'contentEditable' attribute to true.
     * @param {Event} event - The event object triggered by the click action.
     */
    clickInput(event) {
        if (event.target.id === "input_fiel" && !this.isDay){
            event.target.setAttribute('contentEditable', true);
            event.target.focus();
            event.target.setAttribute('data-time', "");
            }
    }
    //Function to change the unit_amount of the timesheet on editing
    async spanFocusOut(event, amount){
        var self= this;
        const selected = this.element.el.querySelector('#view-selector').value
        const taskData = event.target.parentElement.parentElement.parentElement.parentElement.querySelector('.task-data-id')
        const projectData = event.target.parentElement.parentElement.parentElement.parentElement.querySelector('.project-span')
        var taskId = parseInt(taskData.dataset.id)
        var projectId = parseInt(projectData.dataset.id)
        var dateString = (selected === 'Day')?event.target.offsetParent.parentElement.dataset.date : event.target.offsetParent.dataset.date
        var employeeId = parseInt (event.target.offsetParent.dataset.employee)
        const userTimezoneDate = new Date(dateString).toLocaleString(session.uid.tz);
        if(!this.isDay){
            var value=event.target.innerText.replace(/:/g ,'');
            if ($.isNumeric(value)){
                event.target.classList.remove('text-opacity-25');
                event.target.classList.remove('data-time-italic');
                let hours, minutes;
                if (event.target.innerText.includes(':') && event.target.innerText.includes('.')) {
                    await this.orm.call('timesheet.grid', 'hours_value_backend', [projectId,taskId,employeeId,userTimezoneDate]).then(function(result){
                    event.target.innerText=self.formatTime(result)
                    var timeValue = self.formatTime(result);
                    const [hoursString, minutesString] = timeValue.split(":");
                    // Parse the hours and minutes into integer values
                    hours = parseInt(hoursString, 10);
                    minutes = parseInt(minutesString, 10);
                    event.target.setAttribute('data-time', timeValue);
                    });
                }
                else if (event.target.innerText.includes(':')) {
                    const [originalHours, originalMinutes] = event.target.innerText.split(':');
                    hours = Number(originalHours);
                    minutes = Number(originalMinutes);
                }
                else {
                    hours = Math.floor(event.target.innerText.replace(/:/g ,'.'));
                    minutes = Math.round((event.target.innerText.replace(/:/g ,'.') % 1) * 60);
                }
                const formattedHours = hours.toString().padStart(2, '0');
                const formattedMinutes = minutes.toString().padStart(2, '0');
                const convertedValue = `${formattedHours}:${formattedMinutes}`;
                event.target.innerText = convertedValue;
                const floatValue = this.convertToFloat(convertedValue);
                // Convert the date object to the user's timezone
                const time = new Date(dateString);
                this.block();
                await this.orm.call('timesheet.grid', 'change_hours_backend', [projectId,taskId,floatValue,userTimezoneDate,employeeId]).then((result)=>{

                    this.env.searchModel._notify().then(()=>{
                        setTimeout(this.unblock,1000);
                        event.target.setAttribute('data-time', convertedValue);
                    })
                    event.target.innerText = " ";
                });
            }
            else{
                await this.orm.call('timesheet.grid', 'hours_value_backend', [projectId,taskId,employeeId,userTimezoneDate]).then(function(result){
                    var timeValue = self.formatTime(result);
                    event.target.setAttribute('data-time', timeValue);
                    event.target.innerText=" "
                    if (event.target.getAttribute('data-time') === '00:00' || event.target.getAttribute('data-time') === '0.00'){
                        event.target.classList.add('text-opacity-25');
                        event.target.classList.add('data-time-italic');
                    }
                });
            }
        }
    }
    /**
    * Handles the click event on a span element. Updates the value of the span text in a toggle manner,
    * specifically for day view mode. Updates the timesheet entry for the corresponding task, date,
    * and employee.
    * @param {Event} event - The click event object.
    */
    async spanClick(event){
        if (this.isDay){
            const selected = this.element.el.querySelector('#view-selector').value
            const taskData = event.target.parentElement.parentElement.parentElement.parentElement.querySelector('.task-data-id')
            const projectData = event.target.parentElement.parentElement.parentElement.parentElement.querySelector('.project-span')
            var taskId = parseInt(taskData.dataset.id)
            var projectId = parseInt(projectData.dataset.id)
            var dateString = (selected === 'Day')?event.target.offsetParent.parentElement.dataset.date : event.target.offsetParent.dataset.date
            var employeeId = parseInt (event.target.offsetParent.dataset.employee)
            const userTimezoneDate = new Date(dateString).toLocaleString(session.uid.tz);
            const values = ["0.00", "0.50", "1.00"];
            const currentIndex = values.indexOf(event.target.innerHTML);
            const nextIndex = (currentIndex + 1) % values.length;
            event.target.innerHTML = values[nextIndex];
            const currentValue = parseFloat(event.target.innerHTML);
            const valueDay = currentValue === 1 ? this.table.employeeWorkHour : currentValue === 0.5 ? this.table.employeeWorkHour / 2 : 0;
            const floatValue = valueDay;
            await this.orm.call('timesheet.grid', 'change_hours_backend', [projectId,taskId,floatValue,userTimezoneDate,employeeId])
            this.env.searchModel._notify()
        }
    }
    /**
     * Function to convert the time from HH:MM format into a floating-point number.
     * @param {string} timeValue - The time value in HH:MM format.
     * @returns {number} The converted time value as a floating-point number.
     */
    convertToFloat(timeValue) {
        if (!this.isDay) {
            const [hours, minutes] = timeValue.split(':');
            const floatHours = parseInt(hours, 10);
            const floatMinutes = parseInt(minutes, 10) / 60;
            const floatValue = floatHours + floatMinutes;
            return floatValue;
        }
    }
    /**
     * Async function to handle the start button click event for starting a timer.
     * @param {Event} ev - The click event object.
     * @returns {Promise<void>}
     */
    async onclickStart(ev) {
        const startButton = this.element.el.querySelector('.btn_start_timer');
        const stopButton = this.element.el.querySelector('.btn_stop_timer');
        const discardButton = this.element.el.querySelector('.btn_discard_timer');
        const shortKey = this.element.el.querySelector('.short_key');
        const container = this.element.el.querySelector('.cy-record_container')
        if(this.myTimeSheet){
            startButton.style.display = "none";
            stopButton.style.display = "block";
            discardButton.style.display = "block";
            shortKey.style.display = "none";
        }
        container?.classList.add("div-expanded-start-cy-grid")
        this.timerStartsRunning.timer = true;
        this.grid.record = this.props.list.model.root;
        await this.grid.record.addNewRecord(this.editable === "top");
        this.grid.runningTime = true;
        await this.startCountingTime();
    }
    /**
    * Clears the "stop" icon items and toggles the "alphabet" icon item as active.
    * Additionally, updates the class of the parent element to indicate the play state.
    */
    clearStopIconItems(){
        let activeElement = (typeof this.activeElementId !== 'string' ) ? this.activeElementId.getAttribute('id') : this.activeElementId
        if(activeElement){
            let elementId = this.element.el.querySelector(`#${activeElement}`)
            let stopSpan = elementId.querySelector('.serial-stop')
            let alphabetSpan = elementId.querySelector('.serial-alphabet')
            let activeElementId = elementId.querySelector('.active')
            if (! activeElementId.classList.contains('serial-alphabet')){
                alphabetSpan.classList.add('active')
                stopSpan.classList.remove('active')
                elementId.parentElement.classList.add('play')
            }
        }
    }
    /**
     * Function to handle the discard button click event for discarding the timer.
     * @param {Event} ev - The click event object.
     */
    onclickDiscard(ev) {
        this.clearStopIconItems()
        const startButton = ev.target.offsetParent.querySelector('.btn_start_timer');
        const stopButton = ev.target.offsetParent.querySelector('.btn_stop_timer');
        const discardButton = ev.target.offsetParent.querySelector('.btn_discard_timer');
        const shortKey = ev.target.offsetParent.querySelector('.short_key');
        const container = this.element.el.querySelector('.cy-record_container')
        container.classList.remove("div-expanded-start-cy-grid")
        startButton.style.display = "block";
        stopButton.style.display = "none";
        discardButton.style.display = "none";
        shortKey.style.display = "block";
        this.project.projectVal = { id: null, display_name: '' };
        this.task.taskVal = { id: null, display_name: '' };
        this.timerStartsRunning.timer = false;
        this.grid.runningTime = false;
        clearInterval(this.counterInterval);
        this.grid.time = 0;
        browser.localStorage.removeItem('AnalyticCache');
        browser.localStorage.removeItem('AnalyticCacheResume');
    }
    /**
     * Async function to handle the stop button click event for stopping the timer and creating an analytic entry.
     * @param {Event} ev - The click event object.
     */
    async onclickStop(ev) {
        const startButton = this.element.el.querySelector('.btn_start_timer');
        const stopButton = this.element.el.querySelector('.btn_stop_timer');
        const discardButton = this.element.el.querySelector('.btn_discard_timer');
        const shortKey = this.element.el.querySelector('.short_key');
        const container = this.element.el.querySelector('.cy-record_container')
        container.classList.remove("div-expanded-start-cy-grid")
        const inputVals = this.element.el.querySelector('.analytic-description-input').value;
        const project_id = this.element.el.querySelector('.project-input')?.dataset.projectId;
        const task_id = this.element.el.querySelector('.task-input')?.dataset.taskId;
        const projectValidation = this.element.el.querySelector('.project-input');
        if (projectValidation.dataset.projectId === 'null') {
            projectValidation.querySelector('.o-autocomplete--input').style.borderBottomColor = 'red';
            this.env.services['action'].doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Invalid fields:',
                    'message': "Project",
                    'type': 'danger',
                    'sticky': false,
                }
            });
        } else {
            this.timerStartsRunning.timer = false;
            const timesheetDuration = await this.orm.call('timesheet.grid', 'timesheet_duration', []);
            const analytic_account_id = await this.orm.call('account.analytic.line', 'create', [{
                project_id: parseInt(project_id),
                task_id: parseInt(task_id),
                name: inputVals,
                unit_amount: this.formatTimerValue(this.grid.time) < timesheetDuration.minimum_duration / 60 ?
                    timesheetDuration.minimum_duration / 60 :
                    (this.formatTimerValue(this.grid.time) / (timesheetDuration.round_up/60)) * (timesheetDuration.round_up/60)
            }]);
            this.grid.runningTime = false;
            startButton.style.display = "block";
            stopButton.style.display = "none";
            discardButton.style.display = "none";
            shortKey.style.display = "block";
            clearInterval(this.counterInterval);
            this.grid.time = 0;
            this.project.projectVal = { id: null, display_name: '' };
            this.task.taskVal = { id: null, display_name: '' };
            browser.localStorage.removeItem('AnalyticCache');
            browser.localStorage.removeItem('AnalyticCacheResume');
            this.env.searchModel._notify()
            this.clearStopIconItems()
            this.activeElementId = ''
        }
    }
    /**
     * Async function to handle adding a task and project on click serial button, setting the project and task, and starting the timer.
     * @param {HTMLElement} elementId - The HTML element representing the clicked task.
     * @returns {number} - The ID of the selected project.
     */
    async addTaskOnClick(elementId) {
        const targetRow = elementId?.parentElement.parentElement.querySelector('.table-project-task-div');
        const targetRowTask = targetRow?.querySelector('.task-span');
        const targetRowProject = targetRow?.querySelector('.project-span');
        const projectId = parseInt(targetRowProject?.dataset.id);
        this.project.projectVal = { id: projectId, display_name: targetRowProject?.innerText };
        this.task.taskVal = { id: parseInt(targetRowTask?.dataset.id), display_name: targetRowTask?.innerText };
        await this.onclickStart();
        return projectId;
    }
    /**
    * Sets the specified element as active by toggling the "alphabet" icon item as active
    * and updating the parent element's class to indicate the play state.
    * @param {HTMLElement} elementId - The HTML element to set as active.
    */
    setActive(elementId){
        let alphabetSpan = elementId.querySelector('.serial-alphabet')
        let activeElement = elementId.querySelector('.active')
        if (! activeElement.classList.contains('serial-alphabet')){
            activeElement.classList.remove('active')
            alphabetSpan.classList.add('active')
            elementId.parentElement.classList.add('play')
        }
    }
    /**
     * Async function to handle the click of a serial button, clearing the timer interval and setting the project and task.
     * @param {Event} ev - The event object triggered by the button click.
     */
    async serialButtonClick(ev) {
        clearInterval(this.counterInterval);
        const id = ev.target.getAttribute('data-parent-id');
        let elementId = id ? this.element.el.querySelector(`#${id}`) : ev.target;
        this.activeElementId = elementId || ''
        let activeElement = elementId.querySelector('.active')
        let stopSpan = elementId.querySelector('.serial-stop')
        let alphabetSpan = elementId.querySelector('.serial-alphabet')
        let universalElementId = await this.element.el.querySelectorAll('.serial-number-btn')
        universalElementId.forEach(element =>{ this.setActive(element) })
        if (activeElement.classList.contains('serial-alphabet')){
            this.grid.time = 0;
            activeElement.classList.remove('active')
            stopSpan.classList.add('active')
            elementId.parentElement.classList.remove('play')
            const addProjectTask = await this.addTaskOnClick(elementId);
            const currentProject = this.element.el.querySelector('#project-input')
        }
        else{
            stopSpan.classList.remove('active')
            alphabetSpan.classList.add('active')
            elementId.parentElement.classList.add('play')
            this.onclickStop();
            this.clearStopIconItems()
            this.env.searchModel._notify()
        }
    }
    /**
     * Function to change the format of the timer value from hours and minutes to a float value.
     * @param {number} time - The time value to be formatted.
     * @returns {number} - The formatted time value as a float.
     */
    formatTimerValue(time) {
        const hours = Math.floor(time);
        const minutes = Math.round((time - hours) * 60);
        const hoursComponent = hours; // Hours component
        const minutesComponent = minutes; // Minutes component
        const totalMinutes = hoursComponent * 60 + minutesComponent;
        const floatTimeValue = totalMinutes / 60;
        return parseFloat(floatTimeValue);
    }
    /**
     * Function to update the header of the table with the selected view (Day, Week, or Month).
     * @param {string} days - The selected view mode ('Day', 'Week', or 'Month').
     */
    updateTableHead() {
        const selected = this.table.selectedMod;
        let currentDate = new Date();
        if (selected === 'Day') {
            // Set the current view date to today and update the table header with the current date.
            this.table.tableHead = [this.getDate(this.viewDay.currentViewDate)];
        } else if (selected === 'Week' || selected === 'Month') {
            // Set the current view date to today and update the table header with the current week or month.
            this.setWeekAndDay(this.viewDay.currentViewDate);
        }
    }
    /**
     * Selector function to choose the view mode (Day, Week, or Month) and update the table accordingly.
     * @param {Event} ev - The event triggered by selecting a view mode.
     */
    async onclickSelector(ev) {
        this.table.selectedMod = ev.target.value;
        this.block()
        await this.updateTableHead(); // Update the table header based on the selected view mode.
        await this.getDataSearch();
        await this.props.onPagerUpdate()
    }
    /**
     * Function to generate and set the dates in the table header based on the selected view mode (Week or Month).
     * @param {Date} dateObj - The reference date object.
     */
    setWeekAndDay(dateObj) {
        let tableHead = [];
        const dayVal = this.element.el.querySelector('#view-selector').value;
        const currentYear = dateObj.getFullYear();
        const currentMonth = dateObj.getMonth();
        const iterTime = (dayVal === 'Month') ? new Date(currentYear, currentMonth + 1, 0).getDate() : 7;
        if (dayVal === 'Month') {
            for (let i = 1; i <= iterTime; i++) {
                const date = new Date(currentYear, currentMonth, i);
                tableHead.push(this.getDate(date));
            }
        } else {
            dateObj.setDate(dateObj.getDate() - dateObj.getDay());
            for (let i = 0; i < iterTime; i++) {
                const date = new Date(dateObj);
                date.setDate(dateObj.getDate() + i);
                tableHead.push(this.getDate(date));
            }
        }
        this.table.tableHead = tableHead;
        this.viewDay.currentViewDate = dateObj;
    }
    /**
     * Function to update the current view date based on the selected view mode (Day, Week, or Month)
     * and the direction (next or previous) of the action.
     * @param {string} event - The direction of the action ('add' for next, 'subtract' for previous).
     */
    setNewDate(event) {
        const currentDate = this.viewDay.currentViewDate;
        const dateObj = new Date(currentDate);
        const selected = this.element.el.querySelector('#view-selector').value;
        if (selected === 'Week') {
            dateObj.setDate(dateObj.getDate() + (event === 'add' ? 7 : -7));
            this.setWeekAndDay(dateObj);
        } else if (selected === 'Day') {
            dateObj.setDate(dateObj.getDate() + (event === 'add' ? 1 : -1));
            this.viewDay.currentViewDate = dateObj;
            this.table.tableHead = [this.getDate(this.viewDay.currentViewDate)];
        } else {
            dateObj.setDate(dateObj.getDate() + (event === 'add' ? 30 : -30));
            this.setWeekAndDay(dateObj);
        }
        this.getDataSearch();
    }
    /**
     * Click function for the next button to navigate to the next date range.
     * @param {Event} ev - The click event object.
     */
    onclickNext(ev) {
        if (this.element.el.querySelector('#view-selector').value != 'Day')
            this.block();
        this.setNewDate('add');
        this.props.onPagerUpdate()
    }
    /**
     * Click function for the previous button to navigate to the previous date range.
     * @param {Event} ev - The click event object.
     */
    async onclickBack(ev) {
        if (this.element.el.querySelector('#view-selector').value != 'Day')
            this.block()
        this.setNewDate('subtract');
        this.props.onPagerUpdate()
    }
    /**
     * Function to convert a date object into a formatted date string.
     * @param {Date} date - The date object to be formatted.
     * @returns {Object} An object containing formatted date information.
     */
    getDate(date) {
        const day = date.toLocaleString("en-US", { weekday: "short" });
        const monthAndDate = date.toLocaleString("en-US", { month: "short", day: "2-digit" });
        const formattedDate = date.toLocaleString("en-US", { weekday: "short", month: "short", day: "2-digit" });
        const today = new Date();
        const css = (date.getDate() === today.getDate() && date.getMonth() === today.getMonth() && date.getYear() === today.getYear()) ? 'current-date' : '';
        return { 'dateObj': date, 'day': day + ', '+ monthAndDate, 'monthAndDate': monthAndDate, 'css': css, 'formattedDate': formattedDate };
    }
    /**
     * Function to add a new timesheet line.
     * @param {Event} ev - The click event object.
     */
    async addLine(ev) {
        const employeeId = parseInt(ev.target.parentElement.dataset.id);
        const selected = this.element.el.querySelector('#view-selector').value;
        const date = (selected === 'Day') ? this.viewDay.currentViewDate : new Date();
        await this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('Add a line'),
            res_model: 'account.analytic.line',
            views: [[false, 'form']],
            view_mode: 'form',
            target: 'new',
            context: {
                'form_view_ref': this.myTimeSheet ? 'hr_timesheet.hr_timesheet_line_form' : 'hr_timesheet.timesheet_view_form_user',
                'default_date': date,
                'default_employee_id': employeeId,
            },
        }, {
            onClose: (ev) => {
                this.env.searchModel._notify();
            },
        });
    }
    /**
     * Click function to set the current date to today's date.
     */
    setDateToday() {
        const selected = this.element.el.querySelector('#view-selector').value;
        const dateObj = new Date();
        if (selected === 'Day') {
            this.viewDay.currentViewDate = dateObj;
        } else {
            this.block();
            this.viewDay.currentViewDate = dateObj;
        }
        this.updateTableHead(selected);
        this.getDataSearch();
        this.props.onPagerUpdate()
    }
    /**
     * Click function to redirect to the corresponding project.
     * @param {Event} ev - The click event object.
     */
    async gotoProject(ev) {
        const dataId = ev.target.dataset.id;
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'project.project',
            views: [[false, 'form']],
            res_id: parseInt(dataId),
        });
    }
    /**
     * Click function to redirect to the corresponding task.
     * @param {Event} ev - The click event object.
     */
    gotoTask(ev) {
        const dataId = ev.target.dataset.id;
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'project.task',
            views: [[false, 'form']],
            res_id: parseInt(dataId),
        });
    }
    /**
     * Function to get a list of count of days in month and week.
     * @returns {Array} - An array containing the count of days.
     */
    weekMonthCount() {
        const selected = this.element.el.querySelector('#view-selector').value;
        const dateObj = new Date(this.viewDay.currentViewDate);
        const currentYear = dateObj.getFullYear();
        const currentMonth = dateObj.getMonth();
        const startDate = new Date(currentYear, currentMonth, 1);
        const endDate = new Date(currentYear, currentMonth + 1, 0);
        const daysInMonth = endDate.getDate();
        const iterations = selected === 'Week' ? 7 : daysInMonth;
        const dayList = Array.from({ length: iterations }, (_, index) => index + 1);
        return dayList;
    }
    iterations(val){
       return Array.from({ length: val }, (_, index) => index);
    }
    /**
     * Change the date format of a given date object.
     * @param {Date|String} object - The date object or string to be formatted.
     * @returns {String} - The formatted date string in 'YYYY-MM-DD' format.
     */
    changeDateObject(object) {
        const dateObject = new Date(object);
        // Get the individual components
        const year = dateObject.getFullYear();
        const month = dateObject.getMonth() + 1; // (Note: Months are zero-based, so we add 1)
        const day = dateObject.getDate();
        // Create the date string in the desired format
        const dateString = `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
        return dateString;
    }
    /**
     * Get the domain for filtering based on project.
     * @returns {Array} - The domain array for project filtering.
     */
    getDomainProject() {
        const taskVal = this.task.taskVal;
        return taskVal.id ? [['task_ids', 'in', [taskVal.id]]] : [];
    }
    /**
     * Get the domain for filtering based on task.
     * @returns {Array} - The domain array for task filtering.
     */
    getDomainTask() {
        const projectVal = this.project.projectVal;
        return projectVal.id > 0 ? [['project_id', '=', projectVal.id]] : [];
    }
    /**
     * Update the project value based on user selection.
     * @param {Array} ev - The array containing the updated project value.
     */
    async onUpdateProject(ev) {
        if(ev){
            const nameGet = await this.orm.read('project.project',[ev[0].id])
            this.project.projectVal = {id : nameGet[0].id, display_name : nameGet[0].display_name }
        }
        else{
            this.project.projectVal = { }
        }
        return ;
    }
    /**
     * Update the task value based on user selection.
     * @param {Array} ev - The array containing the updated task value.
     */
    async onUpdateTask(ev) {
        if(ev){
            const nameGet = await this.orm.read('project.task',[ev[0]?.id])
            this.task.taskVal = {id : nameGet[0].id, display_name : nameGet[0].display_name }
        }
        else{
            this.task.taskVal = { }
        }
        return ;
    }
}
GridRenderer.template = "grid_view.GridRenderer";
GridRenderer.GridRowRenderer = "grid_view.GridRowRenderer";
GridRenderer.dayRowRender = "grid_view.dayRowRender";
GridRenderer.addALine = "grid_view.addALine";
GridRenderer.addALineWeekMonth = "grid_view.addALineWeekMonth";
GridRenderer.weekMonthRowRenderer = "grid_view.weekMonthRowRenderer";
GridRenderer.components = {
    View,
    Field,
    Record,
    ViewScaleSelector,
    Many2XAutocomplete,
    FloatTimeField,
    GridFloatTimeField
};
