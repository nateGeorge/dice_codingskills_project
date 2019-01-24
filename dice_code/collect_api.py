# todo: map job locations, and allow selecting location to show jobs in that
# location
# also bar chart of top locations
# selector for recent or all-time jobs
# cluster jobs in bay area and denver, maybe suburbs of other cities

# todo: get number of jobs in different categories with 'unspecified', etc
# in salary field
# todo: make classifier that predicts if wage is hourly or annual based on
# features such as length of number, period in it, tfidf vector of
# hr, hourly, hour, annual, annualy, etc

# need this for flask to work (multiprocessing issue)
import matplotlib
try:
    matplotlib.use('gdk')
except:
    pass

import os
import psutil
import gc
import requests as req
import json
import re
from bs4 import BeautifulSoup as bs
from lxml import html
import pandas as pd
import numpy as np
from collections import Counter, defaultdict
from pymongo import MongoClient
from datetime import datetime
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import ticker
from . import word_vectors as wv
try:
    from bokeh.mpl import to_bokeh
    from bokeh.charts import Bar, output_file, show, save
    from bokeh.properties import Dict, Int, String
except:
    print('no bokeh.mpl, bokeh.charts, or bokeh.properties in latest bokeh, use earlier version or fix code')
from bokeh.plotting import figure

from bokeh.models import TickFormatter, HoverTool, GlyphRenderer, Range1d, TapTool
from bokeh.models.callbacks import CustomJS

from bokeh.embed import components
import traceback
import collections
import threading
from bokeh.models import (
  GMapPlot, GMapOptions, ColumnDataSource, Circle, DataRange1d, PanTool, WheelZoomTool, BoxSelectTool
)

BASE_URL = 'https://www.dice.com/jobs/q-{}-startPage-{}-jobs'
page = 1 # page number, 1-indexed
search_term = 'data science'
DB_NAME = 'dice_jobs'

rc_dict = {'axes.labelsize':'xx-large',
            'figure.titlesize':'xx-large',
            'legend.fontsize':'large',
            'xtick.labelsize':'large'}
# rcParams['] = 'medium'
plt.rcParams.update(rc_dict)

def create_url(search_term, base_url=BASE_URL, page=1):
    """
    Creates formatted url for a get request to dice api

    Parameters
    ----------
    base_url : string
        the starting dice api url
    page : int
        page number (1-indexed); 50 results per page
    search_term : string
        term to find in the job posting

    Returns
    -------
    formatted url string
    """
    search_term = clean_search_term(search_term)
    search_term = re.sub('\s', '_', search_term) # sub spaces with underscore
    # AND means it must find all words
    return BASE_URL.format(search_term, str(page))# + '&sort=2'# this last bit sorts by job title


def segment_jobs(job_postings, search_term='data science'):
    """
    Takes list of json job postings, and returns list of those
    containing 'data scientist', in the title, and a list of the rest.

    Parameters
    ----------
    job_postings : list
        json objects of job listings
    Returns
    -------
    ds_jobs : list
        list of ds jobs with 'data scientist' in title
    non_ds_jobs : list
        the remaining jobs
    """
    search_term = clean_search_term(search_term)
    relevant_jobs = []
    non_relevant_jobs = []
    for j in job_postings:
        title = str.lower(j['jobTitle']) # .encode('ascii', 'ignore')
        if search_term == 'data science':
            if 'data scientist' in title or 'data science' in title:
                relevant_jobs.append(j)
            else:
                non_relevant_jobs.append(j)
        elif search_term == 'front end developer':
            if 'front end developer' in title or 'front-end developer' in title or 'frontend developer' in title:
                relevant_jobs.append(j)
            else:
                non_relevant_jobs.append(j)
        elif search_term == 'full stack':
            if 'full stack' in title or 'fullstack' in title or 'full-stack' in title:
                relevant_jobs.append(j)
            else:
                non_relevant_jobs.append(j)
        else:
            if search_term in title:
                relevant_jobs.append(j)
            else:
                non_relevant_jobs.append(j)
        # doesn't seem to be any mle jobs, which is good
        # elif 'machine learning engineer' in title:
        #     mle_jobs.append(j)
    return relevant_jobs, non_relevant_jobs


def print_ds_jobs(ds_jobs, aspect='jobTitle'):
    """
    Looks through ds_jobs list and prints the specified field (aspect).

    Parameters
    ----------
    ds_jobs : list
        json job posting objects
    aspect : string
        field to print, one of [date, jobTitle, company, location, detailUrl]

    Returns
    -------
    None
    """
    for j in ds_jobs:
        print(j[aspect])


def dl_job_post(job_postings=None, url=None, num=0, path='test.html'):
    """
    Downloads one job posting to specified path.

    Parameters
    ----------
    job_postings : list
        json job posting objects -- if None, uses url
    url : string
        url to job posting -- if None, tries for job_postings list
    num : integer
        index of job posting
    path : string
        path to download file to

    Returns
    -------


    """
    if job_postings is not None:
        test_job = job_postings[num]
        res = req.get(test_job['detailUrl'])
    elif url is not None:
        res = req.get(url)
    else:
        print('either job_postings or url must be supplied as an argument')

    with open('test.html', 'w') as f:
        f.write(res.content)


def get_info(info):
    """
    Extracts info from job-info block in html
    """
    if len(info) == 4:
        skills = info[0].find('div', {'class':'iconsiblings'})
        skills = clean_page_skills(skills)
        emp_type = info[1].find('div', {'class':'iconsiblings'}).getText().strip('\n')
        salary = info[2].find('div', {'class':'iconsiblings'}).getText().strip('\n')
        tele_travel = info[3].find('div', {'class':'iconsiblings'}).getText()
        tele_travel = tele_travel.split('\n')
        tele_travel = [t for t in tele_travel if t != '']  # .encode('ascii', 'ignore')
        return skills, emp_type, salary, tele_travel
    else:
        # sometimes some of the info is missing
        skills = []
        emp_type = ''
        salary = ''
        tele_travel = ''
        for i in info:
            icons = i.find('span', {'class':'icons'}).get('class')
            if 'icon-plugin-1' in icons:
                skills = i.find('div', {'class':'iconsiblings'})
                skills = clean_page_skills(skills)
            elif 'icon-briefcase' in icons:
                emp_type = i.find('div', {'class':'iconsiblings'}).getText().strip('\n')
            elif 'icon-bank-note' in icons:
                salary = i.find('div', {'class':'iconsiblings'}).getText().strip('\n')
            elif 'icon-network-2' in icons:
                tele_travel = i.find('div', {'class':'iconsiblings'}).getText()
                tele_travel = tele_travel.split('\n')
                tele_travel = [t for t in tele_travel if t != '']  # .encode('ascii', 'ignore')

        return skills, emp_type, salary, tele_travel


def scrape_a_job(job_json=None, search_term='data science', insert_mongo=True, debug=False, url=None):
    """
    Scrapes important info from job posting.

    Parameters
    ----------
    job_url: string
        url to job posting
    search_term: string
        search term for dice job search; also the mongo db name
    insert_mongo: boolean
        if True, inserts data into mongo db

    Returns
    -------

    """
    search_term = clean_search_term(search_term)

    if insert_mongo and job_json is not None:
        # first check to see if the entry is already in the db
        client = MongoClient()
        db = client[DB_NAME]
        coll = db[search_term]
        in_db = coll.find(job_json).count()
        if in_db > 0:
            if debug:
                print('already in db')
            # don't think I want to update multi, but let's see how many there are
            coll.update(job_json, {'$set': {'recent': True}})#, multi=True)
            if in_db > 1:
                print('WARN: occurs', in_db, 'times')
            return None

    if url is not None:
        res = req.get(url)
    else:
        res = req.get(job_json['detailUrl'])
    if debug:
        print(job_json['detailUrl'])
    if not res.ok:
        if debug:
            print('uh-oh...')
            print(res.status)

    soup = bs(res.content, 'lxml')
    f404 = soup.findAll('p', {'class':'err_p'})
    if len(f404) > 0:
        if debug:
            print('found 404')
            print(f404[0].getText())
        if f404[0].getText() == "404 - The page you're looking for couldn't be found or it may have expired.":
            return None

    info = soup.findAll('div', {'class':'row job-info'})
    skills, emp_type, salary, tele_travel = get_info(info)
    # could do it this way, but there is also a unique id for this section
    # descr_xpath = '//*[@id="bd"]/div/div[1]/div[6]'
    # tree = html.fromstring(res.content)
    # descr = tree.xpath(descr_xpath)
    try:
        descr = soup.find('div', {'id':'jobdescSec'}).getText()
    except AttributeError:
        if debug:
            print('')
            print('couldn\'t find description')
            print('')
            traceback.print_exc()
        return None

    try:
        posted = soup.find('li', {'class': ['posted']}).text.strip()
    except:
        posted = ''
    try:
        location = soup.find('li', {'class': ['location']}).text.strip()
    except:
        location = ''

    # just in case this has a different contact location
    tree = html.fromstring(res.content)
    try:
        contact_loc_xpath = '//*[@id="contact-location"]'
        contact_location = tree.xpath(contact_loc_xpath)[0].text.strip()
    except:
        contact_location = ''

    if insert_mongo:
        clean_skills = clean_db_skills(skills)
        clean_skills = [c.capitalize() for c in clean_skills]
        entry_dict = {'skills': skills,
                        'clean_skills': clean_skills,
                        'emp_type': emp_type,
                        'salary': salary,
                        'telecommute': tele_travel[0],
                        'travel': tele_travel[1],
                        'description': descr,
                        'posted_text': posted,
                        'location': location,
                        'contact_location': contact_location}
        entry_dict.update(job_json)
        found = coll.find(entry_dict).count()
        if found == 0:
            entry_dict.update({'scraped_time': datetime.now(), 'recent': True})
            coll.insert_one(entry_dict)
        else:
            coll.update(entry_dict, {'$set':{'recent': True}})
        client.close()
        return None
    else:
        df = pd.DataFrame(data=np.array([', '.join(skills),
                                        emp_type,
                                        salary,
                                        tele_travel[0],
                                        tele_travel[1],
                                        descr]).reshape(1, -1),
                            columns=['csv_skills',
                                    'emp_type',
                                    'salary',
                                    'telecommute',
                                    'travel',
                                    'description'])

        return df


def clean_page_skills(skills):
    """
    Takes a string of skills from a dice job posting, cleans it, and returns
    the cleaned list of skills.

    Parameters
    ----------
    skills: string
        string of skills section from dice job posting

    Returns
    -------
    skills: list
        cleaned-up list of skills, each is a string
    """
    skills = str.lower(skills.getText().strip('\n').strip('\t').strip('\n'))  # .encode('ascii', 'ignore')
    skills = skills.split(',')
    # they are unicode, so convert to ascii strings (Python2 only)
    skills = [s.strip() for s in skills if s != 'etc']
    skills = [re.sub('\s*etc\s+', '', s) for s in skills]
    skills = [re.sub('\s+etc\s*', '', s) for s in skills]
    return skills


def scrape_all_jobs(job_postings, search_term=None, use_mongo=True, debug=False):
    """
    Loops through the list of job_postings and scrapes key info from each.
    """
    search_term = clean_search_term(search_term)

    full_df = None
    for i, j in enumerate(job_postings):
        if debug:
            print(i, j['jobTitle'], j['company'])
        if use_mongo:
            scrape_a_job(j, search_term=search_term, insert_mongo=use_mongo, debug=debug)
        else:
            df = scrape_a_job(j, search_term=search_term, insert_mongo=use_mongo, debug=debug)
            if full_df is None:
                full_df = df
            else:
                full_df = full_df.append(df)

    if use_mongo:
        return None

    return full_df


def get_skills_tf(df):
    """
    Calculates term-frequency for skills based on a pandas dataframe.
    """
    skills_temp = df['csv_skills'].values
    skills_temp = [str.lower(s).split(', ') for s in skills_temp]  # .encode('ascii', 'ignore')
    skills_list = []
    for s in skills_temp:
        skills_list.extend([sk.split('/') for sk in s])

    skills_count = Counter(skills_list)
    return skills_count


def split_skills(skills_list, char='-'):
    """
    Splits each skill in skills_list on char
    """
    clean_skills_list = []
    for s in skills_list:
        clean_skills_list.extend(s.split('/'))

    return clean_skills_list


def clean_skills_in_db(search_term='data science'):
    """
    Cleans skills for each entry in the db for the search term.
    """
    search_term = clean_search_term(search_term)
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    jobs = list(coll.find())
    for j in jobs:
        clean_skills = clean_db_skills(j['skills'])
        clean_skills = [c.capitalize() for c in clean_skills]
        coll.update_one(j, {'$set': {'clean_skills': clean_skills}})

    client.close()


def clean_db_skills(skills_list):
    """
    Cleans skills list from mongoDB entry.
    """
    # don't think I need this
    #temp_skills = [str.lower(s.encode('ascii', 'ignore')).split(', ') for s in skills_list]
    clean_skills_list = [s.lower() for s in skills_list]  # .encode('ascii', 'ignore')
    for char in ['-', '/', ' or ', ' & ', ' and ']:
        clean_skills_list = split_skills(clean_skills_list, char=char)

    # some weird bug I can't figure out where it can't find the '/'
    # going to do this for everything else to be safe
    for s in clean_skills_list:
        if s == 'sql/nosql':
            print('sql/nosql in s (2):', s)
            print('search:', re.search('/', s))
            print(orig)
            print(clean_skills_list)
            print(now)
        if re.search('^or ', s) is not None:
            clean_skills_list.remove(s)
            clean_skills_list.append(s[3:])
    clean_skills_list = [s.strip() for s in clean_skills_list if s.strip() != '']

    return clean_skills_list


def get_skills_tf_mongo(search_term='data science'):
    """
    Calculated term-frequency for skills based on data in a mongoDB.
    """
    search_term = clean_search_term(search_term)
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    jobs = list(coll.find())
    if len(jobs) == 0:
        continuous_scrape(search_term=search_term)
        jobs = coll.find()
    skills_list = []
    for j in jobs:
        skills_list.extend(clean_db_skills(j['skills']))

    skills_count = Counter(skills_list)
    client.close()

    return skills_count


class FixedTickFormatter(TickFormatter):
    try:
        labels = Dict(Int, String, help="""
        A mapping of integer ticks values to their labels.
        """)
    except:
        print('Dict not loaded from bokeh')

    JS_CODE =  """
    _ = require "underscore"
    Model = require "model"
    p = require "core/properties"
    class FixedTickFormatter extends Model
      type: 'FixedTickFormatter'
      doFormat: (ticks) ->
        labels = @get("labels")
        return (labels[tick] ? "" for tick in ticks)
      @define {
        labels: [ p.Any ]
      }
    module.exports =
      Model: FixedTickFormatter
    """

    __implementation__ = JS_CODE


def old_plot_top_skills(top_skills_all=None, search_term='data science', live=False, hw=None):
    """
    BACKUP OF PLOTTING THAT WORKS
    Makes bar graph of top skills from a counter object.

    Parameters
    ----------
    top_skills_all: Counter
        if not None, used as skills Counter for plotting
    search_term: string
        if top_skills_all is None, this is used to get skills Counter object
    live: boolean
        if True, will show plot after saving it
    """
    if hw is not None:
        # scale factor for screen width
        scale_factor = int(500 / 1366. * hw[1])
    search_term = clean_search_term(search_term)
    if top_skills_all is None:
        if search_term is None:
            return 'search term or top_skills must be supplied'

        skills = get_skills_tf_mongo(search_term=search_term)
        top_skills_all = [s for s in skills.most_common() if s[1] >= 5]

    top_skills = [(str.capitalize(s[0]), s[1]) for s in top_skills_all[:30]]
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    total_jobs = float(coll.find().count())
    client.close()
    # get % counts for each skills
    norm_counts = []
    label_dict = {}
    for i, s in enumerate(top_skills):
        label_dict[i] = s[0]
        norm_counts.append(s[1] / total_jobs * 100)

    df = pd.DataFrame({'skill':[s for s in top_skills], 'pct jobs with skill':norm_counts})
    # clean up df
    df['skill'] = df['skill'].apply(lambda x: x[0])
    df['pct jobs with skill'] = df['pct jobs with skill'].apply(lambda x: round(x, 0))
    df['color'] = '#6999de'
    # the @something is for a column of the dataframe
    # hover = HoverTool(
    #     tooltips=[
    #         ("skill", "$skill"),
    #         ("pct jobs with skill", "$pct jobs with skill")
    #     ]
    # )
    # trying another way to input data for hovertool
    # sourceData = ColumnDataSource(
    #     data = Dict(df.to_dict())
    #     )
    tools = 'pan,lasso_select,box_select,reset,tap'.split(',')
    #tools.append(hover)
    src = df.to_dict(orient='list')
    full_source = ColumnDataSource(src)
    src.update({'index': list(range(df['skill'].shape[0]))})
    #src = ColumnDataSource(src)

    # high-level way to do it, but can't label anything but the indices...
    # p = Bar(data=df, label='index', tools=tools, values='pct jobs with skill', title="Top skills for data science", legend=False, width=1000, height=1000)
    # p.select(dict(type=GlyphRenderer))
    # hover = p.select(dict(type=HoverTool))
    # hover.tooltips = [('skill', '@x'), ('test', '@y')]

    # another way to set hover, but second step wasn't working
    # hover.tooltips = [('Value of ID',' $x'),('Value of Total',' @y')]

    # mid-level way to do it
    max_df = round(df['pct jobs with skill'].max() / 10 + 0.5) * 10
    p = figure(title='Top skills for ' + search_term, width=scale_factor, height=scale_factor, tools='tap', y_range=Range1d(0, max_df), x_range=Range1d(-0.5, 29.5))
    # full_source = None
    for i, r in df.iterrows():
        src = r.to_dict()
        for k, v in src.items():
            src[k] = [v]
        src['index'] = [i]
        source = ColumnDataSource(src)
        # if full_source is None:
        #     full_source = source
        # else:
        #     full_source.add(src)

        p.vbar(source=source, x='index', width=0.9, bottom=0,
            top='pct jobs with skill', color='color')

    taptool = p.select(type=TapTool)
    taptool.callback = CustomJS(args=dict(xr=p.x_range, source=full_source), code="""
    // JavaScript code goes here

    // load jquery if not already loaded
    // Anonymous "self-invoking" function
    (function() {
        var bokeh_data = source.get('data');
        console.log(source);
        console.log(bokeh_data);
        var data_skills = bokeh_data['skill'];
        console.log(data_skills);
        // Load the script
        var script = document.createElement("SCRIPT");
        script.src = 'https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js';
        script.type = 'text/javascript';
        document.getElementsByTagName("head")[0].appendChild(script);

        // Poll for jQuery to come into existance
        var checkReady = function(callback) {
            if (window.jQuery) {
                callback(jQuery);
            }
            else {
                window.setTimeout(function() { checkReady(callback); }, 100);
            }
        };

        // Start polling...
        checkReady(function($) {
            // Use $ here...
            var cur_skill = cb_obj['data']['skill'][0];
            var arrpos = $.inArray(cur_skill, skills);
            console.log(cur_skill);
            var datapos = $.inArray(cur_skill, data_skills)
            console.log(datapos);
            var skill = cb_obj['data']['skill']
            if (arrpos != -1) {
                skills.splice(arrpos, 1); // remove one element from arrpos
                $("[id='" + skill + "']").remove();
                bokeh_data.color[datapos] = '#6999de';
                source.trigger('change');
            } else {
                // need to first make the global skills array like var skills = [];
                skills.push(skill);
                $('#skills_list').append('<li class="list-group-item" style="color:#000;" id="' + skill + '">' + skill + '</li>');
                bokeh_data.color[datapos] = '#e20d0d';
                source.trigger('change');
            }
        });
    })();

    console.log(cb_obj);
    a = cb_obj;
    console.log(cb_obj['data']['skill']);

    // models passed as args are automagically available
    // xr.start = a;
    // xr.end = b;

    """)

    # todo: fix hovertool.  works in standalone plot, but not embedded...hmmm
    # hover = HoverTool(tooltips=[('skill', '@skill'), ('pct jobs with skill', '@{pct jobs with skill}')])
    # p.add_tools(hover)

    # changes labels from 0, 1, 2 etc to Python, SQL, Hadoop, etc
    p.xaxis[0].formatter = FixedTickFormatter(labels=label_dict)
    #SingleIntervalTicker

    # this is a way to set the hover tooltip when you can use a ColumnDataSource
    # which you can't with high level (i.e. Bar()) charts right now
    # p.select(dict(type=GlyphRenderer))
    # hover = p.select(dict(type=HoverTool))
    # hover.tooltips = [('skill', '@skill'), ('test', '@y')]

    # this works but displays a number for index, not label
    # hover.tooltips = [('index', '@index'), ('test', '@y')]

    # set major/minor ticks to be same length
    # p.xaxis[0].minor_tick_in = p.xaxis[0].major_tick_in
    # p.xaxis[0].minor_tick_out = p.xaxis[0].major_tick_out
    # better: just remove minor ticks
    p.xaxis[0].ticker.num_minor_ticks = 0
    p.xaxis[0].ticker.desired_num_ticks = df.shape[0]
    # remove grid lines
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.xaxis.major_label_orientation = 89.0
    # I think we already know the xaxis is a skill...
    # p.xaxis.axis_label = 'skill'
    p.yaxis.axis_label = 'percent of jobs with skill'
    # this is for a 1000x1000 plot
    # p.xaxis.axis_label_text_font_size = "30pt"
    # p.xaxis.major_label_text_font_size = "15pt"
    # p.yaxis.axis_label_text_font_size = "30pt"
    # p.yaxis.major_label_text_font_size = "15pt"
    # p.title_text_font_size = "30pt"
    # this is for 500x500
    big = str(int(scale_factor / 500. * 15))
    small = str(int(scale_factor / 500. * 8))
    p.xaxis.axis_label_text_font_size = big + "pt"
    p.xaxis.major_label_text_font_size = small + "pt"
    p.yaxis.axis_label_text_font_size = big + "pt"
    p.yaxis.major_label_text_font_size = small + "pt"
    p.title.text_font_size = big + "pt"
    if live:
        show(p)
    else:
        script, div = components(p, wrap_script=False)
        return script, div
        # was saving it before, but that generates a complete html file
        # output_file('app/static/img/' + re.sub('\s', '_', search_term) + '_skills.html')
        # save(p)


def plot_top_skills(top_skills_all=None, search_term='data science', live=False, hw=None):
    """
    Makes bar graph of top skills from a counter object.

    Parameters
    ----------
    top_skills_all: Counter
        if not None, used as skills Counter for plotting
    search_term: string
        if top_skills_all is None, this is used to get skills Counter object
    live: boolean
        if True, will show plot after saving it
    """
    if hw is not None:
        # scale factor for screen width
        # seems like hw is no longer a great estimate of screen width
        scale_factor = int(500 / 1366. * hw[1] * 0.75)

    search_term = clean_search_term(search_term)
    if top_skills_all is None:
        if search_term is None:
            return 'search term or top_skills must be supplied'

        skills = get_skills_tf_mongo(search_term=search_term)
        top_skills_all = [s for s in skills.most_common() if s[1] >= 5]

    top_skills = [(str.capitalize(s[0]), s[1]) for s in top_skills_all[:30]]
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    total_jobs = float(coll.find().count())
    client.close()
    # get % counts for each skills
    norm_counts = []
    label_dict = {}
    for i, s in enumerate(top_skills):
        label_dict[i] = s[0]
        norm_counts.append(s[1] / total_jobs * 100)

    df = pd.DataFrame({'skill': [s for s in top_skills], 'pct jobs with skill': norm_counts})
    # clean up df
    df['skill'] = df['skill'].apply(lambda x: x[0])
    # don't think we want to do this
    # df['pct jobs with skill'] = df['pct jobs with skill'].apply(lambda x: round(x, 0))
    df['color'] = '#6999de'
    # the @something is for a column of the dataframe
    # hover = HoverTool(
    #     tooltips=[
    #         ("skill", "$skill"),
    #         ("pct jobs with skill", "$pct jobs with skill")
    #     ]
    # )
    # trying another way to input data for hovertool
    # sourceData = ColumnDataSource(
    #     data = Dict(df.to_dict())
    #     )
    tools = 'pan,lasso_select,box_select,reset,tap'.split(',')
    #tools.append(hover)
    src = df.to_dict(orient='list')
    src.update({'index': list(range(df['skill'].shape[0]))})
    full_source = ColumnDataSource(src)
    #src = ColumnDataSource(src)

    # high-level way to do it, but can't label anything but the indices...
    # p = Bar(data=full_source, label='index', tools=['taptool'], values='pct jobs with skill', title="Top skills for data science", legend=False, width=scale_factor, height=scale_factor)
    # p.select(dict(type=GlyphRenderer))
    # hover = p.select(dict(type=HoverTool))
    # hover.tooltips = [('skill', '@x'), ('test', '@y')]

    # another way to set hover, but second step wasn't working
    # hover.tooltips = [('Value of ID',' $x'),('Value of Total',' @y')]

    # mid-level way to do it
    max_df = round(df['pct jobs with skill'].max() / 10 + 0.5) * 10
    p = figure(title='Top skills for ' + search_term, width=scale_factor, height=scale_factor, tools='tap', y_range=Range1d(0, max_df), x_range=Range1d(-0.5, 29.5))
    p.vbar(source=full_source, x='index', width=0.9, bottom=0,
        top='pct jobs with skill', color='color')
    # for i, r in df.iterrows():
    #     src = r.to_dict()
    #     for k, v in src.iteritems():
    #         src[k] = [v]
    #     src['index'] = [i]
    #     source = ColumnDataSource(src)
    #     if full_source is None:
    #         full_source = source
    #     else:
    #         full_source.add(src)
    #
    #     p.vbar(source=source, x='index', width=0.9, bottom=0,
    #         top='pct jobs with skill', color='color')

    taptool = p.select(type=TapTool)
    taptool.callback = CustomJS(args=dict(xr=p.x_range, source=full_source), code="""
    // JavaScript code goes here

    // load jquery if not already loaded
    // Anonymous "self-invoking" function
    (function() {
        test = cb_obj;
        var bokeh_data = source['data'];
        var data_skills = bokeh_data['skill'];
        bokeh_skills_list = data_skills;
        // Load the script
        var script = document.createElement("SCRIPT");
        script.src = 'https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js';
        script.type = 'text/javascript';
        document.getElementsByTagName("head")[0].appendChild(script);

        // Poll for jQuery to come into existance
        var checkReady = function(callback) {
            if (window.jQuery) {
                callback(jQuery);
            }
            else {
                window.setTimeout(function() { checkReady(callback); }, 100);
            }
        };

        // Start polling...
        checkReady(function($) {
            // Use $ here...
            var cur_skill = cb_obj['data']['skill'];
            selected = cb_obj; // need to declare selected as var earlier,
            // use selected['selected']['1d'].indices to get selected elements
            var arrpos = $.inArray(cur_skill, skills);
            var datapos = $.inArray(cur_skill, data_skills);
            var skill = cb_obj['data']['skill'];
            $('#skills_list').empty();
            var selected_idxs = selected['selected']['1d'].indices;
            for (var i = 0; i < selected_idxs.length; i++) {
                var cur_skill = bokeh_skills_list[selected_idxs[i]];
                $('#skills_list').append('<li class="list-group-item" style="color:#000;" id="' + cur_skill + '">' + cur_skill + '</li>');
                skills.push(cur_skill);
            }
            if (arrpos != -1) {
                //skills.splice(arrpos, 1); // remove one element from arrpos
                //$("[id='" + skill + "']").remove();
                //bokeh_data.color[datapos] = '#6999de';
                source.trigger('change');
            } else {
                // need to first make the global skills array like var skills = [];
                //skills.push(skill);
                //$('#skills_list').append('<li class="list-group-item" style="color:#000;" id="' + skill + '">' + skill + '</li>');
                //bokeh_data.color[datapos] = '#e20d0d';
                source.trigger('change');
            }
        });
    })();

    console.log(cb_obj);
    a = cb_obj;
    console.log(cb_obj['data']['skill']);

    // models passed as args are automagically available
    // xr.start = a;
    // xr.end = b;
    // listen for click in div, and clear skills list accordingly
    if (skills_click_set == false) {
        $('#skills_plot').click(skills_fn);
        skills_click_set = true;
    }

    """)

    # todo: fix hovertool.  works in standalone plot, but not embedded...hmmm
    # hover = HoverTool(tooltips=[('skill', '@skill'), ('pct jobs with skill', '@{pct jobs with skill}')])
    # p.add_tools(hover)

    # changes labels from 0, 1, 2 etc to Python, SQL, Hadoop, etc
    p.xaxis[0].formatter = FixedTickFormatter(labels=label_dict)
    #SingleIntervalTicker

    # this is a way to set the hover tooltip when you can use a ColumnDataSource
    # which you can't with high level (i.e. Bar()) charts right now
    # p.select(dict(type=GlyphRenderer))
    # hover = p.select(dict(type=HoverTool))
    # hover.tooltips = [('skill', '@skill'), ('test', '@y')]

    # this works but displays a number for index, not label
    # hover.tooltips = [('index', '@index'), ('test', '@y')]

    # set major/minor ticks to be same length
    # p.xaxis[0].minor_tick_in = p.xaxis[0].major_tick_in
    # p.xaxis[0].minor_tick_out = p.xaxis[0].major_tick_out
    # better: just remove minor ticks
    p.xaxis[0].ticker.num_minor_ticks = 0
    p.xaxis[0].ticker.desired_num_ticks = df.shape[0]
    # remove grid lines
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.xaxis.major_label_orientation = 89.0
    # I think we already know the xaxis is a skill...
    # p.xaxis.axis_label = 'skill'
    p.yaxis.axis_label = 'percent of jobs with skill'
    # this is for a 1000x1000 plot
    # p.xaxis.axis_label_text_font_size = "30pt"
    # p.xaxis.major_label_text_font_size = "15pt"
    # p.yaxis.axis_label_text_font_size = "30pt"
    # p.yaxis.major_label_text_font_size = "15pt"
    # p.title_text_font_size = "30pt"
    # this is for 500x500
    big = str(int(scale_factor / 500. * 15))
    small = str(int(scale_factor / 500. * 8))
    p.xaxis.axis_label_text_font_size = big + "pt"
    p.xaxis.major_label_text_font_size = small + "pt"
    p.yaxis.axis_label_text_font_size = big + "pt"
    p.yaxis.major_label_text_font_size = small + "pt"
    p.title.text_font_size = big + "pt"
    if live:
        show(p)
    else:
        script, div = components(p, wrap_script=False)
        return script, div
        # was saving it before, but that generates a complete html file
        # output_file('app/static/img/' + re.sub('\s', '_', search_term) + '_skills.html')
        # save(p)


def plot_top_locs(search_term='data science', live=False, hw=None, recent=False):
    """
    Makes bar graph of top locations from a search term.

    Parameters
    ----------
    top_skills_all: Counter
        if not None, used as skills Counter for plotting
    search_term: string
        if top_skills_all is None, this is used to get skills Counter object
    live: boolean
        if True, will show plot after saving it
    """
    scale_factor = 500
    if hw is not None:
        # scale factor for screen width
        scale_factor = int(500 / 1366. * hw[1] * 0.75)

    search_term = clean_search_term(search_term)

    jobs = get_jobs(search_term=search_term, recent=recent)
    jobs_df = pd.DataFrame(jobs)
    jobs_df = jobs_df[jobs_df['location'] != '']

    top_locs = jobs_df['location'].value_counts()[:30]
    locations = top_locs.index

    total_jobs = jobs_df.shape[0]
    # get % counts for each skills
    norm_counts = []
    label_dict = {}
    for i, t, l in zip(list(range(top_locs.shape[0])), top_locs, locations):
        label_dict[i] = l
        norm_counts.append(float(t) / total_jobs * 100)

    df = pd.DataFrame({'location': [l for l in locations], 'pct jobs at location': norm_counts, 'index': list(range(top_locs.shape[0]))})
    # clean up df
    df['color'] = '#6999de'

    src = df.to_dict(orient='list')
    full_source = ColumnDataSource(src)

    # mid-level way to do it
    max_df = round(df['pct jobs at location'].max() / 10 + 0.5) * 10
    p = figure(title='Top locations for ' + search_term, width=scale_factor, height=scale_factor, tools='tap', y_range=Range1d(0, max_df), x_range=Range1d(-0.5, 29.5))
    p.vbar(source=full_source, x='index', width=0.9, bottom=0,
        top='pct jobs at location', color='color')

    taptool = p.select(type=TapTool)
    taptool.callback = CustomJS(args=dict(xr=p.x_range, source=full_source), code="""
    // JavaScript code goes here

    // load jquery if not already loaded
    // Anonymous "self-invoking" function
    (function() {
        test2 = cb_obj;
        var bokeh_data = source['data'];
        var data_locs = bokeh_data['location'];
        bokeh_locs_list = data_locs;
        // Load the script
        var script = document.createElement("SCRIPT");
        script.src = 'https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js';
        script.type = 'text/javascript';
        document.getElementsByTagName("head")[0].appendChild(script);

        // Poll for jQuery to come into existance
        var checkReady = function(callback) {
            if (window.jQuery) {
                callback(jQuery);
            }
            else {
                window.setTimeout(function() { checkReady(callback); }, 100);
            }
        };

        // Start polling...
        checkReady(function($) {
            // Use $ here...
            var cur_loc = cb_obj['data']['locations'];
            selected_loc = cb_obj; // need to declare selected as var earlier,
            // use selected['selected']['1d'].indices to get selected elements
            var arrpos = $.inArray(cur_loc, bokeh_locs_list);
            var datapos = $.inArray(cur_loc, data_locs);
            var loc = cb_obj['data']['location'];
            $('#locs_list').empty();
            var selected_idxs = selected_loc['selected']['1d'].indices;
            for (var i = 0; i < selected_idxs.length; i++) {
                var cur_loc = bokeh_locs_list[selected_idxs[i]];
                $('#locs_list').append('<li class="list-group-item" style="color:#000;" id="' + cur_loc + '">' + cur_loc + '</li>');
                locations.push(cur_loc);
            }
            source.trigger('change');
        });
    })();

    // models passed as args are automagically available
    // xr.start = a;
    // xr.end = b;
    // listen for click in div, and clear skills list accordingly
    if (locs_click_set == false) {
        $('#locs_plot').click(locs_fn);
        locs_click_set = true;
    }

    """)

    # todo: fix hovertool.  works in standalone plot, but not embedded...hmmm
    # hover = HoverTool(tooltips=[('skill', '@skill'), ('pct jobs with skill', '@{pct jobs with skill}')])
    # p.add_tools(hover)

    # changes labels from 0, 1, 2 etc to Python, SQL, Hadoop, etc
    p.xaxis[0].formatter = FixedTickFormatter(labels=label_dict)
    #SingleIntervalTicker

    # this is a way to set the hover tooltip when you can use a ColumnDataSource
    # which you can't with high level (i.e. Bar()) charts right now
    # p.select(dict(type=GlyphRenderer))
    # hover = p.select(dict(type=HoverTool))
    # hover.tooltips = [('skill', '@skill'), ('test', '@y')]

    # this works but displays a number for index, not label
    # hover.tooltips = [('index', '@index'), ('test', '@y')]

    # set major/minor ticks to be same length
    # p.xaxis[0].minor_tick_in = p.xaxis[0].major_tick_in
    # p.xaxis[0].minor_tick_out = p.xaxis[0].major_tick_out
    # better: just remove minor ticks
    p.xaxis[0].ticker.num_minor_ticks = 0
    p.xaxis[0].ticker.desired_num_ticks = df.shape[0]
    # remove grid lines
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.xaxis.major_label_orientation = 89.0
    # I think we already know the xaxis is a skill...
    # p.xaxis.axis_label = 'skill'
    p.yaxis.axis_label = 'percent of jobs at location'
    # this is for a 1000x1000 plot
    # p.xaxis.axis_label_text_font_size = "30pt"
    # p.xaxis.major_label_text_font_size = "15pt"
    # p.yaxis.axis_label_text_font_size = "30pt"
    # p.yaxis.major_label_text_font_size = "15pt"
    # p.title_text_font_size = "30pt"
    # this is for 500x500
    big = str(int(scale_factor / 500. * 15))
    small = str(int(scale_factor / 500. * 8))
    p.xaxis.axis_label_text_font_size = big + "pt"
    p.xaxis.major_label_text_font_size = small + "pt"
    p.yaxis.axis_label_text_font_size = big + "pt"
    p.yaxis.major_label_text_font_size = small + "pt"
    p.title.text_font_size = big + "pt"
    if live:
        output_file('top_locations.html', title='top locations plot')
        show(p)
    else:
        script, div = components(p, wrap_script=False)
        return script, div
        # was saving it before, but that generates a complete html file
        # output_file('app/static/img/' + re.sub('\s', '_', search_term) + '_skills.html')
        # save(p)


def extract_state(x):
    """
    Extracts state from location.
    """
    split = x.split(', ')
    if len(split) != 2:
        return ''

    return split[1]


def plot_top_states(search_term='data science', live=False, hw=None, recent=False):
    """
    Makes bar graph of top locations from a search term.

    Parameters
    ----------
    top_skills_all: Counter
        if not None, used as skills Counter for plotting
    search_term: string
        if top_skills_all is None, this is used to get skills Counter object
    live: boolean
        if True, will show plot after saving it
    """
    scale_factor = 500
    if hw is not None:
        # scale factor for screen width
        scale_factor = int(500 / 1366. * hw[1] * 0.75)

    search_term = clean_search_term(search_term)

    jobs = get_jobs(search_term=search_term, recent=recent)
    jobs_df = pd.DataFrame(jobs)
    jobs_df['state'] = jobs_df['location'].apply(lambda x: extract_state(x))
    jobs_df = jobs_df[jobs_df['state'] != '']

    top_states = jobs_df['state'].value_counts()[:30]
    states = top_states.index

    total_jobs = jobs_df.shape[0]
    # get % counts for each skills
    norm_counts = []
    label_dict = {}
    for i, t, l in zip(list(range(top_states.shape[0])), top_states, states):
        label_dict[i] = l
        norm_counts.append(float(t) / total_jobs * 100)

    df = pd.DataFrame({'location': [s for s in states], 'pct jobs in state': norm_counts, 'index': list(range(top_states.shape[0]))})
    # clean up df
    df['color'] = '#6999de'

    src = df.to_dict(orient='list')
    full_source = ColumnDataSource(src)

    # mid-level way to do it
    max_df = round(df['pct jobs in state'].max() / 10 + 0.5) * 10
    p = figure(title='Top states for ' + search_term, width=scale_factor, height=scale_factor, tools='', y_range=Range1d(0, max_df), x_range=Range1d(-0.5, 29.5))
    p.vbar(source=full_source, x='index', width=0.9, bottom=0,
        top='pct jobs in state', color='color')

    # changes labels from 0, 1, 2 etc to Python, SQL, Hadoop, etc
    p.xaxis[0].formatter = FixedTickFormatter(labels=label_dict)
    p.xaxis[0].ticker.num_minor_ticks = 0
    p.xaxis[0].ticker.desired_num_ticks = df.shape[0]
    # remove grid lines
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.xaxis.major_label_orientation = 89.0
    # I think we already know the xaxis is a skill...
    # p.xaxis.axis_label = 'skill'
    p.yaxis.axis_label = 'percent of jobs in state'
    # this is for a 1000x1000 plot
    # p.xaxis.axis_label_text_font_size = "30pt"
    # p.xaxis.major_label_text_font_size = "15pt"
    # p.yaxis.axis_label_text_font_size = "30pt"
    # p.yaxis.major_label_text_font_size = "15pt"
    # p.title_text_font_size = "30pt"
    # this is for 500x500
    big = str(int(scale_factor / 500. * 15))
    small = str(int(scale_factor / 500. * 8))
    p.xaxis.axis_label_text_font_size = big + "pt"
    p.xaxis.major_label_text_font_size = small + "pt"
    p.yaxis.axis_label_text_font_size = big + "pt"
    p.yaxis.major_label_text_font_size = small + "pt"
    p.title.text_font_size = big + "pt"
    if live:
        output_file('top_locations.html', title='top locations plot')
        show(p)
    else:
        script, div = components(p, wrap_script=False)
        return script, div
        # was saving it before, but that generates a complete html file
        # output_file('app/static/img/' + re.sub('\s', '_', search_term) + '_skills.html')
        # save(p)


def get_locations_mongo(search_term='data science'):
    """
    Retrieves list of job locations from mongoDB.  Need to have full time etc
    in order to filter them properly
    """
    search_term = clean_search_term(search_term)
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    jobs = coll.find()
    locs = defaultdict(list)
    for j in jobs:
        emp_type = str.lower(j['emp_type'])  # .encode('ascii', 'ignore')
        if j['emp_type'] == '' or j['location'] == '':
            continue
        elif 'c2h' in emp_type or 'contract to hire' in emp_type or 'contract-to-hire' in emp_type:
            emp_type = 'contract_to_hire'
        elif 'full time' in emp_type or 'fulltime' in emp_type or 'full-time' in emp_type:
            emp_type = 'full_time'
        elif 'contract' in emp_type:
            emp_type = 'contract'
        else:
            emp_type = 'other'

        locs[emp_type].append(j['location'])

    client.close()

    return locs


def get_salaries_mongo(search_term='data science', debug=False, scrape=True):
    """
    Retrieves list of salaries from mongoDB.  Need to have full time etc
    in order to filter them properly
    """
    search_term = clean_search_term(search_term)
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    jobs = list(coll.find())
    # avoid circular function calls from continuous_scrape with scrape=False
    if len(jobs) == 0 and scrape:
        continuous_scrape(search_term=search_term)
        jobs = coll.find()

    salary_dict = defaultdict(list)
    for j in jobs:
        sal = str.lower(j['salary'])  # .encode('ascii', 'ignore')
        emp_type = str.lower(j['emp_type'])  # .encode('ascii', 'ignore')
        # some are '', '-', '$' or something like 'top 20%'
        # first check if there is at least a number in the salary
        if 'c2h' in emp_type or 'contract to hire' in emp_type or 'contract-to-hire' in emp_type:
            emp_type = 'contract_to_hire'
        elif 'full time' in emp_type or 'fulltime' in emp_type or 'full-time' in emp_type:
            emp_type = 'full_time'
        elif 'contract' in emp_type:
            emp_type = 'contract'
        else:
            emp_type = 'other'

        avg_sal = 0
        if not any([str.isdigit(l) for l in sal]):
            coll.update_one(j, {'$set': {'clean_emp_type': emp_type, 'clean_sal': avg_sal}})
            continue

        if len(sal) < 2 or '%' in sal or j['emp_type'] == '':
            coll.update_one(j, {'$set': {'clean_emp_type': emp_type, 'clean_sal': avg_sal}})
            continue

        salary_dict[emp_type].append(sal)

        # clean up salary and put in db
        s = re.sub(',', '', sal)
        s = re.sub('\$', '', sal)
        try:
            sal = float(s)
            ishourly = False
            if sal < 1000:
                ishourly = True
        except:
            ishourly = False

        if 'hour' in s or 'hourly' in s or 'hr' in s or len(s) < 4 or ishourly and 'k' not in s:
            if debug:
                print('guessing hourly')
            if '-' in s:
                if debug:
                    print(s)
                # probably a range
                sal_match = re.search('(\d+\.*\d*)[/hr]*\s*-\s*(\d+\.*\d*)', s)
                try:
                    min_hr = float(sal_match.group(1))
                    min_hr *= 37.5 * 52
                    max_hr = float(sal_match.group(2))
                    max_hr *= 37.5 * 52
                    avg_hr = (min_hr + max_hr) / 2
                    if debug:
                        print('hourly min, max, avg:', min_hr, max_hr, avg_hr)
                    # calculate yearly salary based on per hour
                    avg_sal = avg_hr
                except:
                    pass
            else:
                sal_match = re.search('\d+\.*\d*', s)
                avg_hr = float(sal_match.group(0)) * 37.5 * 52
                if avg_hr > 10: # saw some as '00' etc
                    avg_sal = avg_hr
                    if debug:
                        print('hourly avg:', avg_hr)
        else: # not hourly, probably annually
            if debug:
                print('guessing annual')
            range_match = re.search('(\d+\.*\d*)\s*-+\s*(\d+\.*\d*)', s)
            if range_match:
                min_sal = float(range_match.group(1))
                max_sal = float(range_match.group(2))
                # one entry was $0.00 - $1 per annum
                if min_sal < 10 and max_sal < 10:
                    continue
                # sometimes written as 110k, etc
                if min_sal < 1000:
                    min_sal *= 1000
                if max_sal < 1000:
                    max_sal *= 1000
                avg_sal = float((min_sal + max_sal) / 2.0)
                if debug:
                    print('annual min, max, avg:', min_sal, max_sal, avg_sal)
            else:
                avg_sal = float(re.search('\d+\.*\d*', s).group(0))
                if avg_sal < 1000:
                    avg_sal *= 1000
                if debug:
                    print('annual avg:', avg_sal)

        coll.update_one(j, {'$set': {'clean_emp_type': emp_type, 'clean_sal': avg_sal}})


    client.close()

    return salary_dict


def get_salary_dist(salary_dict, debug=False):
    """
    Takes dict of salaries (emp_type as keys) and gets range and other metrics.
    """
    new_sal_dict = {}
    min_sals = []
    max_sals = []
    avg_sals = []
    for t in list(salary_dict.keys()): # for each employment type, e.g. full_time, c2h
        new_sal_dict[t] = {}
        new_sal_dict[t]['mins'] = []
        new_sal_dict[t]['maxs'] = []
        new_sal_dict[t]['avgs'] = []
        if debug:
            print(t)
        for s in salary_dict[t]:
            if s == 0:
                continue
            if debug:
                print(s)
            if debug:
                print(s)
            s = re.sub(',', '', s)
            s = re.sub('\$', '', s)
            # check if an hourly wage
            ishourly = False
            try:
                sal = float(s)
                if sal < 1000:
                    ishourly = True
            except:
                ishourly = False
            if 'hour' in s or 'hourly' in s or 'hr' in s or len(s) < 4 or ishourly and 'k' not in s:
                if debug:
                    print('guessing hourly')
                if '-' in s:
                    if debug:
                        print(s)
                    # probably a range
                    sal_match = re.search('(\d+\.*\d*)[/hr]*\s*-\s*(\d+\.*\d*)', s)
                    try:
                        min_hr = float(sal_match.group(1))
                        min_hr *= 37.5 * 52
                        max_hr = float(sal_match.group(2))
                        max_hr *= 37.5 * 52
                        avg_hr = (min_hr + max_hr) / 2
                        if debug:
                            print('hourly min, max, avg:', min_hr, max_hr, avg_hr)
                        # calculate yearly salary based on per hour
                        new_sal_dict[t]['mins'].append(min_hr)
                        new_sal_dict[t]['maxs'].append(max_hr)
                        new_sal_dict[t]['avgs'].append(avg_hr)
                    except:
                        pass
                else:
                    sal_match = re.search('\d+\.*\d*', s)
                    avg_hr = float(sal_match.group(0)) * 37.5 * 52
                    if avg_hr > 10: # saw some as '00' etc
                        new_sal_dict[t]['avgs'].append(avg_hr)
                        if debug:
                            print('hourly avg:', avg_hr)
            else: # not hourly, probably annually
                if debug:
                    print('guessing annual')
                range_match = re.search('(\d+\.*\d*)\s*-+\s*(\d+\.*\d*)', s)
                if range_match:
                    min_sal = float(range_match.group(1))
                    max_sal = float(range_match.group(2))
                    # one entry was $0.00 - $1 per annum
                    if min_sal < 10 and max_sal < 10:
                        continue
                    # sometimes written as 110k, etc
                    if min_sal < 1000:
                        min_sal *= 1000
                    if max_sal < 1000:
                        max_sal *= 1000
                    avg_sal = float((min_sal + max_sal) / 2.0)
                    new_sal_dict[t]['mins'].append(min_sal)
                    new_sal_dict[t]['maxs'].append(max_sal)
                    new_sal_dict[t]['avgs'].append(avg_sal)
                    if debug:
                        print('annual min, max, avg:', min_sal, max_sal, avg_sal)
                else:
                    avg_sal = float(re.search('\d+\.*\d*', s).group(0))
                    if avg_sal < 1000:
                        avg_sal *= 1000
                    new_sal_dict[t]['avgs'].append(avg_sal)
                    if debug:
                        print('annual avg:', avg_sal)

    return new_sal_dict


def plot_salary_dist(sal_dict=None, key='full_time', search_term='data scientist', live=False, debug=False, hw=None):
    """
    Assumes a Gaussian distribution of salaries, excludes outliers using
    1.5 * IQR.

    Parameters
    ----------
    sal_dict: dictionary
        keys should be employment types ('full_time', etc), values are lists
        of salaries; if None, will get from
    key: string
        key for sal_dict to do anaylis on
    search_term: string
        search term associated with sal_dict; used for labeling plot
    live: boolean
        if True, will call plt.show() to show locally, else will save to folder

    hw: list of ints
        [height, width] of web browser

    Returns
    -------

    """
    if hw is not None:
        # scale factor for screen width
        # used to do it this way, but a problem on mobile
        # scale_factor = 500 / 1366. * hw[1] / 100
        scale_factor = 6
        # typical figsize is 6x8 with 80 dpi, so about 2 dpi/inch^2.
        # scale factor is in inches, about 5 in for my screen
        # so this will give about 96 dpi for a 5x5 figure
        # for a 1.5x1.5 fig,
        dpi = int(30 * 80 / scale_factor ** 2)
        # adjust fontsize for screen size
        # rc_dict = {'font.size':int(8*hw[1]/1366.)}
        rc_dict = {'font.size': 10}
        plt.rcParams.update(rc_dict)
        # 80 dpi default, 500/1366 ratio by trial and error
        f = plt.figure(figsize=(scale_factor, scale_factor), dpi=dpi)
    else:
        f = plt.figure()
        scale_factor = 5

    search_term = clean_search_term(search_term)
    if sal_dict is None:
        salary_dict = get_salaries_mongo(search_term=search_term)
        sal_dict = get_salary_dist(salary_dict, debug=debug)

    dist = sal_dict[key]['avgs']
    iqr = stats.iqr(dist) # get interquartile range
    q3 = np.percentile(dist, 75.0)
    q1 = np.percentile(dist, 25.0)
    # exclude outliers
    inliers = np.array([d for d in dist if d > q1 - 1.5 * iqr and d < q3 + 1.5 * iqr])
    gauss = stats.norm(loc=np.mean(inliers), scale=np.std(inliers))
    max_i = max(inliers) + 30000
    min_i = min(inliers) - 30000
    x = np.arange(min_i, max_i, int((max_i - min_i) / 100))
    # double-checking gaussian dist
    # pdf = map(gauss_pdf, x, np.repeat(np.mean(inliers), 100), np.repeat(np.std(inliers), 100))
    unscaled_norm = gauss.pdf(x)
    scaled_norm = unscaled_norm / max(unscaled_norm)
    # abondon matplotlib in favor of seaborn
    # plt.hist(inliers, bins=20, normed=True)
    ax = plt.gca()
    sns.distplot(inliers, norm_hist=True, kde=False, ax=ax)
    sns.kdeplot(inliers, label='KDE', color='#4289f4', ax=ax)
    ax.plot(x, unscaled_norm, label='Gaussian fit', color='#f48342')
    ax.get_xaxis().set_major_formatter(ticker.FuncFormatter(salary_formatter))
    f.suptitle('average ' + search_term + ' salary: ' + salary_formatter(np.mean(inliers), None))
    plt.xlabel('salary')
    plt.yticks([])
    plt.legend()
    plt.tight_layout()
    plt.subplots_adjust(top=0.9)
    if live:
        # attempt to convert to bokeh, but isn't working properly
        # output_file('convert.html', title='test')
        # p = to_bokeh(fig=f)
        # show(p)
        # mpld3 a little better but hard to make interactions
        # import mpld3
        # mpld3.show()
        plt.show()
    else:
        filename = 'app/static/img/' + re.sub('\s', '_', search_term) + '_scale_' + str(scale_factor) + '_salary_dist.png'
        plt.savefig(filename, dpi=dpi)
        return filename[11:]

    # trying to use bokeh for an interactive chart, but not currently worth it
    # from bokeh.charts import Histogram
    # from bokeh.models import HoverTool
    # from bokeh.charts import defaults, vplot, hplot, show, output_file
    # hover = HoverTool(
    #         tooltips=[
    #             ("index", "$index"),
    #             ("(x,y)", "($x, $y)"),
    #             ("desc", "@desc"),
    #         ]
    #     )
    # TOOLS = ['pan', 'wheel_zoom', 'box_zoom', 'reset', hover]
    # hist = Histogram(inliers, title="data science salaries", tools=TOOLS)
    # output_file("histograms.html")
    # show(hist)


def salary_formatter(x, p):
    return '$' + '%.0f' % (x / 1000) + 'k'


def gauss_pdf(x, mu, std):
    """
    Double-checking gaussian plotting.
    """
    return np.exp(-(x - mu)**2/(2.0*std)**2)/(std*np.sqrt(2*np.pi))


def convert_to_dict(job_postings_raw):
    """
    since dice removed their API, this converts the raw web scrape to the old format

    job_postings_raw should be a list of BeautifulSoup HTML objects
    """
    job_postings = []
    current_posting = {}
    for j in job_postings_raw:
        link = j.find('a', {'class': ['dice-btn-link', 'loggedInVisited']})
        current_posting['jobTitle'] = link.get('title')
        current_posting['company'] = j.find('span', {'class': 'compName'}).text
        current_posting['detailUrl'] = 'https://www.dice.com' + link.get('href')
        job_postings.append(current_posting)
        current_posting = {}

    return job_postings


def continuous_scrape(search_term='data science', use_mongo=True, debug=False):
    """

    Parameters
    ----------
    search_term: string
        term to search for on dice api
    use_mongo: boolean
        if True, saves data to mongodb

    Returns
    -------
    None if use_mongo is True

    """
    search_term = clean_search_term(search_term)

    res = req.get(create_url(search_term=search_term))
    soup = bs(res.content, 'lxml')
    # manually counting up pages now
    #next_link = data['nextUrl']
    job_postings_raw = soup.find_all('div', {'class': 'complete-serp-result-div'})
    job_postings = convert_to_dict(job_postings_raw)  # converts format to match old API

    relevant_jobs, non_relevant_jobs = segment_jobs(job_postings, search_term=search_term)
    # in case you want to look at which jobs are filtered out...
    # print [j['jobTitle'] for j in non_relevant_jobs]
    if use_mongo:
        client = MongoClient()
        db = client[DB_NAME]
        coll = db[search_term]
        # first, set all entries to be expired, i.e. not recent
        coll.update({}, {'$set':{'recent':False}}, multi=True)
        scrape_all_jobs(relevant_jobs, search_term=search_term, use_mongo=use_mongo, debug=debug)
    else:
        full_df = scrape_all_jobs(relevant_jobs, search_term=search_term, use_mongo=use_mongo, debug=debug)

    page = 2
    consecutive_blank_pages = 0
    consecutive_same_page = 0
    last_page = None
    while True:
        gc.collect()
        process = psutil.Process(os.getpid())
        print('memory use (GB):')
        print(process.memory_info().rss / 1000000000.0)
        # used to get 'nextLink' from json object, but that seemed to end at 29
        # for some reason.  Changing to manually counting up pages
        #page = re.search('page=(\d+)', next_link).group(1).encode('ascii', 'ignore')
        if debug:
            print('')
            print('-'*20)
            print('')
            print('on page', page)
            print('')
            print('-'*20)
            print('')
        try:
            res = req.get(create_url(search_term=search_term, page=page))
            page += 1

            soup = bs(res.content, 'lxml')
            job_postings_raw = soup.find_all('div', {'class': 'complete-serp-result-div'})
            job_postings = convert_to_dict(job_postings_raw)  # converts format to match old API
            #next_link = data['nextUrl']
            relevant_jobs, non_relevant_jobs = segment_jobs(job_postings, search_term=search_term)
            # in case you want to look at which jobs are filtered out...
            # print [j['jobTitle'] for j in non_relevant_jobs]
            if len(relevant_jobs) == 0:
                consecutive_blank_pages += 1
            else:
                consecutive_blank_pages = 0
            if consecutive_blank_pages == 6: # lower the limit, used to be 10
                break

            # also want to break if we keep seeing the same pages
            # got to a point once where it was at page 7000 something and
            # kept getting the same exact page...
            if last_page is not None and last_page == job_postings:
                consecutive_same_page += 1
            else:
                consecutive_same_page = 0

            if consecutive_same_page == 3:
                break

            last_page = job_postings


            #all_ds_jobs.extend(ds_jobs) # not sure but I think this may have been
            # taking up lots of memory
            #all_non_ds_jobs.extend(all_non_ds_jobs)
            if use_mongo:
                scrape_all_jobs(relevant_jobs, search_term=search_term, use_mongo=use_mongo, debug=debug)
            else:
                full_df = full_df.append(scrape_all_jobs(relevant_jobs, search_term=search_term, use_mongo=use_mongo, debug=debug))
        except Exception as e:
            traceback.print_exc()
            if use_mongo:
                return None

            return full_df

    # re-calculates salaries and things, but we don't use the returned
    # salary distribution so ignore it with _
    _ = get_salaries_mongo(search_term=search_term, scrape=False)

    if use_mongo:
        return None

    return full_df


def test_system(search_term='data science', page=1):
    """
    This was how I first started the project.
    It just runs a few basic tests of the API.
    """
    search_term = clean_search_term(search_term)
    res = req.get(create_url(search_term=search_term, page=page))
    data = json.loads(res.content)
    next_link = data['nextUrl']
    # returns a dict with [u'count', u'nextUrl', u'resultItemList', u'firstDocument', u'lastDocument']
    job_postings = data['resultItemList']
    ds_jobs, non_ds_jobs = segment_jobs(job_postings)

    df = scrape_all_jobs(ds_jobs)

    skills_count = get_skills_tf(df)

    return df, ds_josb, non_ds_jobs, skills_count


def get_jobs_with_skills(skills_list, all_skills=True):
    """
    Retrieves jobs from database with skills in the skills_list.

    Parameters
    ----------
    skills_list : list
        list of strings of skills
    all_skills : boolean
        if True, all skills must be present in jobs

    """
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    jobs = coll.find()
    all_jobs_with_skills = []
    cur_jobs = []
    for j in jobs:
        skills = clean_db_skills(j['skills'])
        mask = [s in skills_list for s in skills]
        if all_skills:
            criterion = np.sum(mask) == len(skills)
        else:
            criterion = any(mask)
        if criterion:
            all_jobs_with_skills.append(j)
            if j['recent']:
                cur_jobs.append(j)

    return all_jobs_with_skills, cur_jobs


def check_if_job_recent(job, search_term='data science'):
    """
    Takes a job dictionary object and checks if is in the MongoDB.
    If so, sets the status to 'recent'.
    """
    search_term = clean_search_term(search_term)
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    # it's a generator so we have to convert to a list
    jobs = list(coll.find(job))
    if len(jobs) > 0:
        coll.find(job)
        client.close()
        return True

    client.close()
    return False


def get_jobs(search_term='data science', fields=None, callback=None, force=False, recent=True):
    """
    Gets all jobs in db that have 'recent' == True.
    Can supply list of fields to only return those fields.

    Callback arg was abandoned, just there as a remnant now.
    """
    search_term = clean_search_term(search_term)
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    field_dict = {}
    field_dict['_id'] = 0
    if fields is not None:
        for f in fields:
            field_dict[f] = 1

    if recent:
        jobs = list(coll.find({'recent': True}, field_dict))
    else:
        jobs = list(coll.find({}, field_dict))
    if len(jobs) == 0:
        # for now, disabling searching for new topics
        if force:
            t1 = threading.Thread(target=continuous_scrape, kwargs={'search_term':search_term})
            t1.start()
            t1.join()
        if callback is None:
            return 'updating db'
        else:
            jobs = list(coll.find({'recent': True}, field_dict))
            return jobs
    # it's a generator so we have to convert to a list
    client.close()

    #jobs = convert(jobs)

    return jobs


def convert(data):
    """
    Converts all parts of dictionary from unicode to string.
    From here: http://stackoverflow.com/questions/1254454/fastest-way-to-convert-a-dicts-keys-values-from-unicode-to-str
    """
    if isinstance(data, str):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(list(map(convert, iter(data.items()))))
    elif isinstance(data, collections.Iterable):
        return type(data)(list(map(convert, data)))
    else:
        return data


def clean_search_term(search_term):
    search_term = re.sub('\s+', ' ', search_term) # replace multi space with one
    search_term = search_term.lower() # always lower case
    if 'data scientist' in search_term:
        search_term = 'data science'
    elif 'data engineer' in search_term:
        search_term = 'data engineer'
    elif search_term in ['fullstack', 'full-stack']:
        search_term = 'full stack'
    elif search_term in ['front-end developer', 'frontend developer']:
        search_term = 'front end developer'

    return search_term


def filter_jobs(jobs, salary_range=None, locations=None, skills=None, fields=None):
    """
    Filters jobs according to given criteria.

    Parameters
    ----------

    jobs: list
        list of dictionaries from mongo db query

    salary_range: list of floats/ints
        [minimum, maximum] salary for range

    locations: list of strings
        list of ['City, State', 'State'] where state is capitalized and
        exactly 2 letters

    skills: list of strings
        list of ['Python', 'R'] where strings are capitalized

    Returns:
    -------
    filtered_jobs: list of dictionaries
        list in same format of parameter 'jobs', but filtered with criteria
    """
    df = pd.DataFrame(jobs)
    df['clean_sal'] = df['clean_sal'].fillna(0)
    df['predicted_salary'] = df['predicted_salary'].fillna(0)
    df['state'] = df['location'].apply(lambda x: extract_state(x))
    # pretty sure I don't need that anymore
    # df['clean_sal'] = df['clean_sal'].fillna(0)
    if salary_range is not None:
        df = df[(df['clean_sal'] >= salary_range[0]) | (df['predicted_salary'] >= salary_range[0])]
        df = df[(df['clean_sal'] <= salary_range[1]) | (df['predicted_salary'] <= salary_range[1])]

    if locations is not None:
        # get seperate lists of states and cities, states
        city_states = [l for l in locations if ',' in l]
        states = [l for l in locations if len(l) == 2]
        df = df[df['state'].isin(states) | df['location'].isin(city_states)]

    if skills is not None:
        skills = set(skills)
        df['skills_diff'] = df['clean_skills'].apply(lambda x: len(skills.difference(set(x))))
        df = df[df['skills_diff'] == 0]

    if fields is not None:
        df = df[fields]

    filtered_jobs = list(df.to_dict(orient='index').values())

    return filtered_jobs


if __name__ == "__main__":
    pass
    # test_url = 'http://www.dice.com/job/result/applecup/54281129?src=19'
    # df = scrape_a_job(test_url)
    #continuous_scrape()#full_df = continuous_scrape()
    # salary_dict = get_salaries_mongo()
    # sal_dists = get_salary_dist(salary_dict)
    # plot_salary_dist(sal_dists)
    # skills = get_skills_tf_mongo()
    # top_skills = [s for s in skills.most_common() if s[1] >= 5]
    # plot_top_skills(top_skills, search_term='data science', live=True)

    # -------------
    # to see which skills are not in the GloVe vectors
    # vectors = wv.load_vectors()
    # for s in top_skills:
    #     if s[0] not in vectors:
    #         print s

    # ways to check for similary of skills not in top_skills:
    # check for presence of word/phrase in lower skills, and add to top_skills
    # hash the values and check that way
    # use GloVe vectors

    # -----------
    # looking at a few postings, here are some things I've noticed

    # 'About you' section
    # div class="row job-info"
    # 'Job Description' section
    # experience required: ...
    # a plus or plus
    # 2+ years ... etc
    # qualifications

    #
    # Spark, Scala, Python, NumPy, Scikit, Scikit-learn, Sklearn, Pandas, MATLAB, C++, SQL, Tableau, Hadoop, Apache
    # SAS, R, SQL, Hadoop, H2O.ai, Sparkling water, Steam, SPSS, Stata, Java, C, C++, C#,
    # Perl, Ruby, NoSQL, Hive, Pig, Mapreduce, Oracle, Teradata, Alteryx, AWS, Azure, Deep Learning, Neural Networks,
    # Data Mining, BI Tools,
    #
    # Bachelor's degree in Computer Science, Statistics, Economics
