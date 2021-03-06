
'use strict';

// We assume this JS is sourced at the end of any HTML, avoiding the
// need for a $(document).ready(…) call. But it really needs the
// document fully loaded to operated properly.

// TODO: put this in our own namespace, not in the window…

// ——————————————————————————————————————————————————————————— for memories
// different value for toggle_content()::open_me()
//
// TODO: if (!inViewport(me))
//scrollToElement(me, scroll_speed, $(me).height());
//scrollToElement(me, scroll_speed, 0);
//scrollToElement(me);
// put the current item in the center of the window.
//scrollToElement(me, scroll_speed, $(window).height() / 2);
// put the current item in the upper part of the window.
//scrollToElement(me, scroll_speed, $(window).height() / 4);


common_init();


function eventually_toggle(event) {
    // see http://stackoverflow.com/a/9183467/654755 for the base I used.

    //console.log('toggled: ' + event.target);

    //debug_notify('eventually_toggle ' + event);

    if ($(event.target).attr('href') == undefined) {
        var togglable   = $(this).closest('.slide-togglable');
        var custom_func = togglable.data('toggle-function');
        var custom_cbk  = togglable.data('toggle-callback');
        var target_sel  = togglable.data('toggle-id');

        if (custom_func != 'undefined'
                && typeof window[custom_func] == 'function') {

            if (custom_cbk != 'undefined'
                    && typeof window[custom_cbk] == 'function') {

                window[custom_func](target_sel,
                                    window[custom_cbk]);
            } else {
                window[custom_func](target_sel);
            }

        } else {

            if (custom_cbk != 'undefined'
                    && typeof window[custom_cbk] == 'function') {

                togglable.slideToggle(function(){

                    // we have to pass the OID in some way, thus we do not
                    // simply pass the callback like we do for `custom_func`.
                    window[custom_cbk](target_sel);
                });
            } else {
                togglable.slideToggle();
            }
        }
    }

    event.stopPropagation();
}

function read_setup(parent) {
    // this function is run after each ajax call, via setup_everything().

    // console.debug('read setup bindings');
   //debug_notify('read_setup(' + parent + ')');

    // not needed with the meta *mobile-web-app-capable stuff.
    //window.scrollTo(0,1);

    $(".article-content p").find('img').parent().addClass('img-legend');

    // HEADS UP: this makes read-items totally
    //           unresponsive on touch devices.
    //           I think it's mostly useless, anyway.
    //if(!Modernizr.touch) {

        find_start(parent, 'content-toggle').on('click', function(ev){

            var target   = $(this).data('toggle-id'),
                callback = $(this).data('toggle-callback');

            if(!target) {
                console.error('No target (data-toggle-id) for ' + this + '!');
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            toggle_content(target, callback);
        });

        find_start(parent, 'slide-togglable').on('tripleclick', eventually_toggle);

    //}
}

function read_init(){
    // for now, this one does nothing.
    // It's not mandatory to create it,
    // but I keep it here as an example.
};

// These will hold IDs of DOM/jQuery elements.
var open_content = null;
var last_opened  = null;
var open_actions = null;
//var open_scrollbars = null;
var auto_mark_read_timers = {};
var remove_iframes_timers = {};
var remove_iframes_delay = 10000;
var navbars_visible = true;

function notice_element(oid) {

    setTimeout(function(){
        flash_fade($("#" + oid), "#ddd", "#bbb");
    }, 1000);
}
function toggle_content(oid, callback) {

    //debug_notify('toggle_content(' + oid + ', ' + callback + ')');
    // console.debug('toggle_content(' + oid + ', ' + callback + ')');

    var run_callback = function() {
        //console.debug('trying to run callback ' + callback + '(' + oid + ')');
        typeof callback === 'function' && callback(oid);
    };

    var me      = "#" + oid,
        $me     = $(me),
        $content = $("#article-content-" + oid),

        open_auxilliary = function ($on_what) {

            var $acontent  = $on_what.find('.article-content').first();
            var async_url = $acontent.data('content-async');
            var meta_url  = $acontent.data('meta-async');

            //console.debug('open_aux on ' + oid + ', '+ auto_mark_read_timers[oid]);
            //console.debug($acontent);
            //console.debug(async_url);

            // no need bothering testing !is(':visible'). It costs
            // a lot, and if it's not, slideDown() will do nothing.
            //$on_what.find('.clicker-muted').first().slideDown();

            if ($on_what.hasClass('not_is_read')
                    && preferences.auto_mark_read_delay > 0) {

                auto_mark_read_timers[oid] = setTimeout(function(){

                    // we need to specify the read_id and not use
                    // `open_content`, because in rare conditions
                    // we have a race where opening next article
                    // marks it as read immediately, whereas the
                    // previous should have been marked instead.

                    mark_something(oid, 'is_read', false, false);
                    delete auto_mark_read_timers[oid];

                }, preferences.auto_mark_read_delay);

                //console.debug('mark read timer set at ' + oid + ', '+ auto_mark_read_timers[oid]);
            }

            if (async_url) {
                $.get(async_url, function(data){

                    //if (open_scrollbars) {
                    //    open_scrollbars.destroy();
                    //}

                    scrollbars(document.querySelector("#article-content-" + oid));

                    $acontent.html(data);

                    // Special case to hide the header on the fly.
                    // TODO: this is a very edge case whose counter-part
                    // (when closing the read) is not handled at all, it
                    // just works smoothly currently. This should be
                    // enhanced in the future to be more solid or more
                    // "officially supported".
                    if ($acontent.find('iframe.no-article-content')) {
                        $on_what.addClass('original-view');
                    }

                    // be sure we don't call it next time, it's already loaded.
                    // DOESN'T WORK: $acontent.removeData('async');
                    $acontent.attr('data-content-async', '');
                });
            }

            //console.log(meta_url);

            $.get(meta_url, function(data) {

                var $data = $(data),
                    $article_meta_information = $on_what.find('.article-meta-information').first(),
                    $article_meta_attributes  = $on_what.find('.article-meta-attributes').first();

                // NOTE: see the server-side template for comments.

                $article_meta_information.html(
                    $data.find('.article-meta-information-data').html());

                $article_meta_attributes.html(
                    $data.find('.article-meta-attributes-data').html());

                setup_everything($article_meta_information);
                setup_everything($article_meta_attributes);
            });
        },

        close_me_real = function () {

            // assign every open-related variable before the
            // animation starts, else potential parallely
            // executed function could fail or get the "old"
            // (previous) values.
            open_content = null;
            last_opened  = oid;

            //if (open_scrollbars) {
            //    open_scrollbars.destroy();
            //}

            // console.debug('set open to null and last to ' + oid);

            // 20150208: don't empty meta informations, for some reasons
            // they are not reloaded. I should find why, but it's an easier
            // fix until then.
            // $('.article-meta-information').html('');
            // $('.article-meta-attributes').html('');

            $content.slideUp(scroll_speed, "swing", run_callback);

            // Put the current item to top of window.
            scrollToElement(me, scroll_speed, 100);

            close_auxilliary($me);
            $me.removeClass('open_content');
        },

        open_me_real = function () {

            try {

                clearTimeout(remove_iframes_timers[oid]);
                delete remove_iframes_timers[oid];

            } catch (err) {
                console.error(err);
            }

            if (scrollTo) {

                if (preferences.read_switches_to_fullscreen) {
                    scrollToElement(me, scroll_speed, -50);

                } else {
                    scrollToElement(me, scroll_speed, 0);
                }
            }

            // bindable_hovered NOT USED YET
            //bindable_hovered = content;

            $me.addClass('open_content');

            open_auxilliary($me);
            $content.slideDown(scroll_speed, "swing", run_callback);

        },

        open_me = function(scrollTo) {

            //console.debug('open_me on ' + me);

            if(typeof scrollTo == 'undefined') {
                var scrollTo = true;
            }

            // set all 'open' related variables before the animation
            // starts, else potential parallely executed function could
            // fail or get the "old" (previous) values.
            last_opened  = oid;
            open_content = oid;

            // console.debug('set open to ' + oid + ' and last to ' + oid);

            if (preferences.read_switches_to_fullscreen) {
                $('.navbar').each(function(index) {
                    if (index == 0) {
                        $(this).slideUp(open_me_real);
                    } else {
                        $(this).slideUp();
                    }
                });
            } else {
                open_me_real();
            }
        },

        close_auxilliary = function ($on_what) {

            // Shouldn't we just use "oid" ?
            var myid = $on_what.attr('id');

            //console.debug('close_aux ' + $on_what);

            if(preferences.auto_mark_read_delay > 0) {
                try {

                    clearTimeout(auto_mark_read_timers[oid]);
                    delete auto_mark_read_timers[oid];

                } catch (err) {
                    console.error(err);
                }
            }

            $on_what.find('.clicker-muted').each(function() {
                // no need bothering testing is(':visible'). It costs
                // a lot, and if it's not, slideUp() will do nothing.
                $(this).slideUp();
            });

            remove_iframes_timers[oid] = setTimeout(function() {
                try {
                    $on_what.find('.article-iframe-wrapper').remove();

                } catch (err) {
                    console.error('error while removing iframe of ' + oid);
                    console.error(err);
                }
            }, remove_iframes_delay);

            // clear the content, for the page to stay light.
            // NOTE: in fact, NO. keep it to avoid useless round-trips
            // with the server, and make recently-read articles fast.
            //$on_what.find('.article-content').first().html('');
            //
            // TODO: unload the content after a few minute, remake the
            // data-async OK, and disable the timer on re-open to avoid
            // shortening the contents while the user is reading it ;-)
        };

    if ($content.is(':visible')) {

        if (preferences.read_switches_to_fullscreen) {

            $('.navbar').each(function(index){

                if (index == 0) {
                    $(this).slideDown(close_me_real);

                } else {
                    $(this).slideDown();
                }
            });

        } else {
            close_me_real();
        }

        // bindable_hovered NOT USED YET
        //
        // This is not mandatory, but doesn't hurt.
        // As we close the content, there is nothing
        // bindable anymore, anyway.
        //bindable_hovered = null;

        // Avoid the body to scroll on mousewhell / touchslide
        $('body').removeClass('modal-open');

    } else {
        //console.debug(oid + ' not visible.');

        if(open_content != null) {

            // console.debug('open_content: ' + open_content);

            var to_close   = open_content,
                $current   = $("#" + open_content),
                cur_height = $current.height();

            // compensate the slideUp() of the $current open
            // element if it's located before us, else the
            // movement in not visually fluent.
            if ($current.data('index') < $(me).data('index')) {
                scrollToElement(me, scroll_speed,
                                preferences.read_switches_to_fullscreen ?
                                    cur_height - 30 : cur_height + 20);
                open_me(false);

            } else {
                open_me(true);
            }

            $("#article-content-" + to_close).slideUp(scroll_speed, "swing", function(){
                $current.removeClass('open_content');

                close_auxilliary($current);
            });


        } else {
            open_me(true);

            // Make the body free again for scrolling
            $('body').addClass('modal-open');
        }
    }
}
function open_next_read() {

    var $items = $('.read-list-item');

    function open_next_internal(which) {

        var $next = $("#" + which)
            .closest('.read-list-item')
            .next('.read-list-item');

        if ($next.length) {
            toggle_content($next.attr('id'));

        } else {
            notify({
                text: read_actions_messages.already_at_end,
                type: 'warning',
                icon: false,
                sticker: false
            });
        }
    }

    if (open_content) {
        open_next_internal(open_content);

    } else {
        if (last_opened) {
            open_next_internal(last_opened);

        } else {

            if ($items.length) {
                notify({
                    text: read_actions_messages.open_first,
                    type: 'info',
                    icon: false,
                    sticker: false
                });

                toggle_content($items.first().attr('id'));

            } else {
                notify({
                    text: read_actions_messages.nothing_to_open,
                    type: 'info',
                    icon: false,
                    sticker: false
                });
            }
        }
    }

    // stop event propagation, old school way
    // because this function is used in <a href="...">
    return false;
}
function open_previous_read() {

    function open_previous_internal(which) {
        var previous = $("#" + which)
            .closest('.read-list-item')
            .prev('.read-list-item');

        if (previous.length) {
            toggle_content(previous.attr('id'));

        } else {
            notify({
                text: read_actions_messages.already_top_first,
                type: 'warning',
                icon: false,
                sticker: false
            });
        }
    }

    if (open_content) {
        open_previous_internal(open_content);

    } else {
        if (last_opened) {
            open_previous_internal(last_opened);

        } else {
            notify({
                text: read_actions_messages.already_top_more,
                type: 'info',
                icon: false,
                sticker: false
            });
        }
    }

    // stop event propagation, old school way
    // because this function is used in <a href="...">
    return false;
}
function close_current_read() {
    if (open_content) {
        return toggle_content(open_content);
    }

    // stop event propagation, old school way
    // because this function is used in <a href="...">
    return false;
}
function open_last_opened() {
    if (last_opened && !open_content) {
        debug_notify('re-opening ' + last_opened);
        return toggle_content(last_opened);
    }
}
function mark_current_read_as(what, send_notify) {
    if (open_content) {
        var read = $("#" + open_content);

        if (read.hasClass('not_' + what)) {
            return mark_something(open_content, what, false, send_notify);
        }
    }
}
function current_read_status(status) {

    if (open_content) {
        return current_status(open_content, status);
    }
}
function toggle_current_read_status(status) {

    if (open_content) {
        return toggle_status(null, open_content, status, true);

    } else {
        notify({
            text: read_actions_messages[status].nothing,
            type: 'warning',
            icon: false,
            sticker: false
        });
    }
}

function show_actions(objekt) {
    // objekt is a DOM entity

    debug_notify('Opening actions for ' + objekt);

    if (open_actions) {
        hide_actions(document.getElementById(open_actions));
    }

    show_hover_muted.call(objekt);
    open_actions = objekt.getAttribute('id');
}
function hide_actions(objekt) {
    // objekt is a DOM entity

    debug_notify('Closing actions for ' + objekt);

    hide_hover_muted.call(objekt);
    open_actions = null;
}
function handle_tap(ev) {

    var $this  = $(this),
        target = $this.data('toggle-id') || $this.attr('id');

    function open_or_hide_actions() {

        debug_notify('Acting on ' + target);

        if (open_content && open_content == target) {
            show_actions(document.getElementById(target));

        } else {
            hide_actions(document.getElementById(target));
        }
    }

    if (ev.gesture.touches.length > 3) {
        return;
    }

    //alert('TAP on ' + $this);

    // WOW. without ev.preventDefault(), the 2 others
    // don't suffice to avoid the event being sent twice.
    ev.gesture.preventDefault();
    ev.stopPropagation();
    //ev.preventDefault();

    if (ev.gesture.touches.length == 3) {
        alert('3-fingers tap on ' + target);
        open_or_hide_actions();

    } else if (ev.gesture.touches.length == 2) {
        alert('2-fingers tap on ' + target);
        toggle_status(null, target, "is_starred");

    } else {
        alert('1-finger tap on ' + target);
        //toggle_content(target, open_or_hide_actions);
        toggle_content(target);
    }
    return false;
}
function toggle_fullscreen() {
    $('.navbar').slideToggle(function() {
        navbars_visible = $('.navbar').first().is(':visible');
    });
}

// ——————————————————————————————————————————————————— open first/next/previous

// “Next”, “Goto Next”, “Open Next”
Mousetrap.bind(['n', 'g n', 'o n'], function() {
    open_next_read();
    return false;
});

// “Previous”, “Goto Previous”, “Open Previous”
Mousetrap.bind(['p', 'g p', 'o p'], function() {
    open_previous_read();
    return false;
});

// “Close”
Mousetrap.bind(['c'], function() {
    close_current_read();
    return false;
});

// “Toggle Watch”
Mousetrap.bind(['t w'], function() {
    if (open_content) {
        $('#'+open_content).find('.clicker-muted').slideToggle();
    }

    return false;
});


// “Last Open” (re-open last closed one)
// WARNING: using just 'o' as only shortcut won't work because
//          of other multi-key shortcuts starting with an 'o'.
Mousetrap.bind(['o l'], function() {
    open_last_opened();
    return false;
});

// —————————————————————————————————————————————————— actions on currently open

// “Mark Read”, “Toggle Read”
Mousetrap.bind(['m r', 't r'], function() {
    toggle_current_read_status("is_read");
    return false;
});

// “Mark Starred”, “Toggle Starred”
Mousetrap.bind(['m s', 't s'], function() {
    toggle_current_read_status("is_starred");
    return false;
});
// “Mark [fF]or Later”, “Toggle Later status”,
// “Mark Bookmarked”, “Toggle Bookmarked”,
// “Keep For Later”, “Read Later”
Mousetrap.bind(['m l', 't l',
                'r l', 'm f l', 'k f l'], function() {

    toggle_current_read_status("is_bookmarked");
    return false;
});

// “Mark Archi[V]ed”
Mousetrap.bind(['m v'], function() {
    toggle_current_read_status("is_archived");
    convert_current_read_to_fulltext();
    return false;
});

// “Mark Fact”, “Toggle Fact”
Mousetrap.bind(['m f', 't f'], function() {
    toggle_current_read_status("is_fact");
    return false;
});

// “Mark Number”, “Toggle Number”
Mousetrap.bind(['m n', 't n'], function() {
    toggle_current_read_status("is_number");
    return false;
});

// “Mark Analysis”, “Toggle Analysis”
Mousetrap.bind(['m a', 't a'], function() {
    toggle_current_read_status("is_analysis");
    return false;
});

// “Mark Quote”, “Toggle Quote”
Mousetrap.bind(['m q', 't q'], function() {
    toggle_current_read_status("is_quote");
    return false;
});

// “Mark Prospective”, “Toggle Prospective”
Mousetrap.bind(['m p', 't p'], function() {
    toggle_current_read_status("is_prospective");
    return false;
});

// “Mark Know-how”, “Toggle Know-how”
Mousetrap.bind(['m k', 't k'], function() {
    toggle_current_read_status("is_knowhow");
    return false;
});

// “Mark Rules”, “Toggle Rules”
Mousetrap.bind(['m u', 't u'], function() {
    toggle_current_read_status("is_rules");
    return false;
});

// “Mark Knowledge”, “Toggle Knowledge”
Mousetrap.bind(['m o', 't o'], function() {
    toggle_current_read_status("is_knowledge");
    return false;
});

// “Oh My God”, “Laugh Out Loud”, “Laughing My Ass Out”, “FUN”
Mousetrap.bind(['o m g', 'l o l', 'l m a o', 'f u n'], function() {
    toggle_current_read_status("is_fun");
    return false;
});

/*

    NOTE: there are some other shortcuts to merge
            in the staff/superuser included files

*/


// —————————————————————————————————————————————————————————— read-flow actions


// “Mark Read” + “Next”, “Goto Next”, “Open Next”
Mousetrap.bind(['shift+r', 'shift+n'], function() {
    mark_current_read_as('is_read');
    open_next_read();
    return false;
});


// “Mark Read” + “Previous”
Mousetrap.bind(['shift+p'], function() {
    mark_current_read_as('is_read');
    open_previous_read();
    return false;
});

// “Star and go next”
Mousetrap.bind(['shift+s'], function() {
    mark_current_read_as('is_starred');
    open_next_read();
    return false;
});

// “mark for Later and go next”
Mousetrap.bind(['shift+l'], function() {
    mark_current_read_as('is_bookmarked');
    open_next_read();
    return false;
});


// ————————————————————————————————————————————————————————————— global actions


Mousetrap.bind(['shift+f'], function() {
    toggle_fullscreen();
    return false;
});


// ——————————————————————————————————————————————————————————————— touch events


if (Modernizr.touch) {

    hammertime.on("swipeleft", ".read-list-item", function(ev) {

        var $this = $(this);

        //alert('SWL on ' + $this);

        if (ev.gesture.touches.length != 1) {
            return;
        }

        ev.gesture.preventDefault();
        ev.stopPropagation();
        ev.preventDefault();

        $this.animate({marginLeft: -50}, 200, function(){
            $this.animate({marginLeft: 0}, 150);
        });

        toggle_status(null, $this.attr('id'), "is_auto_read", false);

        return false;
    });

    hammertime.on("swiperight", ".read-list-item", function(ev) {

        var $this = $(this);

        debug_notify('SWR on '+$this);

        if (ev.gesture.touches.length != 1) {
            return;
        }

        ev.gesture.preventDefault();
        ev.stopPropagation();
        ev.preventDefault();

        $this.animate({marginLeft: 50}, 200, function(){
            $this.animate({marginLeft: 0}, 150);
        });

        toggle_status(null, null, $this.attr('id'), "is_bookmarked", false);

        return false;
    });

    hammertime.on("swipeleft", ".article-content", function(ev) {

        var $this = $(this);

        if(ev.gesture.touches.length == 2) {

            ev.gesture.preventDefault();
            ev.stopPropagation();
            ev.preventDefault();

            open_next_read();
        }

        return false;
    });

    hammertime.on("swiperight", ".article-content", function(ev) {

        var $this = $(this);

        if(ev.gesture.touches.length == 2) {

            ev.gesture.preventDefault();
            ev.stopPropagation();
            ev.preventDefault();

            open_previous_read();
        }

        return false;
    });

    /*
        NOT READY YET

    hammertime.on("swipeleft", ".read-list-item", function(ev) {
        var $this = $(this);

        $this.animate({marginLeft: -ev.distance}, 200, function(){
            $this.animate({marginLeft: 0}, 150);
        });

        var something_done = false;

        if (ev.distance > 100) {
            if ($this.hasClass("hover-muter-open")) {
                $this.removeClass("hover-muter-open");
                hide_hover_muted.call(this);
            }

            something_done = true;

        } else if (ev.distance > 25) {
            toggle_status(null, null, $this.attr('id'), "is_read");
            something_done = true;
        }

        if (something_done) {
            ev.gesture.preventDefault();
            ev.stopPropagation();
        }
    });

    hammertime.on("swiperight", ".read-list-item", function(ev) {
        var $this = $(this);

        $this.animate({marginLeft: ev.distance}, 200, function(){
            $this.animate({marginLeft: 0}, 150);
        });

        var something_done = false;

        if (ev.distance > 100) {
            if (!$this.hasClass("hover-muter-open")) {
                $this.addClass("hover-muter-open");
                show_hover_muted.call(this);
            }
            something_done = true;

        } else if (ev.distance > 25) {
            toggle_status(null, null, $this.attr('id'), "is_bookmarked");
            something_done = true;

        }

        if (something_done) {
            ev.gesture.preventDefault();
            ev.stopPropagation();
        }
    });

        END NOT READY YET
    */

    hammertime.on("tap", ".article-meta", handle_tap);

    hammertime.on("pinchin doubletap", ".article-content", function(ev) {

        var $this  = $(this),
            target = $this.data('toggle-id');

        // WOW. without ev.preventDefault(), the 2 others
        // don't suffice to avoid the event being sent twice.
        ev.gesture.preventDefault();
        ev.stopPropagation();
        ev.preventDefault();

        debug_notify('pinch/dbltap event on ' + target);

        toggle_content(target, function() {
            hide_actions(document.getElementById(target));
        });
    });

    hammertime.on("pinchout", ".article-meta", function(ev) {

        var $this  = $(this),
            target = $this.data('toggle-id');

        // WOW. without ev.preventDefault(), the 2 others
        // don't suffice to avoid the event being sent twice.
        ev.gesture.preventDefault();
        ev.stopPropagation();
        ev.preventDefault();

        debug_notify('pinchout event on ' + target);

        toggle_content(target, function() {
            show_actions(document.getElementById(target));
        });
    });

    hammertime.on("hold", ".read-list-item", function(ev) {

        var $this = $(this);

        // WOW. without ev.preventDefault(), the 2 others
        // don't suffice to avoid the event being sent twice.
        ev.gesture.preventDefault();
        ev.stopPropagation();
        ev.preventDefault();

        if ($this.hasClass("hover-muter-open")) {
            hide_actions(this);

        } else {
            show_actions(this);
        }
    });
}

// —————————————————————————————————————————————————————— init helper functions

function setup_snappers() {

    // http://www.sitepoint.com/forums/showthread.php?779582-Choose-whole-sentences-and-ONLY-whole-sentences-RELIABLY-with-regex

    $('.article-meta-bottom h1').on('click', function(){ $(this).toggleClass('selected') });
    $('.article-content p, .article-content pre, .article-content ul li, .article-content h1, .article-content h2, .article-content h3, .article-content img').on('click', function(){ $(this).toggleClass('selected') });
}

function hide_initial_loading() {

    var update_reads_number = function() {
        // WARNING: do not use sole document.location.
        // In case of a '#' inside it will loop all the
        // articles in the counter span!!

        $.get(
            document.location.pathname + '?count=1',
            function(data){
                console.info("Up-to-date reads number: " + data);
                $('#reads-number').html(data);
            }
        );
    }

    try {
        if ($(".initial-loading").is(":visible")) {
            $(".initial-loading").addClass("hidden").remove();
            update_reads_number();
        }
    } catch (err) {
        console.log(err);
    }
}

function show_initial_loading() {

    $(".initial-loading").removeClass("hidden");
}

function show_no_items() {

    $("#no-items").removeClass("hidden");
}
