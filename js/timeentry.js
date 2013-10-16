/*
 * Represents a timeentry returned from elevenrox
 */

/*
 * _t - raw timeentry json
 */
function Timeentry(_t) {

	this._init(
		_t.entry_id,
		_t.assignment_id,
		_t.assignment_attribute_id,
		_t.buid,
		_t.bun,
		_t.entry_date,
		_t.time,
		_t.notes,
		_t.task_id
	);
};

Timeentry.prototype._init = function(
	id,
	as_id,
	as_attribute_id,
	buid,
	bun,
	entry_date,
	time,
	comments,
	task_id
) {
	this.id              = id;
	this.as_id           = as_id;
	this.as_attribute_id = as_attribute_id;
	this.buid            = buid;
	this.bun             = bun;
	this.entry_date      = entry_date;
	this.time            = time;
	this.comments        = comments;
	this.task_id         = task_id;
};

/*
 * Currently we only support one comment
 *
 * Returns null if no comment exists
 */
Timeentry.prototype._get_comment = function() {

	if (!this.comments.length) {
		return null;
	}

	return this.comments[0];
};
