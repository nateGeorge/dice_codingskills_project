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

var get_job_stats = function(search_term) {
    $.post(post_main_addr + '/get_job_stats', data = {
      job: search_term
      }, function(data, err) {
      jobs = data;
      if (data.length == 21) {
        // the data hasn't ever been scraped.
        // display message that it is currently being scraped, and will be updated in 1.5 mins
        console.log('updating db');
      }
      // console.log(data);
      data = JSON.parse(data)
      // recs = data['recs'];
      // var links = data['links'];
      // $('.list-group-item').each(function(i, v) {
      //     $(v).text(recs[i]);
      //     $(v).attr('href', BASE_URL + links[i]);
      //     $(v).attr('target', 'blank');
      //     console.log(recs[i]);
      // });
  });
}
