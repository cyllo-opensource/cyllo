/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { BlockUI, unblockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";
import {
  Component,
  useState,
  onWillStart,
  onMounted,
  useEffect,
  useRef,
} from "@odoo/owl";
import { renderSalesPerformance } from "@cyllo_commission/js/sales_performance";
import {
  leaderBoard,
  getLeaderBoardData,
} from "@cyllo_commission/js/leaderboard";
import {
  summaryCardData,
  renderSummaryCards,
  formatCurrency,
  getDateRange,
  shiftMonth,
} from "@cyllo_commission/js/summary_cards";
import { renderPlanCards } from "@cyllo_commission/js/plan_cards";
import { renderTeamCommissionDistribution } from "@cyllo_commission/js/commission_distribution";
import { renderPerformanceAnalysis } from "@cyllo_commission/js/performance_analysis";
import {
  filterByPlanType,
  filterByTeam,
  filterByUser,
  filterByDatePeriod,
  applyNonManagerFilters,
} from "./filters";

const actionRegistry = registry.category("actions");

class CommissionDashboard extends Component {
  static template = "cyllo_commission.CommissionDashboard";

  setup() {
    super.setup();
    this.orm = useService("orm");
    this.actionService = useService("action");
    this.commissionDashboardRef = useRef("commissionDashboard");
    this.state = useState({
      data: {
        access: [],
        plans: [],
        commissions: [],
        salespeople: [],
        teams: [],
        sale_orders: [],
        team_members: [],
        orderlines: [],
        customers: [],
        won_opportunities: [],
        opportunities: [],
      },
      filters: {
        planType: "all",
        userIds: [],
        teamIds: [],
        userId: 0,
        teamId: 0,
        period: "this_year",
        sort: "commission",
        salesGraph: "line",
        commissionsGraph: "pie",
        selectedPlan: "",
        leaderboardCommissions: [],
      },
      filteredData: {
        access: [],
        plans: [],
        commissions: [],
        salespeople: [],
        teams: [],
        sale_orders: [],
        team_members: [],
        orderlines: [],
        customers: [],
        won_opportunities: [],
        opportunities: [],
      },
      viewIds: {
        contribution: null,
        target: null,
      },
      showFilterBackdrop: false,
    });

    onWillStart(async () => {
      await this.loadData();
    });

    onMounted(() => {
      this.initializeFilterEvents();
      this.applyFilters(getDateRange);
      this.renderAllVisualizations();
      this.defaultActiveGraphIcons(this.commissionDashboardRef.el);
      this.setDefaultSelectedOptions();
      const { id, isManager } = this.checkAccess(this.state.data.access);
      if (!isManager) {
        this.adjustNonManagerUI(id, isManager, this.state.data);
      } else {
        this.initializeExportEvents();
      }
    });
  }

  async loadData() {
    const result = await this.orm.call(
      "commission.report",
      "get_dashboard_data",
      []
    );
    this.state.data = result;
    this.state.viewIds = result.view_ids;
    this.state.filteredData = JSON.parse(JSON.stringify(result)); // Deep copy
  }

  setDefaultSelectedOptions() {
    const target = this.commissionDashboardRef.el;
    const plans = this.state.filteredData.plans;
    const selects = {
      "date-range": { value: "this_year", text: "This Year" },
      "plan-type": { value: "all", text: "All Plans" },
      "team-filter": { value: "0", text: "All Teams" },
      "user-filter": { value: "0", text: "All Sales Reps" },
      "detailed-plan-select": plans.length > 0
        ? { value: "", text: "Choose a plan.." }
        : { value: "no_plans", text: "No Plans Available" },
      sort: { value: "commission", text: "Commission Earned" },
    };

    Object.entries(selects).forEach(([id, { value, text }]) => {
      const trigger = target.querySelector(`#${id}`);
      if (trigger) {
        const valueElement = trigger.querySelector(".select-value") || trigger;
        valueElement.textContent = text;
        if (["commission", "this_year", "all"].includes(value)) {
          valueElement.classList.remove("placeholder");
        } else {
          valueElement.classList.add("placeholder");
          const dropdown = trigger
            .closest(".custom-select")
            ?.querySelector(".select-dropdown");
          if (dropdown) {
            const options = dropdown.querySelectorAll(".select-option");
            options.forEach((opt) => opt.classList.remove("selected"));

            const defaultOption = Array.from(options).find(
              (opt) => opt.dataset.value === value
            );
            if (defaultOption) {
              defaultOption.classList.add("selected");
            }
          }
        }
        if (id === "date-range") this.state.filters.period = value;
        if (id === "plan-type") this.state.filters.planType = value;
        if (id === "team-filter") {
          this.state.filters.teamIds = [value];
          this.state.filters.teamId = parseInt(value) || 0;
        }
        if (id === "user-filter") {
          this.state.filters.userIds = [value];
          this.state.filters.userId = parseInt(value) || 0;
        }
        if (id === "detailed-plan-select")
          this.state.filters.selectedPlan = value;
        if (id === "sort") this.state.filters.sort = value;
      }
    });
  }

  getCurrencyFormatting() {
    return {
      currency_symbol: this.state.data.currency_symbol,
      symbol_position: this.state.data.symbol_position,
    };
  }

  renderSelectedPlan() {
    const { currency_symbol, symbol_position } = this.getCurrencyFormatting();
    const { period, selectedPlan } = this.state.filters;
    let { commissions, plans } = [];
    if (selectedPlan) {
      commissions = this.state.filteredData.commissions.filter(
        (plan) => plan.plan_id === Number(selectedPlan)
      );
      plans = this.state.filteredData.plans.filter(
        (plan) => plan.id === Number(selectedPlan)
      );
    }
    renderPlanCards(
      this.commissionDashboardRef.el,
      plans,
      commissions,
      period,
      formatCurrency,
      currency_symbol,
      symbol_position,
      (planId) => this.viewPlan(planId)
    );
  }

  renderAllVisualizations() {
    const { currency_symbol, symbol_position } = this.getCurrencyFormatting();
    const {
      period,
      userIds,
      sort,
      salesGraph,
      commissionsGraph,
      planType,
      selectedPlan,
      leaderboardCommissions,
    } = this.state.filters;

    const {
      sale_orders,
      team_members,
      orderlines,
      commissions,
      plans,
      customers,
      won_opportunities,
      opportunities,
    } = this.state.filteredData;

    const viewId =
      planType === "contribution"
        ? this.state.viewIds.contribution
        : this.state.viewIds.target;
    const { isManager } = this.checkAccess(this.state.data.access);
    this.renderLeaderBoard(
      this.commissionDashboardRef.el,
      commissions,
      leaderboardCommissions,
      sort
    );

    renderSalesPerformance(
      this.commissionDashboardRef.el,
      this.state.data.currency,
      sale_orders,
      getDateRange,
      period,
      salesGraph,
      this.env
    );

    renderTeamCommissionDistribution(
      this.commissionDashboardRef.el,
      this.state.data.currency,
      team_members,
      orderlines,
      commissions,
      userIds.length === 1 ? parseInt(userIds[0]) : 0,
      commissionsGraph,
      planType,
      this.env,
      viewId
    );

    renderSummaryCards(
      this.commissionDashboardRef.el,
      period,
      this.state.data.commissions,
      this.state.data.sale_orders,
      commissions,
      sale_orders,
      team_members,
      plans,
      formatCurrency,
      getDateRange,
      shiftMonth,
      currency_symbol,
      symbol_position
    );
    this.renderSelectedPlan();
    if (isManager) {
      renderPerformanceAnalysis(
        this.commissionDashboardRef.el,
        period,
        this.state.data.customers,
        this.state.data.sale_orders,
        this.state.data.orderlines,
        this.state.data.won_opportunities,
        this.state.data.opportunities,
        commissions,
        sale_orders,
        orderlines,
        won_opportunities,
        opportunities,
        team_members,
        currency_symbol,
        symbol_position
      );
    }
  }

  renderLeaderBoard(target, commissions, leaderboardCommissions, sort) {
    const { isManager } = this.checkAccess(this.state.data.access);
    const { currency_symbol, symbol_position } = this.getCurrencyFormatting();
    const dataToUse = isManager ? commissions : leaderboardCommissions;
    leaderBoard(
      target,
      dataToUse,
      formatCurrency,
      currency_symbol,
      symbol_position,
      sort
    );
  }

  checkAccess(access) {
    const user = access[0];
    return {
      id: user.id,
      isManager: user._is_manager,
    };
  }

  get isUserManager() {
    return this.checkAccess(this.state.data.access).isManager;
  }

  applyFilters(getDateRange) {
    const { planType, userIds = [], teamIds = [], period } = this.state.filters;
    const { access } = this.state.data;
    const { id, isManager } = this.checkAccess(access);
    const target = this.commissionDashboardRef.el;
    this.state.filters.sort = "commission";
    this.state.filters.selectedPlan = "";

    const sortSelect = target.querySelector("#sort");
    if (sortSelect) {
      const valueElement =
        sortSelect.querySelector(".select-value") || sortSelect;
      valueElement.textContent = "Commission Earned";
      valueElement.classList.add("placeholder");
      const dropdown = sortSelect
        .closest(".custom-select")
        .querySelector(".select-dropdown");
      const options = dropdown.querySelectorAll(".select-option");
      options.forEach((opt) => opt.classList.remove("selected"));
      const defaultSortOption = Array.from(options).find(
        (opt) => opt.dataset.value === "commission"
      );
      if (defaultSortOption) defaultSortOption.classList.add("selected");
    }

    const planSelect = target.querySelector("#detailed-plan-select");
    if (planSelect) {
      const valueElement =
        planSelect.querySelector(".select-value") || planSelect;
      valueElement.textContent = "Choose a plan..";
      valueElement.classList.add("placeholder");
      const dropdown = planSelect
        .closest(".custom-select")
        .querySelector(".select-dropdown");
      const options = dropdown.querySelectorAll(".select-option");
      options.forEach((opt) => opt.classList.remove("selected"));
      const defaultPlanOption = Array.from(options).find(
        (opt) => opt.dataset.value === ""
      );
      if (defaultPlanOption) defaultPlanOption.classList.add("selected");
    }

    let filteredData = JSON.parse(JSON.stringify(this.state.data));

    if (!isManager) {
      const nonManagerData = applyNonManagerFilters(
        filteredData,
        id,
        teamIds,
        this.state.data
      );
      this.state.filters.userIds = [String(id)];
      this.state.filters.leaderboardCommissions =
        nonManagerData.leaderboardCommissions;
      filteredData = { ...filteredData, ...nonManagerData };
    }

    filteredData = filterByPlanType(filteredData, planType);
    filteredData = filterByTeam(filteredData, teamIds);
    filteredData = filterByUser(filteredData, userIds);
    filteredData = filterByDatePeriod(filteredData, period);

    if (userIds && userIds.length && Object.values(userIds)[0] === "0") {
      this.showMultiSelectPlaceholder("user-filter", "All Sales Reps", target);
    }

    if (teamIds && teamIds.length && Object.values(teamIds)[0] === "0") {
      this.showMultiSelectPlaceholder("team-filter", "All Teams", target);
    }

    this.state.filteredData = filteredData;
    this.renderAllVisualizations();
  }

  onApplyFilters() {
    const target = this.commissionDashboardRef.el;
    const filtersPopup = target.querySelector("#filters-popup");
    const filtersToggle = target.querySelector("#filters-toggle");

    filtersPopup?.classList.remove("active");
    filtersToggle?.classList.remove("active");
    this.defaultActiveGraphIcons(target);
    this.applyFilters(getDateRange);
  }

  onResetFilters() {
    const { id, isManager } = this.checkAccess(this.state.data.access);

    const { userLabel, userValue, teamLabel, teamValue, userTeams } =
      this.getDefaultUserAndTeamFilters(id, isManager, this.state.data);

    this.state.filters = {
      planType: "all",
      userIds: [userValue],
      teamIds: [teamValue],
      period: "this_year",
      sort: "commission",
      selectedPlan: "",
    };

    this.resetSelectElement("#date-range", "This Year", "this_year");
    this.resetSelectElement("#plan-type", "All Plans", "all");
    this.resetSelectElement("#sort", "Commission Earned", "commission");
    this.resetSelectElement("#detailed-plan-select", "Choose a plan..", "");
    this.resetSelectElement("#user-filter", userLabel, userValue, true);
    this.resetSelectElement("#team-filter", teamLabel, teamValue, true);
    this.defaultActiveGraphIcons(this.commissionDashboardRef.el);
    this.applyFilters(getDateRange);
  }

  getDefaultUserAndTeamFilters(id, isManager, data) {
    const userTeams = data.team_members
      .filter((member) => member.user_id === id)
      .map((member) => member.team_id);

    const isSingleTeam = userTeams.length === 1;

    const userLabel = isManager
      ? "All Sales Reps"
      : data.salespeople.find((u) => u.id === id)?.name || "";

    const teamLabel =
      isManager || !isSingleTeam
        ? "All Teams"
        : data.teams.find((t) => t.id === userTeams[0])?.name || "";

    const userValue = isManager ? "0" : String(id);
    const teamValue = isManager || !isSingleTeam ? "0" : String(userTeams[0]);

    return {
      userLabel,
      userValue,
      teamLabel,
      teamValue,
      userTeams,
      isSingleTeam,
    };
  }

  resetSelectElement(selector, label, value, isMulti = false) {
    const target = this.commissionDashboardRef.el;
    const el = target.querySelector(selector);
    if (!el) return;

    const dropdown = el
      .closest(".custom-select")
      ?.querySelector(".select-dropdown");
    const options = dropdown?.querySelectorAll(".select-option") || [];
    options.forEach((opt) => opt.classList.remove("selected"));
    if (isMulti) {
      const containerId =
        selector === "#team-filter"
          ? "#selected-teams-container"
          : "#selected-users-container";
      const container = target.querySelector(containerId);
      if (container) container.innerHTML = "";
      const defaultOption = dropdown?.querySelector(`[data-value="${value}"]`);
      if (defaultOption) {
        defaultOption.classList.add("selected");
        if (selector === "#team-filter") {
          this.state.filters.teamIds = [value];
        } else {
          this.state.filters.userIds = [value];
        }
      }
    }
    const valueElement = el.querySelector(".select-value") || el;
    valueElement.textContent = label;
    valueElement.classList.add("placeholder");
    if (!isMulti && value !== null) {
      const defaultOption = Array.from(options).find(
        (opt) => opt.dataset.value === value
      );
      if (defaultOption) defaultOption.classList.add("selected");
    }
  }

  viewPlan(planId) {
    this.actionService.doAction({
      name: "Commission Plan",
      res_model: "commission.plan",
      res_id: planId,
      views: [[false, "form"]],
      type: "ir.actions.act_window",
      view_mode: "form",
      target: "current",
    });
  }

  setActiveAmongSiblings(clickedElement, activeType = null) {
    if (!clickedElement?.parentElement) return;
    const siblings = clickedElement.parentElement.children;
    for (const btn of siblings) {
      btn.classList.remove("active");
    }
    if (activeType) {
      for (const btn of siblings) {
        if (btn.dataset.chartType === activeType) {
          btn.classList.add("active");
          break;
        }
      }
    } else {
      clickedElement.classList.add("active");
    }
  }

  defaultActiveGraphIcons(target) {
    const graphIcons = target.querySelectorAll(".default");
    graphIcons.forEach((icon) => {
      this.setActiveAmongSiblings(icon);
    });
  }

  renderChart(source, graphType, event) {
    this.setActiveAmongSiblings(event.currentTarget);
    const { period, userIds, planType } = this.state.filters;
    const { sale_orders, team_members, orderlines, commissions } =
      this.state.filteredData;
    const target = this.commissionDashboardRef.el;
    const currency = this.state.data.currency;
    const viewId =
      planType === "contribution"
        ? this.state.viewIds.contribution
        : this.state.viewIds.target;
    if (source === "sale") {
      this.state.data.salesGraph = graphType;
      renderSalesPerformance(
        target,
        currency,
        sale_orders,
        getDateRange,
        period,
        graphType,
        this.env
      );
    } else {
      this.state.data.commissionsGraph = graphType;
      renderTeamCommissionDistribution(
        target,
        currency,
        team_members,
        orderlines,
        commissions,
        userIds.length === 1 ? parseInt(userIds[0]) : 0,
        graphType,
        planType,
        this.env,
        viewId
      );
    }
  }

  handleGraphButtonClick() {
    const graphType = event.currentTarget.dataset.graph;
    const source = event.currentTarget.dataset.source;
    this.renderChart(source, graphType, event);
  }

  initializeFilterEvents() {
    const target = this.commissionDashboardRef.el;
    const filtersToggle = target.querySelector("#filters-toggle");
    const filtersPopup = target.querySelector("#filters-popup");
    const chevronIcon = target.querySelector(".chevron-icon");
    const applyButton = target.querySelector(".filter-popup-apply");
    const resetButton = target.querySelector(".filter-popup-reset");

    target.querySelectorAll(".custom-select").forEach((select) => {
      if (select.classList.contains("multiple")) {
        this.setupMultiSelect(target, select);
      } else {
        this.setupSingleSelect(select);
      }
    });

    if (filtersToggle && filtersPopup && chevronIcon) {
      filtersToggle.addEventListener("click", (e) => {
        e.stopPropagation();
        const exportDropdown = target.querySelector("#export-dropdown");
        const exportToggle = target.querySelector("#export-toggle");
        if (exportDropdown?.classList.contains("active")) {
          exportDropdown.classList.remove("active");
          exportToggle?.classList.remove("active");
        }
        filtersPopup.classList.toggle("active");
        filtersToggle.classList.toggle("active");
      });
      filtersPopup.addEventListener("click", (e) => {
        e.stopPropagation();
        this.closeAllDropdowns();
      });
    }
    target.addEventListener("click", (event) => {
      const isClickInside =
        filtersToggle?.contains(event.target) ||
        filtersPopup?.contains(event.target);
      if (!isClickInside && filtersPopup?.classList.contains("active")) {
        filtersPopup.classList.remove("active");
        filtersToggle.classList.remove("active");
      }
      this.closeAllDropdowns();
    });
    applyButton?.addEventListener("click", () => {
      this.onApplyFilters();
    });
    resetButton?.addEventListener("click", () => this.onResetFilters());
  }

  initializeExportEvents() {
    const target = this.commissionDashboardRef.el;
    const exportToggle = target.querySelector("#export-toggle");
    const exportDropdown = target.querySelector("#export-dropdown");
    const exportOptions = exportDropdown.querySelectorAll(".export-option");

    if (exportToggle && exportDropdown) {
      exportToggle.addEventListener("click", (e) => {
        e.stopPropagation();
        const filtersPopup = target.querySelector("#filters-popup");
        if (filtersPopup?.classList.contains("active")) {
          filtersPopup.classList.remove("active");
          target.querySelector("#filters-toggle").classList.remove("active");
        }
        exportDropdown.classList.toggle("active");
        exportToggle.classList.toggle("active");
      });
    }

    target.addEventListener("click", (event) => {
      const isClickInside =
        exportToggle?.contains(event.target) ||
        exportDropdown?.contains(event.target);
      if (!isClickInside && exportDropdown?.classList.contains("active")) {
        exportDropdown.classList.remove("active");
        exportToggle.classList.remove("active");
      }
    });
    exportOptions.forEach((option) => {
      option.addEventListener("click", () => {
        exportDropdown.classList.remove("active");
        exportToggle.classList.remove("active");
      });
    });
  }

  formatDateToDDMMYYYY(dateStr) {
    if (!dateStr) return "";
    const [year, month, day] = dateStr.split("-");
    return `${day}-${month}-${year}`;
  }

  async exportData(format) {
    const target = this.commissionDashboardRef.el;
    const { startDate, endDate } = getDateRange(this.state.filters.period);
    const formattedStartDate = this.formatDateToDDMMYYYY(startDate);
    const formattedEndDate = this.formatDateToDDMMYYYY(endDate);
    if (format === "pdf") {
      let sales = target.querySelector("#salesPerformanceChart");
      let commission = target.querySelector("#commissionDistribution");
      if (sales) {
        let salesCanvas = await html2canvas(sales);
        sales = salesCanvas.toDataURL("image/png");
      }
      if (commission) {
        let commissionCanvas = await html2canvas(commission);
        commission = commissionCanvas.toDataURL("image/png");
      }

      const churnData = JSON.parse(JSON.stringify(this.state.filteredData));
      const leaderboardData = getLeaderBoardData(
        this.state.filteredData.leaderboardCommissions,
        this.state.filters.sort
      );
      return this.actionService.doAction({
        type: "ir.actions.report",
        report_type: "qweb-pdf",
        report_name: "cyllo_commission.report_commission_dashboard",
        report_file: "cyllo_commission.report_commission_dashboard",
        data: {
          sales,
          commission,
          startDate: formattedStartDate,
          endDate: formattedEndDate,
          churnData,
          leaderboardData,
        },
      });
    } else {
      BlockUI;
      download({
        url: "/commission_xlsx_reports",
        data: {
          model: "commission.report",
          data: JSON.stringify({
            ...this.state.filteredData,
            summary: summaryCardData(
              this.state.filters.period,
              this.state.data.commissions,
              this.state.data.sale_orders,
              this.state.filteredData.team_members,
              this.state.filteredData.plans,
              this.state.filteredData.sale_orders,
              this.state.filteredData.commissions,
              getDateRange,
              shiftMonth
            ),
            filters: {
              date_from: formattedStartDate,
              date_to: formattedEndDate,
            },
            leaderboardData: getLeaderBoardData(
              this.state.filteredData.leaderboardCommissions,
              this.state.filters.sort
            ),
          }),
          output_format: "xlsx",
          report_name: "Commission Report",
        },
        complete: () => unblockUI,
        error: (error) => this.call("crash_manager", "rpc_error", error),
      });
    }
  }

  setupSingleSelect(select) {
    const trigger = select.querySelector(".select-trigger");
    const dropdown = select.querySelector(".select-dropdown");
    const valueElement = select.querySelector(".select-value");
    const dropdownArrow = trigger.querySelector(".select-arrow");
    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      this.toggleDropdown(select);
      dropdown.querySelectorAll(".select-option").forEach((option) => {
        option.addEventListener("click", () => {
          this.selectOption(select, option);
        });
      });
    });
    dropdownArrow.addEventListener("click", (e) => {
      e.stopPropagation();
      this.toggleDropdown(select);
      dropdown.querySelectorAll(".select-option").forEach((option) => {
        option.addEventListener("click", () => {
          this.selectOption(select, option);
        });
      });
    });
  }

  setupMultiSelect(target, select) {
    const trigger = select.querySelector(".select-trigger");
    const dropdown = select.querySelector(".select-dropdown");
    const isTeamSelect = trigger.id === "team-filter";
    const dropdownArrow = trigger.querySelector(".select-arrow");
    const allOption = dropdown.querySelector('[data-value="0"]');
    if (allOption) {
      allOption.style.display = "none";
    }
    const getSelectedValues = () =>
      isTeamSelect
        ? [...(this.state.filters.teamIds || [])]
        : [...(this.state.filters.userIds || [])];
    const setSelectedValues = (values) => {
      if (isTeamSelect) {
        this.state.filters.teamIds = values.length > 0 ? values : ["0"];
        this.state.filters.teamId =
          values.length === 1 ? parseInt(values[0]) : 0;
      } else {
        this.state.filters.userIds = values.length > 0 ? values : ["0"];
        this.state.filters.userId =
          values.length === 1 ? parseInt(values[0]) : 0;
      }
    };
    let selectedValues = getSelectedValues();
    this.updateSelectedOptionsUI(select, selectedValues, isTeamSelect);

    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      this.toggleDropdown(select);
    });
    dropdownArrow.addEventListener("click", (e) => {
      e.stopPropagation();
      this.toggleDropdown(select);
    });

    dropdown.querySelectorAll(".select-option").forEach((option) => {
      const value = option.dataset.value;
      if (value === "0") return;

      if (selectedValues.includes(value)) {
        option.classList.add("selected");
      }

      option.addEventListener("click", (e) => {
        e.stopPropagation();
        let values = getSelectedValues().filter((v) => v !== "0");

        if (option.classList.contains("selected")) {
          option.classList.remove("selected");
          values = values.filter((v) => v !== value);
        } else {
          option.classList.add("selected");
          values.push(value);
        }
        setSelectedValues(values);
        this.updateSelectedOptionsUI(select, values, isTeamSelect);
      });
    });

    target.addEventListener("click", (e) => {
      if (!select.contains(e.target)) {
        dropdown.classList.remove("show");
        trigger.classList.remove("active");
      }
    });
  }

  updateSelectedOptionsUI(select, selectedValues, isTeamSelect) {
    const trigger = select.classList.contains("select-trigger")
      ? select
      : select.querySelector(".select-trigger");

    if (!trigger) return;

    const valueElement = trigger.querySelector(".select-value");
    const placeholder = trigger.querySelector(".select-placeholder");

    if (!valueElement) return;
    valueElement.innerHTML = "";
    const displayValues = selectedValues.filter((v) => v !== "0");
    trigger.classList.toggle("has-selections", displayValues.length > 0);

    if (displayValues.length === 0) {
      if (placeholder) {
        placeholder.textContent = isTeamSelect ? "All Teams" : "All Sales Reps";
        placeholder.style.display = "block";
      }
    } else {
      displayValues.forEach((value) => {
        const data = isTeamSelect
          ? this.state.filteredData.teams.find((t) => t.id == value)
          : this.state.filteredData.salespeople.find((u) => u.id == value);

        if (data) {
          const tag = document.createElement("div");
          tag.className = "selected-option-tag";
          tag.innerHTML = `
                    <span class="tag-text">${data.name}</span>
                    <span class="remove-tag" data-value="${value}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </span>
                `;
          valueElement.appendChild(tag);
          if (placeholder) placeholder.style.display = "none";

          tag.querySelector(".remove-tag").addEventListener("click", (e) => {
            e.stopPropagation();
            this.removeSelectedOption(value, isTeamSelect);
          });
        }
      });
    }
  }

  removeSelectedOption(value, isTeamSelect) {
    const selectId = isTeamSelect ? "team-filter" : "user-filter";
    const target = this.commissionDashboardRef.el;
    const select = target.querySelector(`#${selectId}`);
    if (!select) return;
    const dropdown = select
      .closest(".custom-select")
      ?.querySelector(".select-dropdown");
    const option = dropdown?.querySelector(`[data-value="${value}"]`);
    if (option) {
      option.classList.remove("selected");
    }
    let currentValues = isTeamSelect
      ? [...this.state.filters.teamIds].filter((v) => v !== "0")
      : [...this.state.filters.userIds].filter((v) => v !== "0");

    currentValues = currentValues.filter((v) => v !== value);

    if (isTeamSelect) {
      this.state.filters.teamIds =
        currentValues.length > 0 ? currentValues : ["0"];
      this.state.filters.teamId =
        currentValues.length === 1 ? parseInt(currentValues[0]) : 0;
    } else {
      this.state.filters.userIds =
        currentValues.length > 0 ? currentValues : ["0"];
      this.state.filters.userId =
        currentValues.length === 1 ? parseInt(currentValues[0]) : 0;
    }
    this.updateSelectedOptionsUI(
      select,
      isTeamSelect ? this.state.filters.teamIds : this.state.filters.userIds,
      isTeamSelect
    );
  }

  toggleDropdown(select) {
    const trigger = select.querySelector(".select-trigger");
    const dropdown = select.querySelector(".select-dropdown");
    const isOpen = dropdown.classList.contains("show");
    if (!isOpen) {
      this.closeAllDropdowns();
    }
    if (isOpen) {
      trigger.classList.remove("active");
      dropdown.classList.remove("show");
    } else {
      trigger.classList.add("active");
      dropdown.classList.add("show");
    }
  }

  selectOption(select, option) {
    const valueElement = select.querySelector(".select-value");
    const dropdown = select.querySelector(".select-dropdown");
    const trigger = select.querySelector(".select-trigger");
    const allOptions = dropdown.querySelectorAll(".select-option");
    allOptions.forEach((opt) => opt.classList.remove("selected"));
    option.classList.add("selected");
    valueElement.textContent = option.textContent.trim();
    valueElement.classList.remove("placeholder");
    trigger.classList.remove("active");
    dropdown.classList.remove("show");
    const selectId = select
      .closest(".custom-select")
      .querySelector(".select-trigger").id;
    const value = option.dataset.value;

    if (selectId === "date-range") {
      this.state.filters.period = value;
    } else if (selectId === "plan-type") {
      this.state.filters.planType = value;
      this.state.filters.selectedPlan = "";
    } else if (selectId === "detailed-plan-select") {
      this.state.filters.selectedPlan = value;
      this.renderSelectedPlan();
    } else if (selectId === "sort") {
      this.state.filters.sort = value;
        this.renderLeaderBoard(
            this.commissionDashboardRef?.el,
            this.state.filteredData?.commissions,
            this.state.filteredData?.leaderboardCommissions,
            value
        );
    }
  }

  closeAllDropdowns() {
    const target = this.commissionDashboardRef.el;
    target.querySelectorAll(".select-dropdown.show").forEach((dropdown) => {
      dropdown.classList.remove("show");
    });
    target.querySelectorAll(".select-trigger.active").forEach((trigger) => {
      trigger.classList.remove("active");
    });
  }

  adjustNonManagerUI(id, isManager, data) {
    const target = this.commissionDashboardRef.el;
    if (!target) return;
    const { userLabel, userValue, userTeams } =
      this.getDefaultUserAndTeamFilters(id, isManager, data);
    const isSingleTeam = userTeams.length === 1;
    const userFilter = target.querySelector("#user-filter");
    if (userFilter) {
      userFilter.disabled = true;
      this.closeAllDropdowns();
      const valueElement =
        userFilter.querySelector(".select-value") || userFilter;
      valueElement.textContent = userLabel;

      const customSelect = userFilter.closest(".custom-select");
      if (customSelect) {
        const dropdownArrow = customSelect.querySelector(".select-arrow");
        if (dropdownArrow) {
          dropdownArrow.style.display = "none";
        }
        const dropdown = customSelect.querySelector(".select-dropdown");
        if (dropdown) {
          dropdown.remove();
        }
        const trigger = customSelect.querySelector(".select-trigger");
        if (trigger) {
          trigger.replaceWith(trigger.cloneNode(true));
        }
      }
    }
    if (userTeams && userTeams.length === 1) {
      const teamFilter = target.querySelector("#team-filter");
      if (teamFilter) {
        teamFilter.disabled = true;
        const teamName =
          this.state.filteredData.teams.find(
            (t) => t.id === parseInt(userTeams[0])
          )?.name || "Your Team";
        const valueElement =
          teamFilter.querySelector(".select-value") || teamFilter;
        valueElement.textContent = teamName;

        const customSelect = teamFilter.closest(".custom-select");
        if (customSelect) {
          const dropdownArrow = customSelect.querySelector(".select-arrow");
          if (dropdownArrow) {
            dropdownArrow.style.display = "none";
          }
          const dropdown = customSelect.querySelector(".select-dropdown");
          if (dropdown) {
            dropdown.remove();
          }
          const trigger = customSelect.querySelector(".select-trigger");
          if (trigger) {
            trigger.replaceWith(trigger.cloneNode(true));
          }
        }
      }
    }
  }

  showMultiSelectPlaceholder(selectId, placeholderText, target) {
    const select = target.querySelector(`#${selectId}`);
    if (!select) return;
    const valueElement = select.querySelector(".select-value");
    valueElement.textContent = placeholderText;
    valueElement.classList.add("placeholder");
  }
}

actionRegistry.add("commission_dashboard_tag", CommissionDashboard);
