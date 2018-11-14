"""
Introduzco una región con elbotón izquierdo

e - El siguiente punto se aproximará al edge mas cercano
c - El siguiente punto se aproximará al corner mas cercano
s - Guardo el archivo json en forma: puntos = {'region': [(x0,y0),(x1,y1)], 'arriba': Bool}
q - Salgo de la aplicación.

Para cambiar la resolution introduzca en el argumento la letra r seguida de la resolution, ejemplo:
r320,240

Para usar un video simplemente adjunte a la ejecución el nombre del video con extension

Para importar resolutados instancie la clase:
TwoSidedInstall()
y use su metodo:
TwoSidedInstall::isInside()

La clase TwoSidedInstall() carga los parametros y mediante un metodo llamado .isAbove() determina si un nuevo punto está "arriba" o "abajo" de la linea

git config credential.helper store
git config --global user.name "alvarohurtadobo"
git config --global user.password "your password"
"""


import os
import sys
import cv2
import json
import math
import argparse
import numpy as np
from imutils.video import VideoStream

# By default the ingreso is the web cam

parser = argparse.ArgumentParser(description='Perform ' + sys.argv[0] + ' Installation for people/object counter')
parser.add_argument("-c", "--camera_being_use", type=int, help="specify camera to use", default=0)
parser.add_argument("-l", "--location", type=int, help="Factor for resolution", default=1)
parser.add_argument("-r", "--resolution_factor", type=int, help="Factor for resolution", default=2)
parser.add_argument("-d", "--drawing", type=bool, help="Dibujar", default=False)
parser.add_argument("-s", "--showImage", type=bool, help="Mostrar", default=False)
parser.add_argument('video_file', metavar='video_file', type=str, nargs='?', help='specify optional video file')
args = parser.parse_args()

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
    videoAddress = os.getenv('HOME') +'/trafficFlow/trialVideos'
    jsonToWrite = './datos_{}.json'.format(args.location)

    miCamara = VideoStream(usePiCamera=True, resolution=(3280, 2464)).start()
    windowName = 'Installation'
    if args.camera_being_use == 1:
        cv2.namedWindow(windowName, cv2.WINDOW_NORMAL)
        if True:
            #miCamara.set(3,resolution[0])
            #miCamara.set(4,resolution[1])
            flowFrame = miCamara.read() 
            #for i in range(20):
            #    succesfullyRead, flowFrame = miCamara.read()
            #if args.video_file:
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
