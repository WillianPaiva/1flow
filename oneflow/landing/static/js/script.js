/*
 * All the plugins init are in this file
 **/
$(document).ready(function() {

    $('.feature a').tooltip();
    $('#promise_right a').tooltip();
    $('a.link-tooltip').tooltip();

    try {
        $("#lang-flags input[type=image]").tooltip({placement: 'bottom'});
    } catch(err) {};


    $('#promise_left a').popover({
        trigger: 'hover',
        template: '<div class="popover"><div class="arrow"></div>'
        + '<div class="popover-inner popover-presentation">'
        + '<h3 class="popover-title"></h3><div class="popover-content">'
        + '<iframe src="https://docs.google.com/presentation/d/1qzrhcuhIfYaVxJmYTFaKANFCJdvZ4zLqcVLiIDk63qw/embed?start=true&loop=false&delayms=3000" '
        + 'frameborder="0" width="652" height="420" allowfullscreen="true" mozallowfullscreen="true" webkitallowfullscreen="true"></iframe>'
        + '</div></div></div>',
    });
});
