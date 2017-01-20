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

var get_job_stats = function(search_term) {
    // first clear div
    $('#search_results').empty();
    $.post(post_main_addr + '/get_job_stats', data = {
      job: search_term
      }, function(data, err) {
      if (data.length == 21) {
        // the data hasn't ever been scraped.
        // display message that it is currently being scraped, and will be updated in 1.5 mins
        console.log('updating db');
        $('#search_results').append('<h1>We\'re updating the db, this page will refresh in 1.5 mins when we have some results...');
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
