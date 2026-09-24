/**  @odoo-module **/
import {
  formatCurrency,
  getDateRange,
} from "@cyllo_commission/js/summary_cards";

export function getLeaderBoardData(commissions, sortBy) {
  const grouped = {};
  commissions.forEach((com) => {
    const key = com.salesperson_id;
    if (!grouped[key]) {
      grouped[key] = {
        id: key,
        name: com.salesperson,
        commission: 0,
        sale: 0,
        _countedOrderIds: new Set(),
        _countedCommissionIds: new Set(),
      };
    }
    const salespersonData = grouped[key];
    salespersonData.commission += com.commission_amount || 0;
    let orderIds = [];
    if (Array.isArray(com.sale_order_ids) && com.sale_order_ids.length) {
      orderIds = com.sale_order_ids;
    } else if (com.sale_order_id) {
      orderIds = [com.sale_order_id];
    }
    const saleAmount = com.sale_amount || 0;
    if (orderIds.length > 0) {
      const perOrder = saleAmount / orderIds.length;
      orderIds.forEach((oid) => {
        if (!salespersonData._countedOrderIds.has(oid)) {
          salespersonData._countedOrderIds.add(oid);
          salespersonData.sale += perOrder;
        }
      });
    } else {
      const commKey = com.id || `${com.plan_id || ""}-${com.period_name || ""}-${saleAmount}`;
      if (!salespersonData._countedCommissionIds.has(commKey)) {
        salespersonData._countedCommissionIds.add(commKey);
        salespersonData.sale += saleAmount;
      }
    }
  });
  const sorted = Object.values(grouped)
    .map(({ _countedOrderIds, _countedCommissionIds, ...rest }) => rest) // remove helper sets
    .sort((a, b) => b[sortBy] - a[sortBy])
    .slice(0, 5)
    .map((item, index) => ({ ...item, rank: index + 1 }));
  return sorted;
}

export function leaderBoard(
  target,
  commissions,
  formatCurrency,
  currencySymbol,
  currencyPosition,
  sort
) {
  if (!target) return;
  const leaderBoard = target.querySelector("#leaderboard-body");
  if (!leaderBoard) return;

  leaderBoard.innerHTML = "";

  const leaderBoardData = getLeaderBoardData(commissions, sort);

  if (leaderBoardData.length) {
    leaderBoardData.forEach((person) => {
      const row = document.createElement("tr");
      row.className = "leaderboard-row";
      row.innerHTML = `
      <td>
        <div class="rank rank-${person.rank}">
          <div class="rank-badge">${person.rank}</div>
        </div>
      </td>
      <td class="salesperson">${person.name}</td>
      <td>${formatCurrency(person.sale, currencySymbol, currencyPosition)}</td>
      <td class="commission">${formatCurrency(
        person.commission,
        currencySymbol,
        currencyPosition
      )}</td>
    `;

      leaderBoard.appendChild(row);
    });
  } else {
    leaderBoard.innerHTML = `
                <tr class="no-data-row">
                    <td class="no-data-cell" colspan="4">
                        <svg class="no-data-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                        <div class="no-data-title">No data available</div>
                        <div class="no-data-message">There are currently no sales representatives to display.</div>
                    </td>
                </tr>
            `;
  }
}