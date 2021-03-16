from flask import Flask, Response
import cv2 as cv


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
  "apiKey": "AAAATwkzJus:APA91bHH6f2oNgrBpr3Z-i_1RnDyV36RjDvvIRj9NYrOzQvAcQoLbZTEsLKUZc7IsT8CKxCScDXmuctA0GdlONa-QBE670reWxeloH8X9GsfCfPD8k13ZOCXBjqmr46_Evxh2iRfKC2c",
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
        self.security = db.child("cameras").child(cameraID).child("security").get()
        self.temp = CPUTemperature().temperature

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
            #Time define
            time_start = datetime.datetime().now();
            time_end_default = time_start + datetime.timedelta(minutes=10)
            #Try open folder if not exist create it
            date_now = datetime.datetime.strftime("%d-%m-%y")
            path_name = './videos/' + date_now
            if not os.path.exists(path_name):
                os.makedirs(path_name)
            # Define the codec and create VideoWriter object
            first_name = path_name + 'output.avi'
            fourcc = cv.VideoWriter_fourcc(*'XVID')
            out = cv.VideoWriter(path_name, fourcc, 20.0, (640, 480))
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
            last_name = + time_start_file_name + ' ' + time_end_file_name + '.avi'
            out.release()


    def takePic(self):
        while True:
            ret, frame = cap.read()
            font = cv.FONT_HERSHEY_SCRIPT_COMPLEX
            dt = str(datetime.datetime.now().strftime("%X"))
            frame = cv.putText(frame, dt,(10, 250),font, 1,(210, 155, 155),4, cv.LINE_8)
            img_name = "./Imgage/" + dt + ".jpg"
            cv.imwrite(img_name, frame)
            break
        print("Write image complete")
        ######SEND PHOTO TO DATA BASE######
        #print("Send image to serve")
        #storage.child("images/" + cameraID + "/" + dt +".jpg").put(img_name)
        #print("Send image done")

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
                    
                    print("Some one at home")
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
            cv.imshow('Image', img)
            cv.waitKey(1)
            
    def stream_temple(self):
        self.temp = CPUTemperature().temperature
        if self.temp < 70:
            time.sleep(10)
        else:
            self.addLog("Control by camera", "Turn off security to coolboot cpu")
            time.sleep(10)
            self.addLog("Control by camera", "Turn on security, coolboot cpu complete")

    def stream_handler(self,message):
        self.security  = db.child("cameras").child(cameraID).child("security").get()
        if self.security == True:
            Thr = threading.Thread(target=self.objDection())
            Thr.start()

    def whenDataChage(self):
        my_stream = db.child("cameras").child(cameraID).child("security").stream(self.stream_handler)
        
        


#####################################WEB################################
app = Flask(__name__)
@app.route('/')
def index():
    return "Default Message"

def gen(video):
    while True:
        success, image = cap.read()
        ret, jpeg = cv.imencode('.jpg', image)
        frame = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    global video
    return Response(gen(video),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def runserve():
    app.run(host='192.168.4.144', threaded=True, debug=False)
    
###########################MAINMAIN################################
if __name__ == "__main__":
    func = cameraFunction()
    
    t1 = threading.Thread(target=func.whenDataChage)
    t2 = threading.Thread(target=runserve)
    t1.start()
    t2.start()
    
    print(db.child("cameras").child(cameraID).child("security").get())
