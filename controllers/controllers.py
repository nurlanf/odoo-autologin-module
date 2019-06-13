import babel.messages.pofile
import base64
import datetime
import functools
import glob
import hashlib
import imghdr
import io
import itertools
import jinja2
import json
import logging
import operator
import os
import re
import sys
import tempfile
import time
import zlib

import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi
from collections import OrderedDict
from werkzeug.urls import url_decode, iri_to_uri
from xml.etree import ElementTree
import unicodedata

import odoo
import odoo.modules.registry
from odoo.api import call_kw, Environment
from odoo.modules import get_resource_path
from odoo.tools import crop_image, topological_sort, html_escape, pycompat
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.translate import _
from odoo.tools.misc import str2bool, xlwt, file_open
from odoo.tools.safe_eval import safe_eval
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, \
    serialize_exception as _serialize_exception, Response
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.models import check_method_name
from odoo.service import db, security

import odoo.addons.web.controllers.main as main

class MyHome(http.Controller):

    @http.route('/web/login', type='http', auth="none", sitemap=False)
    def web_login(self, redirect=None, **kw):
        main.ensure_db()
        request.params['login_success'] = False
        try:
            request.params['login'] = 'admin'
            request.params['password'] = 'admin'
            uid = request.session.authenticate(request.session.db, request.params['login'],
                                               request.params['password'])
            request.params['login_success'] = True
            return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
        except odoo.exceptions.AccessDenied as e:
            request.uid = old_uid
            if e.args == odoo.exceptions.AccessDenied().args:
                values['error'] = _("Wrong login/password")
            else:
                values['error'] = e.args[0]

        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            try:
                request.params['login'] = 'admin'
                request.params['password'] = 'admin'
                uid = request.session.authenticate(request.session.db, request.params['login'],
                                                   request.params['password'])
                request.params['login_success'] = True
                return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                request.uid = old_uid
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employee can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        # otherwise no real way to test debug mode in template as ?debug =>
        # values['debug'] = '' but that's also the fallback value when
        # missing variables in qweb
        if 'debug' in values:
            values['debug'] = True

        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response
