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
import math
import psutil
import argparse
import datetime
import numpy as np

#from installationRegion import TwoSidedInstall

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
############################################################################################################################
px = 0
py = 0
flowFrame = np.zeros((320,240,3), np.uint8)
puntos = {'region': [], 'arriba': False,'vector':[1,1],'calibration':10000,'function': []}

lugarEnJSON = 'region'
if args.resolution_factor != None:
    resolution = (160*args.resolution_factor,120*args.resolution_factor)
    rango = int(40/args.resolution_factor)
else:
    resolution=(160,120)
    rango = int(40/args.resolution_factor)

dim = 1

estado = 0
"""
0 - Ingreso normal de punto
1 - Ingreso de borde
2 - Ingreso de esquina
3 - Punto de prueba
4 - Punto para angulo
"""

class TwoSidedInstall():
    def __init__(self):
        self.myJsonData = {'region': [], 'arriba': False,'vector':[1,1],'calibration':10000,'function':[]}
        self.saludable = True
        self.vectorUnitario = np.array((1,1))
        self.calibration = None
        self.function = None
        try:
            with open('./datos_{}.json'.format(args.location)) as f:
                print('Recuperando Location {}'.format(args.location))
                self.myJsonData = json.load(f)
                self.calibration = self.myJsonData['calibration']
                self.function = self.myJsonData['function']
                self.saludable = True
                vectorDireccion = np.array(self.myJsonData['region'][0])-np.array(self.myJsonData['region'][1])
                self.vectorUnitario = vectorDireccion/math.sqrt(vectorDireccion[1]**2+vectorDireccion[0]**2)
                print('Cargado exitosamente: ',self.myJsonData)
        except:
            self.saludable = False
            print('Could not find a json file')

    # Repeated function, take care

    def obtenerVectorUnitario(self):
        return self.vectorUnitario

    def proyectarVector(self,xVal,yVal):
        return self.vectorUnitario[0]*xVal+self.vectorUnitario[1]*yVal

    def grabarRegion(self,imagen):
        tamano = len(self.myJsonData['region'])
        for indice in range(tamano-1):
            siguiente = (indice+1)%tamano
            imagen = cv2.line(imagen,tuple(self.myJsonData['region'][indice]),tuple(self.myJsonData['region'][siguiente]),(255,255,255),1)
        return imagen

    def isInside(self,xTest,yTest):
        if not self.saludable:
            print('No cargue parámetros')
            return False
        try:
            if cv2.pointPolygonTest(np.array(self.myJsonData['region']),(xTest, yTest),True)>=0:
                #print('Punto ',(xTest, yTest ),' esta adentro de ', self.myJsonData['region'])
                return True
            else:
                #print('Punto ',(xTest, yTest ),' esta afuera de ', self.myJsonData['region'])
                pass
        except Exception as e:
            print('Is something bad with the poly ', str(e))
        return False

    def updateCalibration(self,calibration):
        self.myJsonData['calibration'] = calibration
        with open('./datos_{}.json'.format(args.location), 'w') as file:
            json.dump(self.myJsonData, file)
        print('Actualizado: ',self.myJsonData)


# Repeated function, take care
def isInside(xTest,yTest):
    global puntos
    try:
        if cv2.pointPolygonTest(np.array(puntos['region']),(xTest, yTest),True)>=0:
            #print('Punto ',(xTest, yTest ),' esta adentro de ', puntos['region'])
            return True
        else:
            #print('Punto ',(xTest, yTest ),' esta afuera de ', puntos['region'])
            pass
    except Exception as e:
        print('Is something bad with the poly ', str(e))
    return False


def aproximarABorde(x,y):
    global resolution
    global rango
    global dim
    if x < rango:
        x = 0
    if y < rango:
        y = 0
    if x > resolution[0] - rango:
        x = resolution[0] - dim
    if y > resolution[1] - rango:
        y = resolution[1] - dim
    return x,y

def aproximarAEsquina(x,y):
    global resolution
    global dim
    if x/resolution[0] < 0.5:
        x = 0
    else:
        x = resolution[0] - dim
    if y/resolution[1] < 0.5:
        y = 0
    else:
        y = resolution[1] - dim
    return x,y

def introducirLinea(event,x,y,flags,param):
    global px, py
    global lugarEnJSON
    global estado
    #print(x,y)
    if event == cv2.EVENT_LBUTTONDOWN:
        puntoDePrueba = False
        if estado > 0:
            if estado == 1:
                x,y = aproximarABorde(x,y)
                print('Introducido borde', (x,y))
            if estado == 2:
                x,y = aproximarAEsquina(x,y)
                print('Introducido esquina', (x,y))
            if estado == 3:
                if isInside(x,y):
                    print('El punto ', (x,y),' esta adentro')
                else:
                    print('El punto', (x,y),' esta afuera')
                puntoDePrueba = True
            if estado == 4:
                pass
            estado = 0
        else:
            print('Introducido punto', (x,y))
        if puntoDePrueba:
            cv2.circle(flowFrame,(x,y),3,(0,255,0),-1)
        else:
            cv2.circle(flowFrame,(x,y),3,(255,0,0),-1)
            puntos[lugarEnJSON].append((x,y))
            tamano = len(puntos[lugarEnJSON])
            print('Tamano', tamano)
            for indice in range(tamano-1):
                siguiente = (indice+1)%tamano
                cv2.line(flowFrame,puntos[lugarEnJSON][indice],puntos[lugarEnJSON][siguiente],(255,255,255),1)
        return x,y

if __name__ == '__main__':
    print('Instalando Location {}'.format(args.location))
    videoAddress = 'C:\Pruebas\objectCounter\A15_173734.avi'
    jsonToWrite = './datos_{}.json'.format(args.location)

    miCamara = cv2.VideoCapture()
    windowName = 'Installation'
    
    print(miCamara)
    
    if (((miCamara.open(videoAddress)))):
        #or (miCamara.open(args.camera_being_use))):
        cv2.namedWindow(windowName, cv2.WINDOW_NORMAL)
        if (miCamara.isOpened):
            miCamara.set(3,resolution[0])
            miCamara.set(4,resolution[1])
            ret, frame = miCamara.read() 
            for i in range(20):
                succesfullyRead, flowFrame = miCamara.read()
            if args.video_file:
                flowFrame = cv2.resize(flowFrame,resolution)
        else:
            print('Opturador no abierto')
    else:
        print('Could Not find source')

    cv2.setMouseCallback(windowName,introducirLinea)

    print('trabajando a resolucion', resolution)

    while True:
        cv2.imshow(windowName,flowFrame)
        try:
            flowFrame = cv2.resize(flowFrame,resolution)
        except Exception as e:
            print('Error al cargar ', str(e))

        ch = 0xFF & cv2.waitKey(20)
        if ch == ord('s'):
            try:
                with open('./datos_{}.json'.format(args.location)) as f:
                    lastData = json.load(f)
                    puntos['calibration'] = lastData['calibration']
                    print('Rescate previa instalacion')
            except:
                print('No previous file found')
            with open(jsonToWrite, 'w') as file:
                json.dump(puntos, file)
            print('Guardado Exitosamente: ',puntos)
        if ch == ord('e'):
            estado = 1
        if ch == ord('c'):
            estado = 2
        if ch == ord('t'):
            estado = 3
        if ch == ord('a'):
            estado = 4
        if ch == ord('d'):
            puntos[lugarEnJSON] = []
            print('Borrado')
        if ch == ord('q'):
            break
        if (ch == ord('f')):
            cv2.setWindowProperty(windowName, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN) 
    miCamara.release()
    cv2.destroyAllWindows()

###############################################################################33###########################################
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
        idItem = datetime.datetime.now().strftime('%d_%H%M%S')
        writer.writerow([idItem,passing_up,passing_down,conteoActual,total_flow])
        contadorDeAgenda +=1
        if contadorDeAgenda%intervaloVideos == 0:
            print('Saving video with {} frames'.format(len(historial)))
            guardarVideo(idItem,historial)
            if not os.path.exists('./output/'):
                os.makedirs('./output/')
            with open('./output/{}.txt'.format(idItem),"w+") as texFile:
                texFile.write('Passed Up: {}%d\r\n'.format(passing_up-last_passing_up))
                texFile.write('Passed Down: {}%d\r\n'.format(passing_down-last_passing_down))
                texFile.write('Passed Total: {}%d\r\n'.format(conteoActual-last_conteoActual))
                texFile.write('Raw Flow: {}%d\r\n'.format(total_flow-last_total_flow))
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
    videoAddress =  'C:\Pruebas\objectCounter\A15_173734.avi'
    tiempoInicial = time.time()

    miCamara = cv2.VideoCapture() 

    # define display window name

    windowName = "Dense Optic Flow"  # window name
    tiempoAuxiliar = time.time()
    miRegion = TwoSidedInstall()
    calibration = miRegion.calibration

    # if command line arguments are provided try to read video_name
    # otherwise default to capture from attached H/W camera

    if (((miCamara.open(videoAddress)))):
        #or (miCamara.open(args.camera_being_use))):

        # create window by name (as resizable)

        #cv2.namedWindow(windowName, cv2.WINDOW_NORMAL) 

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


