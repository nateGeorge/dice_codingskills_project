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
import word_vectors as wv
from bokeh.charts import Bar, output_file, show
from bokeh.models import TickFormatter
from bokeh.properties import Dict, Int, String
import traceback
from bokeh.models import (
  GMapPlot, GMapOptions, ColumnDataSource, Circle, DataRange1d, PanTool, WheelZoomTool, BoxSelectTool
)

BASE_URL = 'http://service.dice.com/api/rest/jobsearch/v1/simple.json?text='
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
    search_term = re.sub('\s', '%20AND%20', search_term) # sub spaces with %20
    # AND means it must find all words
    return BASE_URL + search_term + '&page=' + str(page)# + '&sort=2'# this last bit sorts by job title


def segment_jobs(job_postings):
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
    ds_jobs = []
    non_ds_jobs = []
    for j in job_postings:
        title = str.lower(j['jobTitle'].encode('ascii', 'ignore'))
        if 'data scientist' in title or 'data science' in title:
            ds_jobs.append(j)
        else:
            non_ds_jobs.append(j)
        # doesn't seem to be any mle jobs, which is good
        # elif 'machine learning engineer' in title:
        #     mle_jobs.append(j)
    return ds_jobs, non_ds_jobs


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
        print j[aspect]


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
        print 'either job_postings or url must be supplied as an argument'

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
        tele_travel = [t.encode('ascii', 'ignore') for t in tele_travel if t != '']
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
                tele_travel = [t.encode('ascii', 'ignore') for t in tele_travel if t != '']

        return skills, emp_type, salary, tele_travel


def scrape_a_job(job_json, search_term=None, insert_mongo=True):
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
    if insert_mongo:
        # first check to see if the entry is already in the db
        client = MongoClient()
        db = client[DB_NAME]
        coll = db[search_term]
        in_db = coll.find(job_json).count()
        if in_db > 0:
            print 'already in db'
            # don't think I want to update multi, but let's see how many there are
            coll.update(job_json, {'$set': {'recent': True}})#, multi=True)
            if in_db > 1:
                print 'WARN: occurs', in_db, 'times'
            return None

    res = req.get(job_json['detailUrl'])
    print job_json['detailUrl']
    if not res.ok:
        print 'uh-oh...'
        print res.status

    soup = bs(res.content, 'lxml')
    f404 = soup.findAll('p', {'class':'err_p'})
    if len(f404) > 0:
        print 'found 404'
        print f404[0].getText()
        if f404[0].getText() == u"404 - The page you're looking for couldn't be found or it may have expired.":
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
        descr = ''
        print ''
        print 'couldn\'t find description'
        print ''
        traceback.print_exc()

    posted_xpath = '//*[@id="header-wrap"]/div[2]/div/div[1]/ul/li[3]'
    tree = html.fromstring(res.content)
    posted = tree.xpath(posted_xpath)[0].text
    if insert_mongo:
        entry_dict = {'skills': skills,
                        'emp_type': emp_type,
                        'salary': salary,
                        'telecommute': tele_travel[0],
                        'travel': tele_travel[1],
                        'description': descr,
                        'posted_text': posted}
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
    skills = str.lower(skills.getText().strip('\n').strip('\t').strip('\n').encode('ascii', 'ignore'))
    skills = skills.split(',')
    # they are unicode, so convert to ascii strings (Python2 only)
    skills = [s.strip() for s in skills if s != 'etc']
    skills = [re.sub('\s*etc\s+', '', s) for s in skills]
    skills = [re.sub('\s+etc\s*', '', s) for s in skills]
    return skills


def scrape_all_jobs(job_postings, search_term=None, use_mongo=True):
    """
    Loops through the list of job_postings and scrapes key info from each.
    """
    full_df = None
    for i, j in enumerate(job_postings):
        print i, j['jobTitle'], j['company']
        if use_mongo:
            scrape_a_job(j, search_term=search_term, insert_mongo=use_mongo)
        else:
            df = scrape_a_job(j, search_term=search_term, insert_mongo=use_mongo)
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
    skills_temp = [str.lower(s.encode('ascii', 'ignore')).split(', ') for s in skills_temp]
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


def clean_db_skills(skills_list):
    """
    Cleans skills list from mongoDB entry.
    """
    # don't think I need this
    #temp_skills = [str.lower(s.encode('ascii', 'ignore')).split(', ') for s in skills_list]
    clean_skills_list = [s.lower().encode('ascii', 'ignore') for s in skills_list]
    for char in ['-', '/', ' or ', ' & ', ' and ']:
        clean_skills_list = split_skills(clean_skills_list, char=char)

    # some weird bug I can't figure out where it can't find the '/'
    # going to do this for everything else to be safe
    for s in clean_skills_list:
        if s == 'sql/nosql':
            print 'sql/nosql in s (2):', s
            print 'search:', re.search('/', s)
            print orig
            print clean_skills_list
            print now
        if re.search('^or ', s) is not None:
            clean_skills_list.remove(s)
            clean_skills_list.append(s[3:])
    clean_skills_list = [s.strip() for s in clean_skills_list if s.strip() != '']

    return clean_skills_list


def get_skills_tf_mongo(search_term='data science'):
    """
    Calculated term-frequency for skills based on data in a mongoDB.
    """
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    jobs = coll.find()
    skills_list = []
    for j in jobs:
        skills_list.extend(clean_db_skills(j['skills']))

    skills_count = Counter(skills_list)
    client.close()

    return skills_count


class FixedTickFormatter(TickFormatter):

    labels = Dict(Int, String, help="""
    A mapping of integer ticks values to their labels.
    """)

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


def plot_top_skills(top_skills_all):
    """
    Makes bar graph of top skills from a counter object.
    """
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

    p = Bar(df, 'index', values='pct jobs with skill', title="Top skills for data science", legend=False, width=1000, height=1000)
    p.xaxis[0].formatter = FixedTickFormatter(labels=label_dict)
    p.xaxis.major_label_orientation = 89.0
    p.xaxis.axis_label = 'skill'
    p.xaxis.axis_label_text_font_size = "30pt"
    p.xaxis.major_label_text_font_size = "20pt"
    p.yaxis.axis_label = 'percent of jobs with skill'
    p.yaxis.axis_label_text_font_size = "30pt"
    p.yaxis.major_label_text_font_size = "20pt"
    p.title_text_font_size = "30pt"
    output_file("bar.html")
    show(p)


def get_locations_mongo(search_term='data science'):
    """
    Retrieves list of job locations from mongoDB.  Need to have full time etc
    in order to filter them properly
    """
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    jobs = coll.find()
    locs = defaultdict(list)
    for j in jobs:
        emp_type = str.lower(j['emp_type'].encode('ascii', 'ignore'))
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


def get_salaries_mongo(search_term='data science'):
    """
    Retrieves list of salaries from mongoDB.  Need to have full time etc
    in order to filter them properly
    """
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    jobs = coll.find()
    salary_dict = defaultdict(list)
    for j in jobs:
        sal = str.lower(j['salary'].encode('ascii', 'ignore'))
        emp_type = str.lower(j['emp_type'].encode('ascii', 'ignore'))
        # some are '', '-', '$' or something like 'top 20%'
        if len(sal) < 2 or '%' in sal or j['emp_type'] == '':
            continue
        # first check if there is at least a number in the salary
        if not any([str.isdigit(l) for l in sal]):
            continue
        elif 'c2h' in emp_type or 'contract to hire' in emp_type or 'contract-to-hire' in emp_type:
            emp_type = 'contract_to_hire'
        elif 'full time' in emp_type or 'fulltime' in emp_type or 'full-time' in emp_type:
            emp_type = 'full_time'
        elif 'contract' in emp_type:
            emp_type = 'contract'
        else:
            emp_type = 'other'

        salary_dict[emp_type].append(sal)

    return salary_dict


def get_salary_dist(salary_dict):
    """
    Takes dict of salaries (emp_type as keys) and gets range and other metrics.
    """
    new_sal_dict = {}
    min_sals = []
    max_sals = []
    avg_sals = []
    for t in salary_dict.keys(): # for each employment type, e.g. full_time, c2h
        new_sal_dict[t] = {}
        new_sal_dict[t]['mins'] = []
        new_sal_dict[t]['maxs'] = []
        new_sal_dict[t]['avgs'] = []
        for s in salary_dict[t]:
            print s
            s = re.sub(',', '', s)
            s = re.sub('\$', '', s)
            # check if an hourly wage
            try:
                sal = float(s)
                if sal < 1000:
                    ishourly = True
            except:
                ishourly = False
            if 'hour' in s or 'hourly' in s or 'hr' in s or len(s) < 4 or ishourly and 'k' not in s:
                print 'guessing hourly'
                if '-' in s:
                    # probably a range
                    sal_match = re.search('(\d+\.*\d*)\s*-\s*(\d+\.*\d*)', s)
                    min_hr = float(sal_match.group(1))
                    min_hr *= 37.5 * 52
                    max_hr = float(sal_match.group(2))
                    max_hr *= 37.5 * 52
                    avg_hr = (min_hr + max_hr) / 2
                    print 'hourly min, max, avg:', min_hr, max_hr, avg_hr
                    # calculate yearly salary based on per hour
                    new_sal_dict[t]['mins'].append(min_hr)
                    new_sal_dict[t]['maxs'].append(max_hr)
                    new_sal_dict[t]['avgs'].append(avg_hr)
                else:
                    sal_match = re.search('\d+\.*\d*', s)
                    avg_hr = float(sal_match.group(0)) * 37.5 * 52
                    if avg_hr > 10: # saw some as '00' etc
                        new_sal_dict[t]['avgs'].append(avg_hr)
                        print 'hourly avg:', avg_hr
            else: # not hourly, probably annually
                print 'guessing annual'
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
                    print 'annual min, max, avg:', min_sal, max_sal, avg_sal
                else:
                    avg_sal = float(re.search('\d+\.*\d*', s).group(0))
                    if avg_sal < 1000:
                        avg_sal *= 1000
                    new_sal_dict[t]['avgs'].append(avg_sal)
                    print 'annual avg:', avg_sal

    return new_sal_dict


def plot_salary_dist(sal_dict, key='full_time', search_term='data scientist'):
    """
    Assumes a Gaussian distribution of salaries, excludes outliers using
    1.5 * IQR.

    Parameters
    ----------
    sal_dict: dictionary
        keys should be employment types ('full_time', etc), values are lists
        of salaries
    key: string
        key for sal_dict to do anaylis on
    search_term: string
        search term associated with sal_dict; used for labeling plot

    Returns
    -------

    """
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
    f = plt.figure()
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
    plt.show()

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


def continuous_scrape(search_term='data science', use_mongo=True):
    """

    Parameters
    ----------
    search_term: string
        term to search for on dice api
    use_mongo: boolean
        if True,

    Returns
    -------
    None if use_mongo is True

    """
    res = req.get(create_url(search_term=search_term))
    data = json.loads(res.content)
    # manually counting up pages now
    #next_link = data['nextUrl']
    job_postings = data['resultItemList']
    relevant_jobs, non_relevant_jobs = segment_jobs(job_postings)
    if use_mongo:
        client = MongoClient()
        db = client[DB_NAME]
        coll = db[search_term]
        # first, set all entries to be expired, i.e. not recent
        coll.update({}, {'$set':{'recent':False}}, multi=True)
        scrape_all_jobs(relevant_jobs, search_term=search_term, use_mongo=use_mongo)
    else:
        full_df = scrape_all_jobs(relevant_jobs, search_term=search_term, use_mongo=use_mongo)

    page = 2
    consecutive_blank_pages = 0
    while True:
        # used to get 'nextLink' from json object, but that seemed to end at 29
        # for some reason.  Changing to manually counting up pages
        #page = re.search('page=(\d+)', next_link).group(1).encode('ascii', 'ignore')
        print ''
        print '-'*20
        print ''
        print 'on page', page
        print ''
        print '-'*20
        print ''
        try:
            res = req.get(create_url(search_term=search_term, page=page))
            page += 1
            data = json.loads(res.content)
            #next_link = data['nextUrl']
            job_postings = data['resultItemList']
            relevant_jobs, non_relevant_jobs = segment_jobs(job_postings)
            if len(relevant_jobs) == 0:
                consecutive_blank_pages += 1
            if consecutive_blank_pages == 10:
                break
            #all_ds_jobs.extend(ds_jobs) # not sure but I think this may have been
            # taking up lots of memory
            #all_non_ds_jobs.extend(all_non_ds_jobs)
            if use_mongo:
                scrape_all_jobs(relevant_jobs, search_term=search_term, use_mongo=use_mongo)
            else:
                full_df = full_df.append(scrape_all_jobs(relevant_jobs, search_term=search_term, use_mongo=use_mongo))
        except Exception as e:
            traceback.print_exc()
            if use_mongo:
                return None

            return full_df

    if use_mongo:
        return None

    return full_df


def test_system(search_term='data science', page=1):
    """
    This was how I first started the project.
    It just runs a few basic tests of the API.
    """
    res = req.get(create_url(search_term=search_term, page=page))
    data = json.loads(res.content)
    next_link = data['nextUrl']
    # returns a dict with [u'count', u'nextUrl', u'resultItemList', u'firstDocument', u'lastDocument']
    job_postings = data['resultItemList']
    ds_jobs, non_ds_jobs = segment_jobs(job_postings)

    df = scrape_all_jobs(ds_jobs)

    skills_count = get_skills_tf(df)

    return df, ds_josb, non_ds_jobs, skills_count


def get_jobs_with_skills(skills_list):
    """
    Retrieves jobs from database with skills in the skills_list.

    Parameters
    ----------
    skills_list : list
        list of strings of skills

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
        if any(mask):
            all_jobs_with_skills.append(j)
            if j['recent']:
                cur_jobs.append(j)

    return all_jobs_with_skills, cur_jobs


def check_if_job_recent(job, search_term='data science'):
    """
    Takes a job dictionary object and checks if is in the MongoDB.
    If so, sets the status to 'recent'.
    """
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


def get_recent_jobs(search_term='data science'):
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    # it's a generator so we have to convert to a list
    jobs = list(coll.find({'recent': True}))
    client.close()
    return jobs


if __name__ == "__main__":
    # test_url = 'http://www.dice.com/job/result/applecup/54281129?src=19'
    # df = scrape_a_job(test_url)
    #continuous_scrape()#full_df = continuous_scrape()
    salary_dict = get_salaries_mongo()
    sal_dists = get_salary_dist(salary_dict)
    plot_salary_dist(sal_dists)
    skills = get_skills_tf_mongo()
    top_skills = [s for s in skills.most_common() if s[1] >= 5]
    plot_top_skills(top_skills)

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
