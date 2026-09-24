/**  @odoo-module **/
import { formatCurrency, getDateRange } from "./summary_cards.js";
import {
  renderLineChart,
  renderBarChart,
  renderDonutChart,
  renderPieChart,
  redirectToListView,
} from "@cyllo_commission/js/graphs";

function createClickHandler(labelToId, dataMap, env, modelName, viewId) {
  return function (labelName) {
    const id = labelToId[labelName];
    const record = dataMap[id];
    const ids = record?.commissionIds || [];
    redirectToListView({ env, ids, modelName, listViewId: viewId });
  };
}

export function renderTeamCommissionDistribution(
  target,
  currency,
  team_members,
  orderLines,
  commissions,
  userId,
  graphBase,
  type,
  env,
  viewId
) {
  setTimeout(() => {
    if (!target) return;
    const canvas = target.querySelector("#commissionDistribution");
    if (!canvas) return;
    if (canvas.chartInstance) canvas.chartInstance.destroy();
    const chartColors = { blue: "#2563eb" };
    const modelName = "commission.report";
    const labels = [],
      data = [],
      labelToId = {};
    let handleGraphClick;

    if (!userId) {
      const saleLineById = Object.fromEntries(orderLines.map((l) => [l.id, l]));
      const teamCommissions = {};

      commissions.forEach((commission) => {
        const lines = commission.sale_orderline_ids
          .map((id) => saleLineById[id])
          .filter(Boolean);
        const total = lines.reduce((sum, l) => sum + l.amount, 0);
        if (total === 0) return;

        const teamShares = {};
        lines.forEach((line) => {
          const { team_id, team_name, amount } = line;
          const share = (commission.commission_amount * amount) / total;
          if (!teamShares[team_id]) {
            teamShares[team_id] = { team_name, total_share: 0 };
          }
          teamShares[team_id].total_share += share;
        });

        for (const teamId in teamShares) {
          const { team_name, total_share } = teamShares[teamId];
          if (!teamCommissions[teamId]) {
            teamCommissions[teamId] = {
              id: parseInt(teamId),
              team_name,
              total_commission: 0,
              commissionIds: [],
            };
          }
          teamCommissions[teamId].total_commission += total_share;
          if (!teamCommissions[teamId].commissionIds.includes(commission.id)) {
            teamCommissions[teamId].commissionIds.push(commission.id);
          }
        }
      });

      for (const key in teamCommissions) {
        const team = teamCommissions[key];
        labels.push(team.team_name);
        data.push(team.total_commission);
        labelToId[team.team_name] = team.id;
      }

      if (type !== "all") {
        handleGraphClick = createClickHandler(
          labelToId,
          teamCommissions,
          env,
          modelName,
          viewId
        );
      }
    } else {
      const grouped = {};
      commissions.forEach((person) => {
        const key = person.salesperson_id;
        if (!grouped[key]) {
          grouped[key] = {
            id: key,
            name: person.salesperson,
            commission: 0,
            commissionIds: [],
          };
        }
        grouped[key].commission += person.commission_amount || 0;
        grouped[key].commissionIds.push(person.id);
      });

      for (const key in grouped) {
        const sp = grouped[key];
        labels.push(sp.name);
        data.push(sp.commission);
        labelToId[sp.name] = sp.id;
      }

      if (type !== "all") {
        handleGraphClick = createClickHandler(
          labelToId,
          grouped,
          env,
          modelName,
          viewId
        );
      }
    }

    if (labels.length === 0 || data.every((v) => v === 0)) {
      canvas.style.display = "none";
      const container = canvas.closest(".chart-body");
      if (!container.querySelector(".no-data-message")) {
        const noDataDiv = document.createElement("div");
        noDataDiv.className = "no-data-message";
        noDataDiv.innerHTML = `
          <div style="display:flex;align-items:center;justify-content:center;height:100%;color:#6b7280;font-size:16px;">
            <div style="text-align:center;">
              <div style="font-size:48px;margin-bottom:16px;">\ud83d\udcca</div>
              <div>No sales data available for the selected period</div>
            </div>
          </div>`;
        container.appendChild(noDataDiv);
      }
      return;
    }

    canvas.style.display = "block";
    const container = canvas.closest(".chart-body") || canvas.parentElement;
    const noDataMessage = container.querySelector(".no-data-message");
    if (noDataMessage) noDataMessage.remove();

    const chartLabel = "Commissions";
    let chartInstance;

    switch (graphBase) {
      case "bar":
        chartInstance = renderBarChart(
          canvas,
          chartColors,
          labels,
          data,
          chartLabel,
          currency,
          handleGraphClick
        );
        break;
      case "line":
        chartInstance = renderLineChart(
          canvas,
          chartColors,
          labels,
          data,
          chartLabel,
          currency,
          handleGraphClick
        );
        break;
      case "donut":
        chartInstance = renderDonutChart(
          canvas,
          labels,
          data,
          currency,
          handleGraphClick
        );
        break;
      default:
        chartInstance = renderPieChart(
          canvas,
          labels,
          data,
          chartLabel,
          currency,
          handleGraphClick
        );
    }
    canvas.chartInstance = chartInstance;
  }, 0);
}
