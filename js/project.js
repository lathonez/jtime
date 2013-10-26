/*
 * Represents a project dict
 */

// constructor
function Project(
	project,
	time,
	tenrox_code,
	tenrox_comment,
	tenrox_time
) {
	this._init(
		project,
		time,
		tenrox_code,
		tenrox_comment,
		tenrox_time
	);
}

Project.prototype._init = function(
	project,
	time,
	tenrox_code,
	tenrox_comment,
	tenrox_time
) {
	this.project        = project;
	this.time           = time;
	this.tenrox_code    = tenrox_code;
	this.tenrox_comment = tenrox_comment;
	this.tenrox_time    = tenrox_time;
	this.assignment     = null;
	this.timeentry      = null;
	this.request_failed = false;
	this.synced         = false;

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

	if (parseInt(er.convert_to_tenrox_time(this.timeentry.time)) != parseInt(this.tenrox_time)) {
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
