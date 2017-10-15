"""
Version 1.0.0
Notify for change in public ip.
Last updated on 14 Oct 2017.

TO DO:
- Notification mail sent verification
- Maintain status file for last_ip

"""
import smtplib
import socket
import sys
import time
from urllib2 import urlopen
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from datetime import timedelta

#
# Global variables, change as required
g_ip_url = 'http://ip.42.pl/raw'
g_gmail_smtp_adr = 'smtp.gmail.com'
g_gmail_smpt_port = '465'
g_curpublic_ip = '000.000.000.000'
g_from_adr = 'sender_email@email.com'
g_to_adrs  = ['reciever_email@gmail.com']
#
# No modify zone frome here
def logErrAndExit(err):
    print "Eror: " + str(err)
    print "Exiting"
    sys.exit(1)


def verifyIPv4(ip):
    try: 
        socket.inet_aton(ip)
        return ip
    except:
        logErrAndExit("Got invalid ip " + ip)


def getPublicIp():
	"""Report back public ipv4 address
	rtype: IPv4
	"""
	try:
            my_ip = urlopen(g_ip_url).read()
            my_ip = my_ip.strip()
        except Exception, e:
            print "Error while reading public ip"
            logErrAndExit(e)
        #
        # validate and return
        return verifyIPv4(my_ip)


def getSystemUptime(dum):
    dum = dum # seems issue without parameter, may be timedelta issue
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_sec = float(f.readline().split()[0])
            uptime_str = timedelta(seconds = uptime_sec)
    except:
        uptime_str = 'unknown'
    return str(uptime_str)


def notifyNewIp(new_ip):
    username = g_from_adr
    password = 'pwd'

    # login with ssl
    try:
            server = smtplib.SMTP_SSL(g_gmail_smtp_adr, g_gmail_smpt_port)
            server.login(username,password)
    except Exception, e:
            print "Error occured while connecting to smtp server"
            logErrAndExit(e)
    email_msg = MIMEMultipart()
    email_msg['From'] = g_from_adr
    email_msg['To'] =  ", ".join(g_to_adrs)
    email_msg['Subject'] = "Server Ip changed"

    body = """
            Public ip has changed:
            Last IP: {0:s}
            New IP: {1:s}
            System is running for: {2:s}            
            
            Note:
            This is an autometically triggered email and contains some confidential 
            inforamtation. If you have received this message in error, please 
            notify the sender and delete the message. 
            
            Thank you            
            """.format(g_curpublic_ip, new_ip, getSystemUptime('dummy'))
    email_msg.attach(MIMEText(body, 'plain'))
    text = email_msg.as_string()
    server.sendmail(g_from_adr, g_to_adrs, text)
    server.quit()


def main():
    _1st_loop_flag = True
    while 1:
        global g_curpublic_ip
        #
        # check new ip
        new_ip = getPublicIp()
        if new_ip == g_curpublic_ip:
            time.sleep(3)
            continue
        #
        # notify new ip and update
        if not _1st_loop_flag:
            print "Got new IP: " + new_ip
            notifyNewIp(new_ip)
            _1st_loop_flag = False
        g_curpublic_ip = new_ip

if __name__ == "__main__":
    main()
