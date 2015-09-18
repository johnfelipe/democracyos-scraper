#!/usr/bin/python2.7
# -*- coding: utf-8 -*-


import os
import re
import json
import urllib2
import lxml.html
import lxml.etree
from datetime import datetime
import unicodedata
from subprocess import call

from urlparse import urlparse, urlunparse, parse_qs
from urllib import urlencode
from StringIO import StringIO

_months = {'Enero': 'January',
           'Febrero': 'February',
           'Marzo': 'March',
           'Abril': 'April',
           'Mayo': 'May',
           'Junio': 'June',
           'Julio': 'July',
           'Agosto': 'August',
           'Septiembre': 'September',
           'Octubre': 'October',
           'Noviembre': 'November',
           'Diciembre': 'December'}

_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')

_correct_text_re = [
    [r'º', r'°'],
    [r'\s+', r' '],
    [r'\s°', r'°'],
    [r'\s\.\s', r'.'],
    [r'\.\. ', r'.'],
    [r'Artículo', r'\nArtículo'],
    [r'Artículo\s(\d+)', r'Artículo \1'],
    [r'Artículo\s(\d+)[^°]', r'Artículo \1°'],
    [r'Artículo\s(\d+)°\.\.', r'Artículo \1°.'],
    [r'Artículo\s(\d+)°([^\.])', r'Artículo \1°.\2'],
    [r'Artículo\s(\d+)°\.\s*', r'Artículo \1°.'],
]

_correct_title_re = [
    [r'\s+', r' '],
]

_correct_summary_re = [
    [r'\s+', r' '],
]

def _slugify(value):
    if not isinstance(value, unicode):
        value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(_slugify_strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)


def text_to_json(url, tag, lawID, publishedAt, state, status, pagename):
    print 'Convirtiendo TXT a JSON '+url

    f = open(pagename)
    fcontent = f.read()
    f.close()

    tree = lxml.etree.parse(StringIO(fcontent), lxml.etree.HTMLParser())

    if tree.xpath('body/div[@class="Section1"]'):

        clauses = []
        mediaTitle = unicode(tree.xpath('body/center/p/font/strong/text()')[0]).encode('utf-8')
        summary = unicode(tree.xpath('body/center/text()')[1]).encode('utf-8')
        text = tree.xpath('body/div[@class="Section1"]/p[@class="MsoNormal"]/span/text()')
        text = unicode(' '.join(text)).encode('utf-8')
        tag = unicode(tag).encode('utf-8')
        lawID = unicode(lawID).encode('utf-8')
        publishedAt = unicode(publishedAt).encode('utf-8')
        state = unicode(state).encode('utf-8')
        status = unicode(status).encode('utf-8')

        for r, f in _correct_text_re:
            text = re.sub(r, f, text).strip()

        for r, f in _correct_title_re:
            mediaTitle = re.sub(r, f, mediaTitle).strip(' .')

        for r, f in _correct_summary_re:
            summary = re.sub(r, f, summary).strip()

        articles = re.findall(r'Artículo\s(\d+)°\.(.*)', text)

        for n, a in articles:
            clauses.append({'clauseName': int(n),
                            'order': int(n)-1,
                            'text': a})

        json_data = [{
            'state': state,
            'status': status,
            'lawID': lawID,
            'tag': tag,
            'mediaTitle': mediaTitle,
            'publishedAt': publishedAt,
            'source': url,
            'summary': summary,
            'clauses': clauses
        }]

        f = open('json/'+os.path.splitext(os.path.basename(pagename))[0]+'.json', 'w')
        f.write(json.dumps(json_data, ensure_ascii=False, indent=4))
        f.close()


def get_selectors(html, selector):
    file = open(html)
    body = file.read()
    file.close()
    doc = lxml.html.document_fromstring(body)
    sessions = doc.cssselect(selector)
    return sessions


def is_valid_url(url):
    regex = re.compile(
        r'^(http|ftp|file|https):///?'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|[a-zA-Z0-9-]*|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$',
        re.IGNORECASE
    )
    return regex.search(url)


def get_pagename(url, ext):
    u = urlparse(url)
    return ext+'/'+_slugify(os.path.basename(u.path)+u.query)+'.'+ext


def download_file(url, dest):
    print 'Descargando '+url
    response = urllib2.urlopen(url)
    file = open(dest, 'w')
    file.write(response.read())
    file.close()


def update_url_params(url, params):
    url_parts = list(urlparse(url))
    query = dict(parse_qs(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return urlunparse(url_parts)


def scrape():

    print 'Obteniendo páginas válidas ...'

    urlbase = 'http://www.camara.gov.co/portal2011/proceso-y-tramite-legislativo/proyectos-de-ley'
    urlparams = {'view': 'proyectosdeley',
                 'option': 'com_proyectosdeley',
                 'limit': 0}
    page = update_url_params(urlbase, urlparams)
    pagename = get_pagename(page, 'html')

    laws = []
    projects = []

    if not os.path.exists(pagename):
        download_file(page, pagename)

    for session in get_selectors(pagename, 'a'):

        project = session.get('href')

        if project.startswith('/'):
            project = 'http://www.camara.gov.co'+project

        link_query_dict = parse_qs(urlparse(project).query)

        if 'view' in link_query_dict and 'idpry' in link_query_dict:
            if link_query_dict['view'][0] == 'ver_proyectodeley':
                projects.append(project)

    for project in projects:

        state = 'project'
        status = 'open'
        lawID = ''
        publishedAt = ''
        tag = ''

        pagename = get_pagename(project, 'html')

        if not os.path.exists(pagename) and is_valid_url(project):
            download_file(project, pagename)

        for session in get_selectors(pagename, '.ar_12black b'):
            if _slugify(session.text) == 'ley':
                status = 'bill'

            if _slugify(session.text) == 'retirado':
                state = 'closed'

        for i, session in enumerate(get_selectors(pagename, '.ar_12black')):
            if session.text:
                if i == 0:
                    lawID = session.text
                if i == 5:
                    date = session.text.split()
                    if date:
                        date[0] = _months[date[0]]
                        date.pop(2)
                        publishedAt = datetime.strptime(' '.join(date), '%B %d %Y').strftime('%Y-%m-%d')
                if i == 7:
                    tag = session.text

        for session in get_selectors(pagename, 'a'):
            law = session.get('href')

            link_query_dict = parse_qs(urlparse(law).query)

            if 'p_tipo' in link_query_dict and is_valid_url(law):
                if int(link_query_dict['p_tipo'][0]) == 5:
                    if (urlparse(law).netloc == 'www.imprenta.gov.co'
                       and urlparse(law).path == '/gacetap/gaceta.mostrar_documento'):
                        laws.append({'url': law,
                                     'tag': tag,
                                     'lawID': lawID,
                                     'publishedAt': publishedAt,
                                     'state': state,
                                     'status': status,
                                     'pagename': get_pagename(law, 'text')})

                    if (urlparse(law).netloc == 'servoaspr.imprenta.gov.co:7778'
                       and urlparse(law).path == '/gacetap/gaceta.mostrar_documento'):
                        url_parts = list(urlparse(law))
                        url_parts[1] = url_parts[1].split(':')[0]
                        laws.append({'url': urlunparse(url_parts),
                                     'tag': tag,
                                     'lawID': lawID,
                                     'publishedAt': publishedAt,
                                     'state': state,
                                     'status': status,
                                     'pagename': get_pagename(law, 'text')})

    for law in laws:

        if not os.path.exists(law['pagename']):
            download_file(law, law['pagename'])

        json = text_to_json(**law)



if __name__ == "__main__":

    base_dir = '/home/felipe/app'
    scrape()

    jsondir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'json')

    for f in os.listdir(jsondir):
        if f.endswith('.json'):
            jsonpath = os.path.join(jsondir, f)
            call('NODE_PATH=. ./bin/dos-db load law '+jsonpath, shell=True)
