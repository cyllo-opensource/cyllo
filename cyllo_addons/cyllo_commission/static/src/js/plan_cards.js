/**  @odoo-module **/
import { formatCurrency } from "./summary_cards.js";

export function renderPlanCards(
  target,
  plans,
  commissions,
  period,
  formatCurrency,
  currency_symbol,
  currency_position,
  viewPlanCallback
) {
  setTimeout(() => {
    if (!target) return;

    const container = target.querySelector(".selected-plan-container");
    if (!container) {
      return;
    }
    container.innerHTML = "";
    if (!plans || plans.length === 0) {
      const card = document.createElement("div");
      card.className = "no-plan-selected";
      card.innerHTML = `
        <svg class="no-plan-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <div class="no-plan-text">No Plan Selected</div>
                <div class="no-plan-subtext">Select a commission plan from the dropdown above to view detailed information</div>
      `;
      container.appendChild(card);
      return;
    }
    for (let plan of plans) {
      const salespeople = commissions.filter((p) => plan.id === p.plan_id);
      const salespeopleCommissions = {};
      salespeople.forEach((person) => {
        const key = person.salesperson_id;
        if (!salespeopleCommissions[key]) {
          salespeopleCommissions[key] = {
            id: key,
            name: person.salesperson,
            commission: 0,
            sale: 0,
          };
        }
        salespeopleCommissions[key].commission += person.commission_amount || 0;
        salespeopleCommissions[key].sale += person.sale_amount || 0;
      });
      const salespeopleArray = Object.values(salespeopleCommissions);
      let paidCommission = 0;
      for (const array of salespeopleArray) {
        paidCommission += array.commission;
      }
      let periodName =
        {
          this_year: "This Year",
          last_year: "Last Year",
          this_quarter: "This Quarter",
          last_quarter: "Last Quarter",
          this_month: "This Month",
          last_month: "Last Month",
        }[period] || "";
      const card = document.createElement("div");
      card.className = "plan-card";
      card.innerHTML = `
        <div class="plan-header">
          <div class="plan-name">
            <span>${plan.name}</span>
            <span class="plan-type ${
              plan.type === "target" ? "target" : "contribution"
            }">
              ${plan.type === "target" ? "Target-Based" : "Contribution-Based"}
            </span>
          </div>
          <div class="chart-action">
            <button class="btn view-plan" data-plan-id="${
              plan.id
            }">View Plan</button>
          </div>
        </div>
        <div class="plan-body">
          <div class="plan-summary">
            <div class="commission-total" id="commission-total-${plan.id}">
              <!-- total commission will be filled later -->
            </div>
            <div class="commission-breakdown" id="commission-breakdown-${
              plan.id
            }">
              <!-- breakdown will be filled later -->
            </div>
          </div>
          <div class="plan-chart">
            <canvas id="plan-commission-chart-${plan.id}"></canvas>
          </div>
        </div>
      `;

      const viewPlanButton = card.querySelector(".view-plan");
      if (viewPlanButton && viewPlanCallback) {
        viewPlanButton.addEventListener("click", () => {
          viewPlanCallback(plan.id);
        });
      }
      container.appendChild(card);
      renderPlanCommissionChart(
        card,
        plan,
        salespeopleArray,
        formatCurrency,
        currency_symbol,
        currency_position
      );
      renderCommissionBreakdown(
        card,
        plan,
        periodName,
        salespeopleArray,
        paidCommission,
        formatCurrency,
        currency_symbol,
        currency_position
      );
    }
  }, 0);
}

export function renderPlanCommissionChart(
  target,
  plan,
  salespeopleArray,
  formatCurrency,
  currency_symbol,
  currency_position
) {
  const chartColors = {
    blue: "#2563eb",
  };
  if (!target) return;
  const canvasId = `plan-commission-chart-${plan.id}`;
  const canvas = target.querySelector(`#${canvasId}`);
  if (!canvas) return;
  if (canvas.chartInstance) {
    canvas.chartInstance.destroy();
  }
  const labels = salespeopleArray.map((sp) => {
    if (!sp.name) return "Unknown";
    return sp.name
      .split(" ")
      .map((word) => word[0].toUpperCase())
      .join(" ");
  });
  const data = salespeopleArray.map((sp) => sp.commission || 0);

  const chart = new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: `Commission - ${plan.name}`,
          data,
          backgroundColor: chartColors.blue,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          backgroundColor: "rgba(255, 255, 255, 0.9)",
          titleColor: "#1f2937",
          bodyColor: "#4b5563",
          borderColor: "#e5e7eb",
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: function (context) {
              const fullName =
                salespeopleArray[context.dataIndex].name || "Unknown";
              return `${fullName}: ${formatCurrency(
                context.raw,
                currency_symbol,
                currency_position
              )}`;
            },
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: {
            drawBorder: false,
            color: "#f3f4f6",
          },
          ticks: {
            callback: function (value) {
              return formatCurrency(value, currency_symbol, currency_position);
            },
          },
        },
        x: {
          grid: {
            display: false,
          },
        },
      },
    },
  });
  canvas.chartInstance = chart;
}

export function renderCommissionBreakdown(
  target,
  plan,
  periodName,
  salespeopleArray,
  paidCommission,
  formatCurrency,
  currency_symbol,
  currency_position
) {
  if (!target) return;

  const totalContainer = target.querySelector(`#commission-total-${plan.id}`);
  const breakdownContainer = target.querySelector(
    `#commission-breakdown-${plan.id}`
  );
  if (!totalContainer || !breakdownContainer) return;
  totalContainer.innerHTML = `
    <div class="commission-label">Total Commission Paid</div>
    <div class="commission-value">${formatCurrency(
      paidCommission,
      currency_symbol,
      currency_position
    )}</div>
    <div class="commission-subtitle">${periodName}</div>
  `;
  breakdownContainer.innerHTML = "";

  const sorted = salespeopleArray.sort((a, b) => b.commission - a.commission);
  const test = [
    { id: 1, name: "Alice Johnson", sale: 15000, commission: 1200 },
    { id: 2, name: "Nathan Bennet", sale: 13600, commission: 1000 },
    { id: 3, name: "Sophia Lee", sale: 9800, commission: 750 },
    { id: 4, name: "David Kim", sale: 11200, commission: 900 },
    { id: 5, name: "Emma Davis", sale: 16400, commission: 1300 },
    { id: 6, name: "Michael Brown", sale: 10250, commission: 820 },
    { id: 7, name: "Liam Wilson", sale: 9200, commission: 690 },
    { id: 8, name: "Olivia Smith", sale: 14300, commission: 1100 },
    { id: 9, name: "William Taylor", sale: 8700, commission: 670 },
    { id: 10, name: "Isabella Clark", sale: 12100, commission: 960 },
  ];

  sorted.forEach((person) => {
    const element = document.createElement("div");
    element.className = "breakdown-person";
    element.innerHTML = `
      <div class="breakdown-header">
                    <div class="breakdown-name">${person.name}</div>
                    <div class="breakdown-commission"><span>${formatCurrency(
                      person.commission,
                      currency_symbol,
                      currency_position
                    )}</span>
                    <span class="commission-label">Commission</span></div>
                  </div>
                  <div class="breakdown-details">
                    <span>${formatCurrency(
                      person.sale,
                      currency_symbol,
                      currency_position
                    )} Sales</span>
                  </div>
      `;
    breakdownContainer.appendChild(element);
  });
}
