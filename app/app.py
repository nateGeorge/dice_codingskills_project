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
    print 'cookie:', user_id
    if user_id is None:
        return app.send_static_file('index.html')

    resp = make_response(render_template('index.html'))
    resp.set_cookie('dice_search', user_id)

@app.route('/get_job_stats', methods=['POST'])
def get_words():
    search_term = request.form.getlist('job')[0]
    print search_term
    fields = ['jobTitle', 'detailUrl', 'location', 'emp_type', 'salary', 'skills']
    jobs = ca.get_recent_jobs(search_term=search_term, fields=fields)
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
        resp = flask.Response(json.dumps(jobs))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/send_user_info', methods=['POST'])
def log_info():
    log_dict = request.form.to_dict()
    log_dict = ca.convert(log_dict)
    log_dict['datetime'] = datetime.now()
    print log_dict
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
