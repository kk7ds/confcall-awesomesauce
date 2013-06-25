#!/usr/bin/python

import sys
import json
import urllib

def make_call(host, port, number, passcode):
    req = json.dumps(dict(number=number,
                          passcode=passcode))
    url = 'http://%s:%i/calls' % (host, port)
    response = urllib.urlopen(url, req)
    print response.read().strip()
    return response.getcode() == 200

if __name__ == '__main__':
    result = make_call(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]),
                       int(sys.argv[4]))
    sys.exit(not (result == 200))
