#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import sys, os, re, lxml.html, lxml.etree, urllib2
import xml.dom.minidom
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from urlparse import urlparse
import unicodedata, string
from datetime import datetime
from subprocess import call

from cStringIO import StringIO
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage

PERSONS = {}
DOMAIN = 'senado.felipeurrego.com'
PERSON_TITLES = [
    ['H. S. Eugenio Prieto Soto', 'Presidente', 'El Presidente'],
    ['H. S. Jorge Eliécer Guevara', 'Presidente', 'El Presidente'],
    ['H. S. Luís Fernando Duque García', 'Presidente', 'El Presidente'],
    ['Dra. Sandra Ovalle García', 'Secretaria', 'La Secretaria'],
    ['Dr. Diego Molano Vega', 'Ministro de TIC', 'Ministro de Tecnologías de la Información y las Comunicaciones'],
    ['Dr. Carlos Pablo Márquez', 'CRC', 'Director Ejecutivo Comisión De Regulación De Comunicaciones \(CRC\)']
]
MONTHS = {
    'enero': '01',
    'febrero': '02',
    'marzo': '03',
    'abril': '04',
    'mayo': '05',
    'junio': '06',
    'julio': '07',
    'agosto': '08',
    'septiembre': '09',
    'octubre': '10',
    'noviembre': '11',
    'diciembre': '12',
}

_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')


class CustomHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)

    http_error_301 = http_error_303 = http_error_307 = http_error_302


class HeadRequest(urllib2.Request):
    def get_method(self):
        return "HEAD"


def get_status_code(url):

    try:
        cookieprocessor = urllib2.HTTPCookieProcessor()
        opener = urllib2.build_opener(CustomHTTPRedirectHandler, cookieprocessor)
        urllib2.install_opener(opener)
        response = urllib2.urlopen(url)
        return response.getcode()
    except Exception:
        return 404

    
def _slugify(value):
    if not isinstance(value, unicode):
        value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(_slugify_strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)

    
def clean_text(text):
    text = re.sub(r'\n(\w*)(.*)([0-9]*)/([0-9]*)(.*)(\w*)(.*)([0-9]*)/([0-9]*)(.*)\n(\w*)(.*)([0-9]*)-([0-9]*)(.*)\n(.*)(\w*)(.*)', '', text)
    text = re.sub(r'\n(\w*)(.*)([0-9]*)-([0-9]*)/(\w*)(.*)([0-9]*)-([0-9]*)(.*)\n(.*)\n(.*)(\w*)(.*)([0-9]*)-([0-9]*)', '', text)
    text = re.sub(r'\n(\w*)(.*)([0-9]*)/([0-9]*)(.*)(\w*)([0-9]*)/([0-9]*)(.*)(\w*)(.*)\n(.*)(\w*)(.*)', '', text)
    text = re.sub(r'\n(\w*)(.*)([0-9]*)-([0-9]*)/(\w*)(.*)([0-9]*)-([0-9]*)(.*)\n(.*)(\w*)(.*)\n(.*)(\w*)([0-9]*)-([0-9]*)', '', text)
    text = re.sub(r'\n(\w*)(.*)([0-9]*)-([0-9]*)/(\w*)(.*)([0-9]*)-([0-9]*)(.*)\n(.*)(\w*)(.*)', '', text)
    text = re.sub(r'Para la Sesión del (\S*)(\s*)([0-9]*)(\s*)de(\s*)(\S*)(\s*)de(\s*)([0-9]*)', '', text)
    text = re.sub(r'Página ([0-9]*)', '', text)
    text = re.sub(r'\f', '', text)
    text = re.sub(r': :', ':', text)
    text = re.sub(r'  ', ' ', text)
    text = re.sub(r'  ', ' ', text)
    text = re.sub(r'   ', ' ', text)
    text = re.sub(r'    ', ' ', text)
    text = re.sub(r'I \n', '', text)
    text = re.sub(r'II \n', '', text)
    text = re.sub(r'III \n', '', text)
    text = re.sub(r'IV \n', '', text)
    text = re.sub(r'V \n', '', text)
    text = re.sub(r'I\n', '', text)
    text = re.sub(r'II\n', '', text)
    text = re.sub(r'III\n', '', text)
    text = re.sub(r'IV\n', '', text)
    text = re.sub(r'V\n', '', text)
    text = re.sub(r'Llamada a lista.', '', text)
    text = re.sub(r'\n\n \n\n \n', '', text)
    text = re.sub(r'\n\n \n\n([0-9]*)', '', text)
    text = re.sub(r' \n \n \n\n([0-9]*)', '', text)
    text = re.sub(r'\n \n ([0-9]*)', '', text)
    text = re.sub(r'([\*]*)', '', text)
    text = re.sub(r' – ', '-', text)
    text = re.sub(r'– ', '-', text)
    text = re.sub(r' –', '-', text)
    text = re.sub(r' - ', '-', text)
    text = re.sub(r'- ', '-', text)
    text = re.sub(r' -', '-', text)
    text = re.sub(r'-\n', '-', text)
    text = re.sub(r'  \n', ' ', text)
    text = re.sub(r' \n', ' ', text)
    text = re.sub(r' \n', ' ', text)
    text = re.sub(r'H\.S\. ', r'H. S. ', text)
    text = re.sub(r'H\. S ', r'H. S. ', text)
    text = re.sub(r'^\s*\n*', '', text)
    # text = re.sub(r'  ', r'<br />', text)
    return text


def clean_speakers(text):

    for i in PERSON_TITLES:
        text = re.sub(i[0]+'[^:]', i[0]+': ', text)
        text = re.sub(i[0]+', '+i[1]+':', '\n'+i[0]+':', text)
        text = re.sub(i[2]+'-'+i[0]+':', '\n'+i[0]+':', text)
        text = re.sub(i[1]+'-'+i[0]+':', '\n'+i[0]+':', text)
        text = re.sub(i[1]+':', '\n'+i[0]+':', text)

    text = re.sub(r'[^\n]H\. S\.', r'\nH. S.', text)
    text = re.sub(r'^\s*\n*', '', text)

    return text


def clean_questions(text):

    text = re.sub(r'[ \.:\?] ([0-9]*)\.', r'\n\1.', text)
    text = re.sub(r'  ', r'\n', text)
    text = re.sub(r'\n\. ', r'. ', text)
    text = re.sub(r'Presentada a consideración(.*)', r'', text, re.DOTALL|re.IGNORECASE)
    text = re.sub(r'Presentado por(.*)', r'', text, re.DOTALL|re.IGNORECASE)
    text = re.sub(r'ANUNCIO para Discusión y Votación(.*)', r'', text, re.DOTALL|re.IGNORECASE)
    return text


def is_valid_person(person):
    for i in ['Dr.', 'Dra.', 'H. S.']:
        if person.startswith(i):
            return True
    return False


def text_to_xml(fname, url):
    print 'Convirtiendo TXT a XML '+fname

    f = open(fname)
    fcontent = f.read()

    match = re.match(r'^(.*)Para la Sesión del (\S*)(\s*)([0-9]*)(\s*)de(\s*)(\S*)(\s*)de(\s*)([0-9]*)', fcontent, re.DOTALL|re.IGNORECASE)
    date_day = match.group(4)
    date_month = MONTHS[match.group(7).lower()]
    date_year = match.group(10)
    dateobject = datetime.strptime(date_day+'-'+date_month+'-'+date_year, '%d-%m-%Y')

    match = re.match(r'^(.*)ACTA No\. ([0-9]*)(.*)', fcontent, re.DOTALL)
    acta = match.group(2)
    intro = match.group(3)

    match = re.match(r'^(.*)CUESTIONARIO(.*)', intro, re.DOTALL)

    if match:
        narrative = match.group(1)
        questions = match.group(2)
        
        match = re.match(r'^(.*)ORDEN DEL \w(.*)', narrative, re.DOTALL)
        q_narrative = clean_text(match.group(1))
        s_narrative = clean_text(match.group(2))

        match = re.match(r'^(.*)LO QUE PROPONGAN LOS HONORABLES SENADORES.(.*)', questions, re.DOTALL)
        questions = match.group(1)
        speech = match.group(2)

    else:

        match = re.match(r'^(.*)LO QUE PROPONGAN LOS HONORABLES SENADORES.(.*)', intro, re.DOTALL)
        narrative = match.group(1)
        speech = match.group(2)

        match = re.match(r'^(.*)ORDEN DEL \w(.*)', narrative, re.DOTALL)
        q_narrative = clean_text(match.group(1))
        s_narrative = clean_text(match.group(2))
        questions = ''

    speech = clean_text(speech)
    speech = clean_speakers(speech)

    questions = clean_text(questions)
    questions = clean_questions(questions)

    # f = open('xml/'+os.path.splitext(os.path.basename(fname))[0]+'.txt', 'w')
    # f.write(s_narrative+'\n---\n'+q_narrative+'\n---\n'+questions)
    # f.close()

    flist = speech.decode('utf-8').split('\n')
    qlist = questions.decode('utf-8').split('\n')

    akoman = Element('akomaNtoso')
    debate = SubElement(akoman, 'debate')

    # META
    meta = SubElement(debate, 'meta')
    references = SubElement(meta, 'references')

    # PREFACE
    preface = SubElement(debate, 'preface')
    doctitle = SubElement(preface, 'docTitle')
    doctitle.text = unicode('ACTA No. '+acta)
    # docdate = SubElement(preface, 'docDate', date=unicode(dateobject.strftime('%d-%m-%Y')))
    link = SubElement(preface, 'link', href=url)

    # DEBATE BODY
    debate_body = SubElement(debate, 'debateBody')
    debate_section_1 = SubElement(debate_body, 'debateSection')
    heading_1 = SubElement(debate_section_1, 'heading')
    heading_1.text = unicode(dateobject.strftime('%Y'))
    debate_section_2 = SubElement(debate_section_1, 'debateSection')
    heading_2 = SubElement(debate_section_2, 'heading')
    heading_2.text = unicode(dateobject.strftime('%m'))
    debate_section_3 = SubElement(debate_section_2, 'debateSection')
    heading_3 = SubElement(debate_section_3, 'heading')
    heading_3.text = unicode(dateobject.strftime('%d-%m-%Y'))
    debate_section_4 = SubElement(debate_section_3, 'debateSection')
    heading_4 = SubElement(debate_section_4, 'heading')
    heading_4.text = unicode('ACTA No. '+acta)

    nq = SubElement(debate_section_4, 'narrative')
    nq.text = unicode(q_narrative.decode('utf-8'))

    if qlist:
        qss = SubElement(debate_section_4, 'questions')
        qssds = SubElement(qss, 'debateSection')
        qssh = SubElement(qssds, 'heading')
        qssh.text = 'CUESTIONARIO'

        for q in qlist:
            if q:
                if q[0].isdigit():
                    qs = SubElement(qssds, 'question')
                    qs.text = unicode(q)
                else:
                    qs = SubElement(qssds, 'narrative')
                    qs.text = unicode(q)

    na = SubElement(debate_section_4, 'narrative')
    na.text = unicode(s_narrative.decode('utf-8'))

    for j in flist:
        se_person = j.split(':')[0]
        se_person_slug = _slugify(se_person)

        if is_valid_person(se_person) and se_person_slug:
            PERSONS[se_person_slug] = {
                'href': '/ontology/person/'+DOMAIN+'/'+se_person_slug,
                'id': se_person_slug,
                'showAs': se_person
            }

            se = SubElement(debate_section_4, 'speech', by='#'+se_person_slug,
                            startTime=unicode(dateobject.strftime('%Y-%m-%dT%H:%M:%S')))
            sef = SubElement(se, 'from')
            sef.text = unicode(se_person)
            sep = SubElement(se, 'p')
            sep.text = unicode(j[len(se_person+':'):])

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

    pages = 1
    validpages = []

    print 'Obteniendo páginas válidas ...'

    while True:
        if get_status_code(url+'page/'+str(pages)) != 404:
            print url+'page/'+str(pages)
            validpages.append(url+'page/'+str(pages))
            pages += 1
        else:
            break

    for page in validpages:
        for session in get_items(page, '.entry-title'):
            link = session.cssselect('a')
            for item in get_items(link[0].get('href'), 'a'):
                if is_pdf_attachment(unicode(item.get('href'))):
                    download_file(unicode(item.get('href')))
                    pdf_to_text('pdf/'+unicode(os.path.basename(item.get('href'))))
                    text_to_xml('text/'+os.path.splitext(unicode(os.path.basename(item.get('href'))))[0]+'.txt', unicode(item.get('href')))

base_dir = '/home/notroot/sayit/sayit.mysociety.org'
url = 'https://comision6senado.wordpress.com/category/actas/'
scrape(url)

xmldir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'xml')

for f in os.listdir(xmldir):
    if f.endswith('.xml'):
        xmlpath = os.path.join(xmldir, f)
        call(base_dir+'/manage.py load_akomantoso --file='+xmlpath+' --instance=concejodemedellin --commit --merge-existing', shell=True)
