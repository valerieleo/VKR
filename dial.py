#подключение необходимых библиотек
import cv2
import numpy as np
import time

import matplotlib.pyplot as plt
import matplotlib.image as mpimg

filename = 'grey_17.jpg'

# Вычисление среднего арифметического всех найденных кругов
def avg_circles(circles, b):
    avg_x=0
    avg_y=0
    avg_r=0
    for i in range(b):
        avg_x = avg_x + circles[0][i][0]
        avg_y = avg_y + circles[0][i][1]
        avg_r = avg_r + circles[0][i][2]
    avg_x = int(avg_x/(b))
    avg_y = int(avg_y/(b))
    avg_r = int(avg_r/(b))
    return avg_x, avg_y, avg_r
    
def find_0_scale(proj):
    maxd = 0
    maxi = 0
    sum = 0

    #идем по массиву
    for i in range (0, proj.shape[0]-1, 2):
        #предположим, что i начало подходящего диапазона и проверим максимальное число похожих на него после
        for j in range (i+1, proj.shape[0], 1):
            if proj[i]>proj[j]:
                razn = proj[i]-proj[j]
            else:
                razn = proj[j]-proj[i]
            #следующий похож
            if (razn<5000):
                sum = sum + 1
            else:
                if sum>maxd:
                    maxd = sum
                    maxi = i
                sum = 0
                break;
    print(maxi,maxd)
    
    
    maxd2 = 0
    maxi2 = 0
    sum = 0

    #идем по массиву
    for i in range (0, maxi, 2):
        #предположим, что i начало подходящего диапазона и проверим максимальное число похожих на него после
        for j in range (i+1, proj.shape[0], 1):
            if proj[i]>proj[j]:
                razn = proj[i]-proj[j]
            else:
                razn = proj[j]-proj[i]
            #следующий похож
            if (razn<5000):
                sum = sum + 1
            else:
                if sum>maxd2:
                    maxd2 = sum
                    maxi2 = i
                sum = 0
                break;
    #идем по массиву
    for i in range (maxi+maxd, proj.shape[0]-1, 2):
        #предположим, что i начало подходящего диапазона и проверим максимальное число похожих на него после
        for j in range (i+1, proj.shape[0], 1):
            if proj[i]>proj[j]:
                razn = proj[i]-proj[j]
            else:
                razn = proj[j]-proj[i]
            #следующий похож
            if (razn<5000):
                sum = sum + 1
            else:
                if sum>maxd2:
                    maxd2 = sum
                    maxi2 = i
                sum = 0
                break;

    print(maxi2,maxd2)
    
    maxd = maxi+maxd
    maxd2 = maxi2+maxd2
    
    return min(maxd, maxi, maxi2, maxd2), max(maxd, maxi, maxi2, maxd2)
    
def calculate_value(scale1, scale2, poiter,mini,maxi):
    value = 0
    if scale1<scale2:
        ves = (maxi-mini)/(1024-(scale2-scale1))
        if pointer>scale2:
            value = mini + ves*(pointer-scale2)
        elif pointer<u1:
            value = mini + ves*(1024-(scale2-pointer))
        elif scale1<pointer<scale2:
            value = 0

    return value
    
#читаем изображение
img = cv2.imread(filename)
img = cv2.resize(img, (1024, 1024))

#конвертация из цветного в серое
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
cv2.imwrite('grey.jpg', gray)

# поиск кругов методом Хафа
height, width = img.shape[:2]
circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 10, np.array([]), 120, 80, int(height*0.30), int(height*0.48))
print (circles.shape)

# отображение всех найденных кругов
imgg = img.copy()

if circles.shape[0] != 0:
    circles = np.uint16(np.around(circles))
    for i in circles[0,:]:
        # draw the outer circle
        cv2.circle(imgg,(i[0],i[1]),i[2],(0,255,0),2)
        # draw the center of the circle
        cv2.circle(imgg,(i[0],i[1]),2,(0,0,255),3)
else:
    print ("no circle found")

cv2.imwrite('circles.jpg', imgg)

#вычисление и отрисовка главного круга
a, b, c = circles.shape
x,y,r = avg_circles(circles, b)
print ('center:',x,y)

img_c = img.copy()
cv2.circle(img_c, (x, y), r, (0, 0, 255), 3, cv2.LINE_AA) 
cv2.circle(img_c, (x, y), 2, (0, 255, 0), 3, cv2.LINE_AA)
cv2.imwrite('circle.jpg', img_c)

# сегментация
print (img.shape[0], img.shape[1])
temp = gray.copy()
for i in range (temp.shape[0]):
    for j in range (temp.shape[1]):
        if (j-x)**2+(i-y)**2>=r**2:
            temp[i][j]=255
cv2.imwrite('template.jpg', temp)

#конвертация дисплея прибора в полярные координаты
img_lin=cv2.linearPolar(temp, (x,y), r, cv2.WARP_FILL_OUTLIERS)
height, width = img_lin.shape
img_lin=img_lin[0:height, int(width/3):width]
cv2.imwrite('polar.jpg', img_lin)

#переводим изображение в бинарное
porog = 127
(thresh, im_bw) = cv2.threshold(img_lin, porog, 255, cv2.THRESH_BINARY_INV)

print(np.sum(im_bw))

#если изображение слишком темное, понижаем порог
if np.sum(im_bw)>80000000:
    porog = porog-50
    (thresh, im_bw) = cv2.threshold(img_lin, porog, 255, cv2.THRESH_BINARY_INV)
cv2.imwrite('bw_lin.png', im_bw)
print(np.sum(im_bw))

# вычисляем горизонтальную проекцию
proj = np.sum(im_bw,1)
m = np.max(proj)
w = img_lin.shape[1]/3*2
result = np.zeros((proj.shape[0],int(img_lin.shape[1]/3*2),3),np.uint8)
print (proj.shape[0])

# отрисовываем проекцию
for row in range(im_bw.shape[0]):
   cv2.line(result, (0,row), (int(proj[row]*w/m),row), (255,255,255), 1)

cv2.imwrite('proj_col.jpg', result)
plt.imshow(result)

#поиск уровня стрелки
maxv = 0
maxi = 0
for i in range (proj.shape[0]):
    if proj[i]>=maxv:
        maxv = proj[i]
        maxi = i
print (maxv, maxi)
print (np.max(proj))
pointer = maxi
cv2.line(result, (0,maxi), (int(proj[maxi]*w/m),maxi), (255,0,0), 3)
cv2.imwrite('proj_col_2.jpg', result)

u1, u2 = find_0_scale(proj)
print (u1, u2)

cv2.line(result, (0,u1), (1024,u1), (0,0,255), 3)
cv2.line(result, (0,u2), (1024,u2), (0,255,255), 3)
cv2.imwrite('proj_col_2.jpg', result)
plt.imshow(result)

value = round(calculate_value(u1,u2,pointer,12,308),3)
print(value)
