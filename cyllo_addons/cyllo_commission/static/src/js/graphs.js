/**  @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { useComponent } from "@odoo/owl";

export function renderLineChart(
  Canvas,
  chartColors,
  Labels,
  Data,
  label,
  Currency,
  onBarClick = null
) {
  const lineGraph = new Chart(Canvas, {
    type: "line",
    data: {
      labels: Labels,
      datasets: [
        {
          label: label,
          data: Data,
          borderColor: chartColors.blue,
          backgroundColor: "rgba(37, 99, 235, 0.1)",
          tension: 0.4,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onClick: (event, elements) => {
        if (elements.length > 0 && typeof onBarClick === "function") {
          const index = elements[0].index;
          const clickedLabel = lineGraph.data.labels[index];
          onBarClick(clickedLabel);
        }
      },
      plugins: {
        legend: {
          position: "top",
          align: "end",
          labels: {
            boxWidth: 12,
            usePointStyle: true,
            pointStyle: "circle",
          },
        },
        tooltip: {
          backgroundColor: "rgba(255, 255, 255, 0.9)",
          titleColor: "#1f2937",
          bodyColor: "#4b5563",
          borderColor: "#e5e7eb",
          borderWidth: 1,
          padding: 10,
          boxWidth: 10,
          usePointStyle: true,
          callbacks: {
            label: function (context) {
              let label = context.dataset.label || "";
              if (label) label += ": ";
              label += new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: Currency || "USD",
              }).format(context.raw);
              return label;
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
              return new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: Currency,
                minimumFractionDigits: 0,
                maximumFractionDigits: 0,
              }).format(value);
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
  return lineGraph;
}

export function renderDonutChart(
  Canvas,
  Labels,
  Datas,
  Currency,
  onBarClick = null
) {
  const donutChart = new Chart(Canvas, {
    type: "doughnut",
    data: {
      labels: Labels,
      datasets: [
        {
          data: Datas,
          borderWidth: 0,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "70%",
      onClick: (event, elements) => {
        if (elements.length > 0 && typeof onBarClick === "function") {
          const index = elements[0].index;
          const clickedLabel = donutChart.data.labels[index];
          onBarClick(clickedLabel);
        }
      },
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            boxWidth: 15,
            padding: 15,
          },
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
              let label = context.dataset.label || "";
              if (label) {
                label += ": ";
              }
              label += new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: Currency || "USD",
              }).format(context.raw);
              return label;
            },
          },
        },
      },
    },
  });
  return donutChart;
}

export function renderBarChart(
  Canvas,
  chartColors,
  Labels,
  Data,
  label,
  Currency,
  onBarClick = null
) {
  const barChart = new Chart(Canvas, {
    type: "bar",
    data: {
      labels: Labels,
      datasets: [
        {
          label: label,
          data: Data,
          backgroundColor: chartColors.blue,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onClick: (event, elements) => {
        if (elements.length > 0 && typeof onBarClick === "function") {
          const index = elements[0].index;
          const clickedLabel = barChart.data.labels[index];
          onBarClick(clickedLabel);
        }
      },
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
              let label = context.dataset.label || "";
              if (label) label += ": ";
              label += new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: Currency || "USD",
              }).format(context.raw);
              return label;
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
              return new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: Currency,
                minimumFractionDigits: 0,
                maximumFractionDigits: 0,
              }).format(value);
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
  return barChart;
}

export function renderPieChart(
  Canvas,
  Labels,
  Data,
  label,
  Currency,
  onBarClick = null
) {
  const pieChart = new Chart(Canvas, {
    type: "pie",
    data: {
      labels: Labels,
      datasets: [
        {
          label: label,
          data: Data,
          borderWidth: 1,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onClick: (event, elements) => {
        if (elements.length > 0 && typeof onBarClick === "function") {
          const index = elements[0].index;
          const clickedLabel = pieChart.data.labels[index];
          onBarClick(clickedLabel);
        }
      },
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            boxWidth: 15,
            padding: 15,
          },
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              let label = context.dataset.label || "";
              if (label) {
                label += ": ";
              }
              label += new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: Currency || "USD",
              }).format(context.raw);
              return label;
            },
          },
        },
      },
    },
  });
  return pieChart;
}

export function redirectToListView({
  env,
  ids,
  modelName,
  listViewId = false,
}) {
  if (!ids || ids.length === 0) return;
  const domain = [["id", "in", ids]];
  const action = env.services.action;

  action.doAction({
    name: `${modelName}.filtered.list`,
    type: "ir.actions.act_window",
    res_model: modelName,
    view_mode: "list",
    views: [
      [listViewId || false, "list"],
      [false, "form"],
    ],
    domain: domain,
    target: "current",
  });
}
