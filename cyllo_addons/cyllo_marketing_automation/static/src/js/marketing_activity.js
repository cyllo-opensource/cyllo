/** @odoo-module **/
import { registry } from "@web/core/registry"
import { useService,useBus } from "@web/core/utils/hooks";
import { MarketingCards } from "./marketing_cards";
import { MarketingTabs } from "./marketing_tabs";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { onWillStart,useState , useRef, useSubEnv,Component,EventBus} from "@odoo/owl";
import { useSaveContext } from "@cyllo_marketing_automation/js/useSaveContext";


class MarketingActivity extends Component{
    /*
        MarketingActivity component is created managing and displaying marketing activities.
    */
    setup(){
        this.action = useService("action");
        this.orm = useService("orm");
        this.context = this.props.action.context;
        this.dialogService = useService('dialog');
        this.savedContext = useSaveContext()
        this.testDiv = useRef('testDiv')
        this.testInput = useRef('testInput')
        this.model = useState({
            modelTarget: {},
            value: false,
            activeTabID:false
        })
        // Set up a sub-environment with necessary services and methods
        useSubEnv({
            action: this.action,
            orm: this.orm,
            context: this.context,
            bus: new EventBus(),
            allActivities: this.allActivities.bind(this)
        })
        this.state = useState({
            activities: [] ,
            recordName:'',
            total_count:0,
            running:0,
            completed:0,
            edit: false
        })
        this.savedContext.saveManually(this.context.state, "state")
        if(!this.context.state){
            this.state.edit = this.savedContext.state === 'running' ? false : true
        } else {
            this.state.edit = (this.context.state === 'running' ? false : true)
        }

        // Subscribe to bus events
        useBus(this.env.bus, 'REFRESH-DATA', (event) => this.handleRefresh(event))
        useBus(this.env.bus, 'ADD-DIALOGUE',  this.addDialogue.bind(this))
        /**
            * Lifecycle hook that runs before the component is initialized.
         */
        onWillStart(async() => {
            await this.getActivities()
            let recordName = await this.orm.searchRead("marketing.campaign",[["id","=",this.context.active_id]],["name","model_name","model_id"]);
            this.state.recordName = recordName[0]
            let participantData = await this.orm.searchRead("marketing.participant",[['campaign_id','=',this.context.active_id],['is_test_participant','=',false]],[])
            this.state.total_count = participantData.length
            this.state.running = participantData.filter(item => item.state === 'running').length
            this.state.completed = participantData.filter(item => item.state === 'completed').length
        })
    }
    /**
        * Triggers the display of a dialog with the specified data.
        * @param {Object} data - The data containing the class and props for the dialog.
    */
    triggerDialog(data){
        this.dialogService.add(data.class, data.props)
    }
    /**
        * Handles the event triggered by a child component to add a dialog.
        * @param {Object} event - The event object containing details about the dialog.
    */
    addDialogue(event){
        this.triggerDialog(event.detail)
    }
    /**
        * Retrieves all activities from the component state.
        * @returns {Object} - The state containing information about all activities.
    */
    allActivities() {
        return this.state
    }
    /**
        * Handles the refresh event by calling the method to retrieve activities.
        * @param {Event} event - The refresh event.
    */
    handleRefresh(event){
        this.getActivities()
        this.model.activeTabID = event.detail.activity
    }
    /**
        * Gets the main activities from the state.
        * @returns {Array} - An array of main activities.
    */
    get mainActivities() {
        return this.state.activities.filter(item => !item.parent_activity_id )
    }
    /**
        * Fetches and updates the list of marketing activities from the server.
        * @returns {Promise} - A promise that resolves with the updated list of marketing activities.
    */
    async getActivities(){
        this.state.activities = await this.orm.searchRead('marketing.activity',[['campaign_id','=',this.context.active_id]],[])
    }
    /**
        * Retrieves the main activities and all activities from the state.
        * @returns {Object} - An object containing the main activities and all activities.
        * @property {Array} activities - The main activities.
        * @property {Array} allActivities - All activities.
    */
    get activities(){
        return {
            activities: this.mainActivities,
            allActivities: this.state.activities,
            activeTabID: this.model.activeTabID ? this.model.activeTabID : this.mainActivities[this.mainActivities.length -1].id
        }
    }
    /**
        * Handles the click event on the parent activity. Initiates an action to open a new window for creating a new marketing activity.
        * @async
        * @method onclickParentActivity
        * @returns {Promise<void>} - A Promise that resolves when the action is completed.
    */
    async onclickParentActivity(){
        if (this.state.edit){
            await this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'marketing.activity',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    'default_campaign_id': this.context.active_id,
                },
            },{
                onClose: (ev) => {
                    this.getActivities()
                }
            });
        }
    }
    /**
        * Handles the click event to launch the test. Shows the test division if it is hidden.
        * @method onclickLaunchTest
        * @param {Event} ev - The click event.
    */
    onclickLaunchTest(ev){
        if(this.testDiv.el.style.display === 'none'){
            this.testDiv.el.style.display = 'block'
        }
    }
    /**
        * Handles the click event to cancel the test. Hides the test division.
        * @method onclickCancelTest
    */
    onclickCancelTest(){
        this.testDiv.el.classList.remove('show');
    }
    /**
        * Gets the current date and time based on the provided date.
        * @async
        * @method getCurrentDateTime
        * @param {Date} date - The date object.
        * @returns {Promise<string>} A formatted string representing the current date and time.
    */
    async getCurrentDateTime(date) {
        var today = await new Date(date);
        var year = today.getFullYear();
        var month = ('0' + (today.getMonth() + 1)).slice(-2);
        var day = ('0' + today.getDate()).slice(-2);
        var hours = ('0' + today.getHours()).slice(-2);
        var minutes = ('0' + today.getMinutes()).slice(-2);
        var seconds = ('0' + today.getSeconds()).slice(-2);
        var formattedDateTime = year + '-' + month + '-' + day + ' ' + hours + ':' + minutes + ':' + seconds;
        return formattedDateTime;
    }
    /**
        * Handles the click event of the launch button.
        * Validates the input fields and creates a new test participant with the selected record.
        * Displays a notification in case of invalid fields.
        * @async
        * @method onclickLaunchButton
    */
    async onclickLaunchButton(){
        let dataSet = this.testInput.el.dataset
        if(dataSet.id == 'null'){
            this.testInput.el.querySelector('.o-autocomplete--input').style.borderBottomColor = 'red';
            this.action.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Invalid fields:',
                    'message': "Record",
                    'type': 'danger',
                    'sticky': false,
                }
            });
        }
        else{
            for (let pData of this.state.activities){
                var currentDate = pData.test_date_started;
            }
            let dataRecords = {
                campaign_id : this.context.active_id,
                record:dataSet.model+','+dataSet.id,
                record_id:parseInt(dataSet.id),
                is_test_participant:true,
                test_date_started: currentDate,
                is_inactive: false,
                record_count:this.state.activities.length
            }

            const participant = await this.orm.call('marketing.participant', 'create_test_participant', [dataRecords]);
            await this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'marketing.participant',
                views: [[false, 'form']],
                res_id:parseInt(participant),
            });
        }
    }
    /**
        * Gets the domain target based on the provided event.
        * If the event is truthy, an empty domain is returned.
        * @param {Object} ev - The event object.
        * @returns {Array} - The domain target.
    */
    getDomainTarget(ev){
        if (ev){
            return []
        }
    }
    /**
        * Handles the update of the target based on the provided event.
        * If the event is truthy, the target is updated with the event details.
        * If the event is falsy, the target is reset to an empty object.
        * @param {Object} ev - The event object.
    */
    async onUpdateTarget(ev){
        if(ev){
            let getRecord = await this.orm.read(this.state.recordName.model_name,[ev[0].id])
            this.model.modelTarget = {id : getRecord[0].id, display_name : getRecord[0].display_name }
        }
        else{
            this.model.modelTarget = { }
        }
        return ;
    }
    /**
        * Redirects the user to the marketing campaign form view.
    */
    goToCampaign(){
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'marketing.campaign',
            views: [[false, 'form']],
            res_id:this.context.active_id
        });
    }
    updateCountValue(count){
        return count.toString().padStart(2, '0');
    }
}

MarketingActivity.template = "MarketingActivity"
MarketingActivity.components = {
    MarketingCards,
    MarketingTabs,
    Many2XAutocomplete
}
registry.category("actions").add('marketing_activity_tags', MarketingActivity);
