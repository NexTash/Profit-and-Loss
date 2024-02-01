// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.require("assets/erpnext/js/financial_statements.js", function() {
	frappe.query_reports["Profit And Loss"] = $.extend({},
		erpnext.financial_statements);

	erpnext.utils.add_dimensions('Profit And Loss', 10);

	frappe.query_reports["Profit And Loss"]["filters"].push(
		{
			"fieldname": "include_default_book_entries",
			"label": __("Include Default Book Entries"),
			"fieldtype": "Check",
			"default": 1
		}
	);

	frappe.query_reports["Profit And Loss"]["filters"] = frappe.query_reports["Profit And Loss"]["filters"].filter(item => item.label != "Filter Based On")
});
