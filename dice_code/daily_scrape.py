# scrapes dice for the 5 chosen job terms
import os
import gc
import sys
sys.path.append('/home/ubuntu/dice_codingskills_project') # hack for AWS
import time
from datetime import datetime

from pytz import timezone

import db_functions as dbf
import dice_code.collect_api as ca
import dice_code.machine_learning as ml
mtn = timezone('America/Denver')


def full_scrape():
    # f = file('/home/ubuntu/dice_codingskills_project/scrape_log_2018_end.txt', 'a')
    # sys.stdout = f
    # sys.stderr = f

    start = datetime.now(mtn)
    print '*' * 20
    print 'STARTING SCRAPE'
    print '*' * 20
    print datetime.now(mtn).strftime("%Y-%m-%d %H:%M"), 'mountain time'

    # f = file('/home/ubuntu/dice_codingskills_project/scrape_log_everything_2018_end.txt', 'a')
    # sys.stdout = f
    # sys.stderr = f

    for i in range(20):
        print ''

    print '*' * 20
    print 'STARTING SCRAPE'
    print '*' * 20
    print datetime.now(mtn).strftime("%Y-%m-%d %H:%M"), 'mountain time'

    # need to change directory to the main directory so we can import collect_api
    main_dir = '/media/nate/Windows/github/dice_codingskills_project/'
    if not os.path.exists(main_dir):
        main_dir = '/home/ubuntu/dice_codingskills_project/'
        if not os.path.exists(main_dir):
            print 'path to', main_dir, 'does not exist.'
            print 'exiting now.'
            exit()

    os.chdir(main_dir)

    jobs = ['data science',
            'data engineer',
            'front end developer',
            'full stack',
            'ruby on rails',
            'php',
            'quality assurance',
            # 'mobile QE',  # this one never returned any results...
            'quality engineer',
            'javascript',
            'C#',
            'nodejs',
            'analyst',
            'gis']

    for j in jobs:
        ca.continuous_scrape(search_term=j, debug=True)
        time.sleep(120) # wait 2 minutes to avoid having ip blocked

    # do ML part separately, because it was causing server to crash sometimes
    for j in jobs:
        ml.predict_salary(search_term=j)


    f = file(main_dir + '/scrape_log.txt', 'a')
    sys.stdout = f
    sys.stderr = f

    print '*' * 20
    print 'FINISHED SCRAPE'
    print '*' * 20
    print datetime.now(mtn).strftime("%Y-%m-%d %H:%M"), 'mountain time'
    end = datetime.now(mtn)
    diff = (end-start)
    print 'took this long:', str(diff)

    dbf.write_backup_file()
    gc.collect()


def daily_scrape():
    print('going to start scraping, 5s to abort...')
    time.sleep(5)
    last_scrape = 0
    seconds_in_day = 3600 * 24
    while True:
        if time.time() - last_scrape > seconds_in_day:
            last_scrape = time.time()
            full_scrape()
        else:
            sleep(600)


if __name__ == "__main__":
    daily_scrape()
