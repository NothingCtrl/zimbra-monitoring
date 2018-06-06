#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@author: nothingctrl
@contact: nothingctrl[at]gmail.com
@version: 2.0
@date: 2018-06-06
This program for run an system command eg: reboot server, with email notification for admin
"""

import os
import logging
import datetime
import smtplib  # Send eamil
import json

_db_file_name = 'server_schedule_database.json'

def write_log(log_msg, echo_msg=False):
    """
    Write log to a file
    :param echo_msg:
    :param log_msg:
    :return:
    """
    today = datetime.date.today()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(dir_path)
    if not os.path.isdir('logs'):
        os.mkdir('logs')
    if echo_msg:
        print "[LOG] %s" % log_msg

    log_msg = " --- " + str(datetime.datetime.now()) + " --- " + log_msg
    logging.basicConfig(filename=dir_path + '/logs/app_log_' + str(today) + '.log', level=logging.DEBUG)
    logging.info(log_msg)

def write_to_db(key, value):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(dir_path)
    db_file = dir_path + "/" + _db_file_name
    if os.path.isfile(db_file):
        data = {}
        with open(db_file) as f:
            try:
                data = json.load(f)
                f.close()
            except:
                pass

        data[key] = value
        with open(db_file, 'w+') as f:
            json.dump(data, f)
            f.close()
    else:
        with open(db_file, 'w+') as f:
            data = {key: value}
            json.dump(data, f)
            f.close()


def read_db():
    data = {}
    dir_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(dir_path)
    db_file = dir_path + "/" + _db_file_name
    if os.path.isfile(db_file):
        with open(db_file) as f:
            try:
                data = json.load(f)
                f.close()
            except:
                pass
    return data

def send_email(send_to, subject, body):
    """
    Send email to admin report error
    :param send_to:
    :param subject:
    :param body:
    :return:

    send_email('abc@gmail.com', "Subject email", "Email body ....")

    """
    write_log("Email subject: [%s] sending" % subject)
    data = read_db()
    email_username = data['gmail_username']
    email_password = data['gmail_password']
    email_port = 587
    email_smtp_addr = 'smtp.gmail.com'

    msg = "\r\n".join([
        "From: %s" % email_username,
        "To: %s" % send_to,
        "Subject: %s" % subject,
        "",
        "%s" % body
    ])
    server = smtplib.SMTP('%s:%s' % (email_smtp_addr, email_port))
    server.ehlo()
    server.starttls()
    server.login(email_username, email_password)
    server.sendmail(email_username, send_to, msg)
    server.quit()

def schedule_reboot_server():
    """
    Reboot mail server every xx days
    :return:
    """
    write_log("fn schedule_reboot_server() run")
    data = read_db()
    today = str(datetime.date.today())
    hour = datetime.datetime.now().hour
    need_reboot = False
    write_to_db('last_run', str(datetime.datetime.now()))
    days_to_reboot = int(data['days_to_reboot'])
    send_to_addr = data['email_send_to_addr']
    hour_reboot = int(data['hour_reboot'])
    if data['today'] != today:
        write_to_db('today', today)
        write_to_db('today_rebooted', False)
        data['today_rebooted'] = False
        if days_to_reboot > 1:
            write_to_db('days_to_reboot', days_to_reboot - 1)
        else:
            if hour == hour_reboot and not data['today_rebooted']:
                need_reboot = True
    else:
        if days_to_reboot == 1 and hour == hour_reboot and not data['today_rebooted']:
            need_reboot = True

    if need_reboot:
        write_to_db('days_to_reboot', data['default_days_reboot'])
        write_to_db('today_rebooted', True)
        write_to_db('just_reboot', True)
        send_email(send_to_addr, "%s Server going to reboot" % data['email_subject_prefix'],
                   "Server %s going to reboot after %d days run.\n\nThis is auto message, don't reply." % (data['email_subject_prefix'], data['default_days_reboot']))
        write_log("Server reboot")
        write_to_db('zimbra_failed_count', 0)
        _reboot_linux_server()
    else:
        if 'just_reboot' in data.keys() and data['just_reboot']:
            write_to_db('just_reboot', False)
            send_email(send_to_addr, "%s Server rebooted" % data['email_subject_prefix'],
                       "Server %s back online.\n\nThis is auto message, don't reply." % (data['email_subject_prefix']))
            
def _reboot_linux_server():
    data = read_db()
    if 'live' in data.keys() and data['live']:
        write_log("Execute server reboot command")
        os.system('/sbin/shutdown -r +5')
        exit()
    else:
        write_log("Not LIVE, not reboot.")

def monitoring_zimbra_services_status():
    write_log("fn monitoring_zimbra_services_status() run")
    data = read_db()
    failed_count = 0
    max_before_restart = 5

    if 'zimbra_failed_count' not in data.keys() or 'zimbra_failed_count_max_before_restart_service' not in data.keys():
        write_to_db('zimbra_failed_count', failed_count)
        write_to_db('zimbra_failed_count_max_before_restart_service', max_before_restart)
    if 'zimbra_failed_count' in data.keys():
        failed_count = int(data['zimbra_failed_count'])
    if 'zimbra_failed_count_max_before_restart_service' in data.keys():
        max_before_restart = int(data['zimbra_failed_count_max_before_restart_service'])

    # read zmcontrol status as zimbra
    out = os.popen('su - zimbra -c "zmcontrol status"').read()

    if "Stopped" in out or "not running" in out:
        # got some problem
        failed_count += 1
        write_log("zmcontrol status got error: %s" % out)
        write_log("failed count: %d" % failed_count)
        if failed_count <= max_before_restart:
            write_to_db('zimbra_failed_count', failed_count)
        else:
            write_to_db('zimbra_failed_count', 0)
            _restart_zmcontrol()            
            send_email(data['email_send_to_addr'], "%s zmcontrol restarted services" % data['email_subject_prefix'],
                       "%s zmcontrol restarted after max failed count pass\n\nThis is auto message, don't reply."
                       % (data['email_subject_prefix']))
    else:
        write_to_db('zimbra_failed_count', 0)

def _check_postfix_with_netstat():
    """
    Check status of postfix service, if running 'netstat -tulpn' return:
        0.0.0.0:587             0.0.0.0:*               LISTEN      1523/master
        0.0.0.0:465             0.0.0.0:*               LISTEN      1523/master
        0.0.0.0:25              0.0.0.0:*               LISTEN      1523/master
    :return:
    """
    out = os.popen('netstat -tulpn').read()
    status = True
    if "0.0.0.0:25" not in out:
        status = False
        write_log("postfix port 25 not working")
    if "0.0.0.0:465" not in out:
        status = False
        write_log("postfix port 465 not working")
    if "0.0.0.0:587" not in out:
        status = False
        write_log("postfix port 587 not working")
    return status

def _restart_postfix_service():
    # restart service
    write_log("stop postfix")
    stop = os.popen('su - zimbra -c "postfix stop"').read()
    write_log(stop)
    write_log("start postfix")
    start = os.popen('su - zimbra -c "postfix start"').read()
    write_log(start)

def monitoring_postfix_status():
    """
    check if postfix not run, try to restart service -- only try once
    :return:
    """
    write_log("fn monitoring_postfix_status() run")
    data = read_db()
    # count retry resume postfix
    failed_count = 0
    if 'postfix_failed_count' in data.keys():
        failed_count = data['postfix_failed_count']
    status = _check_postfix_with_netstat()
    if not status:
        failed_count += 1
        write_to_db('postfix_failed_count', failed_count)
        if failed_count <= 3:
            write_log("Going restart postfix, postfix_failed_count = %d" % failed_count)
            _restart_postfix_service()
        else:
            if failed_count == 4:
                send_email(data['email_send_to_addr'],
                           "%s Service postfix is not running -- please check" % data[
                               'email_subject_prefix'],
                           "Server %s: detect postfix service is not working and tried to restart but is not success. Please check.\n\nThis is auto message, don't reply."
                           % (data['email_subject_prefix']))
                write_log("postfix problem after many time retry, send email notification to admin")
            write_log("postfix problem after many time retry, do nothing")            
    else:
        # postfix resume work
        if failed_count > 0:
            write_to_db('postfix_failed_count', 0)
            write_log("postfix resume to work, postfix_failed_count: %d" % failed_count)
            send_email(data['email_send_to_addr'],
                       "%s Service postfix is running -- auto resume success" % data['email_subject_prefix'],
                       "Server %s: service postfix is working (postfix_failed_count: %d).\n\nThis is auto message, don't reply."
                       % (data['email_subject_prefix'], failed_count))

def _restart_zmcontrol():
    write_log('Restart zmcontrol')
    log = os.popen('su - zimbra -c "zmcontrol restart"').read()
    write_log(log)

def monitoring_zmmailboxd_out():
    """
    Problem: sometime zimbra service dying, imap and pop service in state: Initiating shutdown
        check_postfix_status() will return true
        _check_postfix_with_netstat() will return true
        monitoring_zimbra_services_status() not detect problem
        telnet to port 993 995 465 587 still woring
    but mail client cannot authentication and pop-up authentication error, before we find out why service dying, we need monitoting zmmailboxd.out
    --
    in file "/opt/zimbra/log/zmmailboxd.out", a log line show up, ex: zmthrdump: Requested thread dump [PID 22191] at Tue Jun  5 19:12:30 2018
    this is a signal allow we know service got problem
    This function use for check "/opt/zimbra/log/zmmailboxd.out", if log line above show up, going restart zimbra service
    :return:
    """
    write_log("fn monitor_zmmailboxd_out() run")
    list_time = []
    now = datetime.datetime.now()
    for i in range(1, 6):
        ago = now - datetime.timedelta(minutes=i)
        list_time.append(" %d %s:%s" % (ago.day, (ago.hour < 10 and "0" + str(ago.hour) or ago.hour), (ago.minute < 10 and "0" + str(ago.minute) or ago.minute)))
    # read all zmmailboxd.out* file
    logs = os.popen('cat /opt/zimbra/log/zmmailboxd.out* | grep "Requested thread dump "').read()
    logs = logs.splitlines()
    data = read_db()
    last_detect_string = ''
    if 'zmthrdump_last_detect_string' in data.keys():
        last_detect_string = data['zmthrdump_last_detect_string']
    for log in logs:
        if "zmthrdump: Requested thread dump" in log:
            for t in list_time:
                if t in log:
                    if last_detect_string != log:
                        write_log("Detect 'Requested thread dump' in zmmailboxd.out, string: %s, going to restart zimbra service" % log)
                        write_to_db('zmthrdump_last_detect_string', log)
                        _restart_zmcontrol()
                        send_email(data['email_send_to_addr'], '%s Requested thread dump detect: service restarted' % data['email_subject_prefix'], "zmthrdump: %s" % log)

def monitoring_auth_failed():
    """
    Monitoring file /opt/zimbra/mailbox.log
    detect hacking attem by string: ' authentication failed for '
    :return:
    """
    write_log("fn monitoing_auth_failed() run")
    now = datetime.datetime.now()
    safe_ignore_string = ['(account(or domain) status is closed)']
    # only run once per day
    if now.hour == 23 and now.minute in (55, 56, 57, 58, 59):
        logs = os.popen('cat /opt/zimbra/mailbox.log | grep "authentication failed for"').read()
        logs = logs.splitlines()
        data = read_db()
        report = ''
        new_line = ''
        for log in logs:
            ignore = False
            for s in safe_ignore_string:
                if s in log:
                    ignore = True
            if not ignore:
                report += new_line + log
                new_line = "\n"
        if len(report) > 0:
            write_log("monitoing_auth_failed: report send")
            write_log("Report:\n%s" % report)
            send_email(data['email_send_to_addr'],
                       '%s Report login failed in mailbox.log' % data['email_subject_prefix'], report)
        else:
            write_log("monitoing_auth_failed: nothing to report")

def create_database_if_not_exist():
    today = str(datetime.date.today())
    if not read_db():
        write_to_db('days_to_reboot', 45)
        write_to_db('today', today)
        write_to_db('today_rebooted', False)
        write_to_db('email_send_to_addr', 'your_email@foo.bar')     # email receive system report / error nofification
        write_to_db('default_days_reboot', 45)   # reboot every 45 days
        write_to_db('hour_reboot', 3)            # reboot at 3AM server time
        write_to_db('email_subject_prefix', "[any_prefix_you_want]")
        write_to_db('live', True)
        write_to_db('gmail_username', 'account_for_app_to_send_email@gmail.com')
        write_to_db('gmail_password', 'account_email_password')
        write_to_db('just_reboot', False)
        write_to_db('zimbra_failed_count', 0)
        write_to_db('zimbra_failed_count_max_before_restart_service', 5)
        write_log("Database created")
        data = read_db()
        send_email(data['email_send_to_addr'], "%s Test message" % data['email_subject_prefix'],
                   "This is email test on server %s.\n\nThis is auto message, don't reply." % (data['email_subject_prefix']))


def main():
    create_database_if_not_exist()
    schedule_reboot_server()
    monitoring_zimbra_services_status()
    monitoring_postfix_status()
    monitoring_zmmailboxd_out()
    monitoring_auth_failed()

# ----------------------------
main()
