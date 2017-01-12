import requests as req
import json
import re
from bs4 import BeautifulSoup as bs
from lxml import html
import pandas as pd
import numpy as np
from collections import Counter

BASE_URL = 'http://service.dice.com/api/rest/jobsearch/v1/simple.json?text='
page = 1 # page number, 1-indexed
search_term = 'data science'


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
    search_term = re.sub('\s', '%20', search_term) # sub spaces with %20
    return BASE_URL + search_term + '&page=' + str(page)


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


def dl_job_post(job_postings, num=0, path='test.html'):
    """
    Downloads one job posting to specified path.

    Parameters
    ----------
    job_postings : list
        json job posting objects
    num : integer
        index of job posting
    path : string
        path to download file to
    Returns
    -------


    """
    test_job = job_postings[num]
    res = req.get(test_job['detailUrl'])
    with open('test.html', 'w') as f:
        f.write(res.content)


def get_info(info):
    """
    Extracts info from job-info block in html
    """
    if len(info) == 4:
        skills = info[0].find('div', {'class':'iconsiblings'})
        skills = clean_skills(skills)
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
            icons = i.find('span', {'class':'icons'})
            if 'icon-plugin-1' in icons:
                skills = i.find('div', {'class':'iconsiblings'})
                skills = clean_skills(skills)
            elif 'icon-briefcase' in icons:
                emp_type = i.find('div', {'class':'iconsiblings'}).getText().strip('\n')
            elif 'icon-bank-note' in icons:
                salary = i.find('div', {'class':'iconsiblings'}).getText().strip('\n')
            elif 'icon-network-2' in icons:
                tele_travel = i.find('div', {'class':'iconsiblings'}).getText()
                tele_travel = tele_travel.split('\n')
                tele_travel = [t.encode('ascii', 'ignore') for t in tele_travel if t != '']

        return skills, emp_type, salary, tele_travel


def scrape_a_job(job_url):
    """
    Scrapes important info from job posting.

    Parameters
    ----------
    job_url: string
        url to job posting

    Returns
    -------

    """
    res = req.get(job_url)
    if not res.ok:
        print 'uh-oh...'
        print res.status

    soup = bs(res.content, 'lxml')
    info = soup.findAll('div', {'class':'row job-info'})
    skills, emp_type, salary, tele_travel = get_info(info)
    # could do it this way, but there is also a unique id for this section
    # descr_xpath = '//*[@id="bd"]/div/div[1]/div[6]'
    # tree = html.fromstring(res.content)
    # descr = tree.xpath(descr_xpath)
    descr = soup.find('div', {'id':'jobdescSec'}).getText()
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


def clean_skills(skills):
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


def scrape_all_jobs(job_postings):
    """

    """
    full_df = None
    for i, j in enumerate(job_postings):
        print i, j['jobTitle'], j['company']
        df = scrape_a_job(j['detailUrl'])
        if full_df is None:
            full_df = df
        else:
            full_df = full_df.append(df)

    return full_df


def get_skills_tf(df):
    skills_temp = df['csv_skills'].values
    skills_temp = [str.lower(s.encode('ascii', 'ignore')).split(', ') for s in skills_temp]
    skills_list = []
    for s in skills_temp:
        skills_list.extend(s)

    skills_count = Counter(skills_list)
    return skills_count

def continuous_scrape(search_term='data science'):
    res = req.get(create_url(search_term=search_term))
    data = json.loads(res.content)
    next_link = data['nextUrl']
    job_postings = data['resultItemList']
    all_ds_jobs, all_non_ds_jobs = segment_jobs(job_postings)
    full_df = scrape_all_jobs(all_ds_jobs)
    while next_link:
        print ''
        print '-'*20
        print ''
        print 'on page',
        print ''
        print '-'*20
        print ''
        try:
            res = req.get(next_link)
            data = json.loads(res.content)
            next_link = data['nextUrl']
            job_postings = data['resultItemList']
            ds_jobs, non_ds_jobs = segment_jobs(job_postings)
            all_ds_jobs.extend(ds_jobs)
            all_non_ds_jobs.extend(all_non_ds_jobs)
            full_df = full_df.append(scrape_all_jobs(ds_jobs))
        except Exception as e:
            print e
            return full_df, all_ds_jobs, all_non_ds_jobs


    return full_df, all_ds_jobs, all_non_ds_jobs


def test_system(search_term='data science'):
    res = req.get(create_url(search_term=search_term))
    data = json.loads(res.content)
    next_link = data['nextUrl']
    # returns a dict with [u'count', u'nextUrl', u'resultItemList', u'firstDocument', u'lastDocument']
    job_postings = data['resultItemList']
    ds_jobs, non_ds_jobs = segment_jobs(job_postings)

    df = scrape_all_jobs(ds_jobs)

    skills_count = get_skills_tf(df)

    return df, ds_josb, non_ds_jobs, skills_count


if __name__ == "__main__":
    full_df, all_ds_jobs, all_non_ds_jobs = continuous_scrape()


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
