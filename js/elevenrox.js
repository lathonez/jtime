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
};

ElevenRox.prototype.upload = function () {

	var fn = 'ElevenRox.upload: ';

	console.log(fn + 'uploading..');

	this._login();
};

ElevenRox.prototype._login = function () {

	var request = {};

	request.method = "login";
	request.params = {};
	request.params.username = this.username;
	request.params.password = this.password;

	request.id = 1;

	this._send(request);

};

ElevenRox.prototype._handle = function (_resp) {

	console.log(_resp);
};

ElevenRox.prototype._send = function (_req) {

	var obj = this;

	// make the request
	jQuery.post(this.url, JSON.stringify(_req), obj._handle, "json");
};
