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
import uuid
import azure.storage.blob
import random
import string

from struct import unpack, pack
from azure.storage.common import CloudStorageAccount
from azure.storage.blob.models import BlobBlock

views = Blueprint('views', __name__, template_folder='templates')

class FamosParser:
   def __init__(__self, file):
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
     __self.__interval = 100
     __self.__title = '' 
     __self.__type = None 
     __self.__count = 0  
     __self.__limit = -1
     __self.__sample = 1
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
         p = 0
         v = []

         if (__self.__numberFormat in __self.__longFormats):
            v = [b'0', b'0', b'0', b'0']
         else:
            v = [b'0', b'0'] 

         counter = 0 

         for b in values:     
            if (p == 4 and __self.__numberFormat in __self.__longFormats): 
               if __self.__numberFormat == '6':
                  r = struct.unpack("i", b''.join(v))[0] 
                  if (__self.__type in __self.__geoTypes):  
                     r = r/10000000
                  
                  __self.__data.append(r)
 
               elif __self.__numberFormat == '7':
                  r = struct.unpack("f", b''.join(v))[0] 
                  __self.__data.append(r)
                
               __self.__count += 1   

               p = 0

            elif (p == 2 and __self.__numberFormat in __self.__shortFormats):
               if (counter % __self.__sample == 0 or counter == 0):   
                  r = struct.unpack(">h",  b''.join(v))[0] 
                  r = r/100000
                  __self.__data.append(r)
                  __self.__count += 1 

               p = 0    
               
            if (__self.__limit != -1 and len(__self.__data) >= __self.__limit):
               print('Count reached: ' + __self.__type + " - " + id.decode('utf-8') + ":" + str(__self.__limit) + ":" +  str(len(__self.__data)))
               return

            counter += 1
            v[p] = b.to_bytes(1, byteorder='big') 
            p += 1

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

      output = 'TY={TY}, FF={FF}, KL={KL}, P={P}, BU={BU}, BR={BR}, NF={NF}, SB={SB}, O={O}, DSN={DSN} IB={IB}, LEN={LEN}, SP={SP}'.format(
        TY=__self.__type, FF=__self.__fileFormat, KL=__self.__keyLength, P=__self.__processor, BU=__self.__bufRef, BR=__self.__byteReqd,
        NF=__self.__numberFormat, SB=__self.__signBits, O=__self.__offset, DSN=__self.__directSeqNo, IB=__self.__intervalBytes,
        LEN=str(len(__self.__data)), SP=str(__self.__sample))

      __self.log(output)

   def setLimit(__self, limit):
      __self.__limit = limit

   def setSample(__self, sample):
      __self.__sample = sample

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
   zip_file_name = None


   try:
      import famos_file_manager.configuration as config

      account_name = config.ACCOUNT_NAME
      container_name = config.CONTAINER_NAME
      default_folder_name = config.DEFAULT_FOLDER_NAME
      save_files = config.SAVE_FILES
      socket_timeout = config.SOCKET_TIMEOUT
      debug_file = config.DEBUG_FILE
      staging_dir = config.STAGING_DIR
      zip_file_name = config.ZIP_FILE_NAME

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
   staging_dir = environ.get('STAGING_DIR', staging_dir)
   zip_file_name = environ.get('ZIP_FILE_NAME', zip_file_name)

   return {
      "account_key": account_key,
      "account_name": account_name,
      'container_name': container_name,
      'default_folder_name': default_folder_name,
      'save_files': save_files,
      'socket_timeout': socket_timeout,
      'debug_file': debug_file,
      'staging_dir': staging_dir
   }   

def store(f, configuration, file_name, guid):
   log(f, 'Account Name: ' + configuration['account_name'])
   log(f, 'Container Name: ' + configuration['container_name'])
   
   input_zip = ZipFile(file_name, 'r')

   log(f, 'Processing (Zip) : ' + file_name)

   folder = 'unknown'
   timestamp = 'unknown'
   summary_types = ['0', '11', '13', '14', '39', '48', '52']
   
   titles = []
   types = []
   matrix = []
   sizes = []
   processed_files = []

   for name in input_zip.namelist():     
      log(f, 'Processing: ' + name)

      if (name.endswith('.raw')):
         processed_files.append(name)

         parser = FamosParser(f)
         
         if (name in ['X Axis Acceleration.raw', 'Y Axis Acceleration.raw', 'Z Axis Acceleration.raw']):
            parser.setSample(200)
 
         if (name in 'Error_Frames_1.raw'):                
            parser.setSample(4)

         content = input_zip.read(name)
         parser.parse(content)
         parser.summary()

         titles.append(parser.getTitle())
         types.append(parser.getType())
         data = parser.getData()
 
         if (name.startswith('GPS.time.sec_BUSDAQ')):
            parts = re.search("_([0-9]*)?(\.raw)", name, re.DOTALL)
            folder = parts.group(1)
         
         if (parser.getType() == '52'):
            timestamp = re.sub(r'\..*', '', '%.7f' % data[0])
         
         if (parser.getType() in summary_types and not parser.getTitle().startswith('Error')):
            matrix.append(data)
            types.append(parser.getType())
            sizes.append(len(data))          
   
   log(f, 'Compiling File : ' + file_name)

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

   log(f, 'File Compiled : ' + file_name)

   summary = json.dumps({"timestamp": timestamp, 
                          "titles": titles, 
                          "types": types,
                          "files": processed_files,
                          "logs": guid + ".zip"})

   csvfile.close()
   input_zip.close()

   account = CloudStorageAccount(account_name=configuration['account_name'], 
                                 account_key=configuration['account_key'])
 
   service = account.create_block_blob_service()

   service.create_container(configuration['container_name']) 
   
   log(f, 'Storing Content')

   service.create_blob_from_stream(configuration['container_name'], folder + '/' + timestamp + '/output.csv.gz',
                                             io.BytesIO(zlib.compress(content.encode())))

       
   log(f, 'Saving Summary')

   service.create_blob_from_stream(configuration['container_name'],  folder + '/' + timestamp + '/summary.json',
                                   io.BytesIO(summary.encode()))

                                                  
   log(f, 'Stored: ' + file_name)

   os.remove(file_name)

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

      account = CloudStorageAccount(account_name=configuration['account_name'], 
                                    account_key=configuration['account_key'])
 
      service = account.create_block_blob_service()

      service.create_container(configuration['container_name']) 

      output = []

      blobs = service.list_blobs(configuration['container_name'])

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

   account = CloudStorageAccount(account_name=configuration['account_name'], 
                                 account_key=configuration['account_key'])
 
   service = account.create_block_blob_service()

   stream = io.BytesIO()

   service.get_blob_to_stream(container_name=configuration['container_name'], 
                                   blob_name=name + '/' + timestamp + '/output.csv.gz', stream=stream)

   content = zlib.decompress(stream.getbuffer())

   log(f, 'Retrieved - ' + name + '/' + timestamp)

   return content

@views.route("/commit", methods=["GET"])
def commit():
   try:
      guid = request.values.get('guid')
      folder = request.values.get('folder')

      blob_name = folder + '/' + guid + ".zip"

      configuration = getConfiguration()

      f = open(configuration['debug_file'], 'a')

      log(f, 'Committing: ' +  blob_name)
      
      account = CloudStorageAccount(account_name=configuration['account_name'], 
                                    account_key=configuration['account_key'])
   
      service = account.create_block_blob_service()

      blockslist = service.get_block_list(configuration['container_name'], blob_name, None, 'uncommitted')
      blocks = blockslist.uncommitted_blocks
      
      service.put_block_list(configuration['container_name'], blob_name, blocks)
      
      log(f, 'Committed: ' +  blob_name)
 
      output = {
         'status' : 'ok'
      }
 
   except Exception as e:
      log(f, str(e))
      f.close()
      output.append({
         "status" : 'fail',
         "error" : str(e)
      })
   
   return json.dumps(output, sort_keys=True)
   
@views.route("/process", methods=["GET"])
def process():
   output = []
   
   try:
      configuration = getConfiguration()
      
      f = open(configuration['debug_file'], 'a')
   
      file_name = request.args.get('file_name')
      guid = request.args.get('guid')

      result = store(f, configuration, file_name, guid)

      return result

   except Exception as e:
      log(f, str(e))
      f.close()
      output.append({
         "status" : 'fail',
         "error" : str(e)
      })
      
   return json.dumps(output, sort_keys=True)

@views.route("/upload", methods=["POST"])
def upload():
   configuration = getConfiguration()

   temp_file_name = request.values.get('file_name')
   guid = request.values.get('guid')
   folder = request.values.get('folder')
   chunk = request.values.get('chunk')

   blob_name = folder + '/' + guid + ".zip"

   f = open(configuration['debug_file'], 'a')
   
   uploadedFiles = request.files
   
   fileContent = None

   for uploadFile in uploadedFiles:
      fileContent = request.files.get(uploadFile)
   
   output = []

   account = CloudStorageAccount(account_name=configuration['account_name'], 
                                 account_key=configuration['account_key'])
 
   service = account.create_block_blob_service()

   buffer = fileContent.read()

   if (temp_file_name == ''):
      with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            temp_file_name = tmpfile.name
    
            log(f, 'Temp File Allocated allocated - ' + temp_file_name)

            with open(temp_file_name, 'ab') as temp:

               temp.write(buffer)
               temp.close()

            guid = str(uuid.uuid4())
            log(f, 'UUID allocated - ' + guid)

            blob_name = folder + '/' + guid + ".zip"
            log(f, 'blob_name - ' + blob_name)

            service.create_container(configuration['container_name']) 
        
            log(f, "Created Container - [" +  (configuration['container_name']) + "] - " + blob_name)
            
   else:
      with open(temp_file_name, 'ab') as temp:

         temp.write(buffer)
         temp.close()
  
   service.put_block(configuration['container_name'], blob_name, buffer, chunk.zfill(32))

   output.append({
      "file_name" : temp_file_name,
      "guid" : guid,
      "folder" : folder,
      "chunk" : chunk
   })

   f.close()
   
   return  json.dumps(output, sort_keys=True)
