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

	var synced = false;

	// build our local data model
	this._get_timeentries();

	// update the entries
	synced = this._update_recorded_time();

	// check to see if we've got anything to update
	if (!synced) {
		// display the upload button
		$('#upload_button').attr('disabled',false);
	} else {
		// reflect that there's nothing to upload
		$('#upload_button').attr('value','In Sync');
	}
};

/*
 * Upload timeentries to 11rx
 */
jTime.prototype.upload = function () {

	var fn = 'jTime.upload: ',
	    obj = this,
	    p;

	$('#upload_button').attr('disabled',true);
	$('#upload_button').attr('value','Uploading..');

	// apply project time to the timeentries we're going to set
	for (var i = 0; i < this.projects.length; i++) {
		p = this.projects[i];

		// don't bother doing projects that are already in sync or don't have assingments
		if (p.synced || !p.assignment) {
			continue;
		}

		p.timeentry.time = this.er.convert_to_seconds(p.tenrox_time);
	}

	// fall into the callback to do the upload
	this._set_time_cb();
};

/*
 * Make requests to tenrox to set the time for each project
 *
 * This is called 'recursively', first from upload
 * then as a result of each further request sent herein
 *
 * _resp - response from tenrox (if recursing)
 * _project - project response applies to (if recursing)
 */
jTime.prototype._set_time_cb = function(_resp,_project) {

	var fn = 'jTime._set_time_cb: ',
	    obj = this,
	    sent = 0,
	    synced = false,
	    p;

	// base handling if it's not our first time in
	if (_resp !== undefined) {

		// reset the timeentry we've updated from 10rx
		_project.response = _resp;
		_project.set_timeentry(this._get_timeentry_for_project(_project));
		this._update_recorded_time();

		if (_resp.error) {
			console.log(fn + 'failed to set time for ' + _project.project);
			_project.request_failed = true;
		} else {
			console.log(fn + 'successfully set time for ' + _project.project);
		}
	}

	for (var i = 0; i < this.projects.length; i++) {

		p = this.projects[i];

		// we don't want to send projects that are already in sync or have no assignments
		if (p.synced || !p.assignment || p.request_failed) {
			sent++;
			continue;
		}

		this.er.set_timeentry(p.timeentry, function(_resp) {obj._set_time_cb(_resp,p)});

		// only send one project (for now..)
		break;
	}

	if (sent == this.projects.length) {
		// if we're not synced, enabled the button again
		if (!synced) {
			$('#upload_button').attr('disabled',false);
			$('#upload_button').attr('value','Upload');

			// unset request failed
			for (var i = 0; i < this.projects.length; i++) {
				this.projects[i].request_failed = false;
			}
		} else {
			// reflect that there's nothing to upload
			$('#upload_button').attr('value','In Sync');
		}
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
		p.set_timeentry(this._get_timeentry_for_project(p));
	}
};

/*
 * Get a timeentry for an individual project
 */
jTime.prototype._get_timeentry_for_project = function(_project) {

	var fn = 'jTime._get_timeentry_for_project: ',
	    as = this.er.get_assignment_by_name(_project.tenrox_code);

	if (!as) {
		console.log(fn + 'assignment not found for ' + _project.tenrox_code);
		return null;
	}

	if (as.length > 1) {
		console.log(fn + 'multiple assignments found for ' + _project.tenrox_code + ' not adding.');
		return null;
	}

	_project.assignment = as[0];

	return er.get_timeentry(_project.assignment,this.date);
};

/*
 * Apply the recorded (10rx) time in the model to the view
 *
 * Returns true if we're in sync with 10rx, else false
 */
jTime.prototype._update_recorded_time = function() {

	var overall = er.convert_to_tenrox_time(er.get_total_time_for_date(this.date)),
	    sync = true,
	    p, pt, pn;

	$('#overall_recorded').html(overall);

	for (var i = 0; i < this.projects.length; i++) {

		pt = 0;
		p = this.projects[i];
		pn = '#' + p.project + '_recorded';

		// don't display 0 if we've got no assignment
		if (!p.assignment) {
			pt = 'N/A';
		}

		if (p.timeentry) {
			pt = er.convert_to_tenrox_time(p.timeentry.time);
		}

		// we only count synchronisation for assignments that exist
		if (p.assignment && !p.synced) {
			sync = false;
		}

		$(pn).html(pt);
	}

	return sync;
};

