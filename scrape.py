#!/usr/bin/python
# -*- coding: latin-1 -*-

from xml.etree.ElementTree import Element, SubElement, tostring
import os, lxml.html, lxml.etree, urllib2
from subprocess import call


inSpeach = 0
speach = ""
speaker = ""
persons = []
titulos = [
  'concejal ', 
  'concejala', 
  'La Presidencia', 
  'señor', 
  'señora', 
  'comunidad', 
  'doctor',
  'doctora',
  'joven',
  'edil',
  'maestro',
  'profesor',
  'servidora pública del Concejo',
  'ciudadano',
  'diputado',
  'senador',
  'secretario Privado',
  'líder comunitario',
  'representante de la Personería',
  'el sacerdote',
  'estudiante',
  'Director de Planeación',
  'presidente del Concejo',
  'personero'
  ]
especial = {'La Presidencia':'Nicolás Albeiro Echeverri Alvarán'}

def speakers(line, special = 0):
  global titulos, speaker, references
  nameEnd = 0

  for titulo in titulos:
    titlePos = line.find(titulo)
    if titlePos != -1:
      nameEnd = line.find(':')
      name = line[titlePos+len(titulo):nameEnd]
      if special and titulo in especial:
        name = especial[titulo]
      break
    else:
      titlePos = line.find(titulo.capitalize())
      if titlePos != -1:
        nameEnd = line.find(':')
        name = line[titlePos+len(titulo):nameEnd]
        if special and titulo in especial:
          name = especial[titulo]
        break
      else:
        name = 'unknown'
  #Si es desconocido vemos si lo podemos sacar por la regla de la coma
  if (name == 'unknown'):
    titlePos = line.find(',')
    if titlePos != -1:
      nameEnd = line.find(':')
      name = line[titlePos+2:nameEnd]
    else:
      print 'ERROR NAME: '+line

  deco_name = name.decode('utf-8')
  personId = deco_name.lower().replace(' ', '-')
  #guardamos el speaker
  speaker = '#'+personId
  #SPEAKERS
  if name not in persons:
    person = {
      'href' : "/ontology/person/127.0.0.1/"+personId,
      'id' : personId,
      'showAs' : deco_name
    }
    persons.append(name)
    SubElement(references, 'TLCPerson', person)
  return line[nameEnd+2:]


          



def process(line):
  global inSpeach, speach, speaker, debate_section
  if line != None and len(line) > 3:
    #Si está en speach agrego la linea salvo que tenga el cierre
    if inSpeach:
      #Vemos desde la posición de intervino si hay comillas o pasamos a la otra linea
      firstPos = line[1:].find('“')
      lastPos = line[1:].find('”')
      if lastPos != -1 or firstPos != -1:
        if ((lastPos <= firstPos or firstPos == -1) and lastPos != -1):
          #Vemos si es final de speech
          intervencion = {
            'by': speaker,
          }
          #anadimos el speach
          speach += line[:lastPos+1]
          xmlSpeach = SubElement(debate_section, 'speech', intervencion)
          xmlSpeach.text = speach.decode('utf-8')
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
      #Vemos si son Intervinientes
      if line.find('Intervino') != -1 and line.find(':') != -1 :
        newLine = speakers(line)
        inSpeach = 1
        process(newLine)
      if line.find('La Presidencia:') != -1:
        newLine = speakers(line, 1)
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
  meta = SubElement(debate, 'meta')
  references = SubElement(meta, 'references')
  debate_body = SubElement(debate, 'debateBody')
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
          call(['pdftotext', 'actas/'+pdfFile])
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
url = 'http://www.concejodemedellin.gov.co/concejo/concejo/index.php?sub_cat=7543'
scrape(url)
#processTxt('24131.txt')