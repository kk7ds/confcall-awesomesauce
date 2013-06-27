#!/usr/bin/python

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import ConfigParser
try:
    import json
except ImportError:
    # Compatability for old python implementations
    import anyjson as json
import os
import sys


def get_config():
    cp = ConfigParser.ConfigParser()
    cp.read('server.cfg')
    return cp


class CallHandler(BaseHTTPRequestHandler):
    def _make_call(self, req):
        config = get_config()
        call_file_data = """# Automatically generated
Channel: SIP/%(phone_ext)s
Context: %(context)s
Extension: %(exten)s
Priority: 1
Set: passcode=%(passcode)s#
Set: number=%(number)s
Set: peer=%(peer)s
"""

        params = dict(peer=config.get('main', 'peer'),
                      context=config.get('main', 'context'),
                      exten=config.get('main', 'extension'),
                      phone_ext=config.get('main', 'phone_ext'),
                      passcode=req['passcode'],
                      number=req['number'])

        call_file = file('/tmp/foo.call', 'w')
        call_file.write(call_file_data % params)
        call_file.close()
        os.rename('/tmp/foo.call', '/var/spool/asterisk/outgoing/foo.call')

    def do_POST(self):
        if self.path == '/calls':
            try:
                length = int(self.headers['Content-Length'])
                req = json.loads(self.rfile.read(length))
                self._make_call(req)
                resp = 200
                msg = 'OK'
            except Exception, e:
                resp = 500
                msg = 'Failed: %s' % e
                print e
        else:
            resp = 404
            msg = 'Not Found'

        self.send_response(resp)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', len(msg))
        self.end_headers()
        self.wfile.write(msg)


def do_serve(bindaddr=None):
    if not bindaddr:
        bindaddr = '127.0.0.1'
    try:
        server = HTTPServer((bindaddr, 8081), CallHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()


if __name__ == '__main__':
    try:
        bindaddr = sys.argv[1]
    except:
        bindaddr = None
    do_serve(bindaddr)
