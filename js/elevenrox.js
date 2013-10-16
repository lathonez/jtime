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

	this.ts = new Timesheet(_resp.result.timesheet);

	console.log(fn + 'timesheet retrieved successfully!');

	this._build_set_requests();
	this._set_time_cb();
};

/*
 * Make requests to tenrox to set the time for each project
 *
 * This is called 'recursively', first from _get_time_cb,
 * then as a result of each further request sent herein
 */
ElevenRox.prototype._set_time_cb = function(_resp) {

	var fn = 'ElevenRox._set_time_cb',
	    sent = 0,
	    not_sending = 0;

	for project in this.projects {

		// we weren't able to find a matching assignment for this project
		if (!this.project.request) {
			not_sending++;
			continue;
		}
		// we only care about stuff we've not sent yet
		if (this.project.request_sent) {
			sent++;
			continue;
		}

		project.request_sent = true;

		// TODO - can we pass the project object through here to only mark sent
		// when it has been successfully sent?
		this._send(project.request, function(_resp) {obj._set_time_cb(_resp)})

		// only send one project (for now..)
		break;
	}

	// confirm if we've sent everything we need to send
	if ((sent + not_sending) == this.projects.length) {
		console.log(fn + 'complete -');
		console.log(fn + 'not sent: ' + not_sending);
		console.log(fn + 'sent: ' + sent);
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

	var fn = 'ElevenRox._build_set_requests: ';

	// for each project, we need to find the appropriate assignment or timeentry (if available)
	for project in this.projects {

		project.assignment = this.timesheet.get_assignment(p.tenrox_code);

		if (!project.assignment) {
			console.log(fn + 'assignment not found for ' + p.tenrox_code);
			continue;
		}

		project.timeentry = project.assignment.get_timeentry(this.tenrox_date);
		project.request   = this._build_set_request(project);
	});
};

/*
 * Build a request object for a single project
 */
ElevenRox.prototype._build_set_request = function(_project) {

	var request = {};

    request.method = "set_time"
    request.params = {}
	request.params.assignment_id = _project.assignment.assignment_id;
	request.params.entry_id      = 0;
	request.params.entry_date    = this.tenrox_date;
	request.params.time          = this._convert_to_seconds(_project.tenrox_time);
	request.params.comment       = _project.comment;
	request.params.comment_id    = 0;

	// overwrite some stuff if we've already got an entry
	if (_project.timeentry) {
		request.params.entry_id   = _project.timeentry.entry_id;
		request.params.time      += _project.timeentry.time;

		// ammend existing comment if one exists
		comment = _project.timeentry.get_comment();
		request.params.comment_id = comment.comment_id;
		request.params.comment   += comment.comment;
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
		request.params.token = this.token;
	}

	if (this.timesheet_token) {
		request.params.timesheet_token = this.timesheet_token;
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
