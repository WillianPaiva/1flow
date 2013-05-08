/*
 * All the plugins init are in this file
 **/
$(document).ready(function() {

    $('.feature a').tooltip();
    $('.header-feature a').tooltip();
    $('a.link-tooltip').tooltip();

    try {
        $("#lang-flags input[type=image]").tooltip({placement: 'bottom'});
    } catch(err) {};
});
