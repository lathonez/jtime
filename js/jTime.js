/*
 * jTime controller
 */
function jTime(
	_er,
	_projects,
	_date
) {
	this._init(_er,_projects,_date);
};

/*
 * _er - ElevenRox instance
 */
jTime.prototype._init = function(_er,_projects,_date) {

	var obj = this,
	    cb;

	obj.er       = _er;
	obj.projects = _projects;
	obj.date     = _date;

	cb = function() {
		obj.er_init_cb();
	}

	er.init(obj.date,cb);
};

/*
 * called after ElevenRox has initialised
 */
jTime.prototype.er_init_cb = function() {

	// build our local data model
	this._get_timeentries();

	// update the entries
	this._update_recorded_time();

	// display the upload button
	$('#upload_button').attr('disabled',false);
};

/*
 * Upload timeentries to 11rx
 */
jTime.prototype.upload = function () {

	var fn = 'jTime.upload: ',
	    obj = this;


};

/*
 * Make requests to tenrox to set the time for each project
 *
 * This is called 'recursively', first from _get_time_cb,
 * then as a result of each further request sent herein
 *
 * _resp - response from tenrox (if recursing)
 * _project - project response applies to (if recursing)
 */
jTime.prototype._set_time_cb = function(_resp,_project) {

	var fn = 'jTime._set_time_cb: ',
	    sent = 0,
	    not_sending = 0,
	    failed = 0,
	    obj = this,
	    p;

	// base handling if it's not our first time in
	if (_resp !== undefined) {

		// keep track of the response for each project
		_project.response = _resp;

		if (!this._resp_landing(_resp)) {
			console.log(fn + 'failed to set time for ' + _project.project);
			_project.request_failed = true;
		} else {
			console.log(fn + 'successfully set time for ' + _project.project);
			// update the local data model to reflect the update
			this.timesheet.set(_resp.result.timesheet);
		}
	}

	for (var i = 0; i < this.projects.length; i++) {

		p = this.projects[i];

		// we weren't able to find a matching assignment for this project
		// or the time for the project was already full
		if (!p.request) {
			not_sending++;
			continue;
		}
		// keep a failed counter (we've already sent this)
		if (p.request_failed) {
			sent++;
			failed++;
			continue;
		}
		// we only care about stuff we've not sent yet
		if (p.request_sent) {
			sent++;
			continue;
		}

		p.request_sent = true;

		this._send(p.request, function(_resp) {obj._set_time_cb(_resp,p)})

		// only send one project (for now..)
		break;
	}

	// confirm if we've sent everything we need to send
	if ((sent + not_sending) == this.projects.length) {
		console.log(fn + 'not sent: ' + not_sending);
		console.log(fn + 'sent: ' + sent);
		console.log(fn + 'faled: ' + failed);
	}
};

/*
 * Assign a timeentry to each project (where possible)
 */
jTime.prototype._get_timeentries = function() {

	var fn = 'jTime._build_set_requests: ',
	    p, as;

	// for each project, we need to find the appropriate assignment or timeentry (if available)
	for (var i = 0; i < this.projects.length; i++) {

		p  = this.projects[i];
		as = this.er.get_assignment_by_name(p.tenrox_code);

		if (!as) {
			console.log(fn + 'assignment not found for ' + p.tenrox_code);
			continue;
		}

		if (as.length > 1) {
			console.log(fn + 'multiple assignments found for ' + p.tenrox_code + ' not adding.');
			continue;
		}

		p.assignment = as[0];
		p.timeentry  = er.get_timeentry(p.assignment,this.date);
	}
};

/*
 * Apply the recorded (10rx) time in the model to the view
 */
jTime.prototype._update_recorded_time = function() {

	var overall = er.convert_to_tenrox_time(er.get_total_time_for_date(this.date)),
	    p, pt, pn;

	$('#overall_recorded').html(overall);

	for (var i = 0; i < this.projects.length; i++) {

		pt = 0;
		p = this.projects[i];
		pn = '#' + p.project + '_recorded';

		if (p.timeentry) {
			pt = er.convert_to_tenrox_time(p.timeentry.time);
		}
		$(pn).html(pt);
	}
};

