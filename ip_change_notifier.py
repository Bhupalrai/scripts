"""
Version 1.0.1
Notify for change in public ip.
Last updated on 18 Oct 2017.

"""
import smtplib
import socket
import sys
import time
import getpass
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from datetime import timedelta
from requests import get

#
# Global variables, change as required
g_ip_url = 'http://api.ipify.org/'
g_gmail_smtp_adr = 'smtp.gmail.com'
g_gmail_smpt_port = '465'
g_status_file = '/tmp/.icn_sts_f.dat'
g_default_public_ip = '000.000.000.000'
g_from_adr = 'sender@email.com'
g_password = None
g_to_adrs = ['reciever@email.com']
g_lastmailsent = True
g_ip_get_str = 'get'
g_ip_set_str = 'set'
g_sleep_time = 15
#
# No modify zone frome here
def getTimestamp():
    return str(time.strftime("%Y-%m-%d %H:%M:%S "))


def logErrAndExit(err):
    print "Eror: " + str(err)
    #print "Exiting"
    #sys.exit(1)


def verifyIPv4(ip):
    try:
        socket.inet_aton(ip)
    except:
        logErrAndExit(getTimestamp() + "Got invalid ip " + ip)
        return False
    return True


def getPublicIp():
    """Report back public ipv4 address
    rtype: IPv4
    """
    global g_ip_url
    try:
        my_ip = get(g_ip_url).text
    except Exception, e:
        print getTimestamp() + "Error while reading public ip"
        logErrAndExit(e)
        return None
    #
    # validate and return
    if verifyIPv4(my_ip):
        return my_ip
    else:
        return None


def getSystemUptime():
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_sec = float(f.readline().split()[0])
            uptime_str = timedelta(seconds = uptime_sec)
    except:
        uptime_str = 'unknown'
    return str(uptime_str)


def notifyNewIp(new_ip, last_known_ip):
    global g_lastmailsent
    username = g_from_adr

    #
    # login with ssl
    try:
            server = smtplib.SMTP_SSL(g_gmail_smtp_adr, g_gmail_smpt_port)
            server.login(username, g_password)
    except Exception, e:
            print getTimestamp() + "Error occurred while connecting to smtp server"
            logErrAndExit(e)
            return	
    email_msg = MIMEMultipart()
    email_msg['From'] = g_from_adr
    email_msg['To'] = ", ".join(g_to_adrs)
    email_msg['Subject'] = "Server Ip changed"

    body = ("\n"
            "            Public ip has changed:\n"
            "            Last IP: {0:s}\n"
            "            New IP: {1:s}\n"
            "            System is running for: {2:s}\n"
            "\n"
            "            Note:\n"
            "            This is an automatically triggered email and contains some confidential information.\n"
            "            If you have received this message in error, please notify the sender and delete the message.\n"
            "\n"
            "            Thank you\n"
            "            ").format(last_known_ip, new_ip, getSystemUptime())
    email_msg.attach(MIMEText(body, 'plain'))
    text = email_msg.as_string()
    try:
        server.sendmail(g_from_adr, g_to_adrs, text)
        server.quit()
    except Exception, err:
        print getTimestamp() + 'Sending email failed.'
        logErrAndExit(err)
        g_lastmailsent = False
        return
    #
    # update current ip
    lastKnownIP(g_ip_set_str, new_ip)
    g_lastmailsent = True


def lastKnownIP(mode, new_ip=None):
    if mode == g_ip_get_str:
        try:
            with open(g_status_file, 'r+') as sts_f:
                ip = sts_f.readline().strip()
                if not ip:
                    return g_default_public_ip
                if verifyIPv4(ip):
                    return ip
                else:
                    return g_default_public_ip
        except EnvironmentError, err:
            print getTimestamp() + 'error reading status file ' + g_status_file
            logErrAndExit(err)
            return g_default_public_ip
    elif mode == g_ip_set_str and new_ip:
        try:
            with open(g_status_file, 'w+') as sts_f:
                sts_f.write(new_ip)
                return True
        except EnvironmentError, err:
            print getTimestamp() + 'error writing to status file ' + g_status_file
            logErrAndExit(err)
            return False
    else :
        return g_default_public_ip


def main():
    global g_password
    g_password = getpass.getpass('email password for ' + g_from_adr + ': ')

    while 1:
        #
        # check new ip
        last_known_ip = lastKnownIP(g_ip_get_str)
        new_ip = getPublicIp()
        if not new_ip:
            print getTimestamp() + 'Got empty public ip.'
            print getTimestamp() + 'We will try again'
            time.sleep(g_sleep_time)
            continue
        #
        # try notifying new ip if failed last time
        if not g_lastmailsent:
            notifyNewIp(new_ip, last_known_ip)
            time.sleep(g_sleep_time)
            continue
        if new_ip == last_known_ip:
            time.sleep(g_sleep_time)
            continue
        #
        # notify new ip and update
        print getTimestamp() + "Got new IP: " + new_ip
        notifyNewIp(new_ip, last_known_ip)

if __name__ == "__main__":
    main()
