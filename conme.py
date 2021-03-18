from flask import Flask, Response, request, render_template
import cv2 as cv
import time as tm
import datetime
import numpy as np
import threading
import pyrebase
import os
from gpiozero import CPUTemperature


cap = cv.VideoCapture(0)
whT = 320
confThreshold = 0.5
nmsThreshold = 0.2

cameraID = 'test'

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
  "apiKey": "mznK8xnRlWp5jnWzhejK5z1DPprjZOKCRhJ9rUmJ",
  "authDomain": "od-android-f06ec.firebaseapp.com",
  "databaseURL": "https://od-android-f06ec-default-rtdb.firebaseio.com",
  "storageBucket": "od-android-f06ec.appspot.com"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()
storage = firebase.storage()

#### DONE LOAD FIREBASE

class cameraFunction:

    def __init__(self):
        self.security = db.child("cameras").child(cameraID).child("security").get().val()
        self.temp = CPUTemperature().temperature
        self.stopimmediately = 0

    def addLog(self, data):
        date_set = datetime.datetime.now().strftime("%d-%m-%Y")
        time_set = datetime.datetime.now().strftime("%X")
        db.child("cameras").child(cameraID).child("logs").child(date_set).child(time_set).set(data)

    def videoRecording(self):
        if self.security == False:
            print("Start recording")
            #Time define
            time_start = datetime.datetime.now()
            time_end_default = time_start + datetime.timedelta(minutes=10)
            time_start_file_name = time_start.strftime("%X")
            time_end_default_file_name = time_end_default.strftime("%X")
            #Try open folder if not exist create it
            date_now = time_start.strftime("%d-%m-%y")
            path_name = './videos/' + date_now 
            if not os.path.exists(path_name):
                os.makedirs(path_name)
            # Define the codec and create VideoWriter object
            first_name = path_name + "/" + time_start_file_name + ' ' + time_end_default_file_name + ' default.avi'
            fourcc = cv.VideoWriter_fourcc(*'XVID')
            out = cv.VideoWriter(first_name, fourcc, 20.0, (640, 480))
            while cap.isOpened() and datetime.datetime.now() < time_end_default and self.security == False:
                ret, frame = cap.read()
                font = cv.FONT_HERSHEY_SCRIPT_COMPLEX
                dt = str(datetime.datetime.now().strftime("%X"))
                frame = cv.putText(frame, dt, (10, 450), font, 1, (210, 155, 155), 4, cv.LINE_8)
                #frame = cv.flip(frame, 0)
                # write the flipped frame
                out.write(frame)
                #cv.imshow('frame', frame)
            # Release everything if job is finished
            time_end = datetime.datetime.now()
            time_end_file_name = time_end.strftime("%X")
            last_name = path_name + "/" + time_start_file_name + ' ' + time_end_file_name + '.avi'
            out.release()
            os.rename(first_name, last_name)
            print("Save video sucess")


    def takePic(self):
        ret, frame = cap.read()
        ###set time###    
        now = datetime.datetime.now()
        time = now.strftime("%X")
        date_now = now.strftime("%d-%m-%y")
        path_name = './images/' + date_now 
        if not os.path.exists(path_name):
            os.makedirs(path_name)
        img_name = path_name + "/" + time + ".jpg"
        ###add time in image###
        font = cv.FONT_HERSHEY_SCRIPT_COMPLEX
        frame = cv.putText(frame, time,(10, 450),font, 1,(210, 155, 155),4, cv.LINE_8)
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
        self.addLog(data)
        print("Send image done")
        
    def personDectec(self):
        if self.stopimmediately == 1:
            Thr = threading.Thread(target=self.takePic)
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
        print("Run OD")
        while self.security:
            success, img = cap.read()

            blob = cv.dnn.blobFromImage(img, 1 / 255, (whT, whT), [0, 0, 0], 1, crop=False)
            net.setInput(blob)
            layersNames = net.getLayerNames()
            outputNames = [(layersNames[i[0] - 1]) for i in net.getUnconnectedOutLayers()]
            outputs = net.forward(outputNames)

            self.findPerson(outputs, img)
            #cv.imshow('Image', img)
            #cv.waitKey(1)
            
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

    def stream_handler(self,message):
        self.security  = db.child("cameras").child(cameraID).child("security").get().val()
        print(self.security)
        if self.security == True:
            self.stopimmediately = 0
            Thr = threading.Thread(target=self.objDection)
            Thr.start()
        else:
            Thr = threading.Thread(target=self.videoRecording)
            Thr.start()

    def whenDataChage(self):
        print('data stream')
        my_stream = db.child("cameras").child(cameraID).child("security").stream(self.stream_handler)
        
        


#####################################WEB################################
app = Flask(__name__)
@app.route('/')
def index():
    return render_template('index.html')

def gen():
    while cap.isOpened():
        success, frame = cap.read()
        if success:
            ret, buffer = cv.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            

@app.route('/video_feed')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')
       


def runserve():
    app.run(host='192.168.4.144', debug=False)
    
###########################MAINMAIN################################
if __name__ == "__main__":
    func = cameraFunction()
    
    t1 = threading.Thread(target=func.whenDataChage)
    t2 = threading.Thread(target=runserve)
    t1.start()
    t2.start()
    
