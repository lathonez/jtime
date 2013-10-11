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

	this._init(project, time, tenrox_code, tenrox_comment, tenrox_time);
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
}

