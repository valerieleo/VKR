#подключение необходимых библиотек

import cv2
import numpy as np
import time
import datetime
import sys
import os
import json
import socket
import paho.mqtt.client as mqtt
from   time     import sleep
from   picamera import PiCamera

###########################################
####  настройка параметров устройства  ####

Device_ID = '12'

HOST = '192.168.1.35'
PORT = 1234

BackUpFileName = 'back_data.txt'

# seconds between the capturing
if len(sys.argv) == 2 :    #from console
    TimeStep = int(sys.argv[1])
else:                       #default
    TimeStep = 5

size       = 800
percent_wh = 0.1
rv         = 20
x_crop     = 0.43

#size = 400
#bw_col = 5000000
#rv = 10
#x_crop = 170

camera = PiCamera()
camera.resolution = (size, size)
camera.awb_mode   = 'greyworld'

# Вычисление среднего арифметического всех найденных кругов
def avg_circles(circles, b):
    avg_x = 0
    avg_y = 0
    avg_r = 0
    for i in range(b):
        avg_x = avg_x + circles[0][i][0]
        avg_y = avg_y + circles[0][i][1]
        avg_r = avg_r + circles[0][i][2]
    avg_x = int(avg_x/(b))
    avg_y = int(avg_y/(b))
    avg_r = int(avg_r/(b))
    return avg_x, avg_y, avg_r

# Перевод в бинарный формат
def to_bw(img,percent_wh):
    porog = 160
    (thresh, bw) = cv2.threshold(img, porog, 255, cv2.THRESH_BINARY_INV)
    while np.sum(bw)/255>size*size*percent_wh:
        porog = porog - 10
        (thresh, bw) = cv2.threshold(img, porog, 255, cv2.THRESH_BINARY_INV)
    return bw
    
# Поиск первого и последнего деления шкалы
def find_0_scale(proj, rv):
    maxd = 0
    maxi = 0
    sum  = 0
    for i in range (0, proj.shape[0]-1, 2):
        for j in range (i+1, proj.shape[0], 1):
            if proj[i]>proj[j]:
                razn = proj[i]-proj[j]
            else:
                razn = proj[j]-proj[i]
            if (razn<rv):
                sum = sum + 1
            else:
                if sum>maxd:
                    maxd = sum
                    maxi = i
                sum = 0
                break;    
    maxd2 = 0
    maxi2 = 0
    sum = 0
    for i in range (0, maxi, 2):
        for j in range (i+1, proj.shape[0], 1):
            if proj[i]>proj[j]:
                razn = proj[i]-proj[j]
            else:
                razn = proj[j]-proj[i]
            if (razn<rv):
                sum = sum + 1
            else:
                if sum>maxd2:
                    maxd2 = sum
                    maxi2 = i
                sum = 0
                break;
    for i in range (maxi+maxd, proj.shape[0]-1, 2):
        for j in range (i+1, proj.shape[0], 1):
            if proj[i]>proj[j]:
                razn = proj[i]-proj[j]
            else:
                razn = proj[j]-proj[i]
            if (razn<rv):
                sum = sum + 1
            else:
                if sum>maxd2:
                    maxd2 = sum
                    maxi2 = i
                sum = 0
                break;
    maxd = maxi+maxd
    maxd2 = maxi2+maxd2
    
    return min(maxd, maxi, maxi2, maxd2), max(maxd, maxi, maxi2, maxd2)

# Вычисление показания
def calculate_value(scale1, scale2, pointer,mini,maxi):
    value = 0
    if scale1<scale2:
        ves = (maxi-mini)/(size-(scale2-scale1))
        if pointer>scale2:
            value = mini + ves*(pointer-scale2)
        elif pointer<scale1:
            value = mini + ves*(size-(scale2-pointer))
        elif scale1<pointer<scale2:
            value = 0

    return value

# Обработка изображения
def read(filename):
    # получение изображения
    img = cv2.imread(filename)
    if img.shape[0] != img.shape[1]:
        print ('error: incorrect size')
        return (-1)
    img = cv2.resize(img, (size, size))

    # конвертация исходного изображения в градации серого
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # поиск кругов методом Хафа
    height, width = img.shape[:2]
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 10, np.array([]), 120, 100, int(height*0.20), int(height*0.40))
    
    # проверка наличия кругов
    if circles is None:
        print ("no circle found")
        return(-1)

    # вычисление и отрисовка главного круга
    a, b, c = circles.shape
    x,y,r = avg_circles(circles, b)
    print ('center:',x,y)

    # сегментация
    temp = gray.copy()
    for i in range (temp.shape[0]):
        for j in range (temp.shape[1]):
            if (j-x)**2+(i-y)**2>=r**2:
                temp[i][j]=255

    # конвертация дисплея прибора в полярные координаты
    img_lin=cv2.linearPolar(temp, (x,y), r, cv2.WARP_FILL_OUTLIERS+cv2.INTER_LINEAR)
    height, width = img_lin.shape
    img_lin=img_lin[0:height, int(width*x_crop):width]

    # конвертация изображения в бинарное
    im_bw = to_bw(img_lin, percent_wh)

    # вычисление горизонтальной проекции
    proj = np.sum(im_bw,1)/255
    m = np.max(proj)
    w = img_lin.shape[1]
    result = np.zeros((proj.shape[0],img_lin.shape[1],3),np.uint8)

    # поиск уровня стрелки
    maxv = 0
    maxi = 0
    for i in range (proj.shape[0]):
        if proj[i]>=maxv:
            maxv = proj[i]
            maxi = i
    pointer = maxi
    
    # поиск начала и конца шкалы делений
    u1, u2 = find_0_scale(proj, rv)

    value = round(calculate_value(u1,u2,pointer+2,14,306),2)
    print ('Result =', value)
    return (value)

# Передача значений на облачную платформу
def cloudTransmission(value_):
    THINGSBOARD_HOST = 'demo.thingsboard.io'
    ACCESS_TOKEN = '87RQLKgVRDliCKrkSFNQ'

    sensor_data  = {'value': 0}
    next_reading = time.time()

    client = mqtt.Client()

    # Установка токена доступа
    client.username_pw_set(ACCESS_TOKEN)

    # Подключение к Thingsboard, используя порт MQTT по умолчанию 
    # и 60-секундный интервал активности
    client.connect(THINGSBOARD_HOST, 1883, 60)

    client.loop_start()
    # Отправка данных о считанном значении на Thingsboard
    cur_value = value_
    cur_value = round(value_, 2)
    print(u"Value: {:g}".format(cur_value))
    sensor_data['value'] = cur_value
    client.publish('v1/devices/me/telemetry', json.dumps(sensor_data), 1)
    client.loop_stop()
    client.disconnect()

def set_up_length(value, delimiter):
    if len(value) == 1:
        return ('0' + value + delimiter)
    else:
        return (value + delimiter)

#creating value line with 3 params
def make_value_line(D_ID, now, value):
    if len(D_ID) == 1:
        value_line = D_ID + str('  | ')
    else:
        value_line = D_ID + str(' | ')        
    value_line = value_line + str(now.year) + str('/')    
    value_line = value_line + set_up_length(str(now.month), '/')
    value_line = value_line + set_up_length(str(now.day), ' | ')
    value_line = value_line + set_up_length(str(now.hour), '/')
    value_line = value_line + set_up_length(str(now.minute), '/')
    value_line = value_line + set_up_length(str(now.second), ' | ')        
    value_line = value_line + str(value)    
    while len(value_line) <= 35:
        value_line = value_line + '0'
    
    return value_line

#send value data via socket
def socket_send(D_ID, HOST, PORT, BackUpFileName, value, fl, value_time):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    value_line = make_value_line(D_ID, value_time, value)    
    
    try:    
        s.connect((HOST, PORT))
        print(f"Connected to {HOST}")
        
        msg = s.recv(24)
        print(f"Server income: {msg.decode('utf-8')}")
        
        if not fl:
            #sending all file
            print('Send file values to server')
            BackUpFile = open(BackUpFileName, 'r')
            for line in BackUpFile:
                msg = line[:len(line)-1]
                s.send(bytes(msg,"utf-8"))
            open(BackUpFileName, 'w').close()
                
        s.send(bytes(value_line,"utf-8"))
        s.close()
        fl = True
    except socket.error:
        print('Connection failed')        
        print('Writing value to BackUp file')
        BackUpFile = open(BackUpFileName, 'a')
        BackUpFile.write(value_line + '\n')
        BackUpFile.close()
        
        fl = False
        
    return fl

def main():
    fl = True
    try:
        while True:
            print(f'It is {datetime.datetime.now()}')

            value_time = datetime.datetime.now()
            camera.capture('image.jpg')
            print ('photo ready')
            start_time = datetime.datetime.now()
            read_value = read('image.jpg')

            if read_value == -1:
                print('error')
            else:
                print (f'Result: {read_value}')
                print (f'in {(datetime.datetime.now() - start_time)} seconds')
                #cloudTransmission(read_value)
                fl = socket_send(Device_ID, HOST, PORT, BackUpFileName, read_value, fl, value_time)
            print(f'Wait {TimeStep} seconds...')
            sleep(TimeStep)    
    except KeyboardInterrupt:
        pass

if __name__=='__main__':
    main()


