#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import os
import web
import uuid

from mako.lookup import TemplateLookup
from mako import exceptions

__author__ = 'Michael Liao'

class emptyobject(object):
    def __getattr__(self, attr):
        return ''

    def __setattr__(self, attr, value):
        pass

class odict(dict):
    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value

class WebError(StandardError):
    def __init__(self, message):
        super(WebError, self).__init__(message)

def next_id():
    return uuid.uuid4().hex

def _create_db():
    host = 'localhost'
    db = 'weather'
    port = 3306
    user = 'weather'
    pw = 'weather'
    try:
        import sae.const
        db = sae.const.MYSQL_DB
        user = sae.const.MYSQL_USER
        pw = sae.const.MYSQL_PASS
        host = sae.const.MYSQL_HOST
        port = int(sae.const.MYSQL_PORT)
    except ImportError:
        pass
    return web.database(dbn='mysql', host=host, port=port, db=db, user=user, pw=pw)

db = _create_db()

def _create_memcache_client():
    try:
        import pylibmc
        return pylibmc.Client()
    except ImportError:
        import memcache
        return memcache.Client(['127.0.0.1:11211'])

cache = _create_memcache_client()

TEMPLATE_PATH = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'templates')
logging.info('Init template path: %s' % TEMPLATE_PATH)

TEMPLATES_LOOKUP = TemplateLookup(directories=[TEMPLATE_PATH], input_encoding='utf-8', output_encoding='utf-8')

def handler(method='GET', use_template=True):
    '''
    using decorator:
      @handler('GET')
      def login():
          return 'success'
    
    is equal to:
      def login():
          return 'success'
      login = handler('GET')(login)
    '''
    def _wrapper(func):
        def _new_func(**kw):
            if method=='GET' and web.ctx.method!='GET':
                raise web.badrequest()
            if method=='POST' and web.ctx.method!='POST':
                raise web.badrequest()
            r = func(**kw)
            logging.info('Url handler returns: %s' % type(r))
            if r is None or method=='POST':
                return r
            if func.use_template and isinstance(r, dict):
                try:
                    template = TEMPLATES_LOOKUP.get_template('%s.html' % func.__name__)
                    logging.info('Model: %s' % str(r))
                    return template.render(**r)
                except:
                    return exceptions.html_error_template().render()
            if isinstance(r, str):
                return r
            if isinstance(r, unicode):
                return r.encode('utf-8')
            return str(r)
        _new_func.__name__ = func.__name__
        _new_func.handler = True
        func.use_template = use_template
        return _new_func
    return _wrapper
