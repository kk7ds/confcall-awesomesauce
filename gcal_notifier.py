#!/usr/bin/python

import iso8601
import datetime
import os
import re
import urllib
import ConfigParser
import optparse
import time
import sys
import subprocess

import icalendar

import client

CONF = None

def find_passcodes(text):
    def clean(code):
        return code.replace(' ', '').replace('-', '')

    def intcodes(codes):
        return [int(clean(x)) for x in codes]

    codes = re.findall('[Cc]ode: *([- 0-9]+)', text)
    if codes:
        return intcodes(codes)
    codes = re.findall('PC:? *([- 0-9]+)', text)
    if codes:
        return intcodes(codes)
    codes = re.search('[Pp]asscode:? *([- 0-9]+)', text)
    if codes:
        return intcodes(codes)

def choose_code(codes):
    if not codes:
        return

    codes = set(codes)
    try:
        mycodes = [int(x) for x in
                   CONF.get('prefs', 'my_codes').split(',')]
        mymods = [int(x) for x in
                  CONF.get('prefs', 'my_modcodes').split(',')]
    except:
        print 'Note: No "my_codes" setting'
        return codes[0]

    maybe_codes = codes - set(mycodes)
    if maybe_codes:
        return maybe_codes.pop()
    elif codes and mymods:
        # The codes found in the item were all my codes, so I must be
        # leading this call. Find my moderator code that matches the
        # particpant code that was in the item.
        return mymods[mycodes.index(codes.pop())]

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
        codes = find_passcodes(item.get('location') + item.get('summary'))
        code = choose_code(codes)
        if code:
            upcoming_calls[delta] = (item, code)
    return upcoming_calls

def gui_prompt_to_call_next(opts, delta, item, code):
    sound = CONF.get('prefs', 'alert_sound')
    player = CONF.get('prefs', 'alert_player')
    timeout = int(CONF.get('prefs', 'prompt_timeout'))
    host = CONF.get('prefs', 'asterisk_host')
    port = int(CONF.get('prefs', 'host_port'))
    number = CONF.get('prefs', 'conf_number')

    msg = '%s (Passcode %s). Call this?' % (item.get('summary'),
                                            code)
    os.system('%s %s >/dev/null 2>&1 &' % (player, sound))

    gui = subprocess.Popen(['zenity', '--question', '--text=\'%s\'' % msg])
    start = time.time()
    result = None
    while (time.time() - start) < timeout:
        if gui.poll() is not None:
            result = gui.returncode
            break
    if result is None:
        gui.terminate()
        raise Exception("User did not respond, abort!")

    if result != 0:
        return
    if opts.dryrun:
        print 'Would call %s %s %s %s' % (host, port, number, code)
    else:
        client.make_call(host, port, number, code)

def tui_prompt_to_call_next(opts, delta, item, code):
    host = CONF.get('prefs', 'asterisk_host')
    port = int(CONF.get('prefs', 'host_port'))
    number = CONF.get('prefs', 'conf_number')

    print item.get('summary')
    print '  Passcode %s' % code
    print 'Call this? [y/N] ',
    answer = sys.stdin.readline()
    if answer.strip() != 'y':
        return
    if opts.dryrun:
        print '\rWould call %s %s %s %s' % (host, port, number, code)
    else:
        client.make_call(host, port, number, code)

def fetch_latest():
    return urllib.urlopen(CONF.get('prefs', 'gcal_url')).read()

def parse_config(conf_file='gcal_notifier.cfg'):
    global CONF
    CONF = ConfigParser.ConfigParser()
    CONF.read(conf_file)

def parse_opts():
    optparser = optparse.OptionParser()
    optparser.add_option('-t', '--text',
                         default=False, action='store_true',
                         help='Text mode')
    optparser.add_option('-m', '--minutes',
                         default=None, type='int',
                         help='Override lookahead_minutes')
    optparser.add_option('-d', '--dryrun',
                         default=False, action='store_true',
                         help='Do not actually place a call')
    opts, args = optparser.parse_args()
    return opts

def main():
    opts = parse_opts()
    parse_config()
    caldata = fetch_latest()
    timerange = datetime.timedelta(minutes=opts.minutes or int(
            CONF.get('prefs', 'lookahead_minutes')))
    cal = icalendar.Calendar.from_ical(caldata)
    calls = get_upcoming(cal, timerange)

    for delta in sorted(calls.keys()):
        item, code = calls[delta]

        if opts.text:
            tui_prompt_to_call_next(opts, delta, item, code)
        else:
            gui_prompt_to_call_next(opts, delta, item, code)

if __name__ == '__main__':
    main()
