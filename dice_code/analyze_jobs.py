"""
Used to analyze data from job scrapes, such as which skills are most desired for certain job titles.
"""
from collections import Counter

import pandas as pd
from pymongo import MongoClient
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib
font = {'size'   : 22}
matplotlib.rc('font', **font)

import collect_api as ca

DB_NAME = 'dice_jobs'

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
    search_term = ca.clean_search_term(search_term)
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    jobs = list(coll.find())
    if len(jobs) == 0:
        continuous_scrape(search_term=search_term)
        jobs = coll.find()

    skills_per_job = []
    skills_list = []

    for j in jobs:
        skills_per_job.append(j['skills'])
        skills_list.extend(j['skills'])
        # skills_list.extend(clean_db_skills(j['skills']))

    skills_count = Counter(skills_list)
    client.close()

    return skills_count


search_term = 'data engineering'
search_term = ca.clean_search_term(search_term)

skills = get_skills_tf_mongo(search_term=search_term)
top_skills_all = [s for s in skills.most_common() if s[1] >= 5]

top_skills = [(str.capitalize(s[0]), s[1]) for s in top_skills_all[:30]]

client = MongoClient()
db = client[DB_NAME]
coll = db[search_term]
total_jobs = float(coll.find().count())
client.close()

norm_counts = []
label_dict = {}
for i, s in enumerate(top_skills):
    label_dict[i] = s[0]
    norm_counts.append(s[1] / total_jobs * 100)

df = pd.DataFrame({'skill': [s for s in top_skills], 'pct jobs with skill': norm_counts})
# clean up df
df['skill'] = df['skill'].apply(lambda x: x[0])

"""
Bar chart of top desired skills.
"""


df.plot.bar(x='skill', y='pct jobs with skill', figsize=(20, 20), legend=False)
plt.xlabel('skill')
plt.ylabel('percent of job with skill')
plt.title('indeed.com "data engineer" top skills')
plt.tight_layout()
plt.show()

"""
Look at plot of when jobs were posted and collected
"""
client = MongoClient()
db = client[DB_NAME]
coll = db[search_term]
jobs = list(coll.find())
# get scraped times for now

scraped_times = [j['scraped_time'] for j in jobs]
scraped_time_df = pd.DataFrame({'scraped_time': scraped_times})
scraped_time_df.sort_values(by='scraped_time', inplace=True)
scraped_time_df.reset_index(inplace=True)
scraped_time_df['count'] = scraped_time_df.index + 1
scraped_time_df.index = scraped_time_df['scraped_time']
scraped_time_df['count'].plot(figsize=(20, 20), linewidth=10)
ax = plt.gca()
years = mdates.YearLocator()   # every year
months = mdates.MonthLocator()  # every month
monthsFmt = mdates.DateFormatter('%b')  # abbreviated month label
yearsFmt = mdates.DateFormatter('%Y')
ax.xaxis.set_major_locator(months)
ax.xaxis.set_major_formatter(monthsFmt)
plt.xlabel('scrape time')
plt.ylabel('cumulative job postings')
plt.title('indeed.com "data engineer" job scrapes')
plt.tight_layout()
plt.show()

"""
Bar chart of job titles.
"""
job_titles = [j['jobTitle'] for j in jobs]
locations = [j['location'] for j in jobs]
title_df = pd.DataFrame({'job title': job_titles, 'location': locations})
title_df_t_groups = title_df.groupby('job title').count()
title_df_t_groups.reset_index(inplace=True)
title_df_t_groups.columns = ['job_title', 'percent of jobs']
title_df_t_groups['percent of jobs'] = title_df_t_groups['percent of jobs'] / title_df_t_groups['percent of jobs'].sum() * 100
title_df_t_groups.sort_values(by='percent of jobs', inplace=True, ascending=False)
title_df_t_groups.iloc[:10].plot.bar(x='job_title', y='percent of jobs', figsize=(20, 20), legend=False)
plt.xlabel('job title')
plt.ylabel('percent of jobs')
plt.title('indeed.com "data engineer" jobs')
plt.tight_layout()
plt.show()

"""
df of jobs for EDA/exploration
"""
full_df = pd.io.json.json_normalize(jobs)
