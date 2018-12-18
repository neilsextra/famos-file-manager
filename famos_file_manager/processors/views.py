from flask import Flask, render_template, request
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
from os import environ

from struct import unpack, pack
from azure.storage.blob import BlockBlobService, PublicAccess

views = Blueprint('views', __name__, template_folder='templates')

class FamosParser:
  def __init__(__self):
     __self.__data = []
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
     __self.__title = '' 
     __self.__type = None 
     __self.__count = 0  
     __self.__buffer = None 

  def process(__self, data):
     packed = __self.__regex.match(data);

     if packed == None:
        print('completed')
        return;

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
  
        arrayData = result.group(4)

        values = bytearray(result.group(4))

        __self.__count = 0         
        c = 0 
        p = 0
        v = [] 
        for b in values:
           if (p == 4 and __self.__numberFormat in __self.__longFormats):
              if __self.__numberFormat == '6':
                 r = struct.unpack("i", b''.join(v))[0] 
                 if (__self.__type in __self.__geoTypes):  
                    r = r/10000000
                 __self.__data.append('%.7f' % (r))
              elif __self.__numberFormat == '7':
                 r = struct.unpack("f", b''.join(v))[0] 
                 __self.__data.append('%.7f' % (r))

              __self.__count += 1         
              p = 0
              v = [] 

           elif (p == 2 and __self.__numberFormat in __self.__shortFormats):
              r = struct.unpack(">h",  b''.join(v))[0] 
              r = r/100000
              __self.__data.append('%.7f' % (r))
              __self.__count += 1         
              p = 0
              v = [] 

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
     print('Title: ' + __self.__title, '[' + __self.__type + ']')
     print('TY='+__self.__type, 
           'FF='+__self.__fileFormat, 
           'KL='+__self.__keyLength, 
           'P='+__self.__processor, 
           'BU='+__self.__bufRef, 
           'BR='+__self.__byteReqd, 
           'NF='+__self.__numberFormat, 
           'SB='+__self.__signBits, 
           'O='+__self.__offset, 
           'DSN='+__self.__directSeqNo, 
           'IB='+__self.__intervalBytes,
           'LEN='+str(len(__self.__data)))

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

   return {
      "account_key": account_key,
      "account_name": account_name,
      'container_name': container_name,
      'default_folder_name': default_folder_name,
      'save_files': save_files,
      'socket_timeout': socket_timeout,
      'debug_file': debug_file
   }   

def storeFiles(content, folder, fileNames, start_time, summary, buffers):
   configuration = getConfiguration()

   if (folder == None):
      folder = configuration['container_name']
   
   print('Account Name: ', configuration['account_name'])
   print('Container Name: ', configuration['container_name'])

   block_blob_service = BlockBlobService(account_name=configuration['account_name'], 
                                         account_key=configuration['account_key'], 
                                         socket_timeout=configuration['socket_timeout'])

   block_blob_service.create_container(configuration['container_name']) 

   block_blob_service.set_container_acl(configuration['container_name'], public_access=PublicAccess.Container)

   if configuration['save_files'] == 'true':
      for iBuffer, buffer in enumerate(buffers):    
         print(fileNames[iBuffer])
         block_blob_service.create_blob_from_stream(configuration['container_name'], 
                                                    folder + '/' + start_time + '/' +
                                                    fileNames[iBuffer] + '.gz', 
                                                    io.BytesIO(zlib.compress(buffer)))
   
   block_blob_service.create_blob_from_stream(configuration['container_name'], folder + '/' + start_time + '/output.csv.gz',
                                              io.BytesIO(zlib.compress(content.encode())))
   
   block_blob_service.create_blob_from_stream(configuration['container_name'],  folder + '/' + start_time + '/summary.json',
                                              io.BytesIO(summary.encode()))

   print('Upload Completed')
   app.logger.info('Upload Completed')
   return

@views.route("/")
def home():
    return render_template("main.html")

@views.route("/list", methods=["GET"])
def list():
   configuration = getConfiguration()

   block_blob_service = BlockBlobService(account_name=configuration['account_name'], 
                                         account_key=configuration['account_key'], 
                                         socket_timeout=configuration['socket_timeout'])

   block_blob_service.create_container(configuration['container_name']) 

   block_blob_service.set_container_acl(configuration['container_name'], public_access=PublicAccess.Container)
   output = []

   try:
      blobs = block_blob_service.list_blobs(configuration['container_name'])
   except:
      return json.dumps(output)

   for blob in blobs:
      if (re.match("(.*)\/(.*)\/(summary\.json)$", blob.name,  re.DOTALL)):
          data = re.search("(.*)\/(.*)\/(summary\.json)$", blob.name, re.DOTALL)
          output.append({
             "summary_file": blob.name,
             "folder": data.group(1),
             "start_time": data.group(2)
          })
    
   return json.dumps(output, sort_keys=True)


@views.route("/retrieve", methods=["GET"])
def retrieve():
   timestamp = request.args.get('timestamp')
   name = request.args.get('name')

   print(timestamp, name)

   configuration = getConfiguration()

   block_blob_service = BlockBlobService(account_name=configuration['account_name'], 
                                         account_key=configuration['account_key'], 
                                         socket_timeout=configuration['socket_timeout'])

   stream = io.BytesIO()

   block_blob_service.get_blob_to_stream(container_name=configuration['container_name'], 
                                   blob_name=name + '/' + timestamp + '/output.csv.gz', stream=stream)

   content = zlib.decompress(stream.getbuffer())

   return content

@views.route("/upload", methods=["POST"])
def upload():
   configuration = getConfiguration()

   f = open(configuration.debug_file, 'a') 
   f.write('started\n')

   matrix = []
   titles = []
   types = []
   sizes = []
   buffers = []
   fileNames = []

   folder = "unknown"

   start_time = 0 
   stop_time = 0 

   processedFiles = []
   uploadedFiles = request.files

   for uploadFile in uploadedFiles:

      input_zip = ZipFile(request.files.get(uploadFile))
         
      for name in input_zip.namelist():
         f.write('saving: ' + name + '\n')
 
         if (not name.endswith('.raw')):
            continue

         if (name.startswith('GPS.time.sec_BUSDAQ')):
            parts = re.search("_([0-9]*)?(\.raw)", name, re.DOTALL)
            folder = parts.group(1)

         processedFiles.append(name)

         app.logger.info('Processing', name)

         content = input_zip.read(name)
       
         parser = FamosParser()
         parser.parse(content)

         data = parser.getData()

         if len(data) > 0:
            sizes.append(len(data))
            matrix.append(data)
            types.append(parser.getType())
            titles.append(parser.getTitle())
            buffers.append(parser.getBuffer())
            fileNames.append(name)

            if (parser.getType() == '52'):
               start_time = re.sub(r'\..*', '', data[0])
               stop_time = re.sub(r'\..*', '', data[len(data) - 1])
        
   minSize = min(sizes)
   maxSize = max(sizes)

   sampleSize = int(maxSize/minSize)
   csvfile = io.StringIO()
   famosWriter = csv.writer(csvfile, delimiter=',',
                                     quotechar='"', quoting=csv.QUOTE_MINIMAL)

   famosWriter.writerow(titles)

   iRow = 0
   iSample = 0

   while iRow < minSize:
      iColumn = 0
      row = []
      while iColumn < len(matrix): 
         if (sizes[iColumn] == minSize):
            row.append(matrix[iColumn][iRow])
         else:
            row.append(matrix[iColumn][iSample])
    
         iColumn += 1

      iRow += 1
      iSample = iSample + sampleSize if (iSample + sampleSize) < minSize else iRow

      famosWriter.writerow(row)

   content = csvfile.getvalue()
   summary = json.dumps({"start": start_time, "stop": stop_time, 
                          "titles": titles, "types":types,
                          "files": processedFiles}, sort_keys=True)
   f.write('started thread\n')
   f.close() 
   thread = threading.Thread(name='storefiles', target=storeFiles, args=(content, folder, fileNames, start_time, summary, buffers))
   thread.setDaemon(True)
   thread.start()

   csvfile.close()
   
   return content
