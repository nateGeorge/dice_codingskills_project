# dice_codingskills_project
Data science project for Dice job application.

# running on AWS
Usually I spin up a spot instance because it's cheaper.  The m4.xlarge seems to be a decent choice right now.  Once the instance is up, you should ssh into it, and the repo should be cloned into it.

## elastic IP
Then you need an elastic IP, and have to assign it to the instance.  Create the elastic IP (Amazon pool), then choose 'actions' and 'associate address'.  The address needs to be associated with the server that was just spun up.  Once the IP is associated, you should use that IP to ssh into the instance.
Then go to route 53, and set up the rest:  
Follow this guide: http://techgenix.com/namecheap-aws-ec2-linux/
It can take a while (up to 24 hours) for the nameservers to update, and for your web address to actually work.  You do not need the period after the DNS server names

# Starting the db and server
Next, you need to start mongo: `sudo mongod --dbpath=/var/lib/mongodb --smallfiles`
This can be run in a tmux shell, or sent to the background with ctrl+z, then typing `bg`.


To be able to access the site, we have to make available port 80:  Enter the commands
`sudo iptables -A INPUT -i eth0 -p tcp --dport 80 -j ACCEPT`
`sudo iptables -A INPUT -i eth0 -p tcp --dport 10001 -j ACCEPT`
`sudo iptables -A PREROUTING -t nat -i eth0 -p tcp --dport 80 -j REDIRECT --to-port 10001`

-- this one seemed to the the final key to making it work, after running the above 3
`sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-ports 10001`

`sudo iptables -t nat -D PREROUTING 1`
`sudo iptables -t nat -A OUTPUT -o lo -p tcp --dport 80 -j REDIRECT --to-port 10001`
(doesn't seem to work in the /etc/rc.local file, maybe add to bashrc or something)

Next it's best to run this in a tmux session (`tmux new -s server` -- creates a tmux session called server), which will mean you can access the running server after logging out and the ssh-ing back in.  Navigate to the home dir of the repo and do `python app/app.py`.
You should be able to access at your ip with port 10001, like so: 54.70.49.112:10001
Yay!

# Setup cronjob scraping
TODO: create function in the scraping file so it runs periodically and can be run from within a tmux shell.
to setup cronjob in ubuntu linux:
`sudo crontab -e`

and enter the following at the end:
(min hr day month weekday file)
`0 10 * * * /usr/bin/python /home/ubuntu/dice_codingskills_project/dice_code/daily_scrape.py >> /home/ubuntu/dice_codingskills_project/scrape_log.log`

Do `which python` to make sure the python path is correct.

Cron will run from the home directory (it used to be the stdout redirect is going to /scrape_log.txt)

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

(from within bash shell, not mongo)

Export:
`mongodump -d <database_name> -o <directory_backup>`
i.e.
`mongodump -d dice_jobs -o dice_jobs.db`

Import:
`mongorestore -d <database_name> <directory_backup>`
i.e.
`mongorestore -d dice_jobs dice_jobs.db/dice_jobs`

Then from local machine, you can get the data with scp:

`scp -r -i ~/.ssh/ubuntu16lap.pem ubuntu@54.68.106.57:/home/ubuntu/dice_jobs_jan_2018.bkup /media/nate/data_lake/dice_jobs_backups`

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

# troubleshooting
If the scraping isn't finishing, likely memory is running out.  I was trying to run this on a 8GB memory machine at first, and the scraping crashed for a while without me noticing.  I was able to find it was crashing from checking:
`nano /var/log/kern.log`
which I found out about from here: https://unix.stackexchange.com/questions/27461/how-can-i-know-when-a-cron-job-was-killed-or-it-crashed
