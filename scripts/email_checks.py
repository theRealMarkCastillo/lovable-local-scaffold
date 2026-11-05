"""Local Supabase Auth email capture and backend recovery checks; no cloud targets."""
import argparse
import json
import os
import secrets
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
import stack


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('config','test','smoke'))
    args=parser.parse_args()
    if args.action=='config':
        stack.render()
        stack.compose('up','-d','--wait','--wait-timeout','180','mail','auth')
        print('Applied local Supabase Auth/Mailpit configuration; existing users preserved')
        return
    env=stack.env_values(stack.ENV)
    base=env['PUBLIC_URL'].rstrip('/')
    origin=urllib.parse.urlparse(base)
    if origin.hostname not in ('localhost','127.0.0.1') and not (origin.hostname or '').endswith('.orb.local'):
        raise SystemExit('Email checks are restricted to localhost/OrbStack; public/cloud origins are not tested')
    api=base+'/supabase/auth/v1'
    mail='http://localhost:'+env['MAIL_PORT']
    tls=ssl.create_default_context(cafile=os.getenv('DEMO_CA_FILE'))
    if (origin.hostname or '').endswith('.orb.local') and not os.getenv('DEMO_CA_FILE'):
        cert=subprocess.run(['security','find-certificate','-a','-c','OrbStack','-p'],check=True,capture_output=True,text=True)
        tls.load_verify_locations(cadata=cert.stdout)
    opener=urllib.request.build_opener(urllib.request.HTTPSHandler(context=tls))
    def request(url,method='GET',body=None,token=None,expected=(200,)):
        headers={'apikey':env['ANON_KEY']}
        if token:headers['Authorization']='Bearer '+token
        if body is not None:headers['Content-Type']='application/json'
        req=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
        try:response=opener.open(req,timeout=30)
        except urllib.error.HTTPError as error:response=error
        assert response.status in expected,f'Email API returned {response.status}, expected {expected}'
        data=response.read()
        return json.loads(data) if data else None
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.links=[]
        def handle_starttag(self,tag,attrs):
            href=dict(attrs).get('href','')
            if tag=='a' and '/auth/v1/verify' in href:self.links.append(href)
    def captured_link(recipient,seen):
        for _ in range(50):
            for message in request(mail+'/api/v1/messages')['messages']:
                if message['ID'] not in seen and any(to.get('Address')==recipient for to in message['To']):
                    detail=request(mail+'/api/v1/message/'+message['ID'])
                    links=Links();links.feed(detail['HTML'])
                    assert links.links,'Captured email has no verification link'
                    link=links.links[0];target=urllib.parse.urlparse(link)
                    assert (target.scheme,target.netloc)==(origin.scheme,origin.netloc),'Email callback has wrong origin'
                    assert target.path=='/supabase/auth/v1/verify','Email callback has wrong path'
                    return link
            time.sleep(.2)
        raise AssertionError('Email not captured in local Mailpit')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    redirects=urllib.request.build_opener(urllib.request.HTTPSHandler(context=tls),NoRedirect())
    def verify(link):
        try:response=redirects.open(link,timeout=30)
        except urllib.error.HTTPError as error:response=error
        assert response.status in (302,303),'Expected Auth callback redirect'
        target=urllib.parse.urlparse(response.headers['Location'])
        assert (target.scheme,target.netloc)==(origin.scheme,origin.netloc),'Auth returned to wrong origin'
        values=urllib.parse.parse_qs(target.fragment)
        assert 'error' not in values,'Auth rejected email action'
        return values
    email='email-check-'+secrets.token_hex(6)+'@example.test'
    password=secrets.token_urlsafe(24)+'aA1!'
    seen={message['ID'] for message in request(mail+'/api/v1/messages')['messages']}
    request(api+'/signup','POST',{'email':email,'password':password},expected=(200,201))
    link=captured_link(email,seen)
    print('PASS: synthetic signup email captured in Mailpit with configured callback origin')
    if args.action=='test':
        print('Synthetic unconfirmed Auth user and captured message retained locally; no external delivery')
        return
    verify(link)
    session=request(api+'/token?grant_type=password','POST',{'email':email,'password':password})
    assert session['user']['email_confirmed_at'],'Synthetic user was not confirmed'
    print('PASS: verification link confirms account and password login succeeds')
    seen={message['ID'] for message in request(mail+'/api/v1/messages')['messages']}
    request(api+'/recover?redirect_to='+urllib.parse.quote(base+'/',safe=''),'POST',{'email':email})
    action=verify(captured_link(email,seen))
    assert action.get('type')==['recovery'] and action.get('access_token'),'Expected recovery session'
    new_password=secrets.token_urlsafe(24)+'aA1!'
    request(api+'/user','PUT',{'password':new_password},action['access_token'][0])
    session=request(api+'/token?grant_type=password','POST',{'email':email,'password':new_password})
    request(api+'/token?grant_type=password','POST',{'email':email,'password':password},expected=(400,401))
    request(api+'/logout','POST',token=session['access_token'],expected=(204,))
    print('PASS: recovery email, backend password change, new-password login and old-password rejection')
    print('Synthetic Auth user/messages retained locally. API recovery tested; no password-reset UI is implemented')


if __name__=='__main__':main()
