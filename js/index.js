/*
 * Returns yesterday in dd/mm/yyyy
 */
function yesterday() {

	var date = new Date(),
		d, m, y;

	date.setDate(date.getDate() - 1)

	d = ("00" + date.getDate()).slice (-2);
	m = ("00" + (date.getMonth()+1)).slice (-2);
	y = date.getFullYear();

	return d + '/' + m + '/' + y;
}

function do_submit() {
	var tenrox_user   = $('#t_username').val(),
		tenrox_pass   = $('#t_password').val(),
		do_submit, er, loc;

	// disable the button
	$('submit_button').disabled = true;

	// bit of a hack, we should probably do this server side
	er = new ElevenRox(
		tenrox_user,
		tenrox_pass,
		elevenrox_url
	);

	do_submit_final = function(_resp) {
		// if we've logged in successfully, submit
		if (er.token) {
			$('#tenrox_token').val(er.token);
			if($('#remember').is(':checked')) {
				set_cookie();
			}
			$('#frm').submit();
		} else{
			// we've got some error, find what it is and report it
			if (_resp.error.code < 30000) {
				loc = '/' + url + 'msg=HTTP_ELEVENROX';
			}

			if (_resp.error.code == -32001 && _resp.error.data.search('Invalid username or password') > -1) {
				loc = '/' + url + 'msg=BAD_T_USER';
			}

			// dunno what the problem is
			if (typeof loc === undefined) {
				loc = '/' + url + 'msg=UNKNOWN';
			}

			window.location.href = loc;
		}
	};

	er.login(do_submit_final);
	start_progress();
}

function start_progress() {
	progress = 0;
	$(".dial").knob();
	$('#knob').css('display','block');
	progress_forever();
}

function progress_forever() {

	if (progress == 100) {
		progress = 0;
	} else {
		progress++;
	}

	$('.dial')
		.val(progress)
		.trigger('change');

	setTimeout(progress_forever, 175);
}

function fill_from_cookie() {

	var fn = 'fill_from_cookie: ',
	    raw = $.cookie(login_cookie_name),
	    spl;

	if (typeof raw == "undefined") {
		console.log(fn + 'cookie not found');

		// clear by default (opt-in)
		$('#remember').attr('checked',false);
		return;
	}

	spl = raw.split("|");

	if (spl.length != 5) {
		console.log(fn + 'invalid cookie format');
	}

	$('#j_username').val(spl[0]);
	$('#j_password').val(spl[1]);
	$('#t_username').val(spl[2]);
	$('#t_password').val(spl[3]);

	if (spl[4] == "true") {
		$('#find_codes').attr('checked',true);
	} else {
		$('#find_codes').attr('checked',false);
	}
}

function set_cookie() {

	var cookie_val = '';

	cookie_val += $('#j_username').val() + '|';
	cookie_val += $('#j_password').val() + '|';
	cookie_val += $('#t_username').val() + '|';
	cookie_val += $('#t_password').val() + '|';
	cookie_val += $('#find_codes').is(':checked');

	$.cookie(login_cookie_name, cookie_val, {
		expires: 365,
		path:    '/',
		domain: document.domain,
		secure: true
	});
}

