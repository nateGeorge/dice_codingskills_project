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
app = Flask(__name__, static_url_path='')

app.debug = True

# dict for keeping track of what's already scraping
scraping_dict = {}

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
    jobs = 'updating db'#ca.get_recent_jobs(search_term=search_term, fields=fields)
    if jobs == 'updating db':
        resp = flask.Response(json.dumps({'updating db':True}))
    else:
        resp = flask.Response(json.dumps(jobs))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10001, debug=True, threaded=True)
