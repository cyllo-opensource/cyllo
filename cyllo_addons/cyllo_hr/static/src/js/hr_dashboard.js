
/** @odoo-module **/
import { registry } from '@web/core/registry';
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

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
			recruitment_stages_labels: [],
			recruitment_stages_counts: [],
			contract_type_labels: [],
			contract_type_counts: [],
			contract_status_labels: [],
			contract_status_counts: [],
			employeeStatusChartType: 'bar',
			attendanceTrendChartType: 'line',
			recruitmentChartType: 'doughnut',
			contractStatusChartType: 'pie',
			contractTypeChartType: 'bar',
			date_filter: 'year',
		});

		this.charts = {};

		onWillStart(async () => {
			await this.loadDashboardData();
		});

		onMounted(() => {
			this.renderCharts();
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

	async onFilterChange(filter) {
		this.state.date_filter = filter;
		await this.loadDashboardData();
		this.renderCharts();
	}

	renderCharts() {
		this.renderEmployeeStatusChart();
		this.renderAttendanceTrendChart();
		this.renderRecruitmentChart();
		this.renderContractTypeChart();
		this.renderContractStatusChart();
	}

	renderEmployeeStatusChart() {
		const ctx = document.getElementById("employeeStatusChart");
		if (!ctx) return;

		if (this.charts.employeeStatus) {
			this.charts.employeeStatus.destroy();
		}

		const type = this.state.employeeStatusChartType;
		const config = {
			type: type,
			data: {
				labels: this.state.employee_status_labels,
				datasets: [{
					label: 'Employee Role',
					data: this.state.employee_status_counts,
					backgroundColor: [
						'#6366f1', '#10b981', '#f43f5e', '#f59e0b', '#8e44ad', '#0ea5e9'
					],
					borderRadius: type === 'bar' ? 12 : 0,
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { display: ['pie', 'doughnut'].includes(type) },
					tooltip: { mode: 'index', intersect: false }
				},
			}
		};

		if (type === 'bar') {
			config.options.scales = {
				y: { beginAtZero: true, grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#94a3b8' } },
				x: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#94a3b8' } }
			};
		}

		this.charts.employeeStatus = new Chart(ctx, config);
	}

	changeEmployeeStatusChartType(type) {
		this.state.employeeStatusChartType = type;
		this.renderEmployeeStatusChart();
	}



	renderAttendanceTrendChart() {
		const ctx = document.getElementById("attendanceTrendChart");
		if (!ctx) return;

		if (this.charts.attendanceTrend) {
			this.charts.attendanceTrend.destroy();
		}

		const type = this.state.attendanceTrendChartType;
		this.charts.attendanceTrend = new Chart(ctx, {
			type: type,
			data: {
				labels: this.state.attendance_trend_labels,
				datasets: [{
					label: 'Attendance Rate (%)',
					data: this.state.attendance_trend_data,
					borderColor: '#6366f1',
					backgroundColor: type === 'line' ? 'rgba(99, 102, 241, 0.1)' : '#6366f1',
					fill: type === 'line',
					tension: type === 'line' ? 0.45 : 0,
					pointRadius: type === 'line' ? 6 : 0,
					pointHoverRadius: type === 'line' ? 8 : 0,
					pointBackgroundColor: '#6366f1',
					pointBorderColor: '#fff',
					pointBorderWidth: 2,
					borderRadius: type === 'bar' ? 6 : 0,
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { display: false },
					tooltip: { mode: 'index', intersect: false }
				},
				scales: {
					y: { min: 0, max: 100, grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#94a3b8' } },
					x: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#94a3b8' } }
				}
			}
		});
	}

	changeAttendanceTrendChartType(type) {
		this.state.attendanceTrendChartType = type;
		this.renderAttendanceTrendChart();
	}

	renderRecruitmentChart() {
		const ctx = document.getElementById("recruitmentChart");
		if (!ctx) return;

		if (this.charts.recruitment) {
			this.charts.recruitment.destroy();
		}

		const type = this.state.recruitmentChartType;
		const config = {
			type: type,
			data: {
				labels: this.state.recruitment_stages_labels,
				datasets: [{
					label: 'Applications',
					data: this.state.recruitment_stages_counts,
					backgroundColor: [
						'#818cf8', '#34d399', '#f472b6', '#fbbf24', '#60a5fa', '#a78bfa', '#f87171'
					],
					borderWidth: 0,
					borderRadius: type === 'bar' ? 8 : 0,
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: {
						display: ['pie', 'doughnut'].includes(type),
						position: 'right',
						labels: { color: '#94a3b8', font: { size: 11 } }
					},
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
					grid: { color: 'rgba(255, 255, 255, 0.1)', drawBorder: false },
					ticks: { color: '#94a3b8', font: { size: 10 } }
				},
				x: {
					grid: { color: 'rgba(255, 255, 255, 0.1)' },
					ticks: { color: '#94a3b8', font: { size: 10 } }
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
		const ctx = document.getElementById("contractTypeChart");
		if (!ctx) return;

		if (this.charts.contractType) {
			this.charts.contractType.destroy();
		}

		const type = this.state.contractTypeChartType;
		const config = {
			type: type,
			data: {
				labels: this.state.contract_type_labels,
				datasets: [{
					label: 'Contract Type',
					data: this.state.contract_type_counts,
					backgroundColor: [
						'#6366f1', '#10b981', '#f59e0b', '#f43f5e', '#8b5cf6', '#ec4899', '#0ea5e9'
					],
					borderWidth: 0,
					borderRadius: type === 'bar' ? 8 : 0,
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: {
						display: ['pie', 'doughnut'].includes(type),
						position: 'right',
						labels: { color: '#94a3b8', font: { size: 11 } }
					},
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
				y: { beginAtZero: true, grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#94a3b8' } },
				x: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#94a3b8' } }
			};
			config.data.datasets[0].backgroundColor = 'rgba(99, 102, 241, 0.8)';
			config.data.datasets[0].borderColor = '#6366f1';
			config.data.datasets[0].borderWidth = 1;
			config.data.datasets[0].barThickness = 40;
		}

		this.charts.contractType = new Chart(ctx, config);
	}

	changeContractTypeChartType(type) {
		this.state.contractTypeChartType = type;
		this.renderContractTypeChart();
	}

	renderContractStatusChart() {
		const ctx = document.getElementById("contractStatusChart");
		if (!ctx) return;

		if (this.charts.contractStatus) {
			this.charts.contractStatus.destroy();
		}

		const type = this.state.contractStatusChartType;
		const config = {
			type: type,
			data: {
				labels: this.state.contract_status_labels,
				datasets: [{
					label: 'Contract Status',
					data: this.state.contract_status_counts,
					backgroundColor: [
						'#6366f1', '#10b981', '#f59e0b', '#f43f5e', '#8b5cf6', '#ec4899'
					],
					borderWidth: 0,
					borderRadius: type === 'bar' ? 8 : 0,
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: {
						display: ['pie', 'doughnut'].includes(type),
						position: 'right',
						labels: { color: '#94a3b8', font: { size: 11 } }
					},
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
				y: { beginAtZero: true, grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#94a3b8' } },
				x: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#94a3b8' } }
			};
		}

		this.charts.contractStatus = new Chart(ctx, config);
	}

	changeContractStatusChartType(type) {
		this.state.contractStatusChartType = type;
		this.renderContractStatusChart();
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

	openTimeOff(record) {
		const model = record.request_type === "allocation" ? "hr.leave.allocation" : "hr.leave";
		this.action.doAction({
			type: "ir.actions.act_window",
			name: "Time Off",
			res_model: model,
			res_id: record.id,
			views: [[false, "form"]],
			view_mode: "form",
			target: "current",
		});
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
