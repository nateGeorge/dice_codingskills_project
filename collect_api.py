import requests as req
import json
import re
from bs4 import BeautifulSoup as bs
from lxml import html

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
        if 'data scientist' in title:
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

    soup = bs(res.content, 'lxml')
    info = soup.findAll('div', {'class':'row job-info'})
    skills = info[0].find('div', {'class':'iconsiblings'})
    skills = clean_skills(skills)
    emp_type = info[1].find('div', {'class':'iconsiblings'}).getText().strip('\n')
    salary = info[2].find('div', {'class':'iconsiblings'}).getText().strip('\n')
    tele_travel = info[3].find('div', {'class':'iconsiblings'}).getText()
    tele_travel = tele_travel.split('\n')
    tele_travel = [t for t in tele_travel if t != '']
    # could do it this way, but there is also a unique id for this section
    # descr_xpath = '//*[@id="bd"]/div/div[1]/div[6]'
    # tree = html.fromstring(res.content)
    # descr = tree.xpath(descr_xpath)
    descr = soup.find('div', {'id':'jobdescSec'}).getText()


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
    skills = skills.getText().strip('\n').strip('\t').strip('\n')
    skills = skills.split(',')
    skills = [s.strip() for s in skills if s != 'etc']
    skills = [re.sub('\s*etc\s+', '', s) for s in skills]
    skills = [re.sub('\s+etc\s*', '', s) for s in skills]
    return skills


if __name__ == "__main__":
    res = req.get(create_url(search_term='data science'))

    data = json.loads(res.content)
    next_link = data['nextUrl']
    # returns a dict with [u'count', u'nextUrl', u'resultItemList', u'firstDocument', u'lastDocument']
    job_postings = data['resultItemList']



    # -----------
    # this will get a job and save the html as test.html



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
