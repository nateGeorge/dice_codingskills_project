// todo: if send a term that hasn't been searched for before, send back a response
// that causes a progress bar to be shown
// then check back again in a bit

var post_main_addr = 'http://0.0.0.0:10001' // 'http://cannadvise.me' //'http://35.161.235.42:10001'; // address with flask api
var jobs;
$.post(post_main_addr + '/get_job_stats', data = {
    job: 'data science'
}, function(data, err) {
    jobs = data;
    console.log(data);
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
