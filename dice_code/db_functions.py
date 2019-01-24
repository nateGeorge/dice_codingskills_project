import os
import glob
import datetime

import pytz


def write_backup_file(backup_dir='/home/nate/Dropbox/data/dice_jobs/'):
    """
    uses mongodump to write backup file

    needs to be run from the dice_code directory

    backup_dir should be '../db_backups/' for server, '/home/nate/Dropbox/data/dice_jobs/' for desktop
    """
    tz = pytz.timezone('US/Mountain')
    todays_date_mountain = datetime.datetime.now(tz).strftime('%m-%d-%Y')
    filename = backup_dir + 'dice_jobs.{}.gz'.format(todays_date_mountain)
    os.system('mongodump --archive={} --gzip --db dice_jobs'.format(filename))
    # if file was written, then delete older ones
    if os.path.exists(filename):
        # list all files, and remove all but most recent
        list_of_files = glob.glob('../db_backups/*.gz')
        latest_file = max(list_of_files, key=os.path.getctime)
        for f in list_of_files:
            if f != filename:
                os.remove(f)


def restore_backup_file(backup_dir='/home/nate/Dropbox/data/dice_jobs/'):
    list_of_files = glob.glob(backup_dir + '*.gz')
    latest_file = max(list_of_files, key=os.path.getctime)
    os.system('mongorestore --gzip --archive={} --db dice_jobs'.format(latest_file))
