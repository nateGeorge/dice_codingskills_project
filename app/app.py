import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import leafly.nlp_funcs as nl
import leafly.scrape_leafly as sl
import json
import cPickle as pk
import re
from flask import Flask, request, make_response
import flask
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

if __name__ == '__main__':
    pass
    # link_dict needed to get links from recommendation function
    # strains = sl.load_current_strains(True)
    # # make dict of names to links for sending links to rec page
    # names = [s.split('/')[-1] for s in strains]
    # link_dict = {}
    # for i, n in enumerate(names):
    #     link_dict[n] = strains[i]
    #
    # latest_model = 'leafly/10groupsrec_engine.model'
    # if not os.path.exists(latest_model):
    #     glp.train_and_save_everything(latest_model)
    # else:
    #     rec_engine = glp.load_engine(filename=latest_model)
    #
    # prod_group_dfs, user_group_dfs = glp.load_group_dfs()
    # prod_top_words, prod_word_counter = glp.load_top_words()
    # users_in_rec = pk.load(open('leafly/users_in_rec.pk'))
    app.run(host='0.0.0.0', port=10001, debug=True, threaded=True)
