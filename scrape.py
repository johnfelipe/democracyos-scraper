#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import re
from urlparse import urlparse
from xml.etree.ElementTree import Element, SubElement, tostring, parse
import sys, os, lxml.html, lxml.etree, urllib2
from subprocess import call
import unicodedata, string
from time import strptime, strftime
import xml.dom.minidom

import unicodedata
from cStringIO import StringIO
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage


PERSONS = {}
PERSON_TITLES = [
    ['H. S. Eugenio Prieto Soto', 'Presidente', 'El Presidente'],
    ['Dra. Sandra Ovalle García', 'Secretaria', 'La Secretaria'],
    ['Dr. Diego Molano Vega', 'Ministro de TIC', 'Ministro de Tecnologías de la Información y las Comunicaciones'],
    ['Dr. Carlos Pablo Márquez', 'CRC', 'Director Ejecutivo Comisión De Regulación De Comunicaciones (CRC)']
]
_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')


def _slugify(value):
    if not isinstance(value, unicode):
        value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(_slugify_strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)


def text_to_xml(fname):
    print 'Convirtiendo TXT a XML '+fname

    f = open(fname)
    fcontent = f.read()
    fcontent = re.sub(r' \n(\w*)(.*)([0-9]*)/([0-9]*) ([–-]) (\w*) ([0-9]*)/([0-9]*) \n(\w*) (\w*) ([0-9]*)-([0-9]*) \n(.*) \n \n \n\n\f([0-9]*)', '', fcontent)
    fcontent = re.sub(r'\n(\w*)(.*)([0-9]*)/([0-9]*) ([–-]) (\w*) ([0-9]*)/([0-9]*) \n(\w*) (\w*) ([0-9]*)-([0-9]*) \n(.*) \n \n\n(.*) \n\n\f', '', fcontent)
    fcontent = re.sub(r'\n(\w*)(.*)([0-9]*)/([0-9]*) ([–-]) (\w*) ([0-9]*)/([0-9]*) \n(\w*) (\w*) ([0-9]*)-([0-9]*) \n\n(.*) \n\n\f', '', fcontent)
    fcontent = re.sub(r'\n(\w*)(.*)([0-9]*)/([0-9]*) ([–-]) (\w*) ([0-9]*)/([0-9]*) \n(\w*) (\w*) ([0-9]*)-([0-9]*)', '', fcontent)

    f = open('xml/'+os.path.splitext(os.path.basename(fname))[0]+'.txt', 'w')
    f.write(fcontent)
    f.close()

    fcontent = re.sub(r'\f', '', fcontent)
    fcontent = re.sub(r'  ', ' ', fcontent)
    fcontent = re.sub(r'  ', ' ', fcontent)
    fcontent = re.sub(r'   ', ' ', fcontent)
    fcontent = re.sub(r'    ', ' ', fcontent)
    fcontent = re.sub(r'\n\n \n\n \n', '', fcontent)
    fcontent = re.sub(r'\n\n \n\n([0-9]*)', '', fcontent)
    fcontent = re.sub(r'([\*]*)', '', fcontent)
    fcontent = re.sub(r'III', '', fcontent)
    fcontent_match = re.match(r'^(.*)LO QUE PROPONGAN LOS HONORABLES SENADORES\.(.*)', fcontent, re.DOTALL)

    if fcontent_match:
        fcontent = fcontent_match.group(2)

    fcontent = re.sub(r' – ', '-', fcontent)
    fcontent = re.sub(r'– ', '-', fcontent)
    fcontent = re.sub(r' –', '-', fcontent)
    fcontent = re.sub(r' - ', '-', fcontent)
    fcontent = re.sub(r'-\n', '-', fcontent)
    fcontent = re.sub(r' \n', ' ', fcontent)
    fcontent = re.sub(r' \n', ' ', fcontent)
    fcontent = re.sub(r'H\.S\. ', r'H. S. ', fcontent)
    fcontent = re.sub(r'H\. S ', r'H. S. ', fcontent)

    for i in PERSON_TITLES:
        fcontent = re.sub(i[0]+', '+i[1]+':', '\n'+i[0]+':', fcontent)
        fcontent = re.sub(i[2]+'-'+i[0]+':', '\n'+i[0]+':', fcontent)
        fcontent = re.sub(i[1]+'-'+i[0]+':', '\n'+i[0]+':', fcontent)
        fcontent = re.sub(i[1]+':', '\n'+i[0]+':', fcontent)

    fcontent = re.sub(r'[^\n]H\. S\.', r'\nH. S.', fcontent)
    flist = fcontent.decode('utf-8').split('\n')

    akoman = Element('akomaNtoso')
    debate = SubElement(akoman, 'debate')
    dabate_date = SubElement(debate, 'docDate')
    debate_body = SubElement(debate, 'debateBody')
    debate_section = SubElement(debate_body, 'debateSection')
    meta = SubElement(debate, 'meta')
    references = SubElement(meta, 'references')

    for j in flist:
        se_person = j.split(':')[0]
        se_person_slug = _slugify(se_person)

        if se_person_slug:
            PERSONS[se_person_slug] = {
                'href': '/ontology/person/senado.felipeurrego.com/'+se_person_slug,
                'id': se_person_slug,
                'showAs': se_person,
            }

            se = SubElement(debate_section, 'speech', by='#'+se_person_slug)
            se.text = j[len(se_person+':'):]

    for key, value in PERSONS.iteritems():
        se_person_tag = SubElement(references, 'TLCPerson', **value)

    xml_content = xml.dom.minidom.parseString(tostring(akoman))

    f = open('xml/'+os.path.splitext(os.path.basename(fname))[0]+'.xml', 'w')
    f.write(xml_content.toprettyxml().encode('utf-8'))
    f.close()


def get_items(url, selector):
    req = urllib2.Request(url)
    response = urllib2.urlopen(req)
    body = response.read()
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


def is_pdf_attachment(url):
    if is_valid_url(url):
        parse_object = urlparse(url)
        url_basename = os.path.basename(parse_object.path)
        url_ext = os.path.splitext(url_basename)[1]
        url_loc = parse_object.netloc

        if 'files' in url_loc and url_ext == '.pdf' and 'acta' in url_basename:
            return True
    return False


def download_file(url):
    print 'Descargando '+url

    parse_object = urlparse(url)
    response = urllib2.urlopen(url)

    file = open('pdf/'+os.path.basename(parse_object.path), 'w')
    file.write(response.read())
    file.close()


def pdf_to_text(fname):
    print 'Convirtiendo '+fname

    pagenums = set()

    output = StringIO()
    manager = PDFResourceManager()
    converter = TextConverter(manager, output, laparams=LAParams())
    interpreter = PDFPageInterpreter(manager, converter)

    infile = open(fname, 'rb')

    for page in PDFPage.get_pages(infile, pagenums):
        interpreter.process_page(page)

    infile.close()
    converter.close()
    text = output.getvalue()
    output.close

    file = open('text/'+os.path.splitext(os.path.basename(fname))[0]+'.txt', 'w')
    file.write(text)
    file.close()


def scrape(url):

    for session in get_items(url, '.entry-title'):
        link = session.cssselect('a')

        for item in get_items(link[0].get('href'), 'a'):

            if is_pdf_attachment(unicode(item.get('href'))):
                # download_file(unicode(item.get('href')))
                pdf_to_text('pdf/'+unicode(os.path.basename(item.get('href'))))
                text_to_xml('text/'+os.path.splitext(unicode(os.path.basename(item.get('href'))))[0]+'.txt')


url = 'https://comision6senado.wordpress.com/category/actas/'
scrape(url)
