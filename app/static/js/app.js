// todo: if send a term that hasn't been searched for before, send back a response
// that causes a progress bar to be shown
// then check back again in a bit
// also keep db of scrape requests and times
// queue the scrapes
// display estimate of time to result if the result hasn't been scraped before
// enable email subscription to when scrape is finished

var jobs;
var bokeh_skills_list;
var bokeh_locs_list;
var global_search_term;
var jobs;
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
    global_search_term = search_term;
    if (last_clicked != undefined && new Date() - last_clicked < 1000) {
      return;
    }
    last_clicked = new Date();
    $('#search_results1').empty();
    $('#search_results2').empty();
    $('#job_listings').empty();
    $('#salary_range').empty();
    $('#location_plot1').empty();
    $('#location_plot2').empty();
    $('#add_locs').empty();
    locs_fn();
    skills_fn();
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
        alert('We added "' + search_term + '" to the request list!  Check back in a day or two for results.');
        Pace.stop();
        return;
        // $('#search_results').append('<h1>We don\'t have that search term in our database yet.  Check back tomorrow, we\'ll probably have it!</h1>');
        // $('#search_results').append('<h1>We\'re updating the db, this page will refresh in 1.5 mins when we have some results...</h1>');
      } else {
        $('#results').css('display', 'block');
        var json_data = JSON.parse(data);
        var num_jobs = json_data['num_jobs'];
        jobs = json_data['jobs']
        skills_div = json_data['skills_div'];
        var locs_div = json_data['locs_div'];
        var states_div = json_data['states_div'];
        $('#search_results1').append($(skills_div).attr('id', 'skills_plot'));
        $('#location_plot1').append($(locs_div).attr('id', 'locs_plot'));
        $('#location_plot2').append($(states_div).attr('id', 'states_plot'));
        var skills_script = json_data['skills_script'];
        var locs_script = json_data['locs_script'];
        var states_script = json_data['states_script'];
        skills_script = skills_script
        eval(skills_script);
        eval(locs_script);
        eval(states_script);
        // center the plot in the div
        var clean_search = json_data['search_term']
        var salary_plot = json_data['salary_file'];
        // make it refresh with each date
        var shebang = new Date().getTime();
        var im_height = 480 / 1366 * hw[1];
        $('#search_results2').append('<img id="salary_img" src="' + salary_plot + '?' + shebang + '" height="' + im_height + '" width="' + im_height + '" />');
        $('#salary_img').css('display', 'inline-block');
        $('#locs_plot').css('display', 'inline-block');
        $('#states_plot').css('display', 'inline-block');
        var salaryrange = `
        <input class="form-control" type="text" value="0" defaultValue="0" id="sal_min"
        onblur="if (this.value == '') {this.value = '0';}"
        onfocus="if (this.value == '0') {this.value = '';}" />
        <span class="input-group-addon">-</span>
        <input class="form-control" type="text" value="1,000,000" defaultValue="1,000,000" id="sal_max"
        onblur="if (this.value == '') {this.value = '1,000,000';}"
        onfocus="if (this.value == '1,000,000') {this.value = '';}" />
        `;
        $('#salary_range').append(salaryrange);
        var locationinput = `
        <form id="loc_form" id="loc_form"><input class="form-control" type="text" value="enter locations to include" defaultValue="enter locations to include" id="loc_input"
        onblur="if (this.value == '') {this.value = 'enter locations to include';}"
        onfocus="if (this.value == 'enter locations to include') {this.value = '';}" /></form><br />
        `;
        $('#add_locs').append(locationinput);

        // update locations list on press enter in field
        $('#loc_form').keypress(function (e) {
          if (e.which == 13) {
            var new_loc = $('#loc_input').val();
            // this section pretty much cleans/standardizes the location
            comma_idx = $.inArray(',', new_loc);
            if (comma_idx != -1) {
              var city = new_loc.slice(0, comma_idx);
              var state = new_loc.slice(comma_idx + 1).replace(/ /g,'');
              if (state.length > 2) {
                state = abbrState(state, 'abbr');
                if (state == undefined) {
                  new_loc = city;
                } else {
                  state = state.toUpperCase();
                  new_loc = city + ', ' + state;
              }
            } else if (state.length == 2) {
              state = state.toUpperCase();
              new_loc = city + ', ' + state;
            } else {
              new_loc = city;
            }
          } else if (new_loc.length == 2) {
            new_loc = new_loc.toUpperCase();
          }

            var idx = $.inArray(new_loc, locations);
            if (idx == -1){
              locations.push(new_loc);
              $('#locs_list').append('<li class="list-group-item" style="color:#000;" id="' + new_loc + '">' + new_loc + '</li>');
            }
            return false;    //<---- Add this line
          }
        });
        // $('#loc_form').submit(function() {
        //   locations.push($('#loc_input').val());
        // });

        var reset_button = `
        <button id="reset_locations" type="button" class="btn btn-primary center-block" style="background-color: #006d59; display: inline-block" onclick="locs_fn()">Reset locations</button><br /><br />
        `
        $('#add_locs').append(reset_button);
        // un-hide filtering elements
        // actually don't need this since the entire div is hidden
        // $('#search_instructions1').css('display', 'block');
        // $('#search_instructions2').css('display', 'block');
        // $('#filter_jobs').css('display', 'block');
        populate_jobs(jobs);
        $('#num_jobs').remove();
        $('#filter_button_row').append('<h3 class="text-center" id="num_jobs">' + num_jobs + ' jobs found!</h3>');
      }

      var offset = 20; //Offset of 20px

      $('html, body').animate({
          scrollTop: $("#results").offset().top + offset
      }, 1000);
  });
}

var populate_jobs = function(jobs_list) {
  for (var i=0; i<jobs_list.length; i++) {
    var job_link = '<h3><a href="' + jobs_list[i]['detailUrl'] + '" style="color: white; text-decoration: underline;">' + jobs_list[i]['jobTitle'] + '</a></h3>';
    if (jobs_list[i]['predicted_salary'] == undefined | jobs_list[i]['predicted_salary'] == 0) {
      var job_salary = '<p>Salary: $' + Math.round(parseInt(jobs_list[i]['clean_sal'])/5000)*5000 + '</br> ';
    }
    else {
      var job_salary = '<p>Salary: $' + Math.round(parseInt(jobs_list[i]['predicted_salary'])/5000)*5000 + ' (predicted)</br> ';
    }
    var job_location = jobs_list[i]['location'] + '</br> ';
    var job_company = jobs_list[i]['company'] + '</br> ';
    var job_skills = 'Skills: ' + jobs_list[i]['clean_skills'][0];
    for (var j=1; j<jobs_list[i]['clean_skills'].length; j++) {
      job_skills = job_skills + ', ' + jobs_list[i]['clean_skills'][j];
    }
    job_skills = job_skills + '</br> ';
    var emp_type = jobs_list[i]['emp_type'] + '</br> ';
    if (jobs_list[i]['telecommute'] == 'Telecommuting available') {
      var job_tele = jobs_list[i]['telecommute'] + '</p>';
    } else {
      var job_tele = '';
    }
    var job_text = job_link + job_salary + job_company + job_location + job_skills + emp_type + job_tele;
    $('#job_listings').append(job_text);
  }
  $('#job_listings').append('<hr class="light">');
}


// pretty sure this function is doing nothing...need to get rid of probably
var get_job_stats_form = function() {
  var input_val = $('#job_search_input').val();
  if (input_val != $('#job_search_input').attr('defaultValue')) {
    get_job_stats(input_val);
  }
}

// for user/device tracking
var log_user_info = function(cur_page, search_term) {
  $.getJSON('//freegeoip.net/json/?callback=?', null, function(ip_data) {
    if (cur_page == undefined) {
      cur_page = window.location.href.split('/')[3];
    }
    if (search_term != undefined) {
      ip_data.search_term = search_term;
    }
    ip_data.current_page = cur_page;
    $.post(post_main_addr + '/send_user_info', data = ip_data, function(data, err) {
        //
      });
  });
}

// log user on page loads
$(document).ready(function() {
  log_user_info();
  post_main_addr = 'http://' + window.location.href.split('/')[2];
});

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
  $('#skills_list').empty();
  skills = [];
  // var idxs = selected['selected']['1d'].indices;
  // for (var i = 0; i < idxs.length; i++) {
  //     var cur_skill = bokeh_skills_list[idxs[i]];
  //     skills.push(cur_skill);
  // }
}

var locs_fn = function() {
  locations = [];
  $('#locs_list').empty();
  // var idxs = selected['selected']['1d'].indices;
  // for (var i = 0; i < idxs.length; i++) {
  //     var cur_skill = bokeh_skills_list[idxs[i]];
  //     skills.push(cur_skill);
  // }
}

var skills_click_set = false; // for setting the listening event in the taptool callback
var locs_click_set = false;

function abbrState(input, to){

    var states = [
        ['Arizona', 'AZ'],
        ['Alabama', 'AL'],
        ['Alaska', 'AK'],
        ['Arkansas', 'AR'],
        ['California', 'CA'],
        ['Colorado', 'CO'],
        ['Connecticut', 'CT'],
        ['Delaware', 'DE'],
        ['Florida', 'FL'],
        ['Georgia', 'GA'],
        ['Hawaii', 'HI'],
        ['Idaho', 'ID'],
        ['Illinois', 'IL'],
        ['Indiana', 'IN'],
        ['Iowa', 'IA'],
        ['Kansas', 'KS'],
        ['Kentucky', 'KY'],
        ['Louisiana', 'LA'],
        ['Maine', 'ME'],
        ['Maryland', 'MD'],
        ['Massachusetts', 'MA'],
        ['Michigan', 'MI'],
        ['Minnesota', 'MN'],
        ['Mississippi', 'MS'],
        ['Missouri', 'MO'],
        ['Montana', 'MT'],
        ['Nebraska', 'NE'],
        ['Nevada', 'NV'],
        ['New Hampshire', 'NH'],
        ['New Jersey', 'NJ'],
        ['New Mexico', 'NM'],
        ['New York', 'NY'],
        ['North Carolina', 'NC'],
        ['North Dakota', 'ND'],
        ['Ohio', 'OH'],
        ['Oklahoma', 'OK'],
        ['Oregon', 'OR'],
        ['Pennsylvania', 'PA'],
        ['Rhode Island', 'RI'],
        ['South Carolina', 'SC'],
        ['South Dakota', 'SD'],
        ['Tennessee', 'TN'],
        ['Texas', 'TX'],
        ['Utah', 'UT'],
        ['Vermont', 'VT'],
        ['Virginia', 'VA'],
        ['Washington', 'WA'],
        ['West Virginia', 'WV'],
        ['Wisconsin', 'WI'],
        ['Wyoming', 'WY'],
    ];

    if (to == 'abbr'){
        input = input.replace(/\w\S*/g, function(txt){return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();});
        for(i = 0; i < states.length; i++){
            if(states[i][0] == input){
                return(states[i][1]);
            }
        }
    } else if (to == 'name'){
        input = input.toUpperCase();
        for(i = 0; i < states.length; i++){
            if(states[i][1] == input){
                return(states[i][0]);
            }
        }
    }
}

var fjobs;

var filter_jobs = function() {
  var sal_range = [0, 1000000];
  var sal_min = $('#sal_min').val();
  var sal_max = $('#sal_max').val();
  if (sal_min != '0') {
    sal_range[0] = sal_min;
  }
  if (sal_max != '1,000,000') {
    sal_range[1] = sal_max;
  }
  console.log(global_search_term);
  $.post(post_main_addr + '/filter_jobs', data = {
    job: global_search_term,
    sal_range: sal_range,
    skills: skills,
    locations: locations
    }, function(data, err) {
      var json_data = JSON.parse(data);
      fjobs = json_data['filt_jobs'];
      var orig_num = json_data['orig_jobs'];
      var num_jobs = json_data['num_jobs'];
      $('#job_listings').empty();
      populate_jobs(fjobs);
      $('#num_jobs').remove();
      $('#filter_button_row').append('<h3 class="text-center" id="num_jobs">' + num_jobs + ' jobs found out of ' + orig_num + '.</h3>');
    });
}
