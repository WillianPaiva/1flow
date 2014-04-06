/**
 * Require the module at `name`.
 *
 * @param {String} name
 * @return {Object} exports
 * @api public
 */

function require(name) {
  var module = require.modules[name];
  if (!module) throw new Error('failed to require "' + name + '"');

  if (module.definition) {
    module.client = module.component = true;
    module.definition.call(this, module.exports = {}, module);
    delete module.definition;
  }

  return module.exports;
}

/**
 * Registered modules.
 */

require.modules = {};

/**
 * Register module at `name` with callback `definition`.
 *
 * @param {String} name
 * @param {Function} definition
 * @api private
 */

require.register = function (name, definition) {
  require.modules[name] = {
    definition: definition
  };
};

/**
 * Define a module's exports immediately with `exports`.
 *
 * @param {String} name
 * @param {Generic} exports
 * @api private
 */

require.define = function (name, exports) {
  require.modules[name] = {
    exports: exports
  };
};

require.register("eivindfjeldstad~scrollbar-size@master", function (exports, module) {
/**
 * Scrollbar size detection.
 */

var div = document.createElement('div');

div.style.width = '50px';
div.style.height = '50px';
div.style.overflow = 'scroll';
div.style.position = 'absolute';
div.style.top = '-9999px';

document.body.appendChild(div);
var size = div.offsetWidth - div.clientWidth;
document.body.removeChild(div);

module.exports = size;

});

require.register("component~event@0.1.3", function (exports, module) {
var bind = window.addEventListener ? 'addEventListener' : 'attachEvent',
    unbind = window.removeEventListener ? 'removeEventListener' : 'detachEvent',
    prefix = bind !== 'addEventListener' ? 'on' : '';

/**
 * Bind `el` event `type` to `fn`.
 *
 * @param {Element} el
 * @param {String} type
 * @param {Function} fn
 * @param {Boolean} capture
 * @return {Function}
 * @api public
 */

exports.bind = function(el, type, fn, capture){
  el[bind](prefix + type, fn, capture || false);
  return fn;
};

/**
 * Unbind `el` event `type`'s callback `fn`.
 *
 * @param {Element} el
 * @param {String} type
 * @param {Function} fn
 * @param {Boolean} capture
 * @return {Function}
 * @api public
 */

exports.unbind = function(el, type, fn, capture){
  el[unbind](prefix + type, fn, capture || false);
  return fn;
};
});

require.register("component~query@0.0.3", function (exports, module) {
function one(selector, el) {
  return el.querySelector(selector);
}

exports = module.exports = function(selector, el){
  el = el || document;
  return one(selector, el);
};

exports.all = function(selector, el){
  el = el || document;
  return el.querySelectorAll(selector);
};

exports.engine = function(obj){
  if (!obj.one) throw new Error('.one callback required');
  if (!obj.all) throw new Error('.all callback required');
  one = obj.one;
  exports.all = obj.all;
  return exports;
};


});

require.register("component~matches-selector@0.1.2", function (exports, module) {
/**
 * Module dependencies.
 */

var query = require("component~query@0.0.3");

/**
 * Element prototype.
 */

var proto = Element.prototype;

/**
 * Vendor function.
 */

var vendor = proto.matches
  || proto.webkitMatchesSelector
  || proto.mozMatchesSelector
  || proto.msMatchesSelector
  || proto.oMatchesSelector;

/**
 * Expose `match()`.
 */

module.exports = match;

/**
 * Match `el` to `selector`.
 *
 * @param {Element} el
 * @param {String} selector
 * @return {Boolean}
 * @api public
 */

function match(el, selector) {
  if (vendor) return vendor.call(el, selector);
  var nodes = query.all(selector, el.parentNode);
  for (var i = 0; i < nodes.length; ++i) {
    if (nodes[i] == el) return true;
  }
  return false;
}

});

require.register("discore~closest@0.1.2", function (exports, module) {
var matches = require("component~matches-selector@0.1.2")

module.exports = function (element, selector, checkYoSelf, root) {
  element = checkYoSelf ? {parentNode: element} : element

  root = root || document

  // Make sure `element !== document` and `element != null`
  // otherwise we get an illegal invocation
  while ((element = element.parentNode) && element !== document) {
    if (matches(element, selector))
      return element
    // After `matches` on the edge case that
    // the selector matches the root
    // (when the root is not the document)
    if (element === root)
      return
  }
}
});

require.register("component~delegate@0.2.1", function (exports, module) {
/**
 * Module dependencies.
 */

var closest = require("discore~closest@0.1.2")
  , event = require("component~event@0.1.3");

/**
 * Delegate event `type` to `selector`
 * and invoke `fn(e)`. A callback function
 * is returned which may be passed to `.unbind()`.
 *
 * @param {Element} el
 * @param {String} selector
 * @param {String} type
 * @param {Function} fn
 * @param {Boolean} capture
 * @return {Function}
 * @api public
 */

exports.bind = function(el, selector, type, fn, capture){
  return event.bind(el, type, function(e){
    var target = e.target || e.srcElement;
    e.delegateTarget = closest(target, selector, true, el);
    if (e.delegateTarget) fn.call(el, e);
  }, capture);
};

/**
 * Unbind event `type`'s callback `fn`.
 *
 * @param {Element} el
 * @param {String} type
 * @param {Function} fn
 * @param {Boolean} capture
 * @api public
 */

exports.unbind = function(el, type, fn, capture){
  event.unbind(el, type, fn, capture);
};

});

require.register("component~events@1.0.6", function (exports, module) {

/**
 * Module dependencies.
 */

var events = require("component~event@0.1.3");
var delegate = require("component~delegate@0.2.1");

/**
 * Expose `Events`.
 */

module.exports = Events;

/**
 * Initialize an `Events` with the given
 * `el` object which events will be bound to,
 * and the `obj` which will receive method calls.
 *
 * @param {Object} el
 * @param {Object} obj
 * @api public
 */

function Events(el, obj) {
  if (!(this instanceof Events)) return new Events(el, obj);
  if (!el) throw new Error('element required');
  if (!obj) throw new Error('object required');
  this.el = el;
  this.obj = obj;
  this._events = {};
}

/**
 * Subscription helper.
 */

Events.prototype.sub = function(event, method, cb){
  this._events[event] = this._events[event] || {};
  this._events[event][method] = cb;
};

/**
 * Bind to `event` with optional `method` name.
 * When `method` is undefined it becomes `event`
 * with the "on" prefix.
 *
 * Examples:
 *
 *  Direct event handling:
 *
 *    events.bind('click') // implies "onclick"
 *    events.bind('click', 'remove')
 *    events.bind('click', 'sort', 'asc')
 *
 *  Delegated event handling:
 *
 *    events.bind('click li > a')
 *    events.bind('click li > a', 'remove')
 *    events.bind('click a.sort-ascending', 'sort', 'asc')
 *    events.bind('click a.sort-descending', 'sort', 'desc')
 *
 * @param {String} event
 * @param {String|function} [method]
 * @return {Function} callback
 * @api public
 */

Events.prototype.bind = function(event, method){
  var e = parse(event);
  var el = this.el;
  var obj = this.obj;
  var name = e.name;
  var method = method || 'on' + name;
  var args = [].slice.call(arguments, 2);

  // callback
  function cb(){
    var a = [].slice.call(arguments).concat(args);
    obj[method].apply(obj, a);
  }

  // bind
  if (e.selector) {
    cb = delegate.bind(el, e.selector, name, cb);
  } else {
    events.bind(el, name, cb);
  }

  // subscription for unbinding
  this.sub(name, method, cb);

  return cb;
};

/**
 * Unbind a single binding, all bindings for `event`,
 * or all bindings within the manager.
 *
 * Examples:
 *
 *  Unbind direct handlers:
 *
 *     events.unbind('click', 'remove')
 *     events.unbind('click')
 *     events.unbind()
 *
 * Unbind delegate handlers:
 *
 *     events.unbind('click', 'remove')
 *     events.unbind('click')
 *     events.unbind()
 *
 * @param {String|Function} [event]
 * @param {String|Function} [method]
 * @api public
 */

Events.prototype.unbind = function(event, method){
  if (0 == arguments.length) return this.unbindAll();
  if (1 == arguments.length) return this.unbindAllOf(event);

  // no bindings for this event
  var bindings = this._events[event];
  if (!bindings) return;

  // no bindings for this method
  var cb = bindings[method];
  if (!cb) return;

  events.unbind(this.el, event, cb);
};

/**
 * Unbind all events.
 *
 * @api private
 */

Events.prototype.unbindAll = function(){
  for (var event in this._events) {
    this.unbindAllOf(event);
  }
};

/**
 * Unbind all events for `event`.
 *
 * @param {String} event
 * @api private
 */

Events.prototype.unbindAllOf = function(event){
  var bindings = this._events[event];
  if (!bindings) return;

  for (var method in bindings) {
    this.unbind(event, method);
  }
};

/**
 * Parse `event`.
 *
 * @param {String} event
 * @return {Object}
 * @api private
 */

function parse(event) {
  var parts = event.split(/ +/);
  return {
    name: parts.shift(),
    selector: parts.join(' ')
  }
}

});

require.register("component~debounce@0.0.3", function (exports, module) {
/**
 * Debounces a function by the given threshold.
 *
 * @see http://unscriptable.com/2009/03/20/debouncing-javascript-methods/
 * @param {Function} function to wrap
 * @param {Number} timeout in ms (`100`)
 * @param {Boolean} whether to execute at the beginning (`false`)
 * @api public
 */

module.exports = function debounce(func, threshold, execAsap){
  var timeout;

  return function debounced(){
    var obj = this, args = arguments;

    function delayed () {
      if (!execAsap) {
        func.apply(obj, args);
      }
      timeout = null;
    }

    if (timeout) {
      clearTimeout(timeout);
    } else if (execAsap) {
      func.apply(obj, args);
    }

    timeout = setTimeout(delayed, threshold || 100);
  };
};

});

require.register("component~indexof@0.0.3", function (exports, module) {
module.exports = function(arr, obj){
  if (arr.indexOf) return arr.indexOf(obj);
  for (var i = 0; i < arr.length; ++i) {
    if (arr[i] === obj) return i;
  }
  return -1;
};

});

require.register("component~classes@1.2.1", function (exports, module) {
/**
 * Module dependencies.
 */

var index = require("component~indexof@0.0.3");

/**
 * Whitespace regexp.
 */

var re = /\s+/;

/**
 * toString reference.
 */

var toString = Object.prototype.toString;

/**
 * Wrap `el` in a `ClassList`.
 *
 * @param {Element} el
 * @return {ClassList}
 * @api public
 */

module.exports = function(el){
  return new ClassList(el);
};

/**
 * Initialize a new ClassList for `el`.
 *
 * @param {Element} el
 * @api private
 */

function ClassList(el) {
  if (!el) throw new Error('A DOM element reference is required');
  this.el = el;
  this.list = el.classList;
}

/**
 * Add class `name` if not already present.
 *
 * @param {String} name
 * @return {ClassList}
 * @api public
 */

ClassList.prototype.add = function(name){
  // classList
  if (this.list) {
    this.list.add(name);
    return this;
  }

  // fallback
  var arr = this.array();
  var i = index(arr, name);
  if (!~i) arr.push(name);
  this.el.className = arr.join(' ');
  return this;
};

/**
 * Remove class `name` when present, or
 * pass a regular expression to remove
 * any which match.
 *
 * @param {String|RegExp} name
 * @return {ClassList}
 * @api public
 */

ClassList.prototype.remove = function(name){
  if ('[object RegExp]' == toString.call(name)) {
    return this.removeMatching(name);
  }

  // classList
  if (this.list) {
    this.list.remove(name);
    return this;
  }

  // fallback
  var arr = this.array();
  var i = index(arr, name);
  if (~i) arr.splice(i, 1);
  this.el.className = arr.join(' ');
  return this;
};

/**
 * Remove all classes matching `re`.
 *
 * @param {RegExp} re
 * @return {ClassList}
 * @api private
 */

ClassList.prototype.removeMatching = function(re){
  var arr = this.array();
  for (var i = 0; i < arr.length; i++) {
    if (re.test(arr[i])) {
      this.remove(arr[i]);
    }
  }
  return this;
};

/**
 * Toggle class `name`, can force state via `force`.
 *
 * For browsers that support classList, but do not support `force` yet,
 * the mistake will be detected and corrected.
 *
 * @param {String} name
 * @param {Boolean} force
 * @return {ClassList}
 * @api public
 */

ClassList.prototype.toggle = function(name, force){
  // classList
  if (this.list) {
    if ("undefined" !== typeof force) {
      if (force !== this.list.toggle(name, force)) {
        this.list.toggle(name); // toggle again to correct
      }
    } else {
      this.list.toggle(name);
    }
    return this;
  }

  // fallback
  if ("undefined" !== typeof force) {
    if (!force) {
      this.remove(name);
    } else {
      this.add(name);
    }
  } else {
    if (this.has(name)) {
      this.remove(name);
    } else {
      this.add(name);
    }
  }

  return this;
};

/**
 * Return an array of classes.
 *
 * @return {Array}
 * @api public
 */

ClassList.prototype.array = function(){
  var str = this.el.className.replace(/^\s+|\s+$/g, '');
  var arr = str.split(re);
  if ('' === arr[0]) arr.shift();
  return arr;
};

/**
 * Check if class `name` is present.
 *
 * @param {String} name
 * @return {ClassList}
 * @api public
 */

ClassList.prototype.has =
ClassList.prototype.contains = function(name){
  return this.list
    ? this.list.contains(name)
    : !! ~index(this.array(), name);
};

});

require.register("scrollbars", function (exports, module) {

var scrollbarSize = require("eivindfjeldstad~scrollbar-size@master");
var debounce = require("component~debounce@0.0.3");
var classes = require("component~classes@1.2.1");
var events = require("component~events@1.0.6");

module.exports = Scrollbars;

Scrollbars.MIN_SIZE = 25;
Scrollbars.CORNER = 6;

var positioned = ['relative', 'absolute', 'fixed'];

function Scrollbars(element) {
	if (!(this instanceof Scrollbars))
		return new Scrollbars(element);

	var self = this;

	this.elem = element;

	// inject the wrapper
	this.wrapper = document.createElement('div');
	// inherit the classes for styling
	// TODO: also make this work with styling based on id
	this.wrapper.className = this.elem.className;
	this.elem.parentNode.replaceChild(this.wrapper, this.elem);
	this.wrapper.appendChild(this.elem);

	// save the current style, so we can restore if necessary
	var style = getComputedStyle(this.elem);
	this.elemstyle = {
		position: style.position,
		top: style.top,
		right: style.right,
		bottom: style.bottom,
		left: style.left,
	};

	classes(this.elem).add('scrollbars-override');
	setPosition(this.elem, [0, -scrollbarSize, -scrollbarSize, 0]);

	style = this.wrapper.style;
	// set the wrapper to be positioned
	// but don’t mess with already positioned elements
	if (!~positioned.indexOf(this.elemstyle.position))
		style.position = 'relative';
	style.overflow = 'hidden';

	this.events = events(this.elem, this);

	// OSX has native overlay scrollbars which have a width of 0
	// in that case just don’t create any custom ones
	if (!scrollbarSize)
		return this;

	// and create scrollbar handles
	this.handleV = handle('vertical', [0, 0, 0, undefined]);
	this.wrapper.appendChild(this.handleV);
	this.handleH = handle('horizontal', [undefined, 0, 0, 0]);
	this.wrapper.appendChild(this.handleH);

	this.dragging = null;

	// hide after some inactivity
	this.hide = debounce(function () {
		if (!self.dragging || self.dragging.elem != self.handleV)
			self.handleV.firstChild.className = 'scrollbars-handle vertical';
		if (!self.dragging || self.dragging.elem != self.handleH)
			self.handleH.firstChild.className = 'scrollbars-handle horizontal';
	}, 1000);

	// hook them up to scroll events
	this.events.bind('scroll', 'refresh');
	this.events.bind('mouseenter', 'refresh');

	[this.handleV, this.handleH].forEach(function (handle) {
		// don’t hide handle when hovering
		handle.firstChild.addEventListener('mouseenter', function (ev) {
			if (!self.dragging)
				self.dragging = {elem: handle};
		}, false);
		handle.firstChild.addEventListener('mouseleave', function (ev) {
			if (self.dragging && !self.dragging.handler)
				self.dragging = null;
		}, false);

		// and do the dragging
		handle.firstChild.addEventListener('mousedown', function (ev) {
			self._startDrag(handle, ev);
			ev.preventDefault();
		}, false);
	});

	this._endDrag = function () {
		document.removeEventListener('mousemove', self.dragging.handler);
		document.removeEventListener('mouseup', self._endDrag);
		self.dragging = null;
	};
}

Scrollbars.prototype._startDrag = function Scrollbars__startDrag(handle, ev) {
	var vertical = handle == this.handleV;
	var self = this;
	var handler = function (ev) {
		self._mouseMove(ev);
	};
	document.addEventListener('mousemove', handler, false);
	document.addEventListener('mouseup', this._endDrag, false);
	var rect = handle.getBoundingClientRect();
	this.dragging = {
		elem: handle,
		handler: handler,
		offset: vertical ? ev.pageY - rect.top : ev.pageX - rect.left
	};
};

Scrollbars.prototype._mouseMove = function Scrollbars__mouseMove(ev) {
	var vertical = this.dragging.elem == this.handleV;
	var rect = this.elem.getBoundingClientRect();
	var size = handleSize(this.elem);
	var offset;
	if (vertical) {
		offset = ev.pageY - rect.top - this.dragging.offset;
		this.elem.scrollTop = offset / size.sizeH * size.sTM;
	} else {
		offset = ev.pageX - rect.left - this.dragging.offset;
		this.elem.scrollLeft = offset / size.sizeW * size.sLM;
	}
};

function handleSize(elem) {
	var cH = elem.clientHeight;
	var sH = elem.scrollHeight;
	var sTM = elem.scrollTopMax || Math.max(sH - cH, 0);
	var cW = elem.clientWidth;
	var sW = elem.scrollWidth;
	var sLM = elem.scrollLeftMax || Math.max(sW - cW, 0);

	var pH = cH / sH;
	var pW = cW / sW;

	var corner = sTM && sLM ? Scrollbars.CORNER : 0;

	var sizeH = cH - Math.max(Scrollbars.MIN_SIZE, pH * (cH - corner)) - corner;
	var sizeW = cW - Math.max(Scrollbars.MIN_SIZE, pW * (cW - corner)) - corner;

	return {
		corner: corner,
		sTM: sTM,
		sLM: sLM,
		sizeH: sizeH,
		sizeW: sizeW,
		pH: pH,
		pW: pW,
	};
}

/*
 * Refreshes (and shows) the scrollbars
 */
Scrollbars.prototype.refresh = function Scrollbars_refresh() {
	if (!scrollbarSize)
		return;
	var size = handleSize(this.elem);
	var scrolledPercentage;
	// vertical
	if (size.sTM) {
		scrolledPercentage = this.elem.scrollTop / size.sTM;
		setPosition(this.handleV, [
			scrolledPercentage * size.sizeH,
			0,
			(1 - scrolledPercentage) * size.sizeH + size.corner,
			undefined
		]);
		this.handleV.firstChild.className = 'scrollbars-handle vertical show';
	}

	// horizontal
	if (size.sLM) {
		scrolledPercentage = this.elem.scrollLeft / size.sLM;
		setPosition(this.handleH, [
			undefined,
			(1 - scrolledPercentage) * size.sizeW + size.corner,
			0,
			scrolledPercentage * size.sizeW,
		]);
		this.handleH.firstChild.className = 'scrollbars-handle horizontal show';
	}

	this.hide();
};

Scrollbars.prototype.destroy = function Scrollbars_destroy() {
	var self = this;
	if (this.dragging && this.dragging.handler)
		this._endDrag(); // clear global events
	this.wrapper.removeChild(this.elem);
	this.wrapper.parentNode.replaceChild(this.elem, this.wrapper);
	classes(this.elem).remove('scrollbars-override');
	this.events.unbind();

	var style = this.elem.style;
	style.top = this.elemstyle.top;
	style.right = this.elemstyle.right;
	style.left = this.elemstyle.left;
	style.bottom = this.elemstyle.bottom;

	// clear all the props, so the GC can clear them up
	this.wrapper = this.handleV = this.handleH = this.elemstyle = this.elem =
		this._endDrag = this.dragging = this.hide = this.events = null;
};

// create a handle
function handle(klass, pos) {
	// a container that has the handles position
	var container = document.createElement('div');
	var style = container.style;
	style.position = 'absolute';
	setPosition(container, pos);

	// the handle itself
	var handle = document.createElement('div');
	handle.className = 'scrollbars-handle ' + klass;
	container.appendChild(handle);

	return container;
}

// set absolute positioning properties
var props = ['top', 'right', 'bottom', 'left'];
function setPosition(el, positions) {
	for (var i = 0; i < props.length; i++) {
		var prop = props[i];
		var pos = positions[i];
		if (typeof pos !== 'undefined')
			el.style[prop] = Math.round(pos) + 'px';
	}
}

});

var scrollbars = require("scrollbars");
