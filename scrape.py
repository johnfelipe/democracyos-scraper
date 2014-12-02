#!/usr/bin/python
# -*- coding: latin-1 -*-

from xml.etree.ElementTree import Element, SubElement, tostring

i = 0
inSpeach = 0
speach = ""
speaker = ""
persons = []
titulos = ['el concejal ', 'la consejala', 'La Presidencia', 'la directora Técnica de Educación Superior, ']
especial = {'La Presidencia':'Nicolás Albeiro Echeverri Alvarán'}

def speakers(line, special = 0):
  global titulos, speaker

  for titulo in titulos:
      titlePos = line.find(titulo)
      if titlePos != -1:
        nameEnd = line.find(':')
        name = line[titlePos+len(titulo):nameEnd]
        if special and titulo in especial:
          name = especial[titulo]
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
      else:
        persons.append("name")
        #guardamos el speaker
        speaker = "name"



def process(line):
  global inSpeach, speach, speaker
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


#EMPIEZA
f = open("21147.txt", "r+")
lines = f.readlines()

akoman = Element('akomaNtoso')
debate = SubElement(akoman, 'debate')
meta = SubElement(debate, 'meta')
references = SubElement(meta, 'references')
debate_body = SubElement(debate, 'debateBody')
debate_section = SubElement(debate_body, 'debateSection')

for line in lines:
  #Vemos si trae el id del acta (sino se podría poner con el nombre del archivo asumiendo que se guardó de esa manera)
  if line.find('ÍNDICE') != -1:
    debate_heading = SubElement(debate_section, 'heading')
    debate_heading.text = lines[i+1].decode('utf-8')
  process(line)
  i+=1
print tostring(akoman)

f.close()
