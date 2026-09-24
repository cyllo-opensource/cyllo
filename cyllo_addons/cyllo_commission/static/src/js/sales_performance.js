/** @odoo-module **/

import { getDateRange } from "@cyllo_commission/js/summary_cards";
import {
  renderLineChart,
  renderBarChart,
  renderDonutChart,
  renderPieChart,
  redirectToListView,
} from "@cyllo_commission/js/graphs";

export function renderSalesPerformance(
  target,
  currency,
  sale_orders,
  getDateRange,
  period,
  graphBase,
  env
) {
  const chartColors = {
    blue: "#2563eb",
  };

  setTimeout(() => {
    if (!target) return;
    const sales = target.querySelector("#salesPerformanceChart");
    if (!sales) return;

    if (sales.chartInstance) {
      sales.chartInstance.destroy();
    }
    const dateRange = getDateRange(period);
    const startDate = new Date(dateRange.startDate);
    const endDate = new Date(dateRange.endDate);
    const allMonths = [];
    let current = new Date(startDate.getFullYear(), startDate.getMonth(), 1);
    while (current <= endDate) {
      const monthLabel = current.toLocaleString("default", { month: "short" });
      allMonths.push(monthLabel);
      current.setMonth(current.getMonth() + 1);
    }
    let saleTotalByMonth = {};
    let orderIdsByMonth = {};
    allMonths.forEach((month) => {
      saleTotalByMonth[month] = 0;
      orderIdsByMonth[month] = [];
    });
    const orders = sale_orders.filter((o) => {
      const orderDate = new Date(o.date);
      return orderDate >= startDate && orderDate <= endDate;
    });
    orders.forEach((order) => {
      const date = new Date(order.date);
      const month = date.toLocaleString("default", { month: "short" });
      saleTotalByMonth[month] += order.amount;
      orderIdsByMonth[month].push(order.id);
    });
    let labels = Object.keys(saleTotalByMonth);
    let Data = Object.values(saleTotalByMonth);
    const handleGraphClick = (monthLabel) => {
      const ids = orderIdsByMonth[monthLabel] || [];
      redirectToListView({
        env: env,
        ids: ids,
        modelName: "sale.order",
      });
    };
    if (labels.length === 0 || Data.every((value) => value === 0)) {
      sales.style.display = "none";
      const chartContainer = sales.closest(".chart-body");
      if (!chartContainer.querySelector(".no-data-message")) {
        const noDataDiv = document.createElement("div");
        noDataDiv.className = "no-data-message";
        noDataDiv.innerHTML = `
                    <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #6b7280; font-size: 16px;">
                        <div style="text-align: center;">
                            <div style="font-size: 48px; margin-bottom: 16px;">📊</div>
                            <div>No sales data available for the selected period</div>
                        </div>
                    </div>
                `;
        chartContainer.appendChild(noDataDiv);
      }
      return;
    }
    sales.style.display = "block";
    const chartContainer = sales.closest(".chart-body") || sales.parentElement;
    const noDataMessage = chartContainer.querySelector(".no-data-message");
    if (noDataMessage) {
      noDataMessage.remove();
    }
    const chartLabel = "Sales";
    let salesPerformanceChart;
    switch (graphBase) {
      case "bar":
        salesPerformanceChart = renderBarChart(
          sales,
          chartColors,
          labels,
          Data,
          chartLabel,
          currency,
          handleGraphClick
        );
        break;
      case "pie":
        salesPerformanceChart = renderPieChart(
          sales,
          labels,
          Data,
          chartLabel,
          currency,
          handleGraphClick
        );
        break;
      case "donut":
        salesPerformanceChart = renderDonutChart(
          sales,
          labels,
          Data,
          currency,
          handleGraphClick
        );
        break;
      default:
        salesPerformanceChart = renderLineChart(
          sales,
          chartColors,
          labels,
          Data,
          chartLabel,
          currency,
          handleGraphClick
        );
    }
    sales.chartInstance = salesPerformanceChart;
  }, 0);
}