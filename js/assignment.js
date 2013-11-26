/*
 * Represents a project dict
 */

// constructor
function Project(
	assignment_name,
	project,
	time,
	tenrox_comment,
	tenrox_time,
	assignment_hash
) {
	this._init(
		assignment_name,
		project,
		time,
		tenrox_comment,
		tenrox_time,
		assignment_hash
	);
}

Project.prototype._init = function(
	assignment_name,
	project,
	time,
	tenrox_comment,
	tenrox_time,
	assignment_hash
) {
	this.assignment_name = assignment_name;
	this.project         = project;
	this.time            = time;
	this.tenrox_comment  = tenrox_comment;
	this.tenrox_time     = tenrox_time;
	this.assignment_hash = assignment_hash;
	this.assignment      = null;
	this.timeentry       = null;
	this.request_failed  = false;
	this.synced          = false;

	// we've already got the amount of time we're looking for
	// for this project in the timesheet
	this.time_full = false;
}

/*
 * Check to see whether the project's time matches the timeentries
 */
Project.prototype._check_sync = function() {

	if (!this.timeentry) {
		return false;
	}

	if (parseFloat(er.convert_to_tenrox_time(this.timeentry.time)) != parseFloat(this.tenrox_time)) {
		return false;
	}

	return true;
};

/*
 * Set the timeentry for this project
 */
Project.prototype.set_timeentry = function(_timeentry) {

	this.timeentry = _timeentry;
	this.synced = this._check_sync();
};
