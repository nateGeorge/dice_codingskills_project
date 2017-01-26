// todo: if send a term that hasn't been searched for before, send back a response
// that causes a progress bar to be shown
// then check back again in a bit
// also keep db of scrape requests and times
// queue the scrapes
// display estimate of time to result if the result hasn't been scraped before
// enable email subscription to when scrape is finished

var post_main_addr = 'http://0.0.0.0:10001' // 'http://cannadvise.me' //'http://35.161.235.42:10001'; // address with flask api
var jobs;
var bokeh_skills_list;
var bokeh_locs_list;
var test;
var test2;
var selected;
var selected_loc;
var locations = [];
var skills = []; // for skills chosen by clicking on the skills bar chart

// click submit button when pressing enter from input form
// from: http://stackoverflow.com/questions/155188/trigger-a-button-click-with-javascript-on-the-enter-key-in-a-text-box
$("#job_search_input").keyup(function(event){
    if(event.keyCode == 13){
        $("#search_analyze").click();
    }
});

var post_addr;
var last_clicked; // to prevent clicking too frequently
var skills_div;

var get_job_stats = function(search_term) {
    // first clear div
    if (last_clicked != undefined && new Date() - last_clicked < 1000) {
      return;
    }
    last_clicked = new Date();
    $('#search_results1').empty();
    $('#search_results2').empty();
    $('#job_listings').empty();
    $('#salary_range').empty();
    Pace.restart();
    // $('#skills_list').empty();
    post_addr = '/get_job_stats';
    var hw = [window.screen.availHeight, window.screen.availWidth];
    $.post(post_main_addr + post_addr, data = {
      job: search_term,
      hw: hw
      }, function(data, err) {
        log_user_info(post_addr, search_term);
      if (data.length == 21) {
        // the data hasn't ever been scraped.
        // display message that it is currently being scraped, and will be updated in 1.5 mins
        console.log('updating db');
        $('#search_results').append('<h1>We don\'t have that search term in our database yet.  Check back tomorrow, we\'ll probably have it!</h1>');
        // $('#search_results').append('<h1>We\'re updating the db, this page will refresh in 1.5 mins when we have some results...</h1>');
      } else {
        $('#results').css('display', 'block');
        var json_data = JSON.parse(data);
        var jobs = json_data['jobs']
        skills_div = json_data['skills_div'];
        var locs_div = json_data['locs_div'];
        console.log('locs_div:');
        console.log(locs_div);
        test = jobs;
        $('#search_results1').append($(skills_div).attr('id', 'skills_plot'));
        $('#location_plot').append($(locs_div).attr('id', 'locs_plot'));
        var skills_script = json_data['skills_script'];
        var locs_script = json_data['locs_script'];
        skills_script = skills_script
        eval(skills_script);
        eval(locs_script);
        // center the plot in the div
        var clean_search = json_data['search_term']
        var salary_plot = json_data['salary_file'];
        // make it refresh with each date
        var shebang = new Date().getTime();
        console.log('<img src="' + salary_plot + '?' + shebang + ' />');
        $('#search_results2').append('<img id="salary_img" src="' + salary_plot + '?' + shebang + '" />');
        $('#salary_img').css('display', 'inline-block');
        var salaryrange = `
        <input class="form-control" type="text" value="0" defaultValue="0" id="job_search_input"
        onblur="if (this.value == '') {this.value = '0';}"
        onfocus="if (this.value == '0') {this.value = '';}" />
        <span class="input-group-addon">-</span>
        <input class="form-control" type="text" value="1,000,000" defaultValue="1,000,000" id="job_search_input"
        onblur="if (this.value == '') {this.value = '1,000,000';}"
        onfocus="if (this.value == '1,000,000') {this.value = '';}" />
        `;
        $('#salary_range').append(salaryrange);
        // un-hide filtering elements
        // actually don't need this since the entire div is hidden
        // $('#search_instructions1').css('display', 'block');
        // $('#search_instructions2').css('display', 'block');
        // $('#filter_jobs').css('display', 'block');
        populate_jobs(jobs);
      }

      var offset = 20; //Offset of 20px

      $('html, body').animate({
          scrollTop: $("#results").offset().top + offset
      }, 1000);
  });
}

var populate_jobs = function(jobs) {
  for (var i=0; i<jobs.length; i++) {
    var job_link = '<h3><a href="' + jobs[i]['detailUrl'] + '" style="color: white; text-decoration: underline;">' + jobs[i]['jobTitle'] + '</a></h3>';
    var job_salary = '<p>' + jobs[i]['salary'] + '</br>';
    var job_location = jobs[i]['location'] + '</br> ';
    var job_company = jobs[i]['company'] + '</br> ';
    var job_skills = jobs[i]['skills'] + '</br> ';
    var emp_type = jobs[i]['emp_type'] + '</br> ';
    var job_tele = jobs[i]['telecommute'] + '</p>';
    var job_text = job_link + job_salary + job_location + job_skills + emp_type;
    $('#job_listings').append(job_text);
  }
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

// scroll to top on reload
window.onbeforeunload = function () {
  window.scrollTo(0, 0);
}

// for updating skills list if click outside of bars on skills chart
// http://stackoverflow.com/questions/965601/how-to-detect-left-click-anywhere-on-the-document-using-jquery
// IE might return 1 or 0 here, not sure
// $(document).click(function(e) {
//     // Check for left button
//     if (e.button == 0) {
//
//     }
// });

var skills_fn = function() {
  console.log('mousedown');
  $('#skills_list').empty();
  skills = [];
  // var idxs = selected['selected']['1d'].indices;
  // for (var i = 0; i < idxs.length; i++) {
  //     var cur_skill = bokeh_skills_list[idxs[i]];
  //     skills.push(cur_skill);
  // }
}

var locs_fn = function() {
  console.log('mousedown');
  locations = [];
  // var idxs = selected['selected']['1d'].indices;
  // for (var i = 0; i < idxs.length; i++) {
  //     var cur_skill = bokeh_skills_list[idxs[i]];
  //     skills.push(cur_skill);
  // }
}

var skills_click_set = false; // for setting the listening event in the taptool callback
var locs_click_set = false;
