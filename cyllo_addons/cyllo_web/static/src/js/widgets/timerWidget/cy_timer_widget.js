/** @odoo-module **/
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// Helper function to format time in HH:MM:SS format
function formatTime(hours, mins, seconds) {
    return [
        String(hours || 0).padStart(2, '0'),
        String(mins || 0).padStart(2, '0'),
        String(seconds || 0).padStart(2, '0')
    ].join(':');
}

// Helper function to convert seconds to hours, minutes, and seconds
function secondsToHMS(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return {
        hours: String(hours).padStart(2, '0'),
        minutes: String(minutes).padStart(2, '0'),
        seconds: String(remainingSeconds).padStart(2, '0'),
    };
}

export class cyTimerWidget extends owl.Component {
    static template = 'cyTimerWidget';
    static props = { ...standardFieldProps };

    setup() {
        this.hours = 0;
        this.mins = 0;
        this.seconds = 0;
        this.id = this.props.record.resId;
        this.model = this.props.record.resModel;
        this.stoper = false;
        this.ref = useRef('root');
        this.intervalId = null;

        // Load initial time when component is mounted
        onMounted(() => {
            this.loadTime();
        });

        // Handle any cleanup when component is unmounted
        onWillUnmount(() => {
            clearInterval(this.intervalId);
            const changes = { [this.props.name]: this.props.totalTimeInFloat };
            // Handle changes here, if needed
        });
        this.orm = useService("orm");

        super.setup();
    }

    // Load initial time from record data and calculate elapsed time
    async loadTime() {
        const totalSeconds = this.props.record.data[this.props.name] * 3600;
        this.hours = Math.floor(totalSeconds / 3600);
        this.mins = Math.floor((totalSeconds % 3600) / 60);
        this.seconds = totalSeconds % 60;
        await this.orm.searchRead("timer.model.records", [
            ['model_id', '=', this.model],
            ['field_id', '=', this.props.name],
            ['record_id', '=', this.id]
        ]).then(async (timer) => {
            this.lastTIme = await timer[0]?.start_timer
            var StartTimer = timer[0]?.start_timer
            if (StartTimer) {
                const currentTimeStamp = Date.now();
                const currentDatetime = currentTimeStamp / 1000;
                const lastDatetime = parseInt(StartTimer) / 1000;
                const formattedSecond = secondsToHMS(currentDatetime - lastDatetime);
                if (timer[0]?.stopped_timer === false) {
                    this.hours += parseInt(formattedSecond.hours);
                    this.mins += parseInt(formattedSecond.minutes);
                    this.seconds = (this.seconds + parseInt(formattedSecond.seconds) + 60) % 60;
                    this.id = this.props.record.resId
                    this.updateTimeDisplay();
                    this.startTimer();
                } else {
                    this.stoper = true;
                    this.id = this.props.record.resId
                    this.updateTimeDisplay();
                }
            } else {
                this.stoper = true;
                this.id = this.props.record.resId
                this.updateTimeDisplay();
            }

        });
    }

    // Start the timer
    start() {
        this.stoper = false;
        const records = {
            model_id: this.model,
            field_id: this.props.name,
            record_id: this.id,
            start_timer: Date.now(),
            stopped_timer: false
        }
        this.orm.call(
            'timer.model.records',
            'timer_update',
            [records],
            {}
        );
        this.startTimer();
        this.id = this.props.record.resId
        this.updateTimeDisplay();
    }

    // Stop the timer
    stop() {
        clearInterval(this.intervalId);

        const changes = { [this.props.name]: this.props.totalTimeInFloat };
        this.props.record.update(changes);

        if (this.props.record._parentRecord) {
            return this.props.record._parentRecord.save();
        }
         const records = {
            model_id: this.model,
            field_id: this.props.name,
            record_id: this.id,
            start_timer: Date.now(),
            stopped_timer: true
        }
        this.orm.call(
            'timer.model.records',
            'timer_stopped',
            [records],
            {}
        );
        this.stoper = true;
        this.id = this.props.record.resId
        this.updateTimeDisplay();
        return this.props.record.save();
    }

    // Reset the timer
    reset() {
        this.stop();
        this.hours = 0;
        this.mins = 0;
        this.seconds = 0;
        this.props.totalTimeInFloat = 0;
        this.updateRecord(0);
        this.id = this.props.record.resId
        this.updateTimeDisplay();
    }

    // Update the time display
    updateTimeDisplay() {
        const el = this.ref.el;
        if (el.querySelector('#seconds-' + this.id)) {
            el.querySelector('#seconds-' + this.id).innerHTML = String(this.seconds).padStart(2, '0');
            el.querySelector('#mins-' + this.id).innerHTML = String(this.mins).padStart(2, '0') + ':';
            el.querySelector('#hours-' + this.id).innerHTML = String(this.hours).padStart(2, '0') + ':';
            el.querySelector('#start-' + this.id).style.display = this.stoper ? 'block' : 'none';
            el.querySelector('#stop-' + this.id).style.display = this.stoper ? 'none' : 'block';
        }
    }

    // Timer function that runs every second
    startTimer() {
        clearInterval(this.intervalId);
        this.intervalId = setInterval(() => {
            if (this.stoper || this.props.record._config.resModel !== this.model || this.props.record._config.resId !== this.id) {
                clearInterval(this.intervalId);
                return;
            }
            this.seconds++;
            if (this.seconds > 59) {
                this.seconds = 0;
                this.mins++;
                if (this.mins > 59) {
                    this.mins = 0;
                    this.hours++;
                }
            }
            this.id = this.props.record.resId
            this.updateTimeDisplay();
            const formattedTime = formatTime(this.hours, this.mins, this.seconds);
            const [f_hours, f_minutes, f_seconds] = formattedTime.split(":").map(Number);
            const totalTimeInSeconds = f_hours * 3600 + f_minutes * 60 + f_seconds;
            this.props.totalTimeInFloat = totalTimeInSeconds / 3600;
        }, 1000);
    }

    // Update the record with the new total time
    updateRecord(totalTimeInFloat) {
        if (totalTimeInFloat >= 0 && this.props.record._config.resId === this.id && this.props.record._config.resModel === this.model) {
            const changes = { [this.props.name]: totalTimeInFloat };
            this.props.record.update(changes);
            this.props.record.save();
        }
    }
    // Get the current record's ID and model
    get timerId() {
        this.id = this.props.record._config.resId;
        this.model = this.props.record._config.resModel;
        return {
            id: this.props.record._config.resId,
            model: this.props.record._config.resModel,
        };
    }
}

export const CYTimerWidget = {
    component: cyTimerWidget,
    supportedTypes: ["float"],
};

registry.category("fields").add("cy_timer", CYTimerWidget);
