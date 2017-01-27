# dice_codingskills_project
Data science project for Dice job application.

# Setup cronjob scraping
to setup cronjob in ubuntu linux:
`crontab -e`
enter in the file: (min hr day month weekday file)
`00 00 * * * /home/`
or
`@daily /home/ubuntu/dice_codingskills_project/dice_code/daily_scrape.py`

# Exporting MongoDB for transfer
http://stackoverflow.com/questions/11255630/how-to-export-all-collection-in-mongodb

Export:
`mongodump -d <database_name> -o <directory_backup>`
i.e.
`mongodump -d dice_jobs -o dice_jobs.db`

Import:
`mongorestore -d <database_name> <directory_backup>`
i.e.
`mongorestore -d dice_jobs dice_jobs.db`

Todo:  automate backup of db on S3 after scraping is finished (in daily_scrape.py)

# Running on AWS
You will have to redirect the port to port 80 (standard for browsers): `sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-ports 10001` (https://gist.github.com/kentbrew/776580), may also need to do `sudo iptables -t nat -D PREROUTING 1`
`sudo iptables -t nat -A OUTPUT -o lo -p tcp --dport 80 -j REDIRECT --to-port 10001`
I think put those things in here:?
`sudo nano /etc/rc.local`
