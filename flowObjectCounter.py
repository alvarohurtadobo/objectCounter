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
import time
import argparse
import numpy as np

from installationRegion import TwoSidedInstall

#####################################################################

keep_processing = True 
factorAlgoritmo = 2

# parse command line arguments for camera ID or video file

parser = argparse.ArgumentParser(description='Perform ' + sys.argv[0] + ' example operation on incoming camera/video image')
parser.add_argument("-c", "--camera_being_use", type=int, help="specify camera to use", default=0)
parser.add_argument("-f", "--calibration_Input", type=int, help="Factor for calibration", default=10000)
parser.add_argument("-r", "--resolution_Factor", type=int, help="Factor for resolution", default=2)
parser.add_argument('video_file', metavar='video_file', type=str, nargs='?', help='specify optional video file')
args = parser.parse_args()

total_flow = 0
passing_up = 0
passing_down = 0

calibration = int(args.calibrationInput)
print('Introduced calibration: ',calibration)

lastValue = 0

puntosDeFlujo = []

resolution = (160*args.resolutionFactor,120*args.resolutionFactor)
#resolution = (320,240)

print('Working on resolution: ',resolution)

#####################################################################

# draw optic flow visualization on image using a given step size for
# the line glyphs that show the flow vectors on the image

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
    for (x0,y0) in zip(x,y):
        if myRegion.isInside(x0,y0):
            puntosDeFlujo.append((x0,y0))
            print((x0,y0))
            if x0 > xMax:
                xMax = x0
            if y0 > yMax:
                yMax = y0
        else:
            #print('Not in: ',(x0,y0))
            pass
    print('Max: ', xMax, yMax)

def drawVelocity(img,flow,myRegion,factor = 1,step = 4):
    global total_flow
    global passing_up
    global passing_down
    global calibration
    global lastValue
    for (x0,y0) in puntosDeFlujo:
        cv2.circle(img, (x0, y0), 1,(0,0,0) , -1)
        # Integramos el flujo total
        total_flow += int(myRegion.proyectarVector(flow[y0//2][x0//2][0],flow[y0//2][x0//2][1]))
        conteoActual = int(total_flow/calibration)
        if conteoActual != lastValue:
            if conteoActual > lastValue:
                passing_up += (conteoActual-lastValue)
            else:
                passing_down += (lastValue-conteoActual)
            lastValue = conteoActual
            print('Pasaron: ',passing_up,', retrocedieron: ',passing_down,', flujo total: ',total_flow)
    return img

#####################################################################

# define video capture object

if __name__ == '__main__':
    videoAddress = os.getenv('HOME') +'/trafficFlow/trialVideos'

    miCamara = cv2.VideoCapture() 

    # define display window name

    windowName = "Dense Optic Flow"  # window name
    tiempoAuxiliar = time.time()
    miRegion = TwoSidedInstall()

    # if command line arguments are provided try to read video_name
    # otherwise default to capture from attached H/W camera

    if (((args.video_file) and (miCamara.open(videoAddress+'/'+str(args.video_file))))
        or (miCamara.open(args.camera_to_use))):

        # create window by name (as resizable)

        cv2.namedWindow(windowName, cv2.WINDOW_NORMAL) 

        # if video file successfully open then read an initial frame from video

        if (miCamara.isOpened):
            miCamara.set(3,resolution[0])
            miCamara.set(4,resolution[1])
            ret, frame = miCamara.read() 
            for i in range(20):
                succesfullyRead, frame = miCamara.read()
            if args.video_file:
                frame = cv2.resize(frame,resolution)

        # convert image to grayscale to be previous frame

        prevgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        algImg = cv2.resize(prevgray, (prevgray.shape[1]//factorAlgoritmo,prevgray.shape[0]//factorAlgoritmo))
        actualizarPuntosDeFlujo(frame,miRegion)

        while (keep_processing):
            tiempoAuxiliar = time.time()
            # if video file successfully open then read frame from video
            if (miCamara.isOpened):
                ret, frame = miCamara.read() 
                if args.video_file:
                    frame = cv2.resize(frame,resolution)

                # when we reach the end of the video (file) exit cleanly
                if (ret == 0):
                    keep_processing = False 
                    continue 

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
            cv2.imshow(windowName,drawVelocity(gray, flow, miRegion))

            # start the event loop - essential

            # cv2.waitKey() is a keyboard binding function (argument is the time in milliseconds).
            # It waits for specified milliseconds for any keyboard event.
            # If you press any key in that time, the program continues.
            # If 0 is passed, it waits indefinitely for a key stroke.
            # (bitwise and with 0xFF to extract least significant byte of multi-byte response)

            key = cv2.waitKey(1) & 0xFF  # wait 40ms (i.e. 1000ms / 25 fps = 40 ms)

            # It can also be set to detect specific key strokes by recording which key is pressed

            if (key == ord('q')):
                keep_processing = False 
            elif (key == ord('f')):
                cv2.setWindowProperty(windowName, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN) 

        # close all windows
        print('Last Period: ',time.time() - tiempoAuxiliar)
        cv2.destroyAllWindows()

    else:
        print("No source specified") 

