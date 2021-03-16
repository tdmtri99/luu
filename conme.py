import time
import cv2 as cv
import numpy as np
import threading
import pyrebase
import datetime

cap = cv.VideoCapture(0)
whT = 320
confThreshold = 0.5
nmsThreshold = 0.2

cameraID = 'test'

#### LOAD MODEL
## Coco Names
classesFile = "coco.names"
classNames = []
with open(classesFile, 'rt') as f:
    classNames = f.read().rstrip('\n').split('\n')
print(classNames)
## Model Files
modelConfiguration = "yolov4-tiny.cfg"
modelWeights = "yolov4-tiny.weights"
net = cv.dnn.readNetFromDarknet(modelConfiguration, modelWeights)
net.setPreferableBackend(cv.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv.dnn.DNN_TARGET_CPU)
#### DONE LOAD MODEL

#### LOAD FIREBASE

config = {
  "apiKey": "apiKey",
  "authDomain": "od-android-f06ec.firebaseapp.com",
  "databaseURL": "https://od-android-f06ec-default-rtdb.firebaseio.com",
  "storageBucket": "od-android-f06ec.appspot.com"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

#### DONE LOAD FIREBASE

class cameraFunction:

    def __init__(self):
        self.security = db.child("cameras").child(cameraID).child("security").get()

    def addLog(self, case, func):
        date = datetime.datetime.now().strftime("%d-%m-%Y")
        time = datetime.datetime.now().strftime("%X")
        data = {
            'case': case,
            'func': func
        }
        db.child("cameras").child(cameraID).child("logs").child(date).child(time).set(data)

    def videoRecording(self):
        if self.security == False:
            # Define the codec and create VideoWriter object
            fourcc = cv.VideoWriter_fourcc(*'XVID')
            out = cv.VideoWriter('output.avi', fourcc, 20.0, (640, 480))
            time_start = datetime.datetime().now();
            time_end_default = time_start + datetime.timedelta(minutes=10)
            while cap.isOpened() and datetime.datetime.now() < time_end_default and self.security == False:
                ret, frame = cap.read()
                if not ret:
                    print("Can't receive frame (stream end?). Exiting ...")
                    break
                font = cv.FONT_HERSHEY_SCRIPT_COMPLEX
                dt = str(datetime.datetime.now().strftime("%X"))
                frame = cv.putText(frame, dt, (10, 250), font, 1, (210, 155, 155), 4, cv.LINE_8)
                #frame = cv.flip(frame, 0)
                # write the flipped frame
                out.write(frame)
                #cv.imshow('frame', frame)
            # Release everything if job is finished
            time_end = datetime.datetime.now()
            time_start_file_name = time_start.strftime("%X")
            time_end_file_name = time_end.strftime("%X")
            out.release()


    def takePic(self):
        while True:
            ret, frame = cap.read()
            font = cv.FONT_HERSHEY_SCRIPT_COMPLEX
            dt = str(datetime.datetime.now().strftime("%X"))
            frame = cv.putText(frame, dt,(10, 250),font, 1,(210, 155, 155),4, cv.LINE_8)
            img_name = "./Imgage/person.png"
            cv.imwrite(img_name, frame)
            break

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
                    Thr = threading.Thread(target=self.takePic())
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
            # print(x,y,w,h)
            # cv.rectangle(img, (x, y), (x + w, y + h), (255, 0, 255), 2)
            # cv.putText(img, f'{classNames[classIds[i]].upper()} {int(confs[i] * 100)}%', (x, y - 10), cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
           # print(classNames[classIds[i]].upper())


    def objDection(self):
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

    def stream_handler(self,message):
        self.security  = db.child("cameras").child(cameraID).child("security").get()
        if self.security == True:
            Thr = threading.Thread(target=self.objDection())
            Thr.start()

    def whenDataChage(self):
        my_stream = db.child("cameras").child(cameraID).child("security").stream(self.stream_handler)
