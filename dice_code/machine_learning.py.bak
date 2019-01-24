import dice_code.collect_api as ca
import pandas as pd
import numpy as np
import re
import gc
import os
import psutil
from sklearn.model_selection import train_test_split as tts
from sklearn.metrics import mean_squared_error as mse
import xgboost as xgb
import matplotlib.pyplot as plt
from pymongo import MongoClient

DB_NAME = 'dice_jobs'


def dummy_top_n(df, n, col):
    """

    """
    top = df[col].value_counts()
    top_n = ca.convert(top[:n].index.tolist())
    for t in top_n:
        df[t] = df[col] == t

    return df, top_n


def predict_salary(search_term='data science', show_diff_plot=False):
    """
    Predicts unknown salaries for jobs.

    jobs: list of dicts
        list of dictionaries of job listings from mongodb
    """
    # TODO: only use most recent job postings so it uses less memory (maybe those from the last month)
    jobs = ca.get_jobs(search_term=search_term, recent=False)


    keep_columns = ['clean_sal']
    df = pd.DataFrame(jobs)
    # df, top_n = dummy_top_n(df, 5, 'company')
    # keep_columns.extend(top_n)
    top_companies = df['company'].value_counts()
    top_5_companies = ca.convert(top_companies[:5].index.tolist())
    keep_columns.extend(top_5_companies)
    for t in top_5_companies:
        df[t] = df['company'] == t

    skills_counter = ca.get_skills_tf_mongo(search_term=search_term)
    top_10_skills = [s[0].capitalize() for s in skills_counter.most_common()[:10]]
    keep_columns.extend(top_10_skills)
    for t in top_10_skills:
        df[t] = df['clean_skills'].apply(lambda x: t in x)

    # df, top_n = dummy_top_n(df, 10, 'location')
    # keep_columns.extend(top_n)
    top_locations = df[df['location'] != '']['location'].value_counts()
    top_10_locations = ca.convert(top_locations[:10].index.tolist())
    keep_columns.extend(top_10_locations)
    for t in top_10_locations:
        df[t] = df['location'] == t

    df['state'] = df['location'].apply(lambda x: ca.extract_state(x))
    # df, top_n = dummy_top_n(df, 10, 'state')
    # keep_columns.extend(top_n)
    top_states = df[df['state'] != '']['state'].value_counts()
    top_10_states = ca.convert(top_states[:10].index.tolist())
    keep_columns.extend(top_10_states)
    for t in top_10_states:
        df[t] = df['state'] == t

    df['is_senior'] = df['jobTitle'].apply(lambda x: is_senior(x))
    keep_columns.append('is_senior')

    dum_df = pd.get_dummies(df, columns=['clean_emp_type', 'travel'])
    new_cols = ca.convert(set(dum_df.columns).difference(set(df.columns)))
    keep_columns.extend(new_cols)
    df = dum_df[keep_columns]

    df_known = df[df['clean_sal'] != 0].copy()
    df_known = df_known[df_known['clean_sal'].notnull()]
    df_known = df_known[df_known['clean_sal'] > 1000]
    df_known = df_known[df_known['clean_sal'] < 250000] # some outliers in there
    df_unknown = df[~df.index.isin(df_known.index)].copy()
    df_unknown.drop('clean_sal', inplace=True, axis=1)
    target = df_known.pop('clean_sal').values
    # analyzing memory use, seemed to crash around here
    gc.collect()
    process = psutil.Process(os.getpid())
    print 'memory use (GB) after creating 2 dfs:'
    print process.memory_info().rss / 1000000000.0
    for c in df_known.columns:
        print c
        df_known[c] = df_known[c].apply(lambda x: tf_to_10(x))
        df_unknown[c] = df_unknown[c].apply(lambda x: tf_to_10(x))

    features = df_known.values.astype(np.float64)
    uk_feats = df_unknown.values

    X_train, X_test, y_train, y_test = tts(
    features, target, test_size=0.33, random_state=42)
    gc.collect()
    process = psutil.Process(os.getpid())
    print 'memory use (GB) after train/test split:'
    print process.memory_info().rss / 1000000000.0
    # dtrain = xgb.DMatrix(X_train, label=y_train)#, missing=-999)
    # num_round = 200
    # param = {'max_depth':4,
    #             'eta':0.1,
    #             'silent':0,
    #             'subsample':0.4,
    #             'objective':'reg:linear',
    #             'eval_metric':'rmse',
    #             "booster":"gblinear"}
    xgb_model = xgb.XGBRegressor(subsample=0.4).fit(X_train, y_train)
    gc.collect()
    process = psutil.Process(os.getpid())
    print 'memory use (GB) after xgb first fit:'
    print process.memory_info().rss / 1000000000.0
    # dtest = xgb.DMatrix(X_test, label=y_test)#, missing=-999)
    preds = xgb_model.predict(X_test)
    print mse(y_test, preds)
    if show_diff_plot:
        f = plt.figure(figsize=(9, 9))
        plt.scatter(y_test, preds)
        max_lim = max(target)
        plt.xlim([0, max_lim])
        plt.ylim([0, max_lim])
        plt.plot([0, max_lim], [0, max_lim])
        plt.show()

    xgb_final_model = xgb.XGBRegressor(subsample=0.4).fit(features, target)
    gc.collect()
    process = psutil.Process(os.getpid())
    print 'memory use (GB) after 2nd xgb fit:'
    print process.memory_info().rss / 1000000000.0
    predictions = xgb_final_model.predict(uk_feats)
    client = MongoClient()
    db = client[DB_NAME]
    coll = db[search_term]
    df_unknown['predicted_salary'] = predictions
    for i, r in df_unknown.iterrows():
        coll.update_one(jobs[i], {'$set': {'predicted_salary': float(r['predicted_salary'])}})

    client.close()


def tf_to_10(x):
    """
    Maps true/false to 1/0
    """
    if x == True:
        return 1
    elif x == False:
        return 0

    return x

def is_senior(x):
    """
    If Sr or Senior is in the job title, returns True, otherwise False.
    """
    if re.search('sr\.', x, re.IGNORECASE) is not None:
        return True
    elif re.search('senior', x, re.IGNORECASE) is not None:
        return True
    elif re.search('sr\s', x, re.IGNORECASE) is not None:
        return True

    return False
