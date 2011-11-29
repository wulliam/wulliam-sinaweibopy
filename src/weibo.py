#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Liao Xuefeng (askxuefeng@gmail.com)'

'''
Python client SDK for sina weibo API v2.
'''

try:
    import json
except ImportError:
    import simplejson as json
import time
import urllib
import urllib2
import logging

def _obj_hook(pairs):
    '''
    convert json object to python object.
    '''
    o = JsonObject()
    for k, v in pairs.iteritems():
        o[str(k)] = v
    return o

class APIError(StandardError):
    '''
    raise APIError if got failed json message.
    '''
    def __init__(self, error_code, error, request):
        self.error_code = error_code
        self.error = error
        self.request = request
        StandardError.__init__(self, error)

    def __str__(self):
        return 'APIError: %s: %s, request: %s' % (self.error_code, self.error, self.request)

class JsonObject(dict):
    '''
    general json object that can bind any fields.
    '''
    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value

def _encode_params(**kw):
    args = []
    for k, v in kw.iteritems():
        qv = v.encode('utf-8') if isinstance(v, unicode) else v
        args.append('%s=%s' % (k, urllib.quote(qv)))
    return '&'.join(args)

def _http_get(url, authorization=None, **kw):
    return _http_call(url, True, authorization, **kw)

def _http_post(url, authorization=None, **kw):
    return _http_call(url, False, authorization, **kw)

def _http_call(url, is_get, authorization, **kw):
    '''
    send an http request and expect to return a json object if no error.
    '''
    params = _encode_params(**kw)
    http_url = '%s?%s' % (url, params) if is_get else url
    http_body = None if is_get else params
    req = urllib2.Request(http_url, data=http_body)
    if authorization:
        req.add_header('Authorization', 'OAuth2 %s' % authorization)
    resp = urllib2.urlopen(req)
    body = resp.read()
    r = json.loads(body, object_hook=_obj_hook)
    if hasattr(r, 'error_code'):
        raise APIError(r.error_code, getattr(r, 'error', ''), getattr(r, 'request', ''))
    return r

class HttpObject(object):

    def __init__(self, client, is_get):
        self.client = client
        self.is_get = is_get

    def __getattr__(self, attr):
        def wrap(**kw):
            if self.client.is_expires():
                raise APIError('21327', 'expired_token', attr)
            return _http_call('%s%s.json' % (self.client.api_url, attr.replace('__', '/')), self.is_get, self.client.access_token, **kw)
        return wrap

class APIClient(object):
    '''
    API client using synchronized invocation.
    '''
    def __init__(self, app_key, app_secret, redirect_uri, response_type='code', domain='api.weibo.com', version='2'):
        self.client_id = app_key
        self.client_secret = app_secret
        self.redirect_uri = redirect_uri
        self.response_type = response_type
        self.auth_url = 'https://%s/oauth2/' % domain
        self.api_url = 'https://%s/%s/' % (domain, version)
        self.access_token = None
        self.expires = 0.0
        self.get = HttpObject(self, True)
        self.post = HttpObject(self, False)

    def set_access_token(self, access_token, expires_in):
        self.access_token = str(access_token)
        self.expires = time.time() + expires_in

    def get_authorize_url(self, display='default'):
        '''
        return the authroize url that should be redirect.
        '''
        return '%s%s?%s' % (self.auth_url, 'authorize', \
                _encode_params(client_id = self.client_id, \
                        response_type = 'code', \
                        display = display, \
                        redirect_uri = self.redirect_uri))

    def request_access_token(self, code):
        r = _http_post('%s%s' % (self.auth_url, 'access_token'), \
                client_id = self.client_id, \
                client_secret = self.client_secret, \
                redirect_uri = self.redirect_uri, \
                code = code, grant_type = 'authorization_code')
        print r, type(r)
        self.set_access_token(r.access_token, r.expires_in)

    def is_expires(self):
        return not self.access_token or time.time() > self.expires
