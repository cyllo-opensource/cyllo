
/** @odoo-module **/
import { registry } from '@web/core/registry';
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// Olive shades (dark -> light) used by the bar/pie mockup design
const CY_OLIVE_SHADES = ['#48521b', '#5c6a1e', '#7e8c2f', '#9ea700', '#a9b85a', '#c9d49a', '#e2e8c2'];
const CY_GRID_LINE = 'rgba(17, 17, 17, 0.05)';

// Draws each value above its bar top (mockup style). Pass via config.plugins.
const cyHrBarValueLabels = {
	id: 'cyHrBarValueLabels',
	afterDatasetsDraw(chart) {
		if (chart.config.type !== 'bar') return;
		const { ctx } = chart;
		chart.data.datasets.forEach((dataset, i) => {
			const meta = chart.getDatasetMeta(i);
			if (!meta || !meta.visible) return;
			meta.data.forEach((bar, j) => {
				const val = dataset.data[j];
				if (val === null || val === undefined) return;
				ctx.save();
				ctx.fillStyle = '#52525b';
				ctx.font = '600 12px Roboto, sans-serif';
				ctx.textAlign = 'center';
				ctx.textBaseline = 'bottom';
				ctx.fillText(String(val), bar.x, bar.y - 6);
				ctx.restore();
			});
		});
	},
};

export class HrDashboard extends Component {
	setup() {
		this.orm = useService("orm");
		this.action = useService("action");
		this.state = useState({
			total_employees: 0,
			job_applied_count: 0,
			attendance_rate: 0,
			employee_status_labels: [],
			employee_status_counts: [],
			attendance_trend_labels: [],
			attendance_trend_data: [],
			upcoming_leaves: [],
			pending_payslips: [],
			ending_contracts: [],
			leaderboard_data: [],
			timeoff_records: [],
			showFilterMenu: false,
			total_employees_compare: 0,
			total_employees_pct: 0,
			job_applied_compare: 0,
			job_applied_pct: 0,
			attendance_rate_compare: 0,
			attendance_rate_pct: 0,
			upcoming_timeoff_compare: 0,
			upcoming_timeoff_pct: 0,
			upcoming_timeoff_count: 0,
			kpi_compare_label: 'Last period',
			recruitment_stages_labels: [],
			recruitment_stages_counts: [],
			contract_type_labels: [],
			contract_type_counts: [],
			contract_status_labels: [],
			contract_status_counts: [],
			employee_status_legend: [],
			attendance_trend_legend: [],
			recruitment_stages_legend: [],
			contract_type_legend: [],
			contract_status_legend: [],
			employeeStatusChartType: 'bar',
			attendanceTrendChartType: 'line',
			recruitmentChartType: 'doughnut',
			contractStatusChartType: 'pie',
			contractTypeChartType: 'bar',
			date_filter: 'month',
		});

		this.charts = {};

		onWillStart(async () => {
			await this.loadDashboardData();
		});

		onMounted(() => {
			this.renderCharts();
			this._onResize = () => this.fitLegends();
			window.addEventListener('resize', this._onResize);
		});

		onWillUnmount(() => {
			if (this._onResize) {
				window.removeEventListener('resize', this._onResize);
				this._onResize = null;
			}
		});
	}

	async loadDashboardData() {
		const data = await this.orm.call(
			"hr.employee",
			"get_hr_dashboard_data",
			[],
			{ date_filter: this.state.date_filter }
		);
		Object.assign(this.state, data);
	}

	toggleFilterMenu() {
		this.state.showFilterMenu = !this.state.showFilterMenu;
	}

	async onFilterChange(filter) {
		this.state.date_filter = filter;
		this.state.showFilterMenu = false;
		await this.loadDashboardData();
		this.renderCharts();
	}

	renderCharts() {
		this.renderEmployeeStatusChart();
		this.renderAttendanceTrendChart();
		this.renderRecruitmentChart();
		this.renderContractTypeChart();
		this.renderContractStatusChart();
		// Fit the one-line legends once OWL has flushed the new markup
		requestAnimationFrame(() => requestAnimationFrame(() => this.fitLegends()));
	}

	// Keep every legend on a single line: items that would overflow are hidden
	// and replaced by a "+N" chip; hovering the chip lists them (CSS popover).
	fitLegends() {
		const GAP = 20;      // column-gap of .cy-hr-inline-legend
		const CHIP_W = 48;   // estimated width of the "+N" chip incl. gap

		document.querySelectorAll('.cy-hr-inline-legend').forEach((legend) => {
			const items = Array.from(legend.querySelectorAll(':scope > .cy-hr-legend-item'));
			const chip = legend.querySelector(':scope > .cy-hr-legend-more');
			if (!chip || !items.length) return;

			// Reset previous fitting pass
			items.forEach((it) => (it.style.display = ''));
			chip.classList.remove('cy-hr-legend-more--visible');

			const avail = legend.clientWidth;
			let used = 0;
			let visible = 0;

			for (let i = 0; i < items.length; i++) {
				const needed = (i ? GAP : 0) + items[i].offsetWidth;
				const hiddenLeft = items.length - (i + 1);
				const reserve = hiddenLeft > 0 ? GAP + CHIP_W : 0;
				if (used + needed > avail - reserve) break;
				used += needed;
				visible = i + 1;
			}
			if (visible === 0 && items.length) visible = 1;

			const hiddenCount = items.length - visible;
			// The hover popover lists only the items hidden from the row
			const popItems = chip.querySelectorAll('.cy-hr-legend-popover > .cy-hr-legend-item');
			popItems.forEach((it, i) => {
				it.style.display = i < visible ? 'none' : '';
			});
			if (hiddenCount > 0) {
				for (let i = visible; i < items.length; i++) {
					items[i].style.display = 'none';
				}
				const label = chip.querySelector(':scope > .cy-hr-legend-more-label');
				if (label) label.textContent = '+' + hiddenCount;
				chip.classList.add('cy-hr-legend-more--visible');
			}
		});
	}

	renderEmployeeStatusChart() {
		// HTML legend below the header (mock style) replaces the built-in one
		this.state.employee_status_legend = this.buildLegend(this.state.employee_status_labels);

		const ctx = document.getElementById("employeeStatusChart");
		if (!ctx) return;

		if (this.charts.employeeStatus) {
			this.charts.employeeStatus.destroy();
		}

		const type = this.state.employeeStatusChartType;
		const config = {
			type: type,
			plugins: [cyHrBarValueLabels],
			data: {
				labels: this.state.employee_status_labels,
				datasets: [{
					label: 'Employee Role',
					data: this.state.employee_status_counts,
					backgroundColor: CY_OLIVE_SHADES,
					borderRadius: type === 'bar' ? 8 : 0,
					maxBarThickness: 28,
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				layout: { padding: { top: 18 } },
				plugins: {
					legend: { display: false },
					tooltip: { mode: 'index', intersect: false }
				},
			}
		};

		if (type === 'bar') {
			config.options.scales = {
				y: { beginAtZero: true, border: { display: false }, grid: { color: CY_GRID_LINE }, ticks: { color: '#a1a1aa', font: { size: 11 } } },
				x: { border: { display: false }, grid: { display: false }, ticks: { display: false } }
			};
		}

		this.charts.employeeStatus = new Chart(ctx, config);
	}

	changeEmployeeStatusChartType(type) {
		this.state.employeeStatusChartType = type;
		this.renderEmployeeStatusChart();
	}



	renderAttendanceTrendChart() {
		// Single-series HTML legend for the trend card
		this.state.attendance_trend_legend = [{ label: 'Attendance', color: '#9ea700' }];

		const ctx = document.getElementById("attendanceTrendChart");
		if (!ctx) return;

		if (this.charts.attendanceTrend) {
			this.charts.attendanceTrend.destroy();
		}

		const type = this.state.attendanceTrendChartType;
		this.charts.attendanceTrend = new Chart(ctx, {
			type: type,
			plugins: [cyHrBarValueLabels],
			data: {
				labels: this.state.attendance_trend_labels,
				datasets: [{
					label: 'Attendance',
					data: this.state.attendance_trend_data,
					borderColor: '#9ea700',
					backgroundColor: type === 'line' ? 'rgba(158, 167, 0, 0.08)' : '#9ea700',
					fill: type === 'line',
					borderWidth: type === 'line' ? 2 : 0,
					tension: type === 'line' ? 0.45 : 0,
					pointRadius: type === 'line' ? 4 : 0,
					pointHoverRadius: type === 'line' ? 6 : 0,
					pointBackgroundColor: '#9ea700',
					pointBorderColor: '#fff',
					pointBorderWidth: 2,
					borderRadius: type === 'bar' ? 8 : 0,
					maxBarThickness: 28,
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				layout: { padding: { top: 18 } },
				plugins: {
					legend: { display: false },
					tooltip: { mode: 'index', intersect: false }
				},
				scales: {
					y: { min: 0, border: { display: false }, grid: { color: CY_GRID_LINE }, ticks: { color: '#a1a1aa', font: { size: 11 } } },
					x: { border: { display: false }, grid: { display: false }, ticks: { color: '#a1a1aa', font: { size: 11 } } }
				}
			}
		});
	}

	changeAttendanceTrendChartType(type) {
		this.state.attendanceTrendChartType = type;
		this.renderAttendanceTrendChart();
	}

	renderRecruitmentChart() {
		// HTML legend below the header (mock style) replaces the built-in one
		this.state.recruitment_stages_legend = this.buildLegend(this.state.recruitment_stages_labels);

		const ctx = document.getElementById("recruitmentChart");
		if (!ctx) return;

		if (this.charts.recruitment) {
			this.charts.recruitment.destroy();
		}

		const type = this.state.recruitmentChartType;
		const config = {
			type: type,
			plugins: [cyHrBarValueLabels],
			data: {
				labels: this.state.recruitment_stages_labels,
				datasets: [{
					label: 'Applications',
					data: this.state.recruitment_stages_counts,
					backgroundColor: CY_OLIVE_SHADES,
					borderWidth: 0,
					borderRadius: type === 'bar' ? 8 : 0,
					maxBarThickness: 28,
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				layout: { padding: { top: 18 } },
				plugins: {
					legend: { display: false },
					tooltip: {
						backgroundColor: 'rgba(15, 23, 42, 0.9)',
						titleColor: '#fff',
						bodyColor: '#fff',
						padding: 12,
						cornerRadius: 8,
					}
				},
			}
		};

		if (type === 'bar') {
			config.options.scales = {
				y: {
					beginAtZero: true,
					border: { display: false },
					grid: { color: CY_GRID_LINE },
					ticks: { color: '#a1a1aa', font: { size: 10 } }
				},
				x: {
					border: { display: false },
					grid: { display: false },
					ticks: { color: '#a1a1aa', font: { size: 10 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 4 }
				}
			};
		}


		this.charts.recruitment = new Chart(ctx, config);
	}

	changeRecruitmentChartType(type) {
		this.state.recruitmentChartType = type;
		this.renderRecruitmentChart();
	}

	renderContractTypeChart() {
		// HTML legend below the header (mock style) replaces the built-in one
		this.state.contract_type_legend = this.buildLegend(this.state.contract_type_labels);

		const ctx = document.getElementById("contractTypeChart");
		if (!ctx) return;

		if (this.charts.contractType) {
			this.charts.contractType.destroy();
		}

		const type = this.state.contractTypeChartType;
		const config = {
			type: type,
			plugins: [cyHrBarValueLabels],
			data: {
				labels: this.state.contract_type_labels,
				datasets: [{
					label: 'Contract Type',
					data: this.state.contract_type_counts,
					backgroundColor: CY_OLIVE_SHADES,
					borderWidth: 0,
					borderRadius: type === 'bar' ? 8 : 0,
					maxBarThickness: 28,
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				layout: { padding: { top: 18 } },
				plugins: {
					legend: { display: false },
					tooltip: {
						backgroundColor: 'rgba(15, 23, 42, 0.9)',
						padding: 12,
						cornerRadius: 8,
					}
				},
			}
		};

		if (type === 'bar') {
			config.options.scales = {
				y: { beginAtZero: true, border: { display: false }, grid: { color: CY_GRID_LINE }, ticks: { color: '#a1a1aa' } },
				x: { border: { display: false }, grid: { display: false }, ticks: { color: '#a1a1aa', maxRotation: 0, autoSkip: true, maxTicksLimit: 3 } }
			};
			config.data.datasets[0].backgroundColor = CY_OLIVE_SHADES;
			config.data.datasets[0].borderColor = '#9ea700';
			config.data.datasets[0].borderWidth = 0;
			config.data.datasets[0].barThickness = 28;
		}

		this.charts.contractType = new Chart(ctx, config);
	}

	changeContractTypeChartType(type) {
		this.state.contractTypeChartType = type;
		this.renderContractTypeChart();
	}

	renderContractStatusChart() {
		// HTML legend below the header (mock style) replaces the built-in one
		this.state.contract_status_legend = this.buildLegend(this.state.contract_status_labels);

		const ctx = document.getElementById("contractStatusChart");
		if (!ctx) return;

		if (this.charts.contractStatus) {
			this.charts.contractStatus.destroy();
		}

		const type = this.state.contractStatusChartType;
		const config = {
			type: type,
			plugins: [cyHrBarValueLabels],
			data: {
				labels: this.state.contract_status_labels,
				datasets: [{
					label: 'Contract Status',
					data: this.state.contract_status_counts,
					backgroundColor: CY_OLIVE_SHADES,
					borderWidth: 0,
					borderRadius: type === 'bar' ? 8 : 0,
					maxBarThickness: 28,
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				layout: { padding: { top: 18 } },
				plugins: {
					legend: { display: false },
					tooltip: {
						backgroundColor: 'rgba(15, 23, 42, 0.9)',
						padding: 12,
						cornerRadius: 8,
					}
				},
			}
		};

		if (type === 'bar') {
			config.options.scales = {
				y: { beginAtZero: true, border: { display: false }, grid: { color: CY_GRID_LINE }, ticks: { color: '#a1a1aa' } },
				x: { border: { display: false }, grid: { display: false }, ticks: { color: '#a1a1aa', maxRotation: 0, autoSkip: true, maxTicksLimit: 3 } }
			};
		}

		this.charts.contractStatus = new Chart(ctx, config);
	}

	changeContractStatusChartType(type) {
		this.state.contractStatusChartType = type;
		this.renderContractStatusChart();
	}

	buildLegend(labels) {
		// HTML legend items (dot color mirrors the CY_OLIVE_SHADES used per slice/bar)
		return (labels || []).map((label, i) => ({
			label: String(label),
			color: CY_OLIVE_SHADES[i % CY_OLIVE_SHADES.length],
		}));
	}

	// Actions
	openEmployees() {
		this.action.doAction({
			type: "ir.actions.act_window",
			name: "Employees",
			res_model: "hr.employee",
			view_mode: "list,form",
			views: [[false, "list"], [false, "form"]],
			target: "current",
		});
	}

	openRecruitment() {
		this.action.doAction({
			type: "ir.actions.act_window",
			name: "Applications",
			res_model: "hr.applicant",
			view_mode: "list,form",
			views: [[false, "list"], [false, "form"]],
			target: "current",
		});
	}

	openAttendance() {
		this.action.doAction({
			type: "ir.actions.act_window",
			name: "Attendance",
			res_model: "hr.attendance",
			view_mode: "list,form",
			views: [[false, "list"], [false, "form"]],
			target: "current",
		});
	}

	openPayslip(payslipId) {
		this.action.doAction({
			type: "ir.actions.act_window",
			name: "Payslip",
			res_model: "employee.payslip",
			res_id: payslipId,
			views: [[false, "form"]],
			view_mode: "form",
			target: "current",
		});
	}
	openCommission(entry) {
		this.action.doAction({
			type: "ir.actions.act_window",
			name: "Commission Reports",
			res_model: "commission.report",
			view_mode: "list,form",
			views: [[false, "list"], [false, "form"]],
			target: "current",
		});
	}

	openPayslips() {
		// "View All" on the Pending Payslips card (same records it lists)
		this.action.doAction({
			type: "ir.actions.act_window",
			name: "Payslips",
			res_model: "employee.payslip",
			view_mode: "list,form",
			views: [[false, "list"], [false, "form"]],
			domain: [["state", "=", "waiting"]],
			target: "current",
		});
	}

	openEndContracts() {
		// "View All" on the Contract Ending Trend card — contracts still open
		// whose date falls inside the active dashboard period.
		const todayStr = new Date().toISOString().slice(0, 10);
		const start = this.state.start_date || todayStr;
		const end = this.state.end_date || todayStr;
		this.action.doAction({
			type: "ir.actions.act_window",
			name: "Contracts",
			res_model: "hr.contract",
			view_mode: "list,form",
			views: [[false, "list"], [false, "form"]],
			domain: [
				["state", "=", "open"],
				["date_end", "!=", false],
				["date_end", ">=", start],
				["date_end", "<=", end],
			],
			target: "current",
		});
	}

	openTimeOffAll() {
		// "View All" on the Time Off & Allocations card — the same leave rows
		// the dashboard lists for the active period.
		const todayStr = new Date().toISOString().slice(0, 10);
		const start = this.state.start_date || todayStr;
		const end = this.state.end_date || todayStr;
		this.action.doAction({
			type: "ir.actions.act_window",
			name: "Time Off",
			res_model: "hr.leave",
			view_mode: "list,form",
			views: [[false, "list"], [false, "form"]],
			domain: [
				["request_date_from", "<=", end],
				["request_date_to", ">=", start],
			],
			target: "current",
		});
	}

	openTimeOff(record) {
		// The KPI card calls this with the click event, not a dashboard row.
		const isRow = !!(record && record.request_type && record.id);
		const model = isRow && record.request_type === "allocation" ? "hr.leave.allocation" : "hr.leave";

		// Period of the active dashboard filter (falls back to "today").
		const todayStr = new Date().toISOString().slice(0, 10);
		const start = this.state.start_date || todayStr;
		const end = this.state.end_date || todayStr;

		// Mirror the exact domains used in get_hr_dashboard_data.
		let domain;
		if (!isRow) {
			// "Upcoming Time Off" card: validated leaves starting today or later.
			domain = [["state", "=", "validate"], ["request_date_from", ">=", todayStr]];
		} else if (model === "hr.leave.allocation") {
			domain = [["date_from", ">=", start]];
		} else {
			domain = [
				["request_date_from", ">=", start],
				["request_date_to", "<=", end],
			];
		}

		if (isRow && record.employee_id) {
			domain.push(["employee_id", "=", record.employee_id]);
		}

		const action = {
			type: "ir.actions.act_window",
			name: "Time Off",
			res_model: model,
			views: [[false, "list"], [false, "form"]],
			view_mode: "list,form",
			target: "current",
			domain: domain,
		};

		// Open the clicked record's form; the list behind it stays filtered.
		if (isRow) {
			action.res_id = record.id;
		}

		this.action.doAction(action);
	}

	openContract(contractId) {
		this.action.doAction({
			type: "ir.actions.act_window",
			name: "Contract",
			res_model: "hr.contract",
			res_id: contractId,
			views: [[false, "form"]],
			view_mode: "form",
			target: "current",
		});
	}
}

HrDashboard.template = "cyllo_hr.HrDashboard"
registry.category("actions").add(
	"hr_dashboard",
	HrDashboard
);
