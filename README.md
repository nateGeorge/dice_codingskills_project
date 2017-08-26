# dice_codingskills_project
Data science project for Dice job application.

# running on AWS
need an elastic IP, and have to assign it to the instance
need to start mongo: `sudo mongod --dbpath=/var/lib/mongodb --smallfiles`
enter the command `sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-ports 10001` (doesn't seem to work in the /etc/rc.local file, maybe add to bashrc or something)

In the EC2 dashboard, navigate to network and security -> elastic IPs.  Choose 'allocate new address'.  Then choose the new address and go to 'actions -> associate address'.
Then go to route 53, and set up the rest:  
Follow this guide: http://techgenix.com/namecheap-aws-ec2-linux/

navigate to the home dir of the repo and do `python app/app.py`
yay!

# Setup cronjob scraping
to setup cronjob in ubuntu linux:
`sudo crontab -e`

and enter the following at the end:
(min hr day month weekday file)
`0 10 * * * /usr/bin/python /home/ubuntu/dice_codingskills_project/dice_code/daily_scrape.py >> /home/ubuntu/dice_codingskills_project/scrape_log.log`

Do `which python` to make sure the python path is correct.

Cron will run from the home directory, so right now the stdout redirect is going to /scrape_log.txt

Install postfix: `sudo apt-get install postfix` and choose local configuration, so that any errors from crontab are sent to /var/mail/ubuntu.  Check the output with `tail -f /var/mail/ubuntu`

To see what python scripts are currently running, do `ps aux | grep python`.


You should also be able to do it like:
`0 10 * * * /home/ubuntu/dice_codingskills_project/run_cron.sh`

You will also have to do `sudo chmod a+x run_cron.sh` to make the file executable.

I couldn't get that working, though.  To redirect errors, see [this](https://askubuntu.com/questions/222512/cron-info-no-mta-installed-discarding-output-error-in-the-syslog)

Instead of `0 10 * * *`, you should also be able to do
`@daily /home/...`
although I'm not 100% sure this works.

To check your system time do `date "+%H:%M:%S   %d/%m/%y"`.  Usually it should be UTC, so 10am UTC is 4am MST.

To check the log of cron jobs, do: `grep CRON /var/log/syslog`.


# Exporting MongoDB for transfer
http://stackoverflow.com/questions/11255630/how-to-export-all-collection-in-mongodb

Export:
`mongodump -d <database_name> -o <directory_backup>`
i.e.
`mongodump -d dice_jobs -o dice_jobs.db`

Import:
`mongorestore -d <database_name> <directory_backup>`
i.e.
`mongorestore -d dice_jobs dice_jobs.db/dice_jobs`

Todo:  automate backup of db on S3 after scraping is finished (in daily_scrape.py)

# Running on AWS
You will have to redirect the port to port 80 (standard for browsers): `sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-ports 10001` (https://gist.github.com/kentbrew/776580), may also need to do `sudo iptables -t nat -D PREROUTING 1`
`sudo iptables -t nat -A OUTPUT -o lo -p tcp --dport 80 -j REDIRECT --to-port 10001`
I think put those things in here:?
`sudo nano /etc/rc.local`

Run the install_script.sh script

# MongoDB blues
Some problems with MongoDB, to get it started upon startup I had to do `sudo mongod --dbpath=/var/lib/mongodb --smallfiles`
http://stackoverflow.com/questions/14584393/why-getting-error-mongod-dead-but-subsys-locked-and-insufficient-free-space-for
http://stackoverflow.com/questions/24599119/mongodb-not-working-error-dbpath-data-db-does-not-exist
http://askubuntu.com/questions/61503/how-to-start-mongodb-server-on-system-start

# Restarting the server
Upon restart, you may need to run:
`sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-ports 10001`
`sudo mongod --dbpath=/var/lib/mongodb --smallfiles` (this takes a long time)
