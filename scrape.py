#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import re
from urlparse import urlparse
from xml.etree.ElementTree import Element, SubElement, tostring, parse
import sys, os, lxml.html, lxml.etree, urllib2
from subprocess import call
import unicodedata, string
from time import strptime, strftime

from cStringIO import StringIO
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage

inSpeech = 0
speach = ''
speaker = ''
speaker_comp = ''
persons = []
titulos = [
'concejal ',
'Concejal ', 
'concejala ',
'Concejala ', 
'La Presidencia', 
'Alcalde de Medellín',
'señor ', 
'señora ', 
'comunidad ', 
'doctor ',
'doctora ',
'joven ',
'edil ',
'maestro ',
'profesor ',
'servidora pública del Concejo ',
'ciudadano ',
'diputado ',
'senador ',
'secretario Privado ',
'líder comunitario ',
'representante de la Personería ',
'el sacerdote ',
'estudiante ',
'Director de Planeación ',
'presidente del Concejo ',
'personero ',
'el Secretario Vicealcalde de Gobernabilidad, Seguridad y Servicio a la Ciudadanía ',
'la Secretaría de Gobierno del Departamento, programa ‘Entornos Protectores’ ', 
'funcionaria de la Secretaría de Las Mujeres ',
'el representante de la Secretaría de Seguridad ',
'el representante del Área Metropolitana del Valle de Aburrá ',
'en representación de Sintraemdes ',
'en representación de Sintraemdes Medellín ',
'la Secretaría del Medio Ambiente ',
'Secretaria Vicealcaldesa de Educación, Cultura, Participación, Recreación y Deporte ',
'vicealcalde de de Salud, Inclusión Social y Familia ',
'contralora (e ) ',
'representante legal de la Junta de Acción Comunal de Bellavista ',
'representante de Corantioquia ',
'delegado del Área Metropolitana ',
'secretario (e) de Movilidad ',
'representante de Corantioquia ',
'representante del Isvimed ',
'representante del Área Metropolitana ',
'director del Fonvalmed ',
'director de Fonvalmed ',
'la niña ',
'niña ',
'niño ',
'Subsecretaria Piedad Toro Duarte ',
'representante de Empresas Públicas ',
'Gerente de El Poblado ',
'el conejal ',
'la Personería ',
'la presidencia a cargo ',
'José Nicolás Duque Ossa ',
'Representante de los trabajadores ',
'representante de Empresas Públicas de Medellín ',
'contralor ',
'la Administración Municipal ',
'representante de la Contraloría ',
'representante de Medicina Legal y Ciencias Forenses ',
'Secretaría de Seguridad ',
'el concejal ',
'secretaria de Cultura Ciudadana ',
'Subsecretario encargado de Medio Ambiente ',
'subsecretario encargado de Medio Ambiente ',
'presidente de la JAC Robledo ',
'Gerente del proyecto ',
'representante de la Secretaría de Hacienda ',
'representante de Planeación ',
'secretario de Hacienda ',
'secretario (e) de Movilidad ',
'Hábitat, Movilidad, Infraestructura y Sostenibilidad ',
'Movilidad, Infraestructura y Sostenibilidad ',
'Seguridad y Servicio a la Ciudadanía ',
'Cultura, Participación, Recreación y Deporte ',
'delegado de Derechos Humanos ',
'Inclusión Social y Familia ',
'Inclusión y Familia ',
'Internacionalización, CTI y Alianzas Público Privadas ',
'seccional Antioquia ',
'Banca de Inversión ',
'Vamos Mujer ',
'Reconciliación y la Convivencia ',
'corporación Universidad Remington '
]

especial = {
    'La Presidencia':'Nicolás Albeiro Echeverri Alvarán',
    'secretario (e) de Movilidad':'secretario de Movilidad',
    'Alcalde de Medellín':'Aníbal Gaviria Correa'
}

date_translation = {
    'enero': '01',
    'febrero': '02',
    'marzo': '03',
    'abril': '04',
    'mayo': '05',
    'junio': '06',
    'julio': '07',
    'agosto': '08',
    'setiembre': '09',
    'octubre': '10',
    'noviembre': '11',
    'diciembre': '12',
}
base_dir = '/home/notroot/sayit/sayit.mysociety.org'

def speakers(line, special = 0):
    global titulos, speaker, references
    nameEnd = 0
    print line
    titulo=''
    for titulo in titulos:
        titlePos = line.find(titulo)
        if titlePos != -1:
            print 'Encuentr el titulo '+ titulo
            nameEnd = line.find(':')
            name = line[titlePos+len(titulo):nameEnd]
            if titulo in especial:
                name = especial[titulo]
            break
        else:
            titlePos = line.find(titulo.capitalize())
            if titlePos != -1:
                nameEnd = line.find(':')
                name = line[titlePos+len(titulo):nameEnd]
                if titulo in especial:
                    name = especial[titulo]
                break
            else:
                name = 'unknown'
    print name;
    #Si es desconocido vemos si lo podemos sacar por la regla de la coma
    if (name == 'unknown'):
        titlePos = line.find(',')
        nameEnd = line.find(':')
        if titlePos != -1 and nameEnd != -1:
            name = line[titlePos+2:nameEnd]
        else:
            print 'ERROR NAME: '+line

    deco_name = name.decode('utf-8')
    personId = ''.join(x for x in unicodedata.normalize('NFKD', deco_name) if x in string.ascii_letters).lower()
    #guardamos el speaker
    speaker = '#'+personId
    #SPEAKERS
    if personId not in persons:
        person = {
            'href' : '/ontology/person/127.0.0.1/'+personId,
            'id' : personId,
            'showAs' : deco_name
        }
        persons.append(personId)
        SubElement(references, 'TLCPerson', person)

    return line[nameEnd+2:]

def get_speakers():
    global persons
    #Nos quedamos con todos los ids del archivo e iremos sumando a medida que recorremos
    tree = parse('persons.xml')
    root = tree.getroot()
    for person in root.iter('TLCPerson'):
        persons.append(person.get('id'))

def set_speakers():
    global persons
    #Guardamos las personas
    akoman = Element('akomaNtoso')
    debate = SubElement(akoman, 'debate')
    meta = SubElement(debate, 'meta')
    references = SubElement(meta, 'references')

    for personId in persons:
        deco_name = personId.replace('-', ' ').title()
        person = {
            'href' : '/ontology/person/127.0.0.1/'+personId,
            'id' : personId,
            'showAs' : deco_name
        }
        SubElement(references, 'TLCPerson', person)
    write(tostring(akoman), 'persons.xml')
    
def parse_line(line):
    global inSpeech, speach, speaker, debate_section, speaker_comp, speechDate

    #Vemos que no esté vacía la línea y que el largo sea mayor a 4 para dejar los números de las páginas afuera
    if len(line) > 4:

        #Si está en speach agrego la linea salvo que tenga el cierre
        if inSpeech:

            #Vemos desde la posición de intervino si hay comillas o pasamos a la otra linea
            firstPos = line[1:].find('“')
            lastPos = line[1:].find('”')

            if lastPos != -1 or firstPos != -1:

                if ((lastPos <= firstPos or firstPos == -1) and lastPos != -1):

                    if (line[lastPos+6:].strip() != '' ):
                        print 'Linea con intervención dentro: '+line;
                        speach += line
                        return

                    #Vemos si es final de speech
                    intervencion = {
                        'by': speaker,
                        'startTime' : startTime
                    }

                    #anadimos el speach
                    speach += line[:lastPos+1]
                    xmlSpeach = SubElement(debate_section, 'speech', intervencion)
                    xmlSpeach.text = speach.decode('utf-8').replace(u'\u201C', '')

                    #vaciamos las variables
                    inSpeech = 0
                    speaker = ''
                    speach = ''
                    intervencion = {}
                    #Si no es final es comienzo, marcamos para el final

                elif firstPos != -1:
                    speach += line[firstPos+1:]
                    #retornamos para que se procese nuevamente la linea
                    parse_line(line[firstPos+1:])
            else:
                #Sacamos todas las líneas con ACTA ya que tiene caracteres especiales
                if line.find('ACTA') != -1:
                    return
                speach += line
                return
        else:

            #Vemos si es un speaker parcial
            if len(speaker_comp) > 0:
                if line.find(':') != -1:
                    comp_line = speaker_comp + line
                    newLine = speakers(comp_line)
                    inSpeech = 1
                    parse_line(newLine)

                speaker_comp = ''

            #Vemos si son Intervinientes
            if line.find('Intervino') != -1 or line.find('Palabras del') != -1 or line.find('Continuó') != -1 or line.find('Interviene') != -1 or line.find('Continúa') != -1 or line.find('La Secretaría') != -1 or line.find('Interpela') != -1 or line.find('Responde') != -1 or line.find('Informa') != -1:
                #Vemos si el speaker esta en 2 lineas
                if line.find(':') == -1 :
                    comp_start = line.find(',')
                    if comp_start != -1 :
                        speaker_comp = line[comp_start:]
                    else:
                        print 'No se pudo obtener el nombre'
                        return
                else:
                    newLine = speakers(line)
                    inSpeech = 1
                    parse_line(newLine)

            if line.find('La Presidencia:') != -1:
                newLine = speakers(line)
                inSpeech = 1
                parse_line(newLine)
    return


# here's an example function, showing off usage:
def show_paragraphs(fname):

    file = open(fname)
    paragraphs = re.findall(r'\n(.*?)\n', str(file.read()))
    file.close()

    for p in paragraphs:
        print p



def text_to_xml(fname):
    print 'Convirtiendo TXT a XML '+fname
    global akoman, debate, meta, references, debate_body, debate_section, startTime
    date_pos = ''

    i = 0
    akoman = Element('akomaNtoso')
    debate = SubElement(akoman, 'debate')
    dabate_date = SubElement(debate, 'docDate')
    debate_body = SubElement(debate, 'debateBody')
    debate_section = SubElement(debate_body, 'debateSection')
    meta = SubElement(debate, 'meta')
    references = SubElement(meta, 'references')

    show_paragraphs(fname)

    # f = open(fname, 'r+')
    # lines = f.readlines()

    # for line in lines:
        # Vemos si trae el id del acta (sino se podría poner con el nombre del 
        # archivo asumiendo que se guardó de esa manera)

        # if line.find('ÍNDICE') != -1:
        #     debate_heading = SubElement(debate_section, 'heading')
        #     debate_heading.text = lines[i+1].decode('utf-8')

        # if line.find('FECHA') != -1:
        #     date_pos = lines[i+2].find(',')

        # if date_pos:
        #     speech_date_str = lines[i+2][date_pos+2:].replace('de ','').replace('\n','').replace('\r', '').replace('°','')
        #     speech_date_arr = speech_date_str.split(' ')
        #     print speech_date_arr[1]

        #     if speech_date_arr[1] in date_translation:
        #         speech_date_str.replace(speech_date_arr[1], date_translation[speech_date_arr[1]])
        #         speech_date_str = speech_date_str.replace(speech_date_arr[1], date_translation[speech_date_arr[1]])
        #         speech_date_obj = strptime(speech_date_str, '%d %m %Y')
        #         startTime = strftime('%Y-%m-%dT%H:%M:%S', speech_date_obj)

        #     else:
        #         print 'No se pudo convertir la fecha'

        # parse_line(line)
        # i+=1

    # f = open('xml/'+os.path.splitext(os.path.basename(fname))[0]+'.xml', 'w')
    # f.write(tostring(akoman))
    # f.close()

    #print base_dir+'/manage.py load_akomantoso --file=actas-xml/23613.xml--instance=concejodemedellin2013 --commit'
    #call(base_dir+'/manage.py load_akomantoso --file=/home/notroot/actas-consejo-medellin/actas-xml/23613.xml --instance=concejodemedellin2013 --commit', shell=True);


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
                download_file(unicode(item.get('href')))
                pdf_to_text('pdf/'+unicode(os.path.basename(item.get('href'))))
                text_to_xml('text/'+os.path.splitext(unicode(os.path.basename(item.get('href'))))[0]+'.txt')

                raise Exception

url = 'https://comision6senado.wordpress.com/category/actas/'
scrape(url)
