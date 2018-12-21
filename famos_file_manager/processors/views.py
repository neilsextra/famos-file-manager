from flask import Flask, Blueprint, render_template, request
import binascii
import ctypes
import random
import codecs
import struct
import sys
import re
import argparse
import csv
import io
import re
import zlib
from zipfile import ZipFile
import json
import threading
import datetime
from os import environ
import os
import tempfile
import numpy

from struct import unpack, pack
from azure.storage.blob import BlockBlobService, PublicAccess

views = Blueprint('views', __name__, template_folder='templates')

class FamosParser:
   def __init__(__self, file):
     __self.__data = numpy.array([])
     __self.__regex = re.compile(b"\|(CF|CK|CG|NO|CD|NT|CC|CR|CN|CP|CS|Cb),(.*)", re.DOTALL)
     __self.__dataX = re.compile(b"([0-9]?)\,\s*([0-9]*?),\s*([0-9]*?),(.*)", re.DOTALL)
     __self.__shortFormats = ['4']
     __self.__longFormats = ['6', '7']
     __self.__geoTypes = ['13', '14']
     __self.__fileFormat = 0  
     __self.__keyLength = 0  
     __self.__processor = 0  
     __self.__numberFormat = 0  
     __self.__signBits = 0  
     __self.__offset = 0  
     __self.__directSeqNo = 0  
     __self.__intervalBytes = 0
     __self.__interval = 100
     __self.__title = '' 
     __self.__type = None 
     __self.__count = 0  
     __self.file = file 
   
   def log(__self, message):

       __self.file.write(str(datetime.datetime.now()))
       __self.file.write(' : ')
       __self.file.write(message)
       __self.file.write('\n')
       __self.file.flush()

   def process(__self, data):

      packed = __self.__regex.match(data)

      if packed == None:
         return

      id = packed.group(1)
      content = packed.group(2) 

      if id == b'CF':
         process = re.search(b"(.*?);(.*)", content, re.DOTALL)
         m = re.search(b"([0-9]),([0-9]),([0-9]).*", process.group(1), re.DOTALL)
         __self.__fileFormat = m.group(1).decode('utf-8')
         __self.__keyLength = m.group(2).decode('utf-8')
         __self.__processor = m.group(3).decode('utf-8')

         __self.process(process.group(2))

      elif id == b'CP':
         process = re.search(b"(.*?);(.*)", content, re.DOTALL)
         m = re.search(b"([0-9]),([0-9]*?),([0-9]),([0-9]),([0-9]),([0-9]*?),([0-9]*?),([0-9]*?),([0-9]*?),.*$", 
                        process.group(1), re.DOTALL)
         __self.__bufRef = m.group(3).decode('utf-8')
         __self.__byteReqd = m.group(4).decode('utf-8')
         __self.__numberFormat = m.group(5).decode('utf-8')
         __self.__signBits = m.group(6).decode('utf-8')
         __self.__offset = m.group(7).decode('utf-8')
         __self.__directSeqNo = m.group(8).decode('utf-8')
         __self.__intervalBytes = m.group(9).decode('utf-8')

         __self.process(process.group(2))


      elif id == b'CN':
         process = re.search(b"(.*?);(.*)", content, re.DOTALL)
         m = re.search(b"([0-9]*?),([0-9]*?),([0-9]*?),([0-9]*?),([0-9]*?),([0-9]*?),([^,]*?),([0-9]*?),.*$", 
                        process.group(1), re.DOTALL)
         __self.__title = m.group(7).decode('ascii')
         __self.__type = m.group(8).decode('ascii')

         __self.process(process.group(2))

      elif id == b'Cb':
         process = re.search(b"(.*?);(.*)", content, re.DOTALL)
         m = re.search(b"([0-9]*?),([0-9]*?),.*$", process.group(1), re.DOTALL)

         __self.process(process.group(2))

     
      elif id == b'CS':
         result = __self.__dataX.match(content)
   
         values = bytearray(result.group(4))

         __self.__count = 0         
         c = 0 
         p = 0
         i = 0 
         v = [] 
         for b in values:
            if (p == 4 and __self.__numberFormat in __self.__longFormats):
               if __self.__numberFormat == '6':
                  r = struct.unpack("i", b''.join(v))[0] 
                  if (__self.__type in __self.__geoTypes):  
                     r = r/10000000
                  __self.__data = numpy.append(__self.__data, r)
               elif __self.__numberFormat == '7':
                  r = struct.unpack("f", b''.join(v))[0] 
                  __self.__data = numpy.append(__self.__data, r)
 
               __self.__count += 1   

               p = 0
               v = [] 

            elif (p == 2 and __self.__numberFormat in __self.__shortFormats):
                  r = struct.unpack(">h",  b''.join(v))[0] 
                  r = r/100000

                  if (__self.__title.startswith('Error')):
                     if (i % 2 == 0 or i == 0):
                        __self.__data = numpy.append(__self.__data, r)
                        __self.__count += 1 
                  elif (i % __self.__interval == 0 or i == 0):       
                     __self.__data = numpy.append(__self.__data, r)
                     __self.__count += 1 
 
                  i += 1               
                  p = 0
                  v = [] 
            __self.log(__self.__count)
            v.append(b.to_bytes(1, byteorder='big')) 
            p = p + 1

      else:
         if (re.match(b"[^ \t].*$", content, re.DOTALL)):
            m = re.search(b"[^ \t]+(.*)$", content, re.DOTALL)
            content = m.group(1)
        
      process = re.search(b"(.*?);(.*)", content, re.DOTALL)
      __self.process(process.group(2))  
  
   def parse(__self, content):
     __self.__buffer = content
     __self.process(__self.__buffer)

   def summary(__self):
      __self.log('Title: ' + __self.__title +  ' [' + __self.__type + ']')

      output = 'TY={TY}, FF={FF}, KL={KL}, P={P}, BU={BU}, BR={BR}, NF={NF}, SB={SB}, O={O}, DSN={DSN} IB={IB}, LEN={LEN}'.format(
        TY=__self.__type, FF=__self.__fileFormat, KL=__self.__keyLength, P=__self.__processor, BU=__self.__bufRef, BR=__self.__byteReqd,
        NF=__self.__numberFormat, SB=__self.__signBits, O=__self.__offset, DSN=__self.__directSeqNo, IB=__self.__intervalBytes,
        LEN=str(__self.__data.size))

      __self.log(output)

   def getData(__self):
     return __self.__data

   def getType(__self):
     return __self.__type

   def getTitle(__self):
     return __self.__title

   def getCount(__self):
     return __self.__count

   def getBuffer(__self):
     return __self.__buffer

def getConfiguration():    
   account_key = None
   account_name = None
   default_folder_name = None
   container_name = None
   save_files = 'true'
   socket_timeout = None
   debug_file = None

   try:
      import famos_file_manager.configuration as config

      account_name = config.ACCOUNT_NAME
      container_name = config.CONTAINER_NAME
      default_folder_name = config.DEFAULT_FOLDER_NAME
      save_files = config.SAVE_FILES
      socket_timeout = config.SOCKET_TIMEOUT
      debug_file = config.DEBUG_FILE
      data_dir = config.DATA_DIR

   except ImportError:
      pass

   try:
      import famos_file_manager.keys as keys
      account_key = keys.ACCOUNT_KEY

   except ImportError:
      pass

   account_key = environ.get('ACCOUNT_KEY', account_key)
   account_name = environ.get('ACCOUNT_NAME', account_name)
   container_name = environ.get('CONTAINER_NAME', container_name)
   default_folder_name = environ.get('DEFAULT_FOLDER_NAME', default_folder_name)
   save_files = environ.get('SAVE_FILES', save_files)
   socket_timeout = environ.get('SOCKET_TIMEOUT', socket_timeout)
   debug_file = environ.get('DEBUG_FILE', debug_file)
   data_dir = environ.get('DATA_DIR', data_dir)

   return {
      "account_key": account_key,
      "account_name": account_name,
      'container_name': container_name,
      'default_folder_name': default_folder_name,
      'save_files': save_files,
      'socket_timeout': socket_timeout,
      'debug_file': debug_file,
      'data_dir': data_dir
   }   

def storeFiles(f, content, folder, fileNames, start_time, summary, buffers):
   try:
      configuration = getConfiguration()
   
      log(f, 'Account Name: ' + configuration['account_name'])
      log(f, 'Container Name: ' + configuration['container_name'])

      block_blob_service = BlockBlobService(account_name=configuration['account_name'], 
                                          account_key=configuration['account_key'], 
                                          socket_timeout=configuration['socket_timeout'])

      block_blob_service.create_container(configuration['container_name']) 

      block_blob_service.set_container_acl(configuration['container_name'], public_access=PublicAccess.Container)

      if configuration['save_files'] == 'true':
         for iBuffer, buffer in enumerate(buffers):    
            log(f, 'Storing: ' + fileNames[iBuffer])
            block_blob_service.create_blob_from_stream(configuration['container_name'], 
                                                      folder + '/' + start_time + '/' +
                                                      fileNames[iBuffer] + '.gz', 
                                                      io.BytesIO(zlib.compress(buffer)))
            log(f, 'Stored: ' + fileNames[iBuffer])
      
      log(f, 'Saving Files to Azure Storage')
   
      block_blob_service.create_blob_from_stream(configuration['container_name'], folder + '/' + start_time + '/output.csv.gz',
                                                io.BytesIO(zlib.compress(content.encode())))
      
      log(f, 'Saving Summary')

      block_blob_service.create_blob_from_stream(configuration['container_name'],  folder + '/' + start_time + '/summary.json',
                                                io.BytesIO(summary.encode()))

      log(f, 'Upload Complete')
      
 
   except:
      log(f, str(e))
      print(str(e))

   f.close()

   return

def processFile(f, fileName):
   matrix = []
   titles = []
   types = []
   sizes = []
   buffers = []
   fileNames = []
   summary_types = ['0', '11', '13', '14', '39', '48', '52']
 
   folder = "unknown"

   start_time = 0 
   stop_time = 0 

   processedFiles = []
   
   input_zip = ZipFile(fileName, 'r')
   log(f, 'Processing (Zip) : ' + fileName)
    
   for name in input_zip.namelist():
      log(f, 'Processing: ' + name)

      if (not name.endswith('.raw')):
         continue

      if (name.startswith('GPS.time.sec_BUSDAQ')):
         parts = re.search("_([0-9]*)?(\.raw)", name, re.DOTALL)
         folder = parts.group(1)

      processedFiles.append(name)

      content = input_zip.read(name)
      parser = None
      try:
         parser = FamosParser(f)
         parser.parse(content)
         parser.summary()
      except MemoryError:
         log(f, 'out of memory exception')

      data = parser.getData()

      if len(data) > 0:
         fileNames.append(name)
         buffers.append(parser.getBuffer())
 
         if (parser.getType() in summary_types and not parser.getTitle().startswith('Error')):
            titles.append(parser.getTitle())
            matrix.append(data)
            types.append(parser.getType())
            sizes.append(data.size)

         if (parser.getType() == '52'):
            start_time = re.sub(r'\..*', '', '%.7f' % data[0])
            stop_time = re.sub(r'\..*', '', '%.7f' % data[len(data) - 1])
      
   minSize = min(sizes)

   csvfile = io.StringIO()
   famosWriter = csv.writer(csvfile, delimiter=',',
                                     quotechar='"', quoting=csv.QUOTE_MINIMAL)

   famosWriter.writerow(titles)

   iRow = 0
   
   while iRow < minSize:
      iColumn = 0
      row = []
      while iColumn < len(matrix): 
         row.append('%.7f' % (matrix[iColumn][iRow]))
         iColumn += 1

      iRow += 1
 
      famosWriter.writerow(row)

   content = csvfile.getvalue()

   summary = json.dumps({"start": start_time, "stop": stop_time, 
                          "titles": titles, "types":types,
                          "files": processedFiles})

   try: 
      thread = threading.Thread(name='storefiles', target=storeFiles, args=(f, content, folder, fileNames, start_time, summary, buffers))
      thread.setDaemon(True)
      thread.start()
   except Exception as e:
      log(f, str(e))
      print(str(e))

   csvfile.close()
   input_zip.close()
   os.remove(fileName)
   
   return content

def log(f, message):
   f.write(str(datetime.datetime.now()))
   f.write(' : ')
   f.write(message)
   f.write('\n')
   f.flush()

@views.route("/")
def home():
   return render_template("main.html")

@views.route("/list", methods=["GET"])
def list():
   configuration = getConfiguration()
   
   f = open(configuration['debug_file'], 'a')

   try:
      log(f, 'Listing Files - request received')

      block_blob_service = BlockBlobService(account_name=configuration['account_name'], 
                                          account_key=configuration['account_key'], 
                                          socket_timeout=configuration['socket_timeout'])

      block_blob_service.create_container(configuration['container_name']) 

      block_blob_service.set_container_acl(configuration['container_name'], public_access=PublicAccess.Container)
      output = []

      blobs = block_blob_service.list_blobs(configuration['container_name'])


      for blob in blobs:
         if (re.match("(.*)\/(.*)\/(summary\.json)$", blob.name,  re.DOTALL)):
            data = re.search("(.*)\/(.*)\/(summary\.json)$", blob.name, re.DOTALL)
            output.append({
               "summary_file": blob.name,
               "folder": data.group(1),
               "start_time": data.group(2)
            })
      
      f.close()

      return json.dumps(output, sort_keys=True)

   except Exception as e:
      log(f, str(e))

      f.close()
      return ""

@views.route("/retrieve", methods=["GET"])
def retrieve():
   timestamp = request.args.get('timestamp')
   name = request.args.get('name')

   configuration = getConfiguration()
   f = open(configuration['debug_file'], 'a')
   log(f, 'Retrieving - ' + name + '/' + timestamp)

   configuration = getConfiguration()

   block_blob_service = BlockBlobService(account_name=configuration['account_name'], 
                                         account_key=configuration['account_key'], 
                                         socket_timeout=configuration['socket_timeout'])

   stream = io.BytesIO()

   block_blob_service.get_blob_to_stream(container_name=configuration['container_name'], 
                                   blob_name=name + '/' + timestamp + '/output.csv.gz', stream=stream)

   content = zlib.decompress(stream.getbuffer())

   log(f, 'Retrieved - ' + name + '/' + timestamp)

   return content

@views.route("/process", methods=["GET"])
def process():
   
   try:
      configuration = getConfiguration()
      f = open(configuration['debug_file'], 'a')
   
      filename = request.args.get('file_name')

      return processFile(f, filename)
   except:
      log(f, 'Error')
      f.close()
      return
  

@views.route("/upload", methods=["POST"])
def upload():
   configuration = getConfiguration()

   tempFileName = request.values.get('file_name')
   f = open(configuration['debug_file'], 'a')
   
   uploadedFiles = request.files
   
   fileContent = None

   for uploadFile in uploadedFiles:
      fileContent = request.files.get(uploadFile)
   
   output = []

   if (tempFileName == ''):
      with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            temp_file_name = tmpfile.name
            print('TempFileName: ' + temp_file_name)
            log(f, 'Upload allocated - ' + temp_file_name)

            with open(temp_file_name, 'ab') as temp:

               temp.write(fileContent.read())
               temp.close()

            output.append({
               "file_name" : temp_file_name
            })
   else:
      with open(tempFileName, 'ab') as temp:

         temp.write(fileContent.read())
         temp.close()

         output.append({
            "file_name" : tempFileName
         })

   f.close()
   
   return  json.dumps(output, sort_keys=True)
