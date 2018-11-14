#####################################################################
"""
git config credential.helper store
git config --global user.name "alvarohurtadobo"
git config --global user.password "your password"
"""
#####################################################################

import os
import cv2
import sys
import csv
import time
import json
import psutil
import argparse
import datetime
import numpy as np
import imutils
from installationRegion import TwoSidedInstall
from imutils.video import VideoStream
from imutils.video import FPS

#####################################################################
intervaloVideos = 20
periodoGuardadoInformacionEnSegundos = 60


keep_processing = True 
factorAlgoritmo = 2

contadorDeAgenda = 0


# parse command line arguments for camera ID or video file

parser = argparse.ArgumentParser(description='Perform ' + sys.argv[0] + ' Installation for people/object counter')
parser.add_argument("-c", "--camera_being_use", type=int, help="specify camera to use", default=0)
parser.add_argument("-l", "--location", type=int, help="Factor for resolution", default=1)
parser.add_argument("-r", "--resolution_factor", type=int, help="Factor for resolution", default=2)
parser.add_argument("-d", "--drawing", type=bool, help="Dibujar", default=False)
parser.add_argument("-s", "--showImage", type=bool, help="Mostrar", default=False)
parser.add_argument('video_file', metavar='video_file', type=str, nargs='?', help='specify optional video file')
args = parser.parse_args()

fourcc = cv2.VideoWriter_fourcc(*'XVID')

total_flow = 0
passing_up = 0
passing_down = 0
conteoActual = 0

last_total_flow = 0
last_passing_up = 0
last_passing_down = 0
last_conteoActual = 0
csvName = './'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_{}.csv'.format(args.location)

with open(csvName, 'w') as csvFile:
    writer = csv.writer(csvFile, delimiter=';',quotechar='|', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['datetime','in','out','total','flow'])

contadorManual = 0

historial = []

lastValue = 0

puntosDeFlujo = []

resolution = (160*args.resolution_factor,120*args.resolution_factor)
#resolution = (320,240)

print('Working on resolution: ',resolution)

#####################################################################
# draw optic flow visualization on image using a given step size for
# the line glyphs that show the flow vectors on the image

def guardarInformacion():
    global writer
    global total_flow
    global passing_up
    global passing_down
    global conteoActual
    global historial
    global contadorDeAgenda
    global last_passing_up
    global last_passing_down
    global last_conteoActual
    global last_total_flow
    with open(csvName, 'a') as csvFile:
        writer = csv.writer(csvFile, delimiter=';',quotechar='|', quoting=csv.QUOTE_MINIMAL)
        idItem = datetime.datetime.now().strftime('%H%M%S')
        writer.writerow([idItem,passing_up,passing_down,conteoActual,total_flow])
        contadorDeAgenda +=1
        if contadorDeAgenda%intervaloVideos == 0:
            print('Saving video with {} frames'.format(len(historial)))
            guardarVideo(idItem,historial)
            if not os.path.exists('./output/'):
                os.makedirs('./output/')
            with open('./output/{}.txt'.format(idItem),"w+") as texFile:
                texFile.write('Passed Up: {}%d\r\n'.format(passing_up-last_passing_up))
                texFile.write('Passed Up: {}%d\r\n'.format(passing_down-last_passing_down))
                texFile.write('Passed Up: {}%d\r\n'.format(conteoActual-last_conteoActual))
                texFile.write('Passed Up: {}%d\r\n'.format(total_flow-last_total_flow))
        else:
            del historial
            historial = []
            print('Erasing video...')
    last_passing_up = passing_up
    last_passing_down = passing_down
    last_conteoActual = conteoActual
    last_total_flow = total_flow

def guardarVideo(paraNombre,historial):
    global fourcc
    global periodoGuardadoInformacionEnSegundos
    fps = int(len(historial)/periodoGuardadoInformacionEnSegundos//5)*5
    #print('FPS: ',fps)
    if fps>30:
        fps=30
    print(fps)
    nombreVideo = './output/{}.avi'.format(paraNombre)
    
    aEntregar = cv2.VideoWriter(nombreVideo,fourcc, fps,(resolution[0],resolution[1]))
    #contadorVide = 0
    for frame in historial:
        aEntregar.write(frame) 
        #cv2.imwrite('./output/{}_{}.jpg'.format(paraNombre,contadorVide),frame)
        #contadorVide +=1
    aEntregar.release()
    #os.system('ffmpeg -i {} {}.mp4'.format(nombreVideo,nombreVideo[:-4]))
    #os.system('rm {}'.format(nombreVideo))
    #print('Erased '+nombreVideo)

def draw_flow(img, flow, factor = 1,step=4):
    h, w = img.shape[:2]
    y, x = np.mgrid[step/2:h:step, step/2:w:step].reshape(2,-1).astype(int)
    #fx, fy = flow[y,x].T
    fx, fy = flow[y//factor,x//factor].T
    lines = np.vstack([x, y, x+fx, y+fy]).T.reshape(-1, 2, 2)
    lines = np.int32(lines + 0.5)
    vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    cv2.polylines(vis, lines, 0, (0, 255, 0))
    for (x1, y1), (x2, y2) in lines:
        cv2.circle(vis, (x1, y1), 1, (0, 255, 0), -1)
    return vis

def actualizarPuntosDeFlujo(img,myRegion,step = 4):
    h, w = img.shape[:2]
    y, x = np.mgrid[step/2:h:step, step/2:w:step].reshape(2,-1).astype(int)
    print(max(x))
    print(max(y))
    xMax = 0
    yMax = 0
    print('Region: ')
    puntosAdentro = 0
    for (x0,y0) in zip(x,y):
        if myRegion.isInside(x0,y0):
            puntosDeFlujo.append((x0,y0))
            puntosAdentro += 1
            if x0 > xMax:
                xMax = x0
            if y0 > yMax:
                yMax = y0

    print('Max: ', xMax, yMax,' in ', puntosAdentro, ' points inside')

def calculateInOutOnFlow(img,flow,myRegion,draw = False,factor = 1,step = 4):
    global total_flow
    global passing_up
    global passing_down
    global conteoActual
    global lastValue
    for (x0,y0) in puntosDeFlujo:
        # Integramos el flujo total
        velocidad = myRegion.proyectarVector(flow[y0//2][x0//2][0],flow[y0//2][x0//2][1])
        total_flow += int(velocidad)
        if draw:
            color = velocidad*100
            #print(color)
            if color > 10:
                if color > 255:
                    color = 255
                cv2.circle(img, (x0, y0), 1,color , -1)
        if calibration !=0:
            conteoActual = int(total_flow/calibration)
        else:
            conteoActual = 0
        if conteoActual != lastValue:
            if conteoActual > lastValue:
                passing_up += (conteoActual-lastValue)
            else:
                passing_down += (lastValue-conteoActual)
            lastValue = conteoActual
            print('Flujo total: ',conteoActual,', \t\tpasaron: ',passing_up,', \tretrocedieron: ',passing_down)
    return img

#####################################################################

# define video capture object

if __name__ == '__main__':
    videoAddress = os.getenv('HOME') +'/trafficFlow/trialVideos'
    tiempoInicial = time.time()

    if args.camera_being_use == 1:
        miCamara  = VideoStream(usePiCamera=True, resolution=(1640,922)).start()
        time.sleep(2.0)
    else:
        miCamara = cv2.VideoCapture(1) 

    # define display window name

    windowName = "Dense Optic Flow"  # window name
    tiempoAuxiliar = time.time()
    miRegion = TwoSidedInstall()
    calibration = miRegion.calibration

    # if command line arguments are provided try to read video_name
    # otherwise default to capture from attached H/W camera

    if args.camera_being_use == 1:

        # create window by name (as resizable)

        #cv2.namedWindow(windowName, cv2.WINDOW_NORMAL) 

        # if video file successfully open then read an initial frame from video

        if True:
            # miCamara.set(3,resolution[0])
            #miCamara.set(4,resolution[1])
            frame = miCamara.read()        
            frame = cv2.resize(frame, resolution)
            #for i in range(20):
            #    frame = miCamara.read()
            if args.video_file:
                frame = cv2.resize(frame,resolution)

        # convert image to grayscale to be previous frame

        prevgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        algImg = cv2.resize(prevgray, (prevgray.shape[1]//factorAlgoritmo,prevgray.shape[0]//factorAlgoritmo))
        actualizarPuntosDeFlujo(frame,miRegion)


        while (keep_processing):
            tiempoAuxiliar = time.time()
            # if video file successfully open then read frame from video
            if True:
                frame = miCamara.read() 
                #if args.video_file:
                frame = cv2.resize(frame,resolution)

                # when we reach the end of the video (file) exit cleanly
                #if (ret == 0):
                #keep_processing = False 
                #    continue 

            # convert image to grayscale

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            prevAlgImg = cv2.resize(gray, (gray.shape[1]//factorAlgoritmo,gray.shape[0]//factorAlgoritmo))

            # compute dense optic flow using technique of Farneback 2003
            # parameters from example (OpenCV 3.2):
            # https://github.com/opencv/opencv/blob/master/samples/python/opt_flow.py

            flow = cv2.calcOpticalFlowFarneback(algImg,  prevAlgImg, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            prevgray = gray
            algImg = prevAlgImg

            # display image with optic flow overlay
            #cv2.imshow(windowName, draw_flow(algImg, flow,factor=1))        #factorAlgoritmo

            imagen = calculateInOutOnFlow(gray, flow, miRegion,draw = args.drawing)
            historial.append(frame)
            
            if args.showImage:
                cv2.imshow(windowName,imagen)

            # start the event loop - essential

            # cv2.waitKey() is a keyboard binding function (argument is the time in milliseconds).
            # It waits for specified milliseconds for any keyboard event.
            # If you press any key in that time, the program continues.
            # If 0 is passed, it waits indefinitely for a key stroke.
            # (bitwise and with 0xFF to extract least significant byte of multi-byte response)

            ch = cv2.waitKey(1) & 0xFF  # wait 40ms (i.e. 1000ms / 25 fps = 40 ms)

            # It can also be set to detect specific key strokes by recording which key is pressed

            porcentajeDeMemoria = psutil.virtual_memory()[2]

            if (porcentajeDeMemoria > 95):
                print('Estado de Memoria en riesgo: '+str(porcentajeDeMemoria)+'/100')
                os.system('sudo reboot')

            if time.time() - tiempoInicial > periodoGuardadoInformacionEnSegundos:
                guardarInformacion()
                tiempoInicial = time.time()

            if (ch == ord('q')):
                keep_processing = False 
            if (ch == ord('+')):
                contadorManual +=1
                print('Contador Manual: ',contadorManual)
            if (ch == ord('*')):
                contadorManual +=10
                print('Contador Manual: ',contadorManual)
            if (ch == ord('-')):
                contadorManual -=1
                print('Contador Manual: ',contadorManual)
            if ch == ord('r'):
                conteoActual = contadorManual
                calibration = total_flow/conteoActual
                if calibration == 0:
                    calibration = 1
                passing_up = conteoActual
                passing_down = 0
                miRegion.updateCalibration(calibration)
                print('Guardando: ',calibration)
                
            if (ch == ord('f')):
                cv2.setWindowProperty(windowName, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN) 

        # close all windows
        print('Last Period: ',time.time() - tiempoAuxiliar)
        cv2.destroyAllWindows()

    else:
        print("No source specified") 

