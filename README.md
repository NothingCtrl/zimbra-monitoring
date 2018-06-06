Zimbra Server Monitoring
===

Features
--
Simple app for monitoring Zimbra Mail Server (tested with ZC 8.7.7 on Ubuntu 16.04 server)

* Monitoring zimbra service with zmcontrol, auto restart service if got problem
* Monitoring postfix service port (25, 465, 587), auto restart service if got problem
* Monitoring log file `zmmailboxd.out` to detect unexpected error that make services died silenly (unknown bug)
* Monitoring `maibox.log` for authentication failed (ex: hacking attempt), the report will send once per day
* Email: Using Gmail to send error / report to admin email
* Logs: Write simple log per day for audit in logs folder 

Requirement
--
* Python 2.7
* A Gmail account

How to use
--
* Clone this repository to your zimbra server
* Run app: `python2.7 /path/to/file/server-schedule/app.py`
* On the first time run, auto create a database file name: `server_schedule_database.json`
* Modify `server_schedule_database.json` for email account, email prefix
* Create crontask to run `app.py` every 5 minute

Author
--
* nothingctrl[at]gmail.com

DISCLAIMER
--
This app is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

