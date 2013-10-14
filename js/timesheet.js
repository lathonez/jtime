/*
 * Represents a timesheet returned from elevenrox
 */

/*
 * _t - raw timesheet json
 */
function Timesheet(_t) {

	this._init(
		_t.uid,
		_t.start_date,
		_t.end_date,
		_t.assignments,
		_t.user
	);
};

Timesheet.prototype._init = function(
	id,
	start_date,
	end_date,
	assignments,
	user
) {
	this.id          = id;
	this.start_date  = start_date;
	this.end_date    = end_date;
	this.assignments = this._build_assignments(assignments);
	this.user        = user;
};

Timesheet.prototype._build_assignments = function(assignments) {

	var as = [];

	if (assignments === undefined) {
		return as;
	}

	$.each(assignments, function(i,a) {
		as.push(new Assignment(a));
	});

	return as;
};

