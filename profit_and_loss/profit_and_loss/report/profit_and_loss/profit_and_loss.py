# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_list,
)


def execute(filters=None):
	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		filters.periodicity,
		company=filters.company,
	)

	income = get_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)

	expense = get_data(
		filters.company,
		"Expense",
		"Debit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)
	net_profit_loss = get_net_profit_loss(
		income, expense, period_list, filters.company, filters.presentation_currency
	)
	columns = get_columns(
		filters.periodicity, period_list, filters.accumulated_values, filters.company
	)
	
	# column_name = "jun_2024"
	ordinary_income =  {'account': 'Ordinary Income/Expense'}
	direct_income = get_child_accounts(income, "Direct Income")
	cost_of_goods_sold = [row for row in expense if row.get("account_type") == "Cost of Goods Sold"]
	for row in cost_of_goods_sold:
		row.indent = direct_income[0].get("indent")

	gross_profit = {
		"account": "Gross Profit",
		'indent': 1.0,
	}

	for column_name in columns:
		column_name = column_name.get("fieldname")
		get_accounts_difference(direct_income[0], cost_of_goods_sold[0], column_name, gross_profit)

	direct_expense = get_child_accounts(expense, "Direct Expenses")
	net_direct_profit = {
		"account": "Net Ordinary Income",
		'indent': 1.0,
	}

	for column_name in columns:
		column_name = column_name.get("fieldname")
		get_accounts_difference(gross_profit, direct_expense[0], column_name, net_direct_profit)

	other_income =  {'account': 'Other Income/Expense'}
	indirect_income = get_child_accounts(income, "Indirect Income")
	indirect_expense = get_child_accounts(expense, "Indirect Expenses")
	net_indirect_profit = {
		"account": "Net Other Income",
		'indent': 1.0,
	}

	for column_name in columns:
		column_name = column_name.get("fieldname")
		get_accounts_difference(indirect_income[0], indirect_expense[0], column_name, net_indirect_profit)

	net_income = {
		"account": "Net Income",
		'indent': 0.0
	}

	for column_name in columns:
		column_name = column_name.get("fieldname")
		get_accounts_difference(net_direct_profit, net_indirect_profit, column_name, net_income)


	temp_data = []
	temp_data.append(ordinary_income)
	temp_data.extend(direct_income)
	temp_data.extend(cost_of_goods_sold)
	temp_data.append(gross_profit)
	temp_data.extend(direct_expense)
	temp_data.append(net_direct_profit)
	temp_data.append(other_income)
	temp_data.extend(indirect_income)
	temp_data.extend(indirect_expense)
	temp_data.append(net_indirect_profit)
	temp_data.append(net_income)

	data = []
	data.extend(income or [])
	data.extend(expense or [])
	
	data = temp_data

	return columns, data, None

	# if net_profit_loss:
	# 	data.append(net_profit_loss)

	# chart = get_chart_data(filters, columns, income, expense, net_profit_loss)

	# currency = filters.presentation_currency or frappe.get_cached_value(
	# 	"Company", filters.company, "default_currency"
	# )

	# report_summary = get_report_summary(
	# 	period_list, filters.periodicity, income, expense, net_profit_loss, currency, filters
	# )

	# return columns, data, None, chart, report_summary
	
def get_accounts_difference(account_1, account_2, column_name, result):
	try:
		if column_name in account_1 and column_name in account_2:
			result[column_name] = float(account_1[column_name]) - float(account_2[column_name])
	except ValueError:
		pass

def get_child_accounts(accounts, account):
	flag = False
	indent = None
	child_accounts = [] 
	for row in accounts:
		if indent and row.get("indent") == indent and row.get("account_name") != account:
			break

		if row.get("account_name") == account:
			flag = True
			indent = row.get("indent")
		
		if flag and row.get("account") and row.get("account") not in ["Total Income (Credit)", "Total Expense (Debit)"]:
			child_accounts.append(row)
	
	return child_accounts


def get_report_summary(
	period_list, periodicity, income, expense, net_profit_loss, currency, filters, consolidated=False
):
	net_income, net_expense, net_profit = 0.0, 0.0, 0.0

	# from consolidated financial statement
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	for period in period_list:
		key = period if consolidated else period.key
		if income:
			net_income += income[-2].get(key)
		if expense:
			net_expense += expense[-2].get(key)
		if net_profit_loss:
			net_profit += net_profit_loss.get(key)

	if len(period_list) == 1 and periodicity == "Yearly":
		profit_label = _("Profit This Year")
		income_label = _("Total Income This Year")
		expense_label = _("Total Expense This Year")
	else:
		profit_label = _("Net Profit")
		income_label = _("Total Income")
		expense_label = _("Total Expense")

	return [
		{"value": net_income, "label": income_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "-"},
		{"value": net_expense, "label": expense_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "=", "color": "blue"},
		{
			"value": net_profit,
			"indicator": "Green" if net_profit > 0 else "Red",
			"label": profit_label,
			"datatype": "Currency",
			"currency": currency,
		},
	]


def get_net_profit_loss(income, expense, period_list, company, currency=None, consolidated=False):
	total = 0
	net_profit_loss = {
		"account_name": "'" + _("Profit for the year") + "'",
		"account": "'" + _("Profit for the year") + "'",
		"warn_if_negative": True,
		"currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
	}

	has_value = False

	for period in period_list:
		key = period if consolidated else period.key
		total_income = flt(income[-2][key], 3) if income else 0
		total_expense = flt(expense[-2][key], 3) if expense else 0

		net_profit_loss[key] = total_income - total_expense

		if net_profit_loss[key]:
			has_value = True

		total += flt(net_profit_loss[key])
		net_profit_loss["total"] = total

	if has_value:
		return net_profit_loss


def get_chart_data(filters, columns, income, expense, net_profit_loss):
	labels = [d.get("label") for d in columns[2:]]

	income_data, expense_data, net_profit = [], [], []

	for p in columns[1:]:
		if income:
			income_data.append(income[-2].get(p.get("fieldname")))
		if expense:
			expense_data.append(expense[-2].get(p.get("fieldname")))
		if net_profit_loss:
			net_profit.append(net_profit_loss.get(p.get("fieldname")))

	datasets = []
	if income_data:
		datasets.append({"name": _("Income"), "values": income_data})
	if expense_data:
		datasets.append({"name": _("Expense"), "values": expense_data})
	if net_profit:
		datasets.append({"name": _("Net Profit/Loss"), "values": net_profit})

	chart = {"data": {"labels": labels, "datasets": datasets}}

	if not filters.accumulated_values:
		chart["type"] = "bar"
	else:
		chart["type"] = "line"

	chart["fieldtype"] = "Currency"

	return chart
