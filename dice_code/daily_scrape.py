# scrapes dice for the 5 chosen job terms
import os
import sys
sys.path.append('/home/ubuntu/dice_codingskills_project') # hack for AWS
import time

# need to change directory to the main directory so we can import collect_api
main_dir = '/media/nate/Windows/github/dice_codingskills_project/'
if not os.path.exists(main_dir):
    main_dir = '/home/ubuntu/dice_codingskills_project/'
    if not os.path.exists(main_dir):
        print 'path to', main_dir, 'does not exist.'
        print 'exiting now.'
        exit()

os.chdir(main_dir)
import dice_code.collect_api as ca
import dice_code.machine_learning as ml

os.chdir(main_dir)

jobs = ['analyst',
        'data science',
        'front end developer',
        'full stack',
        'ruby on rails']

for j in jobs:
    ca.continuous_scrape(search_term=j, debug=True)
    ml.predict_salary(search_term=j)
    time.sleep(120) # wait 2 minutes to avoid having ip blocked
