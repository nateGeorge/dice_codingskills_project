# followed this guide: http://stackabuse.com/how-to-send-emails-with-gmail-using-python/
import smtplib
import os
import textwrap

def get_env_vars():
    '''
    gets gmail uname/pass, phone number to text, and email to send to
    '''
    gmail_user = os.getenv('udacity_gmail_uname') + '@gmail.com'
    gmail_password = os.getenv('udacity_gmail_pass')
    phone_email = os.getenv('my_phone_num_email')
    email_addr = os.getenv('my_email_addr')
    return gmail_user, gmail_password, phone_email, email_addr

def compose_email(from_addr, to, search_term):
    '''
    sends email with link to udacity project to review

    args:
    from_line -- string; email address the message is from
    to -- list of strings; email addresses the message is to
    link -- string; link to udacity project to review
    '''
    subject = 'New search term requested: {}'.format(search_term)
    body = "New search term requested: {}".format(search_term)

    email_text = ("From: %s\n"
                    "To: %s\n"
                    "Subject: %s\n"
                    ""
                    "%s") % (from_addr, ", ".join(to), subject, body)

    return email_text

def send_messages(search_term, text=False):
    '''
    sends text and email notifying of reviews assigned

    args:
    link -- string; link to udacity review that has been assigned
    text -- boolean; if True will send a text message
    '''
    gmail_user, gmail_password, phone_email, email_addr = get_env_vars()
    to = [email_addr]
    if text:
        to = [phone_email, email_addr]
    email_text = compose_email(from_addr=gmail_user, to=to, search_term=search_term)
    print email_text
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, to, email_text)
        server.close()
    except:
        print 'Something went wrong...'
        print 'Couldn\'t email'
