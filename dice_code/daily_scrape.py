# scrapes dice for the 5 chosen job terms
import os
import sys
sys.path.append('/home/ubuntu/dice_codingskills_project') # hack for AWS
import time
from datetime import datetime
from pytz import timezone
import dice_code.collect_api as ca
import dice_code.machine_learning as ml
mtn = timezone('America/Denver')

f = file('/home/ubuntu/dice_codingskills_project/scrape_log.txt', 'a')
sys.stdout = f
sys.stderr = f

start = datetime.now(mtn)
print '*' * 20
print 'STARTING SCRAPE'
print '*' * 20
print datetime.now(mtn).strftime("%Y-%m-%d %H:%M"), 'mountain time'

f = file('/home/ubuntu/dice_codingskills_project/scrape_log_everything.txt', 'a')
sys.stdout = f
sys.stderr = f

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


f = file('/home/ubuntu/dice_codingskills_project/scrape_log.txt', 'a')
sys.stdout = f
sys.stderr = f

print '*' * 20
print 'FINISHED SCRAPE'
print '*' * 20
print datetime.now(mtn).strftime("%Y-%m-%d %H:%M"), 'mountain time'
end = datetime.now(mtn)
diff = (end-start)
print 'took this long:', str(diff)
