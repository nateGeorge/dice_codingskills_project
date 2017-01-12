import requests as req
import json
import re

BASE_URL = 'http://service.dice.com/api/rest/jobsearch/v1/simple.json?text='
page = 1 # page number, 1-indexed
search_term = 'data science'


def create_url(search_term, base_url=BASE_URL, page=1):
    '''
    creates formatted url for a get request to dice api
    args:
    base_url: string -- the starting dice api url
    page: int -- page number (1-indexed); 50 results per page
    search_term: string -- term to find in the job posting
    '''
    search_term = re.sub('\s', '%20', search_term) # sub spaces with %20
    return BASE_URL + search_term + '&page=' + str(page)

def segment_jobs(job_postings):
    '''
    takes list of json job postings, and returns list of those with 'data scientist'
    in the title, and a list of the rest
    '''
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

if __name__ == "__main__":
    res = req.get(create_url(search_term='data science'))

    data = json.loads(res.content)
    next_link = data['nextUrl']
    # returns a dict with [u'count', u'nextUrl', u'resultItemList', u'firstDocument', u'lastDocument']
    job_postings = data['resultItemList']



    # -----------
    # this will get a job and save the html as test.html
    test_job = job_postings[5]
    res = req.get(test_job['detailUrl'])
    # -----
    # save file for looking at in browser
    with open('test.html', 'w') as f:
        f.write(res.content)


    # scraping skills
    # 'About you' section
    # div class="row job-info"
    # 'Job Description' section
    # experience required: ...
    # a plus or plus
    # 2+ years ... etc
    # qualifications

    #
    Spark, Scala, Python, NumPy, Scikit, Scikit-learn, Sklearn, Pandas, MATLAB, C++, SQL, Tableau, Hadoop, Apache
    SAS, R, SQL, Hadoop, H2O.ai, Sparkling water, Steam, SPSS, Stata, Java, C, C++, C#,
    Perl, Ruby, NoSQL, Hive, Pig, Mapreduce, Oracle, Teradata, Alteryx, AWS, Azure, Deep Learning, Neural Networks,
    Data Mining, BI Tools,

    Bachelor's degree in Computer Science, Statistics, Economics
