from flask import Flask, render_template, request
from . import app
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
from struct import unpack, pack
from azure.storage.blob import BlockBlobService, PublicAccess

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

     # print('Size:', id, len(content), len(data), len(packed.group(0)))

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
        v = b'' 
        for b in values:
           if (p == 4 and __self.__numberFormat in __self.__longFormats):
              if __self.__numberFormat == '6':
                 r = struct.unpack("i", v)[0] 
                 if (__self.__type in __self.__geoTypes):  
                    r = r/10000000
                 __self.__data.append('%.7f' % (r))
              elif __self.__numberFormat == '7':
                 r = struct.unpack("f", v)[0] 
                 __self.__data.append('%.7f' % (r))

              __self.__count += 1         
              p = 0
              v = b'' 

           elif (p == 2 and __self.__numberFormat in __self.__shortFormats):
              r = struct.unpack(">h", v)[0] 
              r = r/100000
              __self.__data.append('%.7f' % (r))
              __self.__count += 1         
              p = 0
              v = b'' 

           v += b.to_bytes(1, byteorder='big') 
           p = p + 1

     else:
        if (re.match(b"[^ \t].*$", content, re.DOTALL)):
           m = re.search(b"[^ \t]+(.*)$", content, re.DOTALL)
           content = m.group(1)

        process = re.search(b"(.*?);(.*)", content, re.DOTALL)
        __self.process(process.group(2))  
  
  def parse(__self, file):
     __self.__buffer = file.read()
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

def storeFiles(csvFile, fileNames, buffers):
   account_key = None
   account_name = None
   vehicle_name = None
   container_name = None
 
   try:
      import famos_file_manager.configuration as config

      account_name = config.ACCOUNT_NAME
      container_name = config.CONTAINER_NAME
      vehicle_name = config.VEHICLE_NAME

   except ImportError:
      pass

   try:
      import famos_file_manager.keys as keys
      account_key = keys.ACCOUNT_KEY

   except ImportError:
      pass

   print('Account Name: ', account_name)
   print('Container Name: ', container_name)

   block_blob_service = BlockBlobService(account_name=account_name, account_key=account_key)

   block_blob_service.create_container(container_name) 

   block_blob_service.set_container_acl(container_name, public_access=PublicAccess.Container)

   for iBuffer, buffer in enumerate(buffers):    
      print(fileNames[iBuffer])

   return

@app.route("/")
def home():
    return render_template("main.html")

@app.route("/upload", methods=["POST"])
def upload():
    app.logger.info('Upload request received')
    uploadedFiles = request.files
    print(uploadedFiles)
    
    matrix = []
    titles = []
    types = []
    sizes = []
    buffers = []
    fileNames = []

    for uploadFile in uploadedFiles:
        app.logger.info('Processing', uploadFile)
 
        file = request.files.get(uploadFile)
        print(file)
        
        parser = FamosParser()
        parser.parse(file)

        data = parser.getData()

        if len(data) > 0:
            sizes.append(len(data))
            matrix.append(data)
            types.append(parser.getType())
            titles.append(parser.getTitle())
            buffers.append(parser.getBuffer())
            fileNames.append(uploadFile)
        
        parser.summary()

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

    contents = csvfile.getvalue()

    storeFiles(contents, fileNames, buffers)

    csvfile.close()

    return contents
