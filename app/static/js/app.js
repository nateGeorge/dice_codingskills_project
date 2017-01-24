// todo: if send a term that hasn't been searched for before, send back a response
// that causes a progress bar to be shown
// then check back again in a bit
// also keep db of scrape requests and times
// queue the scrapes
// display estimate of time to result if the result hasn't been scraped before
// enable email subscription to when scrape is finished

var post_main_addr = 'http://0.0.0.0:10001' // 'http://cannadvise.me' //'http://35.161.235.42:10001'; // address with flask api
var jobs;
var skills = []; // for skills chosen by clicking on the skills bar chart

// click submit button when pressing enter from input form
// from: http://stackoverflow.com/questions/155188/trigger-a-button-click-with-javascript-on-the-enter-key-in-a-text-box
$("#job_search_input").keyup(function(event){
    if(event.keyCode == 13){
        $("#search_analyze").click();
    }
});

var post_addr;

var get_job_stats = function(search_term) {
    // first clear div
    $('#search_results').empty();
    post_addr = '/get_job_stats';
    $.post(post_main_addr + post_addr, data = {
      job: search_term
      }, function(data, err) {
        log_user_info(post_addr, search_term);
      if (data.length == 21) {
        // the data hasn't ever been scraped.
        // display message that it is currently being scraped, and will be updated in 1.5 mins
        console.log('updating db');
        $('#search_results').append('<h1>We don\'t have that search term in our database yet.  Check back tomorrow, we\'ll probably have it!');
        // $('#search_results').append('<h1>We\'re updating the db, this page will refresh in 1.5 mins when we have some results...');
      }
      // console.log(data);
      jobs = JSON.parse(data);

      var offset = 20; //Offset of 20px

      $('html, body').animate({
          scrollTop: $("#results").offset().top + offset
      }, 1000);
  });
}

var get_job_stats_form = function() {
  var input_val = $('#job_search_input').val();
  if (input_val != $('#job_search_input').attr('defaultValue')) {
    get_job_stats(input_val);
  }
}

// for user/device tracking
var log_user_info = function(cur_page, search_term) {
  $.getJSON('//freegeoip.net/json/?callback=?', null, function(ip_data) {
    console.log(JSON.stringify(ip_data, null, 2));
    if (cur_page == undefined) {
      cur_page = window.location.href.split('/')[3];
      console.log(cur_page);
    }
    if (search_term != undefined) {
      ip_data.search_term = search_term;
    }
    ip_data.current_page = cur_page;
    $.post(post_main_addr + '/send_user_info', data = ip_data, function(data, err) {
        console.log(data);
      });
  });
}

// log user on page loads
$(document).ready(log_user_info());
