# todo: figure out way of keeping track of when something is scraping

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import json
import cPickle as pk
import re
from flask import Flask, request, make_response, jsonify
import flask
import dice_code.collect_api as ca
from pymongo import MongoClient
from werkzeug.datastructures import ImmutableMultiDict
from datetime import datetime
app = Flask(__name__, static_url_path='')

app.debug = True

# db for keeping track of scraping queue
DB_NAME = 'dice_jobs'
# db for user tracking
IP_COLL_NAME = 'user_tracking'

@app.route('/')
def index():
    user_id = request.cookies.get('dice_search')
    # print 'cookie:', user_id
    if user_id is None:
        return app.send_static_file('index.html')

    resp = make_response(render_template('index.html'))
    resp.set_cookie('dice_search', user_id)

@app.route('/get_job_stats', methods=['POST'])
def get_words():
    # print request.form
    search_term = request.form.getlist('job')[0]
    hw = request.form.getlist('hw[]')
    hw[0] = int(str(hw[0]))
    hw[1] = int(str(hw[1]))
    fields = ['jobTitle', 'detailUrl', 'location', 'emp_type', 'salary', 'skills', 'company', 'telecommute']
    jobs = ca.get_jobs(search_term=search_term, fields=fields)
    if jobs == 'updating db':
        insert_dict = {}
        insert_dict['search_term'] = search_term
        insert_dict['datetime'] = datetime.now()
        client = MongoClient()
        db = client[DB_NAME]
        coll = db['scraping_queue']
        coll.insert(insert_dict)
        resp = flask.Response(json.dumps({'updating db':True}))
    else:
        filename = ca.plot_salary_dist(search_term=search_term, hw=hw)
        skills_script, skills_div = ca.plot_top_skills(search_term=search_term, hw=hw)
        locs_script, locs_div = ca.plot_top_locs(search_term=search_term, hw=hw)
        states_script, states_div = ca.plot_top_states(search_term=search_term, hw=hw)
        jobs_dict = {}
        jobs_dict['skills_script'] = skills_script.encode('ascii', 'ignore')
        jobs_dict['skills_div'] = skills_div.encode('ascii', 'ignore')
        jobs_dict['locs_script'] = locs_script.encode('ascii', 'ignore')
        jobs_dict['locs_div'] = locs_div.encode('ascii', 'ignore')
        jobs_dict['states_script'] = states_script.encode('ascii', 'ignore')
        jobs_dict['states_div'] = states_div.encode('ascii', 'ignore')
        jobs_dict['jobs'] = jobs
        jobs_dict['search_term'] = re.sub('\s', '_', ca.clean_search_term(search_term))
        jobs_dict['salary_file'] = filename
        print filename
        resp = flask.Response(json.dumps(jobs_dict))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/send_user_info', methods=['POST'])
def log_info():
    log_dict = request.form.to_dict()
    log_dict = ca.convert(log_dict)
    log_dict['datetime'] = datetime.now()
    # print log_dict
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[IP_COLL_NAME]
    coll.insert(log_dict)
    client.close()
    resp = flask.Response('success!')
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10001, debug=True, threaded=True)
