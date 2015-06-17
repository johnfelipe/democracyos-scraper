#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

# TODO:
# Múltiples presidentes en un mismo pdf

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

_persons = {}
_domain = 'senado.felipeurrego.com'
_months = {
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
_remove_paragraphs_re = [
    [r'\S*\s*\d*\s*/\d*\s*(-|–)*\s*\S*\s*\d*/\d*\s*\n\S*\s*\S*\s*\d*-\d*\s*\n\S*.*', r''],
    [r'\S*\s*\d*/\d*\s*(-|–)*\s*\S*\s*\d*/\d*\s*\n\S*\s*\S*\s*\d*-\d*\s*\n\S*.*', r''],
    [r'\S*\s*\d*-\d*\s*/\s*\S*\s*\d*-\d*\s*\n\S*.*\n\S*.*', r''],
    [r'\S*\s*\d*/\d*\s*–\s*\S*\s*\d*/\d*\s*–\s*.*\n\s*\S*\s*\S*\s*\d*-\d*', r''],
    [r'\S*\s*\S*\s*\d*\s*/\s*\S*\s*\d*/\d*\s*\n\S*\s*\S*\s*/\d*-\d*\s*\n\S*.*', r''],
    [r'\S*\s*\S*\s*\d*\s*/\d*\s*(-|–)*\s*\S*\s*\d*/\d*\s*\n\S*\s*\S*\s*/\S*\s*', r''],
    [r'\S*\s*\d*\s*/\d*\s*(-|–)*\s*\S*\s*\d*/\d*\s*\n\S*\s*\S*\s*', r''],
    [r'Para la [sS]esión del (\S*)(\s*)([0-9]*)(\s*)de(\s*)(\S*)(\s*)de(\s*)([0-9]*)(.*)', r''],
    [r'Llamada a lista.', r''],
    [r'\n\nPresidente\.', '\n\nPresidente:'],
    [r'Presdiente', 'Presidente'],
    [r'H\.S\. ', r'H. S. '],
    [r'H\. S ', r'H. S. '],
    [r'Página\s*\d*', r''],
    [r'\nI\s{0,1}\n', r''],
    [r'\nII\s{0,1}\n', r''],
    [r'\nIII\s{0,1}\n', r''],
    [r'\nIV\s{0,1}\n', r''],
    [r'\nV\s{0,1}\n', r''],
    [r'\nVI\s{0,1}\n', r''],
    [r'\n\s{0,1}\d{1,2}\s{0,1}\n', r''],
    [r'([\*]*)', ''],
    [r'^\.\n', ''],
    [r'\f', r''],
    [r'“', '"'],
    [r'”', '"'],
    [r'\s*–\s*', '-'],
    [r'\s*-\s*', '-'],
    [r'\s*-\s*', '-'],
    [r'\s{2,}', ' '],
    [r'\n', ' '],
    [r'\s{2,}', ' '],
    [r':\.', ':'],
    [r'(?<!A LA )PROPOSICIÓN\s*No\.\s*(\d*)/(\d*)\s*', r'PROPOSICIÓN No. \1/\2. '],
    [r'(\d)\.\-', r'######\1.-'],
    [r'(?<!Dr)(?<!DR)(?<!Dra)(?<!DRA)(?<!No)(?<!NO)(?<!Sr)(?<!SR)(?<!Sra)(?<!SRA)(?<! D)(?<! H)(?<! S)(?<!-H)\.\s', r'.######'],
]
_speech_re = [
    [r'\sH\.\sS\.([^#]*?):', r'.######H. S.\1:'],
    [r'######((H\. S\.|Dra\.|Dr\.|Sr\.|Sra\.)[^#]*?):', r'\n\1:'],
]
_questions_re = [
    r'^(.*)\ncuestionario\s*?(:|al|para|adjunto|\n|ADITIVO A LA PROPOSICIÓN|ANEXO A LA PROPOSICIÓN)(.*)$',
    r'^(.*)siguiente\s*cuestionario\s*?(:|al|para|adjunto|\n|ADITIVO A LA PROPOSICIÓN|ANEXO A LA PROPOSICIÓN)(.*)$',
    r'^(.*)ADICIÓNESE\s*A\s*LA\s*PROPOSICIÓN(.*)EL\s*CUESTIONARIO(.*)$',
    r'^(.*)cuestionario(\s*)adjunto(.*)$'
]

# _fix_questions_re = [
#     [r'[ \.:\?] ([0-9]*)\.', r'\n\1.'],
#     [r'  ', r'\n'],
#     [r'\n\. ', r'. '],
#     [r'Presentada a consideración(.*)', r''],
#     [r'Presentado por(.*)', r''],
#     [r'ANUNCIO para Discusión y Votación(.*)', r''],
#     [r'ADITIVO A LA PROPOSICIÓN(.*)\n', r''],
#     [r'ANEXO A LA PROPOSICIÓN(.*)\n', r''],
#     [r'-Sr Presidente(.*)\n', r''],
#     [r'PROPUESTO SOBRE EL DEBATE(.*)\n', r'']
# ]
# _fix_details_re = [
#     [r'“', '"'],
#     [r'”', '"'],
#     [r'\f', ''],
#     [r': :', ':'],
#     [r'  ', ' '],
#     [r'  ', ' '],
#     [r'   ', ' '],
#     [r'    ', ' '],
#     [r'([\*]*)', ''],
#     [r' – ', '-'],
#     [r'– ', '-'],
#     [r' –', '-'],
#     [r' - ', '-'],
#     [r'- ', '-'],
#     [r' -', '-'],
#     [r'-\n', '-'],
#     [r'  \n', ' '],
#     [r' \n', ' '],
#     [r' \n', ' '],
#     [r'H\.S\. ', r'H. S. '],
#     [r'H\. S ', r'H. S. '],
#     [r'^\s*\n*', '']
# ]
_default_presidente = 'H. S. Eugenio Prieto Soto'
_default_secretaria = 'Dra. Sandra Ovalle García'
_common_titles_list = [
    ['Presidente', 'El Presidente'],
    ['Presidenta', 'La Presidenta'],
    ['Secretaria', 'La Secretaria']
]
_titles_list = [
    ['Dr. Diego Molano Vega', 'Ministro de TIC', 'Ministro de Tecnologías de la Información y las Comunicaciones'],
    ['Dr. Carlos Pablo Márquez', 'CRC', 'Director Ejecutivo Comisión De Regulación De Comunicaciones \(CRC\)'],
    ['Dr. Julián Cardona Castro', 'ACIEM', 'Presidente de ACIEM \(Asociación Colombiana de Ingenieros\)']
    # Presidente de Asomóvil-Dr. Rodrigo Lara Restrepo
]

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


def is_valid_person(person):
    for i in ['Dr.', 'Dra.', 'H. S.']:
        if person.startswith(i):
            return True
    return False


def get_narratives(text):
    match = re.search(r'^(.*)ORDEN\s*DEL\s*D(Í|I)A(.*)$', text, flags=re.S)
    return (match.group(1), match.group(3))


def get_presidente(text):
    match = re.search(r'Presidente-(.*?)(:|,|solicita)', text, flags=re.S|re.I)
    if not match:
        return _default_presidente
    return match.group(1)


def get_secretaria(text):
    match = re.search(r'Secretaria-(.*?)(:|,|realiza)', text, flags=re.S|re.I)
    if not match:
        return _default_secretaria
    return match.group(1)


def get_date_object(text):
    m = re.search(r'Para la [sS]esión del (\S*)(\s*)([0-9]*)(\s*)de(\s*)(\S*)(\s*)de(\s*)([0-9]*)', text)
    return datetime.strptime(m.group(3)+'-'+_months[m.group(6).lower()]+'-'+m.group(9), '%d-%m-%Y')


def get_acta_intro(text):
    m = re.search(r'ACTA No\. ([0-9]*)(.*)', text, flags=re.S|re.I)
    return (m.group(1), m.group(2))


def get_questions_match(text):
    return (re.search(_questions_re[0], text, flags=re.S|re.I)
            or re.search(_questions_re[1], text, flags=re.S|re.I)
            or re.search(_questions_re[2], text, flags=re.S|re.I)
            or re.search(_questions_re[3], text, flags=re.S|re.I))


def get_narrative_questions_speech(text):

    match = get_questions_match(text)

    if match:
        narrative = match.group(1)
        questions = match.group(3)

        while True:
            match = get_questions_match(narrative)

            if match:
                narrative = match.group(1)
                questions = match.group(3)+questions

            else:
                break

        match = re.search(r'^(.*)LO\s*QUE\s*PROPONGAN\s*LOS\s*HONORABLES\s*SENADORES(.*)$', questions, flags=re.S)
        questions = match.group(1)
        speech = match.group(2)

    else:
        match = re.search(r'^(.*)LO\s*QUE\s*PROPONGAN\s*LOS\s*HONORABLES\s*SENADORES(.*)$', text, flags=re.S)
        narrative = match.group(1)
        speech = match.group(2)
        questions = ''

    return (narrative, questions, speech)


def process_narratives(text):
    for r, f in _remove_paragraphs_re:
        text = re.sub(r, f, text)

    return text.strip()

def process_speech(text):
    for r, f in _remove_paragraphs_re:
        text = re.sub(r, f, text)

    for i in _titles_list:
        text = re.sub(i[0]+', '+i[1]+':', i[0]+':', text)
        text = re.sub(i[2]+'-'+i[0]+':', i[0]+':', text)
        text = re.sub(i[1]+'-'+i[0]+':', i[0]+':', text)
        text = re.sub(i[0]+'[^:]', i[0]+': ', text)
        text = re.sub(i[1]+':', i[0]+':', text)

    for i in _common_titles_list:
        text = re.sub(i[0]+'\s*(–|-|,)\s*H\.\s*S\.', i[0]+'-H. S.', text)
        text = re.sub(i[1]+'\s*(–|-|,)\s*H\.\s*S\.', i[0]+'-H. S.', text)

    text = text.strip()
    presidente = get_presidente(text)
    secretaria = get_secretaria(text)

    _important_titles_list = [
        [presidente, 'Presidente', 'El Presidente'],
        [secretaria, 'Secretaria', 'La Secretaria'],
    ]
    for i in _important_titles_list+_titles_list:
        text = re.sub(i[0]+', '+i[1]+':', i[0]+':', text)
        text = re.sub(i[2]+'-'+i[0]+':', i[0]+':', text)
        text = re.sub(i[1]+'-'+i[0]+':', i[0]+':', text)
        # text = re.sub(i[0]+'[^:]', i[0]+': ', text)
        # text = re.sub(i[1]+':', i[0]+':', text)

    # for r, f in _speech_re:
    #     text = re.sub(r, f, text)

    return text


def text_to_xml(fname, url):
    print 'Convirtiendo TXT a XML '+fname

    f = open(fname)
    fcontent = f.read()

    dateobject = get_date_object(fcontent)
    acta, intro = get_acta_intro(fcontent)
    narrative, questions, speech = get_narrative_questions_speech(intro)
    q_narrative, s_narrative = get_narratives(narrative)

    speech = process_speech(speech)
    # questions = clean_questions(clean_text(questions))

    q_narrative = process_narratives(q_narrative)
    s_narrative = process_narratives(s_narrative)

    f = open('xml/'+os.path.splitext(os.path.basename(fname))[0]+'.txt', 'w')
    f.write(speech)
    f.close()

    # flist = filter(None, speech.decode('utf-8').split('\n'))
    # qlist = filter(None, questions.decode('utf-8').split('\n'))

    # akoman = Element('akomaNtoso')
    # debate = SubElement(akoman, 'debate')

    # # META
    # meta = SubElement(debate, 'meta')
    # references = SubElement(meta, 'references')

    # # PREFACE
    # preface = SubElement(debate, 'preface')
    # doctitle = SubElement(preface, 'docTitle')
    # doctitle.text = unicode('Comisión Sexta Senado'.decode('utf-8'))
    # link = SubElement(preface, 'link', href=url)

    # # DEBATE BODY
    # debate_body = SubElement(debate, 'debateBody')
    # debate_section_1 = SubElement(debate_body, 'debateSection')
    # heading_1 = SubElement(debate_section_1, 'heading')
    # heading_1.text = unicode(dateobject.strftime('%Y'))
    # debate_section_2 = SubElement(debate_section_1, 'debateSection')
    # heading_2 = SubElement(debate_section_2, 'heading')
    # heading_2.text = unicode(_months.keys()[_months.values().index(dateobject.strftime('%m'))].title())
    # debate_section_3 = SubElement(debate_section_2, 'debateSection')
    # heading_3 = SubElement(debate_section_3, 'heading')
    # heading_3.text = unicode('ACTA No. '+acta+' / '+dateobject.strftime('%d-%m-%Y'))

    # nq = SubElement(debate_section_3, 'speech', by='', startTime=unicode(dateobject.strftime('%Y-%m-%dT%H:%M:%S')))
    # sef = SubElement(nq, 'from')
    # sef.text = unicode('OTROS')
    # sep = SubElement(nq, 'p')
    # sep.text = unicode(q_narrative.decode('utf-8'))

    # if qlist:
    #     qss = SubElement(debate_section_3, 'questions')
    #     qssh = SubElement(qss, 'heading')
    #     qssh.text = 'CUESTIONARIO'

    #     for q in qlist:
    #         if q:
    #             if q[0].isdigit():
    #                 qs = SubElement(qss, 'question')
    #                 qs.text = unicode(q)
    #             else:
    #                 qs = SubElement(qss, 'narrative')
    #                 qs.text = unicode(q)

    # na = SubElement(debate_section_3, 'speech', by='', startTime=unicode(dateobject.strftime('%Y-%m-%dT%H:%M:%S')))
    # sef = SubElement(na, 'from')
    # sef.text = unicode('OTROS')
    # sep = SubElement(na, 'p')
    # sep.text = unicode(s_narrative.decode('utf-8'))

    # for j in flist:
    #     se_person = j.split(':')[0]
    #     se_person_slug = _slugify(se_person)

    #     if is_valid_person(se_person) and se_person_slug:
    #         _persons[se_person_slug] = {
    #             'href': '/ontology/person/'+_domain+'/'+se_person_slug,
    #             'id': se_person_slug,
    #             'showAs': se_person
    #         }

    #         se = SubElement(debate_section_3, 'speech', by='#'+se_person_slug,
    #                         startTime=unicode(dateobject.strftime('%Y-%m-%dT%H:%M:%S')))
    #         sef = SubElement(se, 'from')
    #         sef.text = unicode(se_person)
    #         sep = SubElement(se, 'p')
    #         sep.text = unicode(j[len(se_person+':'):])

    # for key, value in _persons.iteritems():
    #     se_person_tag = SubElement(references, 'TLCPerson', **value)

    # xml_content = xml.dom.minidom.parseString(tostring(akoman))

    # f = open('xml/'+os.path.splitext(os.path.basename(fname))[0]+'.xml', 'w')
    # f.write(xml_content.toprettyxml().encode('utf-8'))
    # f.close()


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

    # while True:
    #     if get_status_code(url+'page/'+str(pages)) != 404:
    #         print url+'page/'+str(pages)
    #         validpages.append(url+'page/'+str(pages))
    #         pages += 1
    #     else:
    #         break

    validpages = [
        'https://comision6senado.wordpress.com/category/actas/page/1',
        'https://comision6senado.wordpress.com/category/actas/page/2'
    ]

    for page in validpages:
        for session in get_items(page, '.entry-title'):
            link = session.cssselect('a')
            for item in get_items(link[0].get('href'), 'a'):
                if is_pdf_attachment(unicode(item.get('href'))):
                    # download_file(unicode(item.get('href')))
                    # pdf_to_text('pdf/'+unicode(os.path.basename(item.get('href'))))
                    text_to_xml('text/'+os.path.splitext(unicode(os.path.basename(item.get('href'))))[0]+'.txt', unicode(item.get('href')))


base_dir = '/home/notroot/sayit/sayit.mysociety.org'
url = 'https://comision6senado.wordpress.com/category/actas/'
scrape(url)

# xmldir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'xml')

# for f in os.listdir(xmldir):
#     if f.endswith('.xml'):
#         xmlpath = os.path.join(xmldir, f)
#         call(base_dir+'/manage.py load_akomantoso --file='+xmlpath+' --instance=concejodemedellin --commit --merge-existing', shell=True)
