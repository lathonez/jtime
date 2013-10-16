/*
 * Handles integration with ElevenRox
 */

function ElevenRox(
	projects,
	tenrox_date,
	username,
	password,
	url
) {

	this._init(
		projects,
		tenrox_date,
		username,
		password,
		url
	);

};

ElevenRox.prototype._init = function(
	projects,
	tenrox_date,
	username,
	password,
	url
) {
	this.projects    = projects;
	this.tenrox_date = tenrox_date;
	this.username    = username;
	this.password    = password;
	this.url         = url;
	this.token       = null;
	this.request_id  = 0;
};

ElevenRox.prototype.upload = function () {

	var fn = 'ElevenRox.upload: ';

	console.log(fn + 'uploading..');

	this._login();
};

ElevenRox.prototype._login = function () {

	var request = {},
	    obj = this;

	request.method = "login";
	request.params = {};
	request.params.username = this.username;
	request.params.password = this.password;


	this._send(request,function(_resp) { obj._login_cb(_resp) });

};

ElevenRox.prototype._login_cb = function (_resp) {

	var fn = 'ElevenRox._login_cb: ';

	if (!this._resp_landing(_resp)){

		console.log(fn + 'login failed!');
		return;
	}

	console.log(fn + 'login successful!');

	// now we're logged in we can go get the timesheet
	this._get_time();
};

ElevenRox.prototype._get_time = function () {

	var request = {},
	    obj = this;

	request.method = "get_time";
	request.params = {};
	request.params.start_date = this.tenrox_date;

	this._send(request,function(_resp) { obj._get_time_cb(_resp) });

};

ElevenRox.prototype._get_time_cb = function (_resp) {

	var fn = 'ElevenRox._get_time_cb: ';

	if (!this._resp_landing(_resp)){

		console.log(fn + 'failed to retrieve timesheet!');
		return;
	}

	this.timesheet = new Timesheet(_resp.result.timesheet);

	console.log(fn + 'timesheet retrieved successfully!');

	this._build_set_requests();
	this._set_time_cb();
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
ElevenRox.prototype._set_time_cb = function(_resp,_project) {

	var fn = 'ElevenRox._set_time_cb: ',
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
		}
	}

	for (var i = 0; i < this.projects.length; i++) {

		p = this.projects[i];

		// we weren't able to find a matching assignment for this project
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
 * Should be invoked from callback overrides, will set standard globals up (timesheet token etc)
 *
 * Returns true if request was succesfull (in elevenrox), else false
 */
ElevenRox.prototype._resp_landing = function (_resp) {

	var fn = 'ElevenRox._resp_landing: ';

	console.log(_resp);

	if (_resp.error) {

		err_string = fn + 'request failed: '

		for (var key in _resp.error) {
			err_string += key + '- ' + eval('_resp.error.' + key) + ' ';
		}

		console.log(err_string);

		return false;
	} else {
		// all successful responses from 11rx should return a token - need to keep it updated
		this.token = _resp.result.token;

		if (_resp.result.timesheet_token !== undefined) {
			this.timesheet_token = _resp.result.timesheet_token;
		}

		return true;
	}
};

/*
 * Build a request object for every set we want to send, adding to each project
 */
ElevenRox.prototype._build_set_requests = function() {

	var fn = 'ElevenRox._build_set_requests: ',
	    p;

	// for each project, we need to find the appropriate assignment or timeentry (if available)
	for (var i = 0; i < this.projects.length; i++) {

		p = this.projects[i];

		p.assignment = this.timesheet.get_assignment(p.tenrox_code);

		if (!p.assignment) {
			console.log(fn + 'assignment not found for ' + p.tenrox_code);
			continue;
		}

		p.timeentry = p.assignment.get_timeentry(this.tenrox_date);
		p.request   = this._build_set_request(p);
	}
};

/*
 * Build a request object for a single project
 */
ElevenRox.prototype._build_set_request = function(_project) {

	var request = {};

    request.method = "set_time"
    request.params = {}
	request.params.assignment_id = _project.assignment.id;
	request.params.entry_id      = 0;
	request.params.entry_date    = this.tenrox_date;
	request.params.time          = this._convert_to_seconds(_project.tenrox_time);
	request.params.comment       = _project.tenrox_comment;
	request.params.comment_id    = 0;

	// overwrite some stuff if we've already got an entry
	// this is safer than additive (in terms of time), should this be run multiple times
	if (_project.timeentry) {
		request.params.entry_id   = _project.timeentry.id;
		request.params.time       = _project.timeentry.time;

		// use existing comment id (don't create a tab).
		comment = _project.timeentry.get_comment();
		request.params.comment_id = comment.uid;
		request.params.comment    = comment.d;
	}

	return request;
};

/*
 * _req      - request object to send to elevenrox
 * _callback - callback function which should be exectued after the standard handler
 */
ElevenRox.prototype._send = function (_req, _callback) {

	_req.id = this.request_id++;

	// add tokens to request
	if (this.token) {
		_req.params.token = this.token;
	}

	if (this.timesheet_token) {
		_req.params.timesheet_token = this.timesheet_token;
	}

	// make the request
	jQuery.post(this.url, JSON.stringify(_req), _callback, "json");
};

/*
 * convert a tenrox time field (e.g. 1.5) to a number of seconds
 */
ElevenRox.prototype._convert_to_seconds = function(_tenrox_time) {

	var minutes = 60 * _tenrox_time,
	    seconds = 60 * minutes;

	return seconds;
};
