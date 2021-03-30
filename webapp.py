from flask import Flask, Response, request, render_template, session
from flask import *
import cv2 as cv
import pyrebase
import datetime
import os
import sys
import numpy as np
import threading
import time as tm
from gpiozero import CPUTemperature

cap = cv.VideoCapture(0)
whT = 320
confThreshold = 0.5
nmsThreshold = 0.2
cameraID = 'test'
#### BACKGROUND_SUBTRACTION
fgbg = cv.createBackgroundSubtractorMOG2(500, 750, True)

#### LOAD MODEL
## Coco Names
classesFile = "./Model/coco.names"
classNames = []
with open(classesFile, 'rt') as f:
    classNames = f.read().rstrip('\n').split('\n')
print(classNames)
## Model Files
modelConfiguration = "./Model/custom-yolov4-tiny.cfg"
modelWeights = "./Model/custom-yolov4-tiny.weights"
net = cv.dnn.readNetFromDarknet(modelConfiguration, modelWeights)
net.setPreferableBackend(cv.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv.dnn.DNN_TARGET_CPU)
#### DONE LOAD MODEL

#### LOAD FIREBASE
config = {
  "apiKey": "AIzaSyDrpM53XC9UDHXhSoCP1jdXhOv8lMwMhZA",
  "authDomain": "od-android-f06ec.firebaseapp.com",
  "databaseURL": "https://od-android-f06ec-default-rtdb.firebaseio.com",
  "storageBucket": "od-android-f06ec.appspot.com"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()
storage = firebase.storage()
auth = firebase.auth()
#### DONE LOAD FIREBASE

class cameraFunction:

    def __init__(self):
        self.security = db.child("cameras").child(cameraID).child("security").get().val()
        self.temp = CPUTemperature().temperature
        self.stopimmediately = 0
        self.stopRecording = False

    def addLog(self, data):
        date_set = datetime.datetime.now().strftime("%d-%m-%Y")
        time_set = datetime.datetime.now().strftime("%H:%M:%S")
        db.child("cameras").child(cameraID).child("logs").child(date_set).child(time_set).set(data)

    def videoRecording(self):
        print("Start recording")
        #Time define
        time_start = datetime.datetime.now()
        time_end_default = time_start + datetime.timedelta(minutes=10)
        time_start_file_name = time_start.strftime("%H:%M:%S")
        time_end_default_file_name = time_end_default.strftime("%H:%M:%S")
        #Try open folder if not exist create it
        date_now = time_start.strftime("%d-%m-%y")
        path_name = './static/videos/' + date_now 
        if not os.path.exists(path_name):
            os.makedirs(path_name)
            # Define the codec and create VideoWriter object
        first_name = path_name + "/" + time_start_file_name + ' ' + time_end_default_file_name + ' default.mp4'
        fourcc = cv.VideoWriter_fourcc(*'avc1')
        out = cv.VideoWriter(first_name, fourcc, 20.0, (640, 480))
        while cap.isOpened() and datetime.datetime.now() < time_end_default and self.stopRecording == False:
            ret, frame = cap.read()
            if ret:
                frame = cv.putText(frame, datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S"),(10, frame.shape[0] - 10), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 1)       
                #frame = cv.flip(frame, 0)
                out.write(frame)
                #cv.imshow('frame', frame)
                
        self.stopRecording = False
        threading.Thread(target=self.videoRecording).start()
        # Release everything if job is finished
        time_end = datetime.datetime.now()
        time_end_file_name = time_end.strftime("%H:%M:%S")
        last_name = path_name + "/" + time_start_file_name + ' ' + time_end_file_name + '.mp4'
        out.release()
        os.rename(first_name, last_name)
        #########Write file name in txt########
        file = "./static/videos/"+date_now+"/videos.txt"
        f = open(file, 'a')
        f.write(time_start_file_name + ' ' + time_end_file_name+'.mp4'+'\n')
        f.close()
        print("Save video sucess")


    def takePic(self, case, func):
        ret, frame = cap.read()
        ###set time###    
        now = datetime.datetime.now()
        time = now.strftime("%H:%M:%S")
        date_now = now.strftime("%d-%m-%y")
        path_name = './static/images/' + date_now 
        if not os.path.exists(path_name):
            os.makedirs(path_name)
        img_name = path_name + "/" + time + ".jpg"
        ###add time in image###
        frame = cv.putText(frame, datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S"),(10, frame.shape[0] - 10), cv
            .FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 1)  
        cv.imwrite(img_name, frame)
        print("Write image complete")
        ######SEND PHOTO TO DATA BASE######
        print("Send image to serve")
        storage.child("images/" + cameraID + "/" + date_now + "/" + time +".jpg").put(img_name)
        img_url = storage.child("images/" + cameraID + "/" + date_now + "/" + time +".jpg").get_url(None)

        post = {
            'case': case,
            'func': func,
            'url': img_url
        }
        
        self.addLog(post)
        file = "./static/images/"+date_now+"/images.txt"
        f = open(file, 'a')
        f.write(time+'.jpg'+'\n')
        f.close()
        print("Send image done")
        
    def personDectec(self):
        if self.stopimmediately == 1:
            self.stopRecording = True
            Thr = threading.Thread(target=self.takePic, args=('camera found', 'have person at home'))
            Thr.start()
            db.child("cameras").child(cameraID).update({"security":False})
            print("Some one at home")

    def findPerson(self,outputs, img):
        #hT, wT, cT = img.shape
        #bbox = []
        #classIds = []
        #confs = []
        for output in outputs:
            for det in output:
                scores = det[5:]
                classId = np.argmax(scores)
                confidence = scores[classId]
                if confidence > confThreshold:
                    self.stopimmediately += 1
                    Thr = threading.Thread(target=self.personDectec)
                    Thr.start()
                    return
            
                    #w, h = int(det[2] * wT), int(det[3] * hT)
                    #x, y = int((det[0] * wT) - w / 2), int((det[1] * hT) - h / 2)
                    #bbox.append([x, y, w, h])
                    #classIds.append(classId)
                    #confs.append(float(confidence))

        #indices = cv.dnn.NMSBoxes(bbox, confs, confThreshold, nmsThreshold)

        #for i in indices:
            #i = i[0]
            #box = bbox[i]
            #x, y, w, h = box[0], box[1], box[2], box[3]
            #print(x,y,w,h)
            #cv.rectangle(img, (x, y), (x + w, y + h), (255, 0, 255), 2)
            #cv.putText(img, f'{classNames[classIds[i]].upper()} {int(confs[i] * 100)}%', (x, y - 10), cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
            #print(classNames[classIds[i]].upper())


    def objDection(self):
        now_plus_15s = datetime.datetime.now() + datetime.timedelta(seconds=15)
        while datetime.datetime.now() < now_plus_15s:
            success, img = cap.read()

            blob = cv.dnn.blobFromImage(img, 1 / 255, (whT, whT), [0, 0, 0], 1, crop=False)
            net.setInput(blob)
            layersNames = net.getLayerNames()
            outputNames = [(layersNames[i[0] - 1]) for i in net.getUnconnectedOutLayers()]
            outputs = net.forward(outputNames)

            self.findPerson(outputs, img)
            #cv.imshow('Image', img)
            #cv.waitKey(1)
        threading.Thread(target=self.background_subtraction).start()
            
    def stream_temple(self):
        self.temp = CPUTemperature().temperature
        if self.temp < 70:
            tm.sleep(10)
        else:
            db.child("cameras").child(cameraID).update({"security":False})
            data1 = {
                'case': "Control by camera",
                'func': "Turn off security to coolboot cpu"
            }
            self.addLog(data1)
            tm.sleep(10)
            db.child("cameras").child(cameraID).update({"security":True})
            data2 = {
                'case': "Control by camera",
                'FutureWarningnc': "Turn on security, coolboot complete"
            }
            self.addLog(data2)
            
    def background_subtraction(self):
        firsttime = True
        while self.security:
            ret, frame = cap.read()
            if not ret:
                continue
            
            resizedFrame = cv.resize(frame, (0, 0), fx=0.5, fy=0.5)
            fgmask = fgbg.apply(resizedFrame)
            count = np.count_nonzero(fgmask)
            if count > 9000 and firsttime == False:
                threading.Thread(target=self.takePic, args=('Camera', 'something movement')).start()
                threading.Thread(target=self.objDection).start()
                break

            cv.imshow('Frame', resizedFrame)
            cv.imshow('Mask', fgmask)
            cv.waitKey(1)
            firsttime = False
        cv.destroyAllWindows()

    
    def stream_handler(self,message):
        self.security  = db.child("cameras").child(cameraID).child("security").get().val()
        print(self.security)
        if self.security == True:
            self.stopimmediately = 0
            Thr = threading.Thread(target=self.background_subtraction)
            Thr.start()


    def whenDataChage(self):
        print('data stream')
        my_stream = db.child("cameras").child(cameraID).child("security").stream(self.stream_handler)
        
        



#####################################WEB################################
app = Flask(__name__)
app.secret_key = "xyz"
app.debug = False

@app.route('/', )
def index():
    if 'user' in session:
        return redirect(url_for('home'))
    else:
        return render_template('login.html')

@app.route('/', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == "POST":
        email = request.form["username"]
        password = request.form["password"]
        print(email, password)
        try:
            auth.sign_in_with_email_and_password(email, password)
            user = {'email':email, 'password':password}
            session['user'] = user
        except:
            error = "Incorrect Password!"
            return render_template('login.html', error=error)
        return redirect(url_for('home'))


@app.route('/home')
def home():
    if 'user' in session:
        return render_template('home.html')
    else:
        return redirect('/')

def gen():
    while cap.isOpened():
        success, frame = cap.read()
        if success:
            frame = cv.putText(frame, datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S"),(10, frame.shape[0] - 10), cv
                               .FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 1)  
            ret, buffer = cv.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
@app.route('/changepassword', methods=['GET', 'POST'])
def changepassword():
    msg = ''
    if request.method == "POST":
        try:
            email = request.form["email"]
            auth.send_password_reset_email(email)
            return redirect('/')
        except:
            msg = "Can't"
    return render_template('changepassword.html',msg=msg)
        
@app.route('/images', methods=['GET','POST'])
def images():
    if request.method == 'POST':
        datechoice = request.form["date"]
        imglist = []
        path = "./static/images/"+datechoice
        file = path + "/images.txt"
        ######value combobox####
        datelist = []
        now = datetime.datetime.now()
        for i in range(7):
            time_new = now - datetime.timedelta(days=i)
            date_new = time_new.strftime("%d-%m-%y")
            datelist.append(date_new)
        if not os.path.exists(path):
            imglist = []
        else:
            f = open(file, 'r')
            for x in f:
                imglist.append(['.'+path + '/' + x, x])
            f.close()
        return render_template('images.html',imglist=imglist, datechoice=datechoice, datelist=datelist)
    else:
        now = datetime.datetime.now()
        date_now = now.strftime("%d-%m-%y")
        imglist = []
        path = "./static/images/"+date_now
        file = path + "/images.txt"
        ######value combobox####
        datelist = []
        now = datetime.datetime.now()
        for i in range(7):
            time_new = now - datetime.timedelta(days=i)
            date_new = time_new.strftime("%d-%m-%y")
            datelist.append(date_new)
            
        if not os.path.exists(path):
            imglist = []
        else:
            f = open(file, 'r')
            for x in f:
                imglist.append(['.'+path + '/' + x, x])
            f.close()
        return render_template('images.html',imglist=imglist, datelist=datelist)


    

@app.route('/videos', methods=['GET','POST'])
def videos():
    if request.method == 'POST':
        datechoice = request.form["date"]
        vdlist = []
        path = "./static/videos/"+datechoice
        file = path + "/videos.txt"
        ######value combobox####
        datelist = []
        now = datetime.datetime.now()
        for i in range(7):
            time_new = now - datetime.timedelta(days=i)
            date_new = time_new.strftime("%d-%m-%y")
            datelist.append(date_new)
        if not os.path.exists(path):
            vdlist = []
        else:
            f = open(file, 'r')
            for x in f:
                vdlist.append(['.'+path + '/' + x, x])
            f.close()
        return render_template('videos.html',vdlist=vdlist, datelist=datelist)
    else:
        now = datetime.datetime.now()
        date_now = now.strftime("%d-%m-%y")
        vdlist = []
        path = "./static/videos/"+date_now
        file = path + "/videos.txt"
        ######value combobox####
        datelist = []
        now = datetime.datetime.now()
        for i in range(7):
            time_new = now - datetime.timedelta(days=i)
            date_new = time_new.strftime("%d-%m-%y")
            datelist.append(date_new)
        try:
            f = open(file, 'r')
            for x in f:
                vdlist.append(['.'+path + '/' + x, x])
            f.close()
        except:
            vdlist = []
        return render_template('videos.html',vdlist=vdlist, datelist=datelist)
        
            
@app.route('/video_feed')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')
            
@app.route('/takePhoto')
def takePhoto():
    ret, frame = cap.read()
    ###set time###    
    now = datetime.datetime.now()
    time = now.strftime("%H:%M:%S")
    date_now = now.strftime("%d-%m-%y")
    path_name = './static/images/' + date_now 
    if not os.path.exists(path_name):
        os.makedirs(path_name)
    img_name = path_name + "/" + time + ".jpg"
    ###add time in image###
    frame = cv.putText(frame, datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S"),(10, frame.shape[0] - 10), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 1)  
    cv.imwrite(img_name, frame)
    print("Write image complete")
    ######SEND PHOTO TO DATA BASE######
    print("Send image to serve")
    storage.child("images/" + cameraID + "/" + date_now + "/" + time +".jpg").put(img_name)
    img_url = storage.child("images/" + cameraID + "/" + date_now + "/" + time +".jpg").get_url(None)

    data = {
        'case': 'Security alarm',
        'func': 'Some person at home',
        'image': img_url
    }
    #addLog(data)
    file = "./static/images/"+date_now+"/images.txt"
    f = open(file, 'a')
    f.write(time+'.jpg'+'\n')
    f.close()
    return redirect('/home')
    
def runServe():
    app.run(host='192.168.4.144', port=5000)
    
if __name__ == '__main__':
    threading.Thread(target=runServe).start()
    func = cameraFunction()
    threading.Thread(target=func.whenDataChage).start()
    threading.Thread(target=func.videoRecording).start()
