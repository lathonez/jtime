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
	request.params.token = this.token;
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
 * _req      - request object to send to elevenrox
 * _callback - callback function which should be exectued after the standard handler
 */
ElevenRox.prototype._send = function (_req, _callback) {

	_req.id = this.request_id++;

	// make the request
	jQuery.post(this.url, JSON.stringify(_req), _callback, "json");
};
