/** @odoo-module **/
import { getDateRange, shiftMonth } from "@cyllo_commission/js/summary_cards";

export const filterByPlanType = (data, planType) => {
  if (planType === "all") return data;

  return {
    ...data,
    plans: data.plans.filter((plan) => plan.type === planType),
    commissions: data.commissions.filter((com) => com.plan_type === planType),
    leaderboardCommissions:
      data.leaderboardCommissions?.filter(
        (com) => com.plan_type === planType
      ) || data.commissions.filter((com) => com.plan_type === planType),
  };
};

export const filterByTeam = (data, teamIds) => {
  if (teamIds.length === 0 || (teamIds.length === 1 && teamIds[0] === "0")) {
    return data;
  }

  const filteredTeamMembers = data.team_members.filter((member) =>
    teamIds.includes(String(member.team_id))
  );
  const teamMemberUserIds = filteredTeamMembers.map((member) => member.user_id);
  const filteredSaleOrders = data.sale_orders.filter((order) =>
    teamIds.includes(String(order.team_id))
  );
  const filteredOrderLines = data.orderlines.filter((line) =>
    teamIds.includes(String(line.team_id))
  );
  const teamOrders = filteredSaleOrders.map((order) => order.id);

  const filterCommissions = (comms) =>
    comms.filter((com) => {
      const singleId = com.sale_order_id;
      const multipleIds = com.sale_order_ids || [];
      return (
        teamOrders.includes(singleId) ||
        multipleIds.some((id) => teamOrders.includes(id))
      );
    });

  const planIds = new Set(
    filterCommissions(data.commissions).map((plan) => plan.plan_id)
  );
  const filteredPlans = data.plans.filter((plan) => planIds.has(plan.id));
  const filteredCustomers = data.customers.filter((cus) =>
    teamIds.includes(String(cus.team_id))
  );
  const filteredWonOpportunities = data.won_opportunities.filter((opp) =>
    teamIds.includes(String(opp.team_id))
  );
  const filteredOpportunities = data.opportunities.filter((opp) =>
    teamIds.includes(String(opp.team_id))
  );

  return {
    ...data,
    team_members: filteredTeamMembers,
    sale_orders: filteredSaleOrders,
    orderlines: filteredOrderLines,
    commissions: filterCommissions(data.commissions),
    plans: filteredPlans,
    customers: filteredCustomers,
    won_opportunities: filteredWonOpportunities,
    opportunities: filteredOpportunities,
    leaderboardCommissions: filterCommissions(
      data.leaderboardCommissions || data.commissions
    ),
  };
};

export const filterByUser = (data, userIds) => {
  if (userIds.length === 0 || (userIds.length === 1 && userIds[0] === "0")) {
    return data;
  }

  const filteredSaleOrders = data.sale_orders.filter((order) =>
    userIds.includes(String(order.user_id))
  );
  const filteredTeamMembers = data.team_members.filter((member) =>
    userIds.includes(String(member.user_id))
  );
  const filteredOrderLines = data.orderlines.filter((line) =>
    userIds.includes(String(line.user_id))
  );
  const userOrders = filteredSaleOrders.map((order) => order.id);

  const filterCommissions = (comms) =>
    comms.filter((com) => {
      const singleId = com.sale_order_id;
      const multipleIds = com.sale_order_ids || [];
      return (
        userOrders.includes(singleId) ||
        multipleIds.some((id) => userOrders.includes(id))
      );
    });

  const planIds = new Set(
    filterCommissions(data.commissions).map((plan) => plan.plan_id)
  );
  const filteredPlans = data.plans.filter((plan) => planIds.has(plan.id));
  const filteredCustomers = data.customers.filter((cus) =>
    userIds.includes(String(cus.user_id))
  );
  const filteredWonOpportunities = data.won_opportunities.filter((opp) =>
    userIds.includes(String(opp.user_id))
  );
  const filteredOpportunities = data.opportunities.filter((opp) =>
    userIds.includes(String(opp.user_id))
  );

  return {
    ...data,
    sale_orders: filteredSaleOrders,
    team_members: filteredTeamMembers,
    orderlines: filteredOrderLines,
    commissions: filterCommissions(data.commissions),
    won_opportunities: filteredWonOpportunities,
    opportunities: filteredOpportunities,
    plans: filteredPlans,
    leaderboardCommissions: filterCommissions(
      data.leaderboardCommissions || data.commissions
    ),
  };
};

export const filterByDatePeriod = (data, period) => {
  if (!period) return data;

  const { startDate, endDate } = getDateRange(period);
  const start = new Date(startDate);
  const end = new Date(endDate);

  const filterByDateRange = (items, dateField) =>
    items.filter((item) => {
      const date = new Date(item[dateField]);
      return date >= start && date <= end;
    });

  const filterCommissions = (comms) =>
    comms.filter((c) => {
      const from = new Date(c.date_from);
      const to = new Date(c.date_to);
      return from <= end && to >= start;
    });

  const filteredCustomers = data.customers.filter((cus) => {
    const date = new Date(cus.create_date);
    return date >= start && date <= end;
  });

  const filteredOpportunities = data.opportunities.filter((opp) => {
    const date = new Date(opp.stage_update_date);
    return date >= start && date <= end;
  });
  const filteredWonOpportunities = data.won_opportunities.filter((opp) => {
    const date = new Date(opp.stage_update_date);
    return date >= start && date <= end;
  });

  const planIds = new Set(
    filterCommissions(data.commissions).map((plan) => plan.plan_id)
  );
  const filteredPlans = data.plans.filter((plan) => planIds.has(plan.id));

  return {
    ...data,
    commissions: filterCommissions(data.commissions),
    plans: filteredPlans,
    customers: filteredCustomers,
    won_opportunities: filteredWonOpportunities,
    opportunities: filteredOpportunities,
    leaderboardCommissions: filterCommissions(
      data.leaderboardCommissions || data.commissions
    ),
    sale_orders: filterByDateRange(data.sale_orders, "date"),
    orderlines: filterByDateRange(data.orderlines, "date"),
  };
};

export const applyNonManagerFilters = (
  filteredData,
  userId,
  teamsIds,
  data
) => {
  const {
    salespeople,
    team_members,
    teams,
    sale_orders,
    orderlines,
    plans,
    commissions,
  } = filteredData;
  const { orderlines: allOrderlines, commissions: allCommissions } = data;
  const filteredSalespeople = salespeople.filter((user) => user.id === userId);
  const filteredTeamMembers = team_members.filter(
    (user) => user.user_id === userId
  );
  const teamIds = filteredTeamMembers.map((team) => team.team_id);
  const filteredTeams = teams.filter((team) => teamIds.includes(team.id));
  let filteredSaleOrders = [];
  let filteredOrderLines = [];
  let filteredPlans = [];
  let filteredCommissions = [];
  let filteredCustomers = [];
  let filteredWonOpportunities = [];
  let filteredOpportunities = [];
  let filteredLeaderboardCommissions = [];
  if (
    teamsIds.length === 0 ||
    (teamsIds.length === 1 && Object.values(teamsIds)[0] === "0")
  ) {
    filteredSaleOrders = sale_orders.filter(
      (order) => order.user_id === userId && teamIds.includes(order.team_id)
    );
    filteredOrderLines = orderlines.filter(
      (line) => line.user_id === userId && teamIds.includes(line.team_id)
    );
    filteredPlans = plans.filter((plan) => plan.salespeople.includes(userId));
    filteredCommissions = commissions.filter(
      (com) => com.salesperson_id === userId
    );
    const teamOrderLines = allOrderlines.filter((line) =>
      teamIds.includes(line.team_id)
    );
    const teamOrderLineIds = teamOrderLines.map((line) => line.id);
    filteredLeaderboardCommissions = allCommissions.filter((com) =>
      com.sale_orderline_ids.some((id) => teamOrderLineIds.includes(id))
    );
  } else {
    const numericTeamIds = Object.values(teamsIds).map(Number);

    filteredSaleOrders = sale_orders.filter(
      (order) =>
        order.user_id === userId && numericTeamIds.includes(order.team_id)
    );
    filteredOrderLines = orderlines.filter(
      (line) => line.user_id === userId && numericTeamIds.includes(line.team_id)
    );
    const orderLineIds = filteredOrderLines.map((line) => line.id);
    filteredCommissions = commissions.filter(
      (com) =>
        com.salesperson_id === userId &&
        com.sale_orderline_ids.some((id) => orderLineIds.includes(id))
    );
    const teamOrderLines = allOrderlines.filter((line) =>
      numericTeamIds.includes(line.team_id)
    );
    const teamOrderLineIds = teamOrderLines.map((line) => line.id);
    filteredLeaderboardCommissions = allCommissions.filter((com) =>
      com.sale_orderline_ids.some((id) => teamOrderLineIds.includes(id))
    );
    const commissionIds = filteredCommissions.map((com) => com.plan_id);
    filteredPlans = plans.filter(
      (plan) =>
        plan.salespeople.includes(userId) && commissionIds.includes(plan.id)
    );
  }
  return {
    salespeople: filteredSalespeople,
    team_members: filteredTeamMembers,
    teams: filteredTeams,
    sale_orders: filteredSaleOrders,
    orderlines: filteredOrderLines,
    plans: filteredPlans,
    commissions: filteredCommissions,
    leaderboardCommissions: filteredLeaderboardCommissions,
    teamId: filteredTeams.length === 1 ? teamIds[0] : 0,
  };
};
