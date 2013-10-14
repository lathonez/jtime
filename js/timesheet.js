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
		_t.timeentries,
		_t.user
	);
};

Timesheet.prototype._init = function(
	id,
	start_date,
	end_date,
	assignments,
	timeentries,
	user
) {
	this.id          = id;
	this.start_date  = start_date;
	this.end_date    = end_date;
	this.assignments = this._build_assignments(assignments);
	this.timeentries = this._build_timeentries(timeentries);
	this.user        = user;
};

Timesheet.prototype._build_assignments = function(assignments) {

	var as = [];

	$.each(assignments, function(i,a) {
		as.push(new Assignment(a));
	});

	return as;
};

// TODO - it probably makes sense to have these belong to assignments
//        then we can get rid of the assignment_attribute_id stuff from the timeentry objects
Timesheet.prototype._build_timeentries = function(timeentries) {

	var ts = [];

	$.each(timeentries, function(i,t) {
		ts.push(new Timeentry(t));
	});

	return ts;
};
