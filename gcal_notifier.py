#!/usr/bin/python

import iso8601
import datetime
import os
import re
import urllib
import ConfigParser

import icalendar

import client

CONF = None

def clean(code):
    return code.replace(' ', '').replace('-', '')

def find_passcode(text):
    m = re.search('[Cc]ode: *([- 0-9]+)', text)
    if m:
        return int(clean(m.group(1)))
    m = re.search('PC:? *([- 0-9]+)', text)
    if m:
        return int(clean(m.group(1)))
    m = re.search('[Pp]asscode:? *([- 0-9]+)', text)
    if m:
        return int(clean(m.group(1)))

def get_upcoming(cal, timerange):
    now = datetime.datetime.utcnow().replace(tzinfo=iso8601.iso8601.Utc())

    upcoming = {}
    for item in cal.walk():
        if item.name == 'VEVENT':
            start = item.decoded('dtstart')
            delta = start - now
            if start > now and delta < timerange:
                upcoming[delta] = item

    upcoming_calls = {}
    for delta in sorted(upcoming.keys()):
        item = upcoming[delta]
        code = find_passcode(item.get('location') + item.get('summary'))
        if code:
            upcoming_calls[delta] = (item, code)
    return upcoming_calls

def maybe_call_next(caldata):
    cal = icalendar.Calendar.from_ical(caldata)
    timerange = datetime.timedelta(minutes=int(
            CONF.get('prefs', 'lookahead_minutes')))
    calls = get_upcoming(cal, timerange)
    sound = CONF.get('prefs', 'alert_sound')
    player = CONF.get('prefs', 'alert_player')
    # Apparently Zenity's timeout function is broken :(
    #timeout = int(CONF.get('prefs', 'prompt_timeout'))
    host = CONF.get('prefs', 'asterisk_host')
    port = int(CONF.get('prefs', 'host_port'))
    number = CONF.get('prefs', 'conf_number')

    for delta in sorted(calls.keys()):
        item, code = calls[delta]
        msg = 'Call %s (Passcode %s). Call this?' % (item.get('summary'),
                                                     code)
        os.system('%s %s >/dev/null 2>&1 &' % (player, sound))
        result = os.system("zenity --question --text='%s'" % (msg))
        print result
        if result == 0:
            client.make_call(host, port, number, code)
            break

def fetch_latest():
    return urllib.urlopen(CONF.get('prefs', 'gcal_url')).read()

def parse_config(conf_file='gcal_notifier.conf'):
    global CONF
    CONF = ConfigParser.ConfigParser()
    CONF.read(conf_file)

if __name__ == '__main__':
    parse_config()
    caldata = fetch_latest()
    maybe_call_next(caldata)
