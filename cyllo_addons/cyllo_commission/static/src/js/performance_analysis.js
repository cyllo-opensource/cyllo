/** @odoo-module **/
import {
  formatCurrency,
  getDateRange,
  shiftMonth,
} from "@cyllo_commission/js/summary_cards";

export function mostSoldProducts(orderLines) {
  const productStats = new Map();

  for (const line of orderLines) {
    const id = line.product_id;
    if (!productStats.has(id)) {
      productStats.set(id, {
        id,
        name: line.product_name,
        count: 0,
        revenue: 0,
      });
    }
    const stats = productStats.get(id);
    stats.count += 1;
    stats.revenue += line.amount;
  }

  const products = Array.from(productStats.values());

  return {
    mostSoldProduct: [...products].sort((a, b) => b.count - a.count),
    mostRevenueProduct: [...products].sort((a, b) => b.revenue - a.revenue),
  };
}
export function teamMaxSales(teamOrderLines) {
  let teamSales = {};
  teamOrderLines.forEach((line) => {
    const key = line.team_id;
    if (!teamSales[key]) {
      teamSales[key] = {
        id: key,
        team: line.team_name,
        amount: 0,
      };
    }
    teamSales[key].amount += line.amount || 0;
  });
  const sortedTeamSales = Object.values(teamSales).sort(
    (a, b) => b.amount - a.amount
  );
  return sortedTeamSales;
}

export function renderPerformanceAnalysis(
  target,
  period,
  allCustomers,
  allOrders,
  allOrderLines,
  allWonOpportunities,
  allOpportunities,
  filteredCustomers,
  filteredOrders,
  filteredOrderLines,
  filteredWonOpportunities,
  filteredOpportunities,
  teamMembers,
  currencySymbol,
  currencyPosition
) {
  if (!target) return;

  const customerAnalysis = target.querySelector("#customers-card");
  const winRateAnalysis = target.querySelector("#winrate-card");
  const productSoldAnalysis = target.querySelector("#max-sold-product-card");
  const productRevenueAnalysis = target.querySelector(
    "#max-revenue-product-card"
  );
  const salesTeamAnalysis = target.querySelector("#sale-team-card");
  const convertionAnalysis = target.querySelector("#convertion-card");

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

  const customers = allCustomers.filter((c) => {
    const date = new Date(c.create_date);
    return date >= start && date <= end;
  });
  const wonOpportunities = allWonOpportunities.filter((c) => {
    const date = new Date(c.stage_update_date);
    return date >= start && date <= end;
  });
  const opportunities = allOpportunities.filter((c) => {
    const date = new Date(c.stage_update_date);
    return date >= start && date <= end;
  });

  const orders = allOrders.filter((o) => {
    const orderDate = new Date(o.date);
    return orderDate >= start && orderDate <= end;
  });
  const orderLines = allOrderLines.filter((o) => {
    const orderDate = new Date(o.date);
    return orderDate >= start && orderDate <= end;
  });

  const teams = new Set(teamMembers.map((team) => team.team_id));
  const teamPrevOrders = orders.filter((order) => teams.has(order.team_id));
  const teamPrevOrderLines = orderLines.filter((line) =>
    teamPrevOrders.some((order) => order.id === line.order_id)
  );
  const teamPrevSales = teamMaxSales(teamPrevOrderLines);

  const teamCurrOrders = filteredOrders.filter((order) =>
    teams.has(order.team_id)
  );
  const teamCurrOrderLines = filteredOrderLines.filter((line) =>
    teamCurrOrders.some((order) => order.id === line.order_id)
  );
  const teamCurrSales = teamMaxSales(teamCurrOrderLines);
  let currTopTeamId = 0;
  let currTopTeam = "N/A";
  let currTopTeamAmount = 0;
  let prevTeamAmount = 0.0;
  let salesPercentage = 0.0;
  if (teamCurrSales.length > 0) {
    currTopTeamId = teamCurrSales[0].id;
    currTopTeam = teamCurrSales[0].team;
    currTopTeamAmount = teamCurrSales[0].amount;
    if (teamPrevSales.length > 0) {
      const team = teamPrevSales.filter((team) => team.id === currTopTeamId);
      prevTeamAmount = team[0].amount;
    }
    salesPercentage = prevTeamAmount
      ? (currTopTeamAmount / prevTeamAmount) * 100
      : 100;
  }
  const {
    mostSoldProduct: prevPeriodSoldProduct,
    mostRevenueProduct: prevPeriodRevenueProduct,
  } = mostSoldProducts(orderLines);
  const {
    mostSoldProduct: currPeriodSoldProduct,
    mostRevenueProduct: currPeriodRevenueProduct,
  } = mostSoldProducts(filteredOrderLines);
  let topSoldProduct = { id: 0, name: "N/A", count: 0 };
  let topSoldProductCount = 0;
  let topProductPrevPeriodSales = 0;
  let productSalePercentage = 0;
  let topRevenueProduct = { id: 0, name: "N/A", revenue: 0 };
  let currRevenue = 0;
  let topProductPrevPeriodRevenue = 0.0;
  let productRevenuePercentage = 0.0;
  if (currPeriodSoldProduct.length > 0) {
    topSoldProduct = currPeriodSoldProduct[0];
    topSoldProductCount = topSoldProduct.count;
    const topSoldProductPrevPeriod = prevPeriodSoldProduct.find(
      (product) => product.id === topSoldProduct.id
    );
    topProductPrevPeriodSales = topSoldProductPrevPeriod
      ? topSoldProductPrevPeriod.count
      : 0;
    productSalePercentage = topProductPrevPeriodSales
      ? ((topSoldProductCount - topProductPrevPeriodSales) /
          topProductPrevPeriodSales) *
        100
      : 100;
  }
  if (currPeriodRevenueProduct.length > 0) {
    topRevenueProduct = currPeriodRevenueProduct[0];
    currRevenue = topRevenueProduct.revenue;
    const topRevenueProductPrevPeriod = prevPeriodRevenueProduct.find(
      (product) => product.id === topRevenueProduct.id
    );
    topProductPrevPeriodRevenue = topRevenueProductPrevPeriod
      ? topRevenueProductPrevPeriod.revenue
      : 0;
    productRevenuePercentage = topProductPrevPeriodRevenue
      ? ((currRevenue - topProductPrevPeriodRevenue) /
          topProductPrevPeriodRevenue) *
        100
      : 100;
  }

  const prevCustomerCount = customers.length;
  const prevWonOpportunitiesCount = wonOpportunities.length;
  const prevOpportunitiesCount = opportunities.length;
  let customerCountPercentage = 0.0;
  let wonPercentage = 0.0;
  const totalCustomerCount = filteredCustomers.length;
  const totalWonOpportunitiesCount = filteredWonOpportunities.length;
  const totalOpportunitiesCount = filteredOpportunities.length;
  customerCountPercentage = prevCustomerCount
    ? (totalCustomerCount / prevCustomerCount) * 100
    : 100;
  const prevWinRate = prevOpportunitiesCount
    ? (prevWonOpportunitiesCount / prevOpportunitiesCount) * 100
    : 0;
  const currentWinRate = totalOpportunitiesCount
    ? (totalWonOpportunitiesCount / totalOpportunitiesCount) * 100
    : 0;
  const winRateChange = currentWinRate - prevWinRate;
  productSalePercentage = topProductPrevPeriodSales
    ? ((topSoldProductCount - topProductPrevPeriodSales) /
        topProductPrevPeriodSales) *
      100
    : 100;
  productRevenuePercentage = topProductPrevPeriodRevenue
    ? ((currRevenue - topProductPrevPeriodRevenue) /
        topProductPrevPeriodRevenue) *
      100
    : 100;

  customerAnalysis.innerHTML = `
                            <div class="metric-header">
                                <div class="metric-icon customers">👥</div>
                                <span class="metric-label">New Customers</span>
                                <button class="info-icon">
                                    i
                                    <div class="tooltip">Number of new customers added in the selected period and their growth compared to the previous period.
                                    </div>
                                </button>
                            </div>
                            <div class="metric-value">
                                ${totalCustomerCount}
                            </div>
                            <div class="metric-trend ${
                              customerCountPercentage >= 0
                                ? "trend-up"
                                : "trend-down"
                            }">
                            <span>${
                              customerCountPercentage >= 0 ? "+" : ""
                            }${customerCountPercentage.toFixed(1)}% </span>
                            <span class="ml-1">from ${periodName}</span>
                            </div>
                            `;

  winRateAnalysis.innerHTML = `
                            <div class="metric-header">
                                <div class="metric-icon win-rate">🎯</div>
                                <span class="metric-label">Win Rate</span>
                                <button class="info-icon">
                                    i
                                    <div class="tooltip">Displays the total number of leads marked as won, and the percentage change compared to the previous period.
                                    </div>
                                </button>
                            </div>
                            <div class="metric-value">${currentWinRate.toFixed(
                              1
                            )}%</div>
                            <div class="metric-trend trend-up" ${
                              winRateChange >= 0 ? "trend-up" : "trend-down"
                            }>
                            <span>${
                              winRateChange >= 0 ? "+" : ""
                            }${winRateChange.toFixed(1)}% </span>
                            <span class="ml-1">from ${periodName}</span>
                            </div>
                            `;
  productSoldAnalysis.innerHTML = `
                            <div class="metric-header">
                                <div class="metric-icon product-mix">📦</div>
                                <span class="metric-label">Most Sold</span>
                                <button class="info-icon">
                                    i
                                    <div class="tooltip">Highlights the top-selling product and how its sales volume changed from the previous period.
                                    </div>
                                </button>
                            </div>
                            <div class="metric-value">${
                              topSoldProduct.name
                            }</div>
                            <div class="metric-trend trend-up" ${
                              productSalePercentage >= 0
                                ? "trend-up"
                                : "trend-down"
                            }>
                            <span>${
                              productSalePercentage >= 0 ? "+" : ""
                            }${productSalePercentage.toFixed(1)}% </span>
                            <span class="ml-1">from ${periodName}</span>
                            </div>
                            `;
  productRevenueAnalysis.innerHTML = `
                            <div class="metric-header">
                                <div class="metric-icon conversion">📈</div>
                                <span class="metric-label">Most Revenue</span>
                                <button class="info-icon">
                                    i
                                    <div class="tooltip">Shows the product that generated the highest revenue and its revenue growth compared to the previous period.
                                    </div>
                                </button>
                            </div>
                            <div class="metric-value">${
                              topRevenueProduct.name
                            }</div>
                            <div class="metric-trend trend-up" ${
                              productRevenuePercentage >= 0
                                ? "trend-up"
                                : "trend-down"
                            }>
                            <span>${
                              productRevenuePercentage >= 0 ? "+" : ""
                            }${productRevenuePercentage.toFixed(1)}% </span>
                            <span class="ml-1">from ${periodName}</span>
                            </div>
                            `;

  salesTeamAnalysis.innerHTML = `
                            <div class="metric-header">
                                <div class="metric-icon sales-team">🤝</div>
                                <span class="metric-label">${currTopTeam}</span>
                                <button class="info-icon">
                                    i
                                    <div class="tooltip">Displays the leading sales team by total sales and the increase in their performance from the previous period.
                                    </div>
                                </button>
                            </div>
                            <div class="metric-value">${formatCurrency(
                              currTopTeamAmount,
                              currencySymbol,
                              currencyPosition
                            )}</div>
                            <div class="metric-trend ${
                              salesPercentage >= 0 ? "trend-up" : "trend-down"
                            }">
                            <span>${
                              salesPercentage >= 0 ? "+" : ""
                            }${salesPercentage.toFixed(1)}% </span>
                            <span class="ml-1">from ${periodName}</span>
                            </div>
                            `;
}