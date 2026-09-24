/**  @odoo-module */

export function formatCurrency(amount, symbol, position) {
  return position === "before"
    ? `${symbol}${amount.toFixed(2)}`
    : `${amount.toFixed(2)} ${symbol}`;
}

export function getDateRange(option) {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth(); // 0-based
  const startOfMonth = (y, m) => new Date(y, m, 1);
  const endOfMonth = (y, m) => new Date(y, m + 1, 0);
  let start, end;

  switch (option) {
    case "this_month":
      start = startOfMonth(year, month);
      end = endOfMonth(year, month);
      break;

    case "last_month":
      const lastMonth = month === 0 ? 11 : month - 1;
      const lastMonthYear = month === 0 ? year - 1 : year;
      start = startOfMonth(lastMonthYear, lastMonth);
      end = endOfMonth(lastMonthYear, lastMonth);
      break;

    case "this_quarter":
      const q = Math.floor(month / 3); // 0,1,2,3
      start = startOfMonth(year, q * 3);
      end = endOfMonth(year, q * 3 + 2);
      break;

    case "last_quarter":
      let lastQ = Math.floor(month / 3) - 1;
      let lastQYear = year;
      if (lastQ < 0) {
        lastQ = 3;
        lastQYear -= 1;
      }
      start = startOfMonth(lastQYear, lastQ * 3);
      end = endOfMonth(lastQYear, lastQ * 3 + 2);
      break;

    case "this_year":
      start = new Date(year, 0, 1);
      end = new Date(year, 11, 31);
      break;

    case "last_year":
      start = new Date(year - 1, 0, 1);
      end = new Date(year - 1, 11, 31);
      break;

    default:
      throw new Error("Unknown option: " + option);
  }
  const formatLocalDate = (date) => {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  };

  return {
    startDate: formatLocalDate(start),
    endDate: formatLocalDate(end),
  };
}

export function shiftMonth(date, diff) {
  const newDate = new Date(date);
  const day = newDate.getDate();

  newDate.setDate(1);
  newDate.setMonth(newDate.getMonth() + diff);

  const maxDay = new Date(
    newDate.getFullYear(),
    newDate.getMonth() + 1,
    0
  ).getDate();
  newDate.setDate(Math.min(day, maxDay));

  return newDate;
}

export function renderSummaryCards(
  target,
  period,
  allCommissions,
  allOrders,
  filteredCommissions,
  filteredOrders,
  team_members,
  plans,
  formatCurrency,
  getDateRange,
  shiftMonth,
  currencySymbol,
  currencyPosition
) {
  if (!target) return;

  const sales_summary = target.querySelector("#sales_card");
  const commission_summary = target.querySelector("#commission_card");
  const reps_summary = target.querySelector("#reps_card");
  const plans_summary = target.querySelector("#plan_cards");

const{total_sales,
    salesPercentage,
    periodName,
    total_commissions,
    commissionPercentage,
    active_plans,
    contributions,
    targets,
    total_reps,
    teamName,}=summaryCardData(
  period,
  allCommissions,
  allOrders,
  team_members,
  plans,
  filteredOrders,
  filteredCommissions,
  getDateRange,
  shiftMonth
)
  sales_summary.innerHTML = `
        <div class="kpi-header">
            <span class="kpi-title">Total Sales</span>
            <div class="kpi-icon icon-money">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="12" y1="1" x2="12" y2="23"/>
                    <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                </svg>
            </div>
        </div>
        <div class="kpi-value">${formatCurrency(
          total_sales,
          currencySymbol,
          currencyPosition
        )}</div>
        <div class="kpi-trend trend-up">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="18 15 12 9 6 15"/>
            </svg>
            ${`${salesPercentage}% from ${periodName}`}
        </div>`;

  commission_summary.innerHTML = `
        <div class="kpi-header">
            <span class="kpi-title">Total Commission</span>
            <div class="kpi-icon icon-commission">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/>
                    <path d="M12 6v12"/>
                </svg>
            </div>
        </div>
        <div class="kpi-value">${formatCurrency(
          total_commissions,
          currencySymbol,
          currencyPosition
        )}</div>
        <div class="kpi-trend trend-up">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="18 15 12 9 6 15"/>
            </svg>
            ${`${commissionPercentage}% from ${periodName}`}
        </div>`;

  plans_summary.innerHTML = `
        <div class="kpi-header">
                        <span class="kpi-title">Active Plans</span>
                        <div class="kpi-icon icon-goal">
                            <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    width="16"
                                    height="16"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    stroke-width="2"
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                            >
                                <circle cx="12" cy="12" r="10"/>
                                <circle cx="12" cy="12" r="6"/>
                                <circle cx="12" cy="12" r="2"/>
                            </svg>
                        </div>
                    </div>
                    <div class="kpi-value">${active_plans}</div>
                    <div class="kpi-trend" style="display:flex;flex-direction:column;align-items: flex-start;">
            <span style="color: #000"><b>${contributions}</b> Contribution</span>
            <span style="color: #000"><b>${targets}</b> Target</span>
        </div>
        `;

  reps_summary.innerHTML = `
        <div class="kpi-header">
            <span class="kpi-title">Active Sales Reps</span>
            <div class="kpi-icon icon-team">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                    <circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
            </div>
        </div>
        <div class="kpi-value">${total_reps}</div>
        <div class="kpi-trend">
            <span style="color: #000">${teamName}</span>
        </div>`;
}

export function summaryCardData(
  period,
  allCommissions,
  allOrders,
  team_members,
  plans,
  filteredOrders,
  filteredCommissions,
  getDateRange,
  shiftMonth
) {
  let prevPeriod = "";
  let periodName = "";

  if (["this_year", "last_year"].includes(period)) {
    prevPeriod = "last_year";
    periodName = "Last Year";
  } else if (["this_quarter", "last_quarter"].includes(period)) {
    prevPeriod = "last_quarter";
    periodName = "Last Quarter";
  } else if (["this_month", "last_month"].includes(period)) {
    prevPeriod = "last_month";
    periodName = "Last Month";
  }

  const { startDate, endDate } = getDateRange(prevPeriod);
  let start = new Date(startDate);
  let end = new Date(endDate);

  if (period === prevPeriod) {
    if (period === "last_year") {
      start.setFullYear(start.getFullYear() - 1);
      end.setFullYear(end.getFullYear() - 1);
    } else if (period === "last_quarter") {
      start = shiftMonth(start, -3);
      end = shiftMonth(end, -3);
    } else if (period === "last_month") {
      start = shiftMonth(start, -1);
      end = shiftMonth(end, -1);
    }
  }

  const commissions = allCommissions.filter((c) => {
    const from = new Date(c.date_from);
    const to = new Date(c.date_to);
    return from <= end && to >= start;
  });

  const orders = allOrders.filter((o) => {
    const orderDate = new Date(o.date);
    return orderDate >= start && orderDate <= end;
  });

  const totalPrevCommission = commissions.reduce(
    (total, c) => total + c.commission_amount,
    0
  );

  const totalPrevSales = orders.reduce((total, o) => total + o.amount, 0);

  const total_sales = filteredOrders.reduce((sum, o) => sum + o.amount, 0);
  const total_commissions = filteredCommissions.reduce(
    (sum, c) => sum + c.commission_amount,
    0
  );

  const total_reps = new Set(team_members.map((m) => m.user_id)).size;
  const team_ids = new Set(team_members.map((m) => m.team_id));
  const active_plans = new Set(plans.map((p) => p.id)).size;

  const contributions = new Set(
    plans.filter((p) => p.type === "contribution").map((p) => p.id)
  ).size;

  const targets = new Set(
    plans.filter((p) => p.type === "target").map((p) => p.id)
  ).size;

  let teamName = "";
  if (team_ids.size > 1) {
    teamName = `Across ${team_ids.size} teams`;
  } else if (team_ids.size === 1) {
    const teamId = team_ids.values().next().value;
    const team_name = team_members.find((m) => m.team_id === teamId)?.team_name;
    teamName = team_name ? `From ${team_name} team` : "";
  }

  const commissionPercentage = totalPrevCommission
    ? (total_commissions / totalPrevCommission) * 100
    : 100;

  const salesPercentage = totalPrevSales
    ? (total_sales / totalPrevSales) * 100
    : 100;

  return {
    total_sales,
    salesPercentage,
    periodName,
    total_commissions,
    commissionPercentage,
    active_plans,
    contributions,
    targets,
    total_reps,
    teamName,
  };
}
