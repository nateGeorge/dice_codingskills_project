import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import json
import cPickle as pk
import re
from flask import Flask, request, make_response
import flask
import code.collect_api as ca
app = Flask(__name__, static_url_path='')

app.debug = True

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
    job_text = request.form.getlist('job')
    print job_text
    # resp = flask.Response(json.dumps(word_dict))
    resp = flask.Response(json.dumps({'testing':123}))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10001, debug=True, threaded=True)
