# server

# подключение необходимых библиотек
from time import sleep
from _thread import *
import time
import threading
import socket
import os
import json
import paho.mqtt.client as mqtt

########################################
####  настройка параметров сервера  ####

HOST = '192.168.1.35'
PORT = 1234

THINGSBOARD_HOST = 'demo.thingsboard.io'
ACCESS_TOKEN     = '87RQLKgVRDliCKrkSFNQ'

listen_number = 5

########################################

print_lock = threading.Lock()

# Передача значений на облачную платформу
def СloudTransmission(THINGSBOARD_HOST, ACCESS_TOKEN, value_):
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

# Распараллеливание процессов
def threaded(conn):
    msg = "Welcome to server!"
    conn.send(bytes(msg,"utf-8"))
    
    while True:
        data = conn.recv(36)
        if not data:
            print_lock.release()
            break
        data = data.decode('utf-8')
        print(f"Device data: {data}")
        DataToCloud = float(data[data.rindex(' ')+1:])

        # отправка на облачную платформу
        СloudTransmission(THINGSBOARD_HOST, ACCESS_TOKEN, DataToCloud)
        
    conn.close()

# Создание сокета
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('Socket created')

try:
    s.bind((HOST, PORT))
except socket.error:
    print('Bind failed')

s.listen(listen_number)
print('Wait for connections...')

# Цикл для подключений клиентов
try:
    while True:
        conn, addr = s.accept()        
        print_lock.acquire()
        print(f"Connection with {addr}")
        
        start_new_thread(threaded, (conn, ))
        
    s.close()
except KeyboardInterrupt:
    pass
