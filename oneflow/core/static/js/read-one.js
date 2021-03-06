
//'use strict';

var read_actions_messages = {};
var auto_vanish_auto_read_timers = {};

function mark_something(article_id, mark_what, mark_inverse, send_notify, message, callback) {

    var run_callback = function() {
        //console.debug('trying to run callback ' + callback + '(' + oid + ')');
        typeof callback === 'function' && callback(article_id, mark_what, mark_inverse, send_notify, message);
    };

    var $article = $("#" + article_id);

    // console.debug('mark_something(' + article_id + ', ' + mark_what + ', ' + mark_inverse + ');');

    //
    // CSS classes are defined in a template-tag.
    //

    if(typeof message == 'undefined') {
        var message = null;
    }

    if(typeof mark_inverse == 'undefined') {
        var mark_inverse = false;
    }

    if (mark_inverse) {
        var klass    = 'not_' + mark_what;
        var inverse  = mark_what;
        var notifmsg = message || read_actions_messages[mark_what]['undone']

    } else {
        var klass   = mark_what;
        var inverse = 'not_' + mark_what;
        var notifmsg = message || read_actions_messages[mark_what]['done']
    }

    if(typeof send_notify == 'undefined') {
        var send_notify = false;
    }

    //
    // HEADS UP: the *row* uses article.id to ease its caching.
    //           But the `url-action-toggle` is *really* the URL
    //           of the User's **Read**.
    //
    $.get($article.data('url-action-toggle').replace('@@KEY@@', mark_what),
        function(){
            //console.debug($article.find(".action-mark-" + klass));
            //console.debug($article.find(".action-mark-" + inverse));

            // This is done automatically via CSS now.
            // $article.find(".action-mark-" + klass).fadeOut('fast', function(){
            //     $article.find(".action-mark-" + inverse).fadeIn('fast');
            // });

            $article.removeClass(inverse).addClass(klass);

            // in case the sidebars are not yet loaded while toggle_read()
            // occurs, we need to delay this a little. This problem happens
            // only when the user sets "mark read immediately" in his
            // preferences, this is a corner case.
            setTimeout(function() {
                $("#meta-" + article_id).removeClass(inverse).addClass(klass);
            }, 250);

            if (send_notify) {
                notify({
                    text: notifmsg,
                    type: 'success',
                    icon: false,
                    sticker: false,
                    nonblock: true,
                    nonblock_opacity: .2
                });
            }

            run_callback();
        }
    );

    // avoid any click event to propagate?
    return false;
}

function post_mark_triggers(article_id, attr_name, send_notify) {

    var $article      = $("#" + article_id);
    var is_bookmarked = $article.hasClass('is_bookmarked');
    var is_read       = $article.hasClass('is_read');
    var is_auto_read  = $article.hasClass('is_auto_read');
    var is_starred    = $article.hasClass('is_starred');
    var is_archived   = $article.hasClass('is_archived');

    if (attr_name == 'is_bookmarked') {

        // in any case, the auto_read status is cleared,
        // but no need to notify about that.
        if(is_bookmarked && is_auto_read) {
            mark_something(article_id, 'is_auto_read', false, false);
        }

        if (preferences.bookmarked_marks_unread) {

            //console.debug('item ' + article_id + ' bookmarked.');
            //console.debug($article.hasClass('is_bookmarked'));
            //console.debug($article.hasClass('is_read'));

            if(is_bookmarked && $article.hasClass('is_read')) {

                // 'true' means mark 'inverse' of is_read.
                mark_something(article_id, 'is_read', true, send_notify);

                // console.log('item ' + article_id + ' bookmarked; marked as unread too.');
            }
        }

        if (preferences.bookmarked_marks_archived) {
            if(is_bookmarked && !is_archived) {
                mark_something(article_id, 'is_archived', false, send_notify);
            }
        }

    } else if (attr_name == 'is_read') {

        // console.debug('item ' + article_id + ' starred.');

        // In any case, when marking read, the is_auto_read status is cleared.
        // NOTE: there could be a conflict (or loop) if everything was handled
        // from the triggers. Here we are in the post_mark_triggers(), thus
        // there will be no loop because the post_mark_triggers() do not
        // trigger, they just run complementary actions. If at anytime they
        // trigger things instead of beiing just post-triggers, there will be
        // a problem.
        if(is_read) {

            if(is_auto_read) {
                mark_something(article_id, 'is_auto_read', false, false);

            } else if (is_bookmarked) {
                // an article marked read implies it not meant to be read
                // later anymore. This could probably go into a preference,
                // but I find this pretty straightforward to understand.
                mark_something(article_id, 'is_bookmarked', false, false);
            }
        }

    }  else if (attr_name == 'is_starred') {

        // console.debug('item ' + article_id + ' starred.');

        // in any case, the auto_read status is cleared,
        // but no need to notify about that.
        if(is_starred && is_auto_read) {
            mark_something(article_id, 'is_auto_read', false, false);
        }

        if (preferences.starred_marks_read) {

            if(is_starred && $article.hasClass('not_is_read')) {

                mark_something(article_id, 'is_read', false, send_notify);

                // console.log('item ' + article_id + ' starred; marked as read too.');
            }
        }

        if (preferences.starred_removes_bookmarked) {

            if(is_starred && is_bookmarked) {

                mark_something(article_id, 'is_bookmarked', true, send_notify);

                // console.log('item ' + article_id + ' starred; unbookmarked too.');
            }
        }

        if (preferences.starred_marks_archived) {
            if (is_starred && !is_archived) {
                    mark_something(article_id, 'is_archived', false, send_notify);
            }
        }

    } else if (attr_name == 'is_auto_read') {

        if ((is_auto_read && !is_read) || (!is_auto_read && is_read)) {
            // is_auto_read syncs is_read, but do not trigger a notify.
            // we toggle only if status is not already synchronized,
            // else the UI is_read state will display the inverse of
            // what is stored server-side in the DB.
            console.log('auto_read syncs read: '+ is_auto_read)
            mark_something(article_id, 'is_read', is_auto_read, false);
        }

        if (preferences.mark_auto_read_hide_delay) {

            if (is_auto_read) {

                auto_vanish_auto_read_timers[article_id] = setTimeout(function(){

                    $article.addClass('vanished');

                    setTimeout(function() {
                        $article.addClass('hide');
                    }, 600);

                    delete auto_vanish_auto_read_timers[article_id];

                }, preferences.mark_auto_read_hide_delay);

            } else {
                try {

                    clearTimeout(auto_vanish_auto_read_timers[article_id]);
                    delete auto_vanish_auto_read_timers[article_id];

                } catch (err) {
                    console.error(err);
                }
            }
        }

    } else if ( _.indexOf(watch_attributes_names, attr_name) >= 0 ) {
        // the read was marked with a watch attribute (any of them)

        // marking with a read attribute clears the is_auto_read state.
        if ($article.hasClass(attr_name) && is_auto_read) {
            mark_something(article_id, 'is_auto_read', false, false);
        }

        if (preferences.watch_attributes_mark_archived) {
            if ($article.hasClass(attr_name) && !is_archived) {
                mark_something(article_id, 'is_archived', false, send_notify);
            }
        }
    }

    // else if (!is_archived) {
    //  Eventually clear every other attributes (watch, starred, bookmarked).
    //  See toggle_status() TODO note for details.
    // }
}

function current_status(article_id, attr_name) {
    return !!$("#" + article_id).hasClass(attr_name);
}

function toggle_status(event, article_id, attr_name, send_notify) {

    if (event !== null) {
        // avoid bubbling, notably when clicking on hover-muted
        // actions in collapsed items of the reading list. In the
        // same idea, avoid the click to reset the page view when
        // the anchor points to “#”.
        event.stopPropagation();
        event.preventDefault();
    }

    var $article = $("#" + article_id);
    //var is_bookmarked = $article.hasClass('is_bookmarked');
    //var is_starred    = $article.hasClass('is_starred');
    //var is_archived   = $article.hasClass('is_archived');

    // TODO: check if we are removing is_archived, and prevent it if the
    // article has any is_{starred,bookmarked,watch*}, or do not prevent
    // it if the user has the hypothetical
    // preferences.unarchive_clears_everything, letting the post_mark…()
    // function clear everything.

    mark_something(article_id, attr_name,
                   !!$article.hasClass(attr_name),
                   send_notify, null,
                   function() {
                        post_mark_triggers(article_id, attr_name, send_notify);
                   }
                );

    // if (ev) {
    //     ev.stopPropagation();
    // }
    return false;
}

function momentFromNow() {
    //return moment(string_date, "YYYYMMDD").fromNow();
    // Django's ISO produces: 2013-11-29T18:33:40+01:00
    // This is "YYYY-MM-DDTHH:mm:ssZZ" but Moment parses
    // ISO dates corectly without specifying them.

    $(this).html(moment($(this).html()).fromNow(true));
}
