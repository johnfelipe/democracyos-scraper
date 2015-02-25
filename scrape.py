#!/usr/bin/python
# -*- coding: utf-8 -*-

from xml.etree.ElementTree import Element, SubElement, tostring, parse
import sys, os, lxml.html, lxml.etree, urllib2
from subprocess import call
import unicodedata, string

inSpeach = 0
speach = ""
speaker = ""
speaker_comp = ""
persons = []
titulos = [
  'concejal ', 
  'concejala ', 
  'La Presidencia', 
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
  'funcionaria de la Secretaría de Las Mujeres ',
  'el representante de la Secretaría de Seguridad ',
  'el representante del Área Metropolitana del Valle de Aburrá ',
  'en representación de Sintraemdes ',
  'en representación de Sintraemdes Medellín ',
  'la Secretaría del Medio Ambiente ',
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
  'Vicealcalde de Gobernabilidad, Seguridad y Servicio a la Ciudadanía ',
  'Seguridad y Servicio a la Ciudadanía ',
  'Cultura, Participación, Recreación y Deporte ',
  'delegado de Derechos Humanos ',
  'Inclusión Social y Familia ',
  'Inclusión y Familia ',
  'Internacionalización, CTI y Alianzas Público Privadas ',
  'seccional Antioquia ',
  'Banca de Inversión ',
  'Vamos Mujer ',
  'Reconciliación y la Convivencia '
  ]
especial = {
  'La Presidencia':'Nicolás Albeiro Echeverri Alvarán',
  'secretario (e) de Movilidad':'secretario de Movilidad',
  'Alcalde de Medellín':'Aníbal Gaviria Correa'
}

def speakers(line, special = 0):
  global titulos, speaker, references
  nameEnd = 0

  for titulo in titulos:
    titlePos = line.find(titulo)
    if titlePos != -1:
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
      'href' : "/ontology/person/127.0.0.1/"+personId,
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
      'href' : "/ontology/person/127.0.0.1/"+personId,
      'id' : personId,
      'showAs' : deco_name
    }
    SubElement(references, 'TLCPerson', person)
  write(tostring(akoman), 'persons.xml')

def process(line):
  global inSpeach, speach, speaker, debate_section, speaker_comp
  #Vemos que no esté vacía la línea y que el largo sea mayor a 4 para dejar los números de las páginas afuera
  if line != None and len(line) > 4:
    #Si está en speach agrego la linea salvo que tenga el cierre
    if inSpeach:
      #Vemos desde la posición de intervino si hay comillas o pasamos a la otra linea
      firstPos = line[1:].find('“')
      lastPos = line[1:].find('”')
      if lastPos != -1 or firstPos != -1:
        if ((lastPos <= firstPos or firstPos == -1) and lastPos != -1):
          #print line[lastPos+6:]
          if (line[lastPos+6:].strip() != '' ):
            print 'Linea con intervención dentro: '+line;
            speach += line
            return
          #Vemos si es final de speech
          intervencion = {
            'by': speaker,
          }
          #anadimos el speach
          speach += line[:lastPos+1]
          xmlSpeach = SubElement(debate_section, 'speech', intervencion)
          xmlSpeach.text = speach.decode('utf-8').replace(u"\u201C", '')
          #vaciamos las variables
          inSpeach = 0
          speaker = ""
          speach = ""
          intervencion = {}
          #Si no es final es comienzo, marcamos para el final
        elif firstPos != -1:
          speach += line[firstPos+1:]
          #retornamos para que se procese nuevamente la linea
          process(line[firstPos+1:])
      else:
        #Sacamos todas las líneas con ACTA ya que tiene caracteres especiales
        if line.find('ACTA') != -1:
          return
        speach += line
        return
    else:
      #Vemos si es un speaker parcial
      if (len(speaker_comp) > 0):
        if line.find(':') != -1 :
          comp_line = speaker_comp + line
          newLine = speakers(comp_line)
          inSpeach = 1
          process(newLine)
        speaker_comp = ""
      #Vemos si son Intervinientes
      if line.find('Intervino') != -1 or line.find('Palabras del') != -1 or line.find('Continuó') != -1:
        #Vemos si el speaker esta en 2 lineas
        if line.find(':') == -1 :
          comp_start = line.find(',')
          if comp_start != -1 :
            speaker_comp = line[comp_start:]
          else:
            print "No se pudo obtener el nombre"
            return
        else:
          newLine = speakers(line)
          inSpeach = 1
          process(newLine)
      if line.find('La Presidencia:') != -1:
        newLine = speakers(line)
        inSpeach = 1
        process(newLine)
  return

def write(content, destination):
  f = open(destination, 'w')
  f.write(content)
  f.close()

def processTxt(fileName):
  global akoman, debate, meta, references, debate_body, debate_section
  i = 0
  akoman = Element('akomaNtoso')
  debate = SubElement(akoman, 'debate')
  debate_body = SubElement(debate, 'debateBody')
  meta = SubElement(debate, 'meta')
  references = SubElement(meta, 'references')
  debate_section = SubElement(debate_body, 'debateSection')

  f = open('actas/'+fileName, "r+")
  lines = f.readlines()

  for line in lines:
    #Vemos si trae el id del acta (sino se podría poner con el nombre del archivo asumiendo que se guardó de esa manera)
    if line.find('ÍNDICE') != -1:
      debate_heading = SubElement(debate_section, 'heading')
      debate_heading.text = lines[i+1].decode('utf-8')
    process(line)
    i+=1
  write(tostring(akoman), 'actas-xml/'+fileName.split('.')[0]+'.xml')

  f.close()

def scrape(url):
  global persons

  req = urllib2.Request(url)
  response = urllib2.urlopen(req)
  body = response.read()
  doc = lxml.html.document_fromstring(body)
  sessions = doc.cssselect('.menu_sesion')
  #recorremos la página que se supone de actas
  for session in sessions:
    link = session.cssselect('a')
    #tomamos solo los links a actas, sin firmas
    if link[0].text.find('firmas') == -1:
      persons = []
      print link[0].text
      relativeUrl_arr = url.split('/')
      relativeUrl_arr.remove(relativeUrl_arr[-1])
      relativeUrl = '/'.join(relativeUrl_arr)+'/'
      pdfUrl = os.path.join(relativeUrl, link[0].attrib['href'])
      pdfFile = pdfUrl.split('/')[-1]
      #Nos fijamos si ya descargamos el pdf
      cache = os.path.join('actas/', pdfFile)
      if os.path.exists(cache):
        print 'Ya fue procesado: '+cache
      else:
        req = urllib2.Request(pdfUrl)
        response = urllib2.urlopen(req)
        body = response.read()
        write(body,'actas/'+pdfFile)
        print 'Se descargó '+ pdfFile
      #Nos fijamos si lo tenemos convertido a txt
      txtName = pdfFile.split('.')[0]+'.txt'
      if os.path.exists('actas/'+txtName):
        print 'Ya fue convertido a txt: '+txtName
      else:
        #Hay un tema acá y es que no le estoy pudiendo pasar 2 argumentos
        try:
          call('pdftotext -nopgbrk actas/'+pdfFile, shell=True);
          print 'se convertió a TXT: '+txtName
        except Exception as e:
          print 'ERROR no se convertió a TXT!!!!: ', e
          continue
      xmlName = pdfFile.split('.')[0]+'.xml'
      if os.path.exists('actas-xml/'+xmlName):
        print 'Ya existe el xml: '+xmlName
      else:
        try:
          processTxt(txtName)
          print 'Se convirtió a xml: '+xmlName
        except Exception as e:
          print 'ERROR no se convertió a XML!!!!: ', e
          continue

#EMPIEZA
#Vemos si tenemos procesadas todas las actas
#get_speakers()
url = 'http://www.concejodemedellin.gov.co/concejo/concejo/index.php?sub_cat=7543'
scrape(url)
#processTxt('21559.txt')
#call('pdftotext -nopgbrk actas/22991.pdf', shell=True)
#set_speakers()
