from flask import Flask, render_template, request
from . import app

@app.route("/")
def home():
    return render_template("main.html")

@app.route("/upload", methods=["POST"])
def upload():
    print('Uploading Files')
    uploadedFiles = request.files
    print(uploadedFiles)
    for uploadFile in uploadedFiles:
        print(uploadFile)
 
        file = request.files.get(uploadFile)
        data = file.read()
        print(data)
        print(file)
    
    return "uploading..."
