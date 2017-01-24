# dice_codingskills_project
Data science project for Dice job application.

# Setup cronjob scraping
to setup cronjob in ubuntu linux:
`crontab -e`
enter in the file: (min hr day month weekday file)
`00 00 * * * /home/`
or
`@daily /home/ubuntu/dice_codingskills_project/dice_code/daily_scrape.py`
