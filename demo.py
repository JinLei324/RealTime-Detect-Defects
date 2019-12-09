from darkflow.net.build import TFNet
import cv2
import numpy as np
import imutils
from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtChart import *
import sys
import pyqtgraph as pg
import tkinter as tk
from tkinter import filedialog
import easygui
import pymysql
import datetime
from threading import Thread
from collections import deque
import random
import time
import defect
import math

from array import array

from pdfrw import PdfWriter
from prettytable import PrettyTable
from fpdf import FPDF
from pytz import timezone

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)

import xlwt

conn = pymysql.connect(host='localhost',
                       user='khb',
                       password='khb')

conn.cursor().execute('create database if not exists defect_database')

conn.cursor().execute('CREATE TABLE IF NOT EXISTS defect_database.defect_info (id int NOT NULL AUTO_INCREMENT, '
                      'defect_name text, belt_number text, detectedTime datetime, defect_snapshot longblob, PRIMARY KEY (id)) '
                      'ENGINE = InnoDB DEFAULT CHARSET = utf8 COLLATE = utf8_unicode_ci  AUTO_INCREMENT=1;')

stream_url = ""
options = {'model': 'cfg/tiny-yolo-voc-5c.cfg','load': 118800, 'threshold': 0.7, 'gpu': 1.0}
#options = {"model": "cfg/tiny-yolo-voc.cfg","load": "bin/tiny-yolo-voc.weights", "threshold": 0.1, "gpu": 1.0}
tfnet = TFNet(options)

imagePath = ""


class TimerMessageBox(QMessageBox):
    def __init__(self, timeout=3, parent=None):
        super(TimerMessageBox, self).__init__(parent)
        self.setWindowTitle("Info")
        self.time_to_wait = timeout
        self.setText("Successfully Downloaded")
        self.setStandardButtons(QtGui.QMessageBox.NoButton)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.changeContent)
        self.timer.start()

    def changeContent(self):
        # self.setText("wait (closing automatically in {0} secondes.)".format(self.time_to_wait))
        self.time_to_wait -= 1
        if self.time_to_wait <= 0:
            self.close()

    def closeEvent(self, event):
        self.timer.stop()
        event.accept()





class ImgWidget(QtGui.QLabel):

    def __init__(self, parent=None):
        global imagePath

        super(ImgWidget, self).__init__(parent)
        pic = QtGui.QPixmap(imagePath)
        self.setPixmap(pic)


"""Scrolling Timestamp Plot Widget Example"""

class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [str(value.minute) + ":" + str(value.second) for value in values]

class DrawingBoard(QWidget):
    def __init__(self, parent = None):
        super(DrawingBoard, self).__init__(parent)
        self.xs = []
        self.ys = array('d')
        self.image = QImage()

    def update(self):
        super(DrawingBoard, self).update()

    def minimumSizeHint(self):
        size = QSize(256, 256)
        return size

    def sizeHint(self):
        size = QSize(256, 256)
        return size

    def resizeEvent(self, event):
        super(DrawingBoard, self).resizeEvent(event)
        self.image = QImage(self.width(), self.height(), QImage.Format_RGB32)
        self.drawLine()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.image);
        painter.end()
        return

    def setLine(self, labels, numbers):
        self.xs = labels
        self.ys = numbers
        self.drawLine()

    def drawLine(self):
        painter = QPainter()
        painter.begin(self.image)

        cx = self.width() / 2
        cy = self.height() / 2
        r = min(cx, cy) * 3 / 4

        painter.setBrush(Qt.white)
        painter.fillRect(self.image.rect(), Qt.white)

        n = min(len(self.xs), len(self.ys))
        if (n < 1):
             return

        painter.setRenderHint(QPainter.Antialiasing, 1)

# find the scale

        sum = 0
        for i in range (n):
            sum += self.ys[i]

        if (sum > 0):
            scale = 1 / sum
        else:
            scale = 0

        ca = array('d')
        a = 0
        r_n = 1.0 / n
        for i in range (n):
             number = self.ys[i]
             da = number * scale * 5760
             c = math.floor(i * 255 / n)
             qc = QColor()
             qc.setHsvF(i * r_n, 0.5, 0.875)
             painter.setBrush(QColor(qc))
             painter.setPen(QColor(0, 0, 0, 0))
             painter.drawPie(cx - r, cy - r, r * 2, r * 2, a, da);
             ca.append((a + da / 2) * math.pi / 2880)
             a += da

        font = QFont("Sans Serif")
        font.setPixelSize(r / 8)
        painter.setFont(font)

        for i in range (n):
             label = self.xs[i]
             x = cx + math.cos(ca[i]) * r * 0.75
             y = cy - math.sin(ca[i]) * r * 0.75
             painter.setPen(QColor(0, 0, 0, 128))
             painter.setBrush(QColor(0, 0, 0, 128))
             painter.drawText(x - r / 2, y - r / 2, r, r, Qt.AlignHCenter | Qt.AlignVCenter, label)

        painter.end()
        self.update()
        return

class CameraURL(QtWidgets.QWidget):

    global stream_url

    def __init__(self, parent = None):
        super(CameraURL, self).__init__(parent)
        uic.loadUi('CameraSet.ui', self)

        self.okBtn = self.findChild(QtWidgets.QPushButton, 'btnOk')  # Find the button
        self.okBtn.clicked.connect(self.onOkBtnClicked)
        self.okBtn.setStyleSheet("background-color:rgb(42, 42, 42)");

        self.btnReset = self.findChild(QtWidgets.QPushButton, 'btnReset')  # Find the button
        self.btnReset.clicked.connect(self.onResetBtnClicked)
        self.btnReset.setStyleSheet("background-color:rgb(42,42,42)");

        self.btnCancel = self.findChild(QtWidgets.QPushButton, 'btnCancel')  # Find the button
        self.btnCancel.clicked.connect(self.onCancelBtnClicked)
        self.btnCancel.setStyleSheet("background-color:rgb(42,42,42)");

        self.cameraURLEdit = self.findChild(QtWidgets.QLineEdit, 'editCameraURL')  # Find the button
        self.cameraURLEdit.setStyleSheet("color: rgb(0, 0, 0);")

    def onOkBtnClicked(self):
        global stream_url

        self.camera_stream_url = self.cameraURLEdit.text()
        if self.camera_stream_url == "":
            easygui.msgbox("Please input camera url!", title="Warning")
            return
        stream_url = self.camera_stream_url
        self.hide()
    def onCancelBtnClicked(self):
        self.hide()
    def onResetBtnClicked(self):
        self.cameraURLEdit.setText("")

class Ui(QtWidgets.QWidget, defect.Ui_DefectAnalytics):

    def     __init__(self, parent=None):
        super(Ui, self).__init__(parent)
        # uic.loadUi('defect.ui', self)
        self.setupUi(self)

        self.warning_image = cv2.imread("res/warning.jpg")
        self.nowarning_image = cv2.imread("res/nowarning.jpg")

        self.running = False

        rMyIcon = QtGui.QPixmap("res/defect_btn.png")
        self.liveBtn.setIcon(QtGui.QIcon(rMyIcon))
        self.minBtn.clicked.connect(self.minimizeWindow)
        rMyIcon = QtGui.QPixmap("res/minimun.png")
        self.minBtn.setIcon(QtGui.QIcon(rMyIcon))

        self.closeBtn.clicked.connect(self.closeWindow)
        rMyIcon = QtGui.QPixmap("res/close.png")
        self.closeBtn.setIcon(QtGui.QIcon(rMyIcon))

        self.startBtn.clicked.connect(self.startLiveStream)
        rMyIcon = QtGui.QPixmap("res/start.png")
        self.startBtn.setIcon(QtGui.QIcon(rMyIcon))

        rMyIcon = QtGui.QPixmap("res/rotate.png")
        self.rotateBtn.setIcon(QtGui.QIcon(rMyIcon))

        self.openVideoBtn.clicked.connect(self.openVideo)
        rMyIcon = QtGui.QPixmap("res/file.png")
        self.openVideoBtn.setIcon(QtGui.QIcon(rMyIcon))

        self.openCameraBtn.clicked.connect(self.openCamera)
        rMyIcon = QtGui.QPixmap("res/camera.png")
        self.openCameraBtn.setIcon(QtGui.QIcon(rMyIcon))

        self.btnSearch.clicked.connect(self.Search)
        rMyIcon = QtGui.QPixmap("res/search.png")
        self.btnSearch.setIcon(QtGui.QIcon(rMyIcon))

        self.btnReset.clicked.connect(self.Reset)
        rMyIcon = QtGui.QPixmap("res/reset.png")
        self.btnReset.setIcon(QtGui.QIcon(rMyIcon))

        self.btnCloseWarning.clicked.connect(self.closeWarning)
        rMyIcon = QtGui.QPixmap("res/close_1.png")
        self.btnCloseWarning.setIcon(QtGui.QIcon(rMyIcon))

        self.btnDownload.clicked.connect(self.Download)
        self.btnDownload.setStyleSheet("background-image: url(res/excel.png); background-attachment: fixed")

        self.btnpdfDownload.clicked.connect(self.pdfDownload)
        self.btnpdfDownload.setStyleSheet(
            "background-image: url(res/pdf.png); background-attachment: fixed")

        #self.urlEdit = self.findChild(QtWidgets.QLabel, 'urlEdit')  # Find the button

        # self.calenFromDate.clicked.connect(self.)

        self.lineEditDefectName.setStyleSheet("color: rgb(0, 0, 0);")

        self.labelTotalCell.setStyleSheet("image: url(res/back_ground.png);\ncolor: rgb(255,255,255);")
        self.labelTotalDefect.setStyleSheet("image: url(res/back_ground.png);\ncolor: rgb(255,255,255);")

        self.DATA_POINTS_TO_DISPLAY = 180

        # Automatically pops from left if length is full
        self.defect1_data = deque(maxlen=self.DATA_POINTS_TO_DISPLAY)
        self.defect2_data = deque(maxlen=self.DATA_POINTS_TO_DISPLAY)
        self.defect3_data = deque(maxlen=self.DATA_POINTS_TO_DISPLAY)
        self.defect4_data = deque(maxlen=self.DATA_POINTS_TO_DISPLAY)
        self.defect5_data = deque(maxlen=self.DATA_POINTS_TO_DISPLAY)
        self.detect1_count=0
        self.detect2_count=0
        self.detect3_count=0
        self.detect4_count=0
        self.detect5_count=0
        self.detect1_total=0
        self.detect2_total=0
        self.detect3_total=0
        self.detect4_total=0
        self.detect5_total=0
        # Create Plot Widget
        #self.plotWidget = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        # Add Background colour to white

        # Enable/disable plot squeeze (Fixed axis movement)
       
        
        self.liveChart = QChart()
        self.liveChart.legend().hide()
        #self.liveChart.resize(16777215, 300)
        #self.liveChart.setTheme(QChart.ChartThemeBlueCerulean)
        self.liveChartView = QChartView(self.liveChart)       

        self.axisX = QDateTimeAxis()
        self.mintime = QDateTime.currentDateTime()
        self.maxtime = self.mintime.addSecs(self.DATA_POINTS_TO_DISPLAY)
        self.axisX.setRange(self.mintime,self.maxtime)        
        self.axisX.setFormat("hh:mm:ss")
        self.liveChart.addAxis(self.axisX, Qt.AlignBottom)
        # self.setAxisX(self.axisX, series)
        
        self.axisY = QValueAxis()
        self.axisY.setRange(0,5)
        self.axisY.setTickCount(6)
        self.axisY.setLabelFormat("%d")
        self.liveChart.addAxis(self.axisY, Qt.AlignLeft)

        
        

        #first series
        ## SeriesUpper1 is the value
        ## SeriesLower1 is X axis
        
        

        #first series
        ## SeriesUpper2 is the value
        ## SeriesLower2 is X axis
        
        '''
        self.plotlayout = QVBoxLayout()
        self.plotlayout.setSpacing(0)
        self.plotlayout.setContentsMargins(0,0,0,0)
        self.plotlayout.addWidget(self.plotWidget)      
        '''
        self.liveLayout = QVBoxLayout(self.plotWidget)
        self.liveLayout.setSpacing(0)
        self.liveLayout.setContentsMargins(0,0,0,0)
        self.liveLayout.addWidget(self.liveChartView)
        self.liveChartView.setMinimumSize(QtCore.QSize(600, 200))
        self.liveChartView.setMinimumSize(QtCore.QSize(600, 200))
        self.xlabels = QtWidgets.QLabel()
        #self.defects = QtWidgets.QPushButton(self.frame)
        self.xlabels.setMinimumSize(QtCore.QSize(30, 30))
        self.xlabels.setMaximumSize(QtCore.QSize(30, 30))
        self.xlabels.setText("")

        self.xlabels.setStyleSheet("color: rgb(255, 255, 255);")
        timeimg = QtGui.QPixmap("res/time.png")
        self.xlabels.setPixmap(timeimg)        
        self.xlabels.setMinimumSize(QtCore.QSize(550, 30))
        self.xlabels.setMaximumSize(QtCore.QSize(550, 30))

        self.liveLayout.addWidget(self.xlabels)
        



        #self.liveChart.setBackgroundBrush(QBrush(Qt.GlobalColor.black))
        #self.liveChart.setPlotAreaBackgroundVisible()
        #self.liveChart.setPlotAreaBackgroundBrush(QBrush(Qt.GlobalColor.white))

        self.total_count = 0
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(800)

        self.series = QPieSeries()
        self.chart = QChart()
        #self.chart.resize(QSizeF(180, 180))
        self.chartView = QChartView(self.chart)
        #self.chartView.setRenderHint(QPainter.Antialiasing)
        
        self.chartView.setChart(self.chart)

           

        minSize = 0.5
        maxSize = 1
        self.series.setHoleSize(minSize)
        self.series.setPieSize(maxSize)
       


        self.labels=['Bus_Bar_Wrong_Orientation','BusBar_Print_Defect','ExcessAL_paste_onSilverPad','MissingAL_paste','Missing_Silver_Pad']
        for j in range(0,5):
            value = 10
            slice_ = QPieSlice(self.labels[j], value)
            #slice_.setLabelVisible()
    
            #slice_.setLabelPosition(QPieSlice.LabelOutside)
            if(j==0):
                slice_.setColor(QColor(252,170,159)) 
            if(j==1):
                slice_.setColor(QColor(121,176,230)) 
            if(j==2):
                slice_.setColor(QColor(126,249,190))
            if(j==3):
                slice_.setColor(QColor(249,245,126))
            if(j==4):
                slice_.setColor(QColor(249,126,248))                      
            self.series.append(slice_)           

        
        self.chart.addSeries(self.series)
        self.chart.legend().hide()
        #self.chart.hide()
        #
        # QHBoxLayout
        self.layout = QVBoxLayout(self.chartFrame)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.addWidget(self.chartView)      
        self.ylabels = QtWidgets.QLabel()
        #self.defects = QtWidgets.QPushButton(self.frame)
        
        #self.ylabels.setText("xxxx")

        self.ylabels.setStyleSheet("color: rgb(255, 255, 255);")
        piimg = QtGui.QPixmap("res/pi.png")
        self.ylabels.setPixmap(piimg)        
        self.ylabels.setMinimumSize(QtCore.QSize(180, 55))
        self.ylabels.setMaximumSize(QtCore.QSize(180, 55))

        self.layout.addWidget(self.ylabels)


        self.vh = self.defectTableWidget.verticalHeader()
        self.vh.setDefaultSectionSize(100)

        self.defectTableWidget.horizontalHeader().setStretchLastSection(True)
        self.defectTableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        #self.plotWidget.setLayout(layout)
        # self.button.clicked.connect(self.printButtonPressed) # Remember to pass the definition/method, not the return value!
        #
        # self.input = self.findChild(QtWidgets.QLineEdit, 'input')
        # self.liveLine1 = self.findChild(QtWidgets.QLabel, 'liveLine1')
        # self.live1Detect = self.findChild(QtWidgets.QLabel, 'live1Detect')
        # self.labelWarning = self.findChild(QtWidgets.QLabel, 'labelWarning')

        self.myOtherWindow = CameraURL()
        p = self.myOtherWindow.palette()
        p.setColor(self.myOtherWindow.backgroundRole(), QtGui.QColor(60, 60, 60))
        self.myOtherWindow.setBackgroundRole(True)
        self.myOtherWindow.setPalette(p)

    def update(self):
           
        '''for d1 in self.defect1_data:
            for k, v in d1.items():
                print(k,v)

        for d1 in self.defect2_data:
            for k, v in d1.items():
                print(k,v)'''
        #print("update")

        if(len(self.defect1_data)<1 and len(self.defect2_data)<1):
            #print("no")
            return
        
        self.liveChart.removeAllSeries()
       

        self.now = QDateTime.currentDateTime()
        #if(self.now>self.maxtime):
        #    self.maxtime=self.now
        #    self.min=QDateTime.fromMSecsSinceEpoch(self.maxtime.toMSecsSinceEpoch()-self.DATA_POINTS_TO_DISPLAY*1000)
        
        if(self.now>self.maxtime):
            self.maxtime=self.now
            self.mintime=QDateTime.fromMSecsSinceEpoch(self.now.toMSecsSinceEpoch()-self.DATA_POINTS_TO_DISPLAY*1000)
            #self.mintime=QDateTime.fromString(self.defect1_data[0]['x'],"yyyy-MM-dd hh:mm:ss")

        #offset = self.defect1_data[0]['x']

        self.liveChart.removeAxis(self.axisX)
        self.axisX =  QDateTimeAxis()      

        #self.mintime = QDataTime.fromString()
        #self.maxtime = self.mintime.addSecs(self.DATA_POINTS_TO_DISPLAY)
        self.axisX.setRange(self.mintime,self.maxtime)        
        self.axisX.setFormat("hh:mm:ss")
        self.liveChart.addAxis(self.axisX, Qt.AlignBottom)

        self.areaSeriesUpper1 = QLineSeries()    
        self.areaSeriesLower1 = QLineSeries() 
        self.areaSeriesUpper1.append(self.mintime.toMSecsSinceEpoch(),5)
        self.areaSeriesLower1.append(self.mintime.toMSecsSinceEpoch(),0)
        self.areaSeriesUpper1.append(self.mintime.toMSecsSinceEpoch(),0)
        self.areaSeriesLower1.append(self.mintime.toMSecsSinceEpoch(),0)
        for i in range(0,self.DATA_POINTS_TO_DISPLAY):
            temp_time = self.mintime.addSecs(i)
            temp_time_str = temp_time.toString('yyyy-MM-dd hh:mm:ss')     
            temp=0
            for j in range(0,len(self.defect1_data)):
                #print(temp_time_str)
                #print(self.defect1_data[j]['x'])
                if(temp_time_str==self.defect1_data[j]['x']):
                    temp=int(self.defect1_data[j]['y'])          
                    #print(temp)         
                    break
            self.areaSeriesUpper1.append(temp_time.toMSecsSinceEpoch(),temp)
            self.areaSeriesLower1.append(temp_time.toMSecsSinceEpoch(),0)
        

        self.areaSeries1 = QAreaSeries(self.areaSeriesUpper1,self.areaSeriesLower1)   
        self.areaSeries1.setName("Bus_Bar_Wrong_Orientation") 
        self.areaSeries1.setPen(QPen(QColor(229,165,165)))
        self.areaSeries1.setBrush(QBrush(QColor(254,179,174,230)))

        self.areaSeriesUpper2 = QLineSeries()    
        self.areaSeriesLower2 = QLineSeries()            
        self.areaSeriesUpper2.append(self.mintime.toMSecsSinceEpoch(),5)
        self.areaSeriesLower2.append(self.mintime.toMSecsSinceEpoch(),0)
        self.areaSeriesUpper2.append(self.mintime.toMSecsSinceEpoch(),0)
        self.areaSeriesLower2.append(self.mintime.toMSecsSinceEpoch(),0)
        for i in range(0,self.DATA_POINTS_TO_DISPLAY):
            temp_time = self.mintime.addSecs(i)
            temp_time_str = temp_time.toString('yyyy-MM-dd hh:mm:ss')     
            temp=0
            for j in range(0,len(self.defect2_data)):
                #print(temp_time_str)
                #print(self.defect1_data[j]['x'])
                if(temp_time_str==self.defect2_data[j]['x']):
                    temp=int(self.defect2_data[j]['y'])                   
                    break
            self.areaSeriesUpper2.append(temp_time.toMSecsSinceEpoch(),temp)
            self.areaSeriesLower2.append(temp_time.toMSecsSinceEpoch(),0)
        

        self.areaSeries2 = QAreaSeries(self.areaSeriesUpper2,self.areaSeriesLower2)    
        self.areaSeries2.setName("BusBar_Print_Defect") 
        self.areaSeries2.setPen(QPen(QColor(118,160,198)))
        self.areaSeries2.setBrush(QBrush(QColor(118,178,232,230)))


        self.areaSeriesUpper3 = QLineSeries()    
        self.areaSeriesLower3 = QLineSeries()            
        self.areaSeriesUpper3.append(self.mintime.toMSecsSinceEpoch(),5)
        self.areaSeriesLower3.append(self.mintime.toMSecsSinceEpoch(),0)
        self.areaSeriesUpper3.append(self.mintime.toMSecsSinceEpoch(),0)
        self.areaSeriesLower3.append(self.mintime.toMSecsSinceEpoch(),0)
        for i in range(0,self.DATA_POINTS_TO_DISPLAY):
            temp_time = self.mintime.addSecs(i)
            temp_time_str = temp_time.toString('yyyy-MM-dd hh:mm:ss')     
            temp=0
            for j in range(0,len(self.defect3_data)):
                #print(temp_time_str)
                #print(self.defect1_data[j]['x'])
                if(temp_time_str==self.defect3_data[j]['x']):
                    temp=int(self.defect3_data[j]['y'])                   
                    break
            self.areaSeriesUpper3.append(temp_time.toMSecsSinceEpoch(),temp)
            self.areaSeriesLower3.append(temp_time.toMSecsSinceEpoch(),0)
        

        self.areaSeries3 = QAreaSeries(self.areaSeriesUpper3,self.areaSeriesLower3)    
        self.areaSeries3.setName("ExcessAL_paste_onSilverPad") 
        self.areaSeries3.setPen(QPen(QColor(104,231,170)))
        self.areaSeries3.setBrush(QBrush(QColor(126,249,190,230)))

        self.areaSeriesUpper4 = QLineSeries()    
        self.areaSeriesLower4 = QLineSeries()            
        self.areaSeriesUpper4.append(self.mintime.toMSecsSinceEpoch(),5)
        self.areaSeriesLower4.append(self.mintime.toMSecsSinceEpoch(),0)
        self.areaSeriesUpper4.append(self.mintime.toMSecsSinceEpoch(),0)
        self.areaSeriesLower4.append(self.mintime.toMSecsSinceEpoch(),0)
        for i in range(0,self.DATA_POINTS_TO_DISPLAY):
            temp_time = self.mintime.addSecs(i)
            temp_time_str = temp_time.toString('yyyy-MM-dd hh:mm:ss')     
            temp=0
            for j in range(0,len(self.defect4_data)):
                #print(temp_time_str)
                #print(self.defect1_data[j]['x'])
                if(temp_time_str==self.defect4_data[j]['x']):
                    temp=int(self.defect4_data[j]['y'])                   
                    break
            self.areaSeriesUpper4.append(temp_time.toMSecsSinceEpoch(),temp)
            self.areaSeriesLower4.append(temp_time.toMSecsSinceEpoch(),0)
        

        self.areaSeries4 = QAreaSeries(self.areaSeriesUpper4,self.areaSeriesLower4)    
        self.areaSeries4.setName("MissingAL_paste") 
        self.areaSeries4.setPen(QPen(QColor(227,223,114)))
        self.areaSeries4.setBrush(QBrush(QColor(249,245,126,230)))

        self.areaSeriesUpper5 = QLineSeries()    
        self.areaSeriesLower5 = QLineSeries()            
        self.areaSeriesUpper5.append(self.mintime.toMSecsSinceEpoch(),5)
        self.areaSeriesLower5.append(self.mintime.toMSecsSinceEpoch(),0)
        self.areaSeriesUpper5.append(self.mintime.toMSecsSinceEpoch(),0)
        self.areaSeriesLower5.append(self.mintime.toMSecsSinceEpoch(),0)
        for i in range(0,self.DATA_POINTS_TO_DISPLAY):
            temp_time = self.mintime.addSecs(i)
            temp_time_str = temp_time.toString('yyyy-MM-dd hh:mm:ss')     
            temp=0
            for j in range(0,len(self.defect5_data)):
                #print(temp_time_str)
                #print(self.defect1_data[j]['x'])
                if(temp_time_str==self.defect5_data[j]['x']):
                    temp=int(self.defect5_data[j]['y'])                   
                    break
            self.areaSeriesUpper5.append(temp_time.toMSecsSinceEpoch(),temp)
            self.areaSeriesLower5.append(temp_time.toMSecsSinceEpoch(),0)
        

        self.areaSeries5 = QAreaSeries(self.areaSeriesUpper5,self.areaSeriesLower5)    
        self.areaSeries5.setName("Missing_Silver_Pad") 
        self.areaSeries5.setPen(QPen(QColor(226,108,225)))
        self.areaSeries5.setBrush(QBrush(QColor(249,126,248,230)))


        

        self.liveChart.addSeries(self.areaSeries1)
        self.liveChart.addSeries(self.areaSeries2)
        self.liveChart.addSeries(self.areaSeries3)
        self.liveChart.addSeries(self.areaSeries4)
        self.liveChart.addSeries(self.areaSeries5)
        
        


        
        #self.chart.legend().show()
        series = self.chart.series()        
        series = series[0]
        slices = series.slices()
        
        slices[0].setValue(self.detect1_total)
        slices[1].setValue(self.detect2_total)
        slices[2].setValue(self.detect3_total)
        slices[3].setValue(self.detect4_total)
        slices[4].setValue(self.detect5_total)
       

        



    def clear_plot_data(self):
        self.defect1_data.clear()
        self.defect2_data.clear()
        self.defect3_data.clear()
        self.defect4_data.clear()
        self.defect5_data.clear()
        self.detect1_count=0
        self.detect2_count=0
        self.detect3_count=0
        self.detect4_count=0
        self.detect5_count=0
        self.detect1_total=0
        self.detect2_total=0
        self.detect3_total=0
        self.detect4_total=0
        self.detect5_total=0
        self.liveChart.removeAllSeries()

    def pdfDownload(self):

        if(self.fromdateEdit.date() > self.todateEdit.date()):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Alert")
            msg.setText("Date Time Range Invalid")
            msg.exec_()
            return False

        if (self.fromdateEdit.date() == self.todateEdit.date() and self.fromTimeEdit.time() > self.toTimeEdit.time()):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Alert")
            msg.setText("Date Time Range Invalid")
            msg.exec_()
            return False

        fromdate = self.fromdateEdit.date().toString("yyyy-MM-dd ")
        fromTime = self.fromTimeEdit.time().toString("hh:mm:ss")

        fromdate = fromdate + fromTime

        todate = self.todateEdit.dateTime().toString("yyyy-MM-dd ")
        toTime = self.toTimeEdit.time().toString("hh:mm:ss")
        todate = todate + toTime

        cursor = conn.cursor()
        sql = "SELECT * from defect_database.defect_info WHERE detectedTime between \'" + fromdate + "\' and \'" + todate + "\'"
        cursor.execute(sql)

        pdf = FPDF()
        pdf.set_font("Arial", size=12)
        pdf.add_page()
        col_width = pdf.w / 4.5
        row_height = pdf.font_size

        pdf.cell(col_width*0.5, row_height * 1, txt='SN', border=1)
        pdf.cell(col_width, row_height * 1, txt='Defect Name', border=1)
        pdf.cell(col_width, row_height * 1, txt='Belt Number', border=1)
        pdf.cell(col_width*1.3, row_height * 1, txt='Detected Time', border=1)
        pdf.ln(row_height * 1)

        rowcount = 1
        for data in cursor.fetchall():
            SN = str(rowcount)
            Defect = data[1]
            conveyor = data[2]
            recordtime = data[3]
            recordtime = recordtime.replace(tzinfo=timezone('Asia/Kolkata'))
            recordtime = str(recordtime)
            recordtime = recordtime.split("+")[0]
            # snapshot = row[4]
            # worksheet.write(rowcount, 0, SN)
            # worksheet.write(rowcount,1, Defect)
            # worksheet.write(rowcount, 2, conveyor)
            # worksheet.write(rowcount, 3, recordtime)
            # worksheet.write(rowcount, 4, snapshot)

            pdf.cell(col_width*0.5,row_height*1,txt=SN, border=1)
            pdf.cell(col_width, row_height * 1, txt=Defect, border=1)
            pdf.cell(col_width, row_height * 1, txt=conveyor, border=1)
            pdf.cell(col_width*1.3, row_height * 1, txt=recordtime, border=1)

            pdf.ln(row_height*1)

            rowcount = rowcount + 1

        cur_time = str(round(time.time()))
        filename = "report" + cur_time + ".pdf"

        pdf.output(filename)

        msgbox = TimerMessageBox(1)
        msgbox.exec_()

        # QMessageBox.about(self, "Info","PDF Report Has Been Successfully Created!")
        # pw = PdfWriter()
        # pw.addPage()
        # pw.setFont('Courier', 12)
        # pw.setHeader('Demo of PrettyTable to PDF')
        # pw.setFooter('Demo of PrettyTable to PDF')
        # for line in lines.split('\n'):
        #     pw.write(line)
        # pw.close()




    def Download(self):
        if (self.fromdateEdit.date() > self.todateEdit.date()):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Alert")
            msg.setText("Date Time Range Invalid")
            msg.exec_()
            return False

        if (self.fromdateEdit.date() == self.todateEdit.date() and self.fromTimeEdit.time() > self.toTimeEdit.time()):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Alert")
            msg.setText("Date Time Range Invalid")
            msg.exec_()
            return False

        fromdate = self.fromdateEdit.date().toString("yyyy-MM-dd ")
        fromTime = self.fromTimeEdit.time().toString("hh:mm:ss")

        fromdate = fromdate + fromTime

        todate = self.todateEdit.dateTime().toString("yyyy-MM-dd ")
        toTime = self.toTimeEdit.time().toString("hh:mm:ss")
        todate = todate + toTime

        cursor = conn.cursor()
        sql = "SELECT * from defect_database.defect_info WHERE detectedTime between \'" + fromdate + "\' and \'" + todate + "\'"
        cursor.execute(sql)

        # create workbook
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('report')
        worksheet.write(0, 0, label="SN")
        worksheet.write(0, 1, label="Defect")
        worksheet.write(0, 2, label="Conveyor")
        worksheet.write(0, 3, label="DateTime")
        rowcount = 1
        for row in cursor.fetchall():
            SN = rowcount
            Defect = row[1]
            conveyor = row[2]
            recordtime = row[3]
            recordtime = recordtime.replace(tzinfo=timezone('Asia/Kolkata'))
            recordtime = str(recordtime)
            recordtime = recordtime.split("+")[0]
            # snapshot = row[4]
            worksheet.write(rowcount, 0, SN)
            worksheet.write(rowcount, 1, Defect)
            worksheet.write(rowcount, 2, conveyor)
            worksheet.write(rowcount, 3, recordtime)
            # worksheet.write(rowcount, 4, snapshot)
            rowcount = rowcount + 1

        cur_time = str(round(time.time()))
        filename = "report" + cur_time + ".xls"


        workbook.save(filename)
        # QMessageBox.about(self, "Info", "Excel Report Has Been Successfully Created!")
        messagebox = TimerMessageBox(1)
        messagebox.exec_()
        # self.showMinimized()

    def closeWarning(self):
        self.nowarning_image = cv2.resize(self.nowarning_image, (self.labelWarning.width(), self.labelWarning.height()))
        height, width, byteValue = self.nowarning_image.shape
        byteValue = byteValue * width

        self.nowarning_image = cv2.cvtColor(self.nowarning_image, cv2.COLOR_BGR2RGB)
        self.nowarning_qimage = QtGui.QImage(self.nowarning_image, self.nowarning_image.shape[1],
                                             self.nowarning_image.shape[0], byteValue,
                                             QtGui.QImage.Format_RGB888)
        self.pix = QtGui.QPixmap.fromImage(self.nowarning_qimage)
        self.labelWarning.setPixmap(self.pix)

    def Reset(self):
        conn.cursor().execute("DELETE from defect_database.defect_info WHERE 1")
        self.defectTableWidget.setRowCount(0)
        #self.clear_plot_data()
        #self.chart.hide()

    def Search(self):
        global imagePath
        defect_name = self.lineEditDefectName.text()
        cursor = conn.cursor()
        cursor.execute("SELECT * from defect_database.defect_info WHERE defect_name = %s", (defect_name,))
        rowCount = 0
        self.defectTableWidget.setRowCount(0)
        for row in cursor.fetchall():
            img_data = row[4]
            with open("rec_temp.jpg", "wb") as img:
                img.write(img_data)
            imagePath = "rec_temp.jpg"
            row_number = row[0]
            name = row[1]
            belt_number = row[2]
            detectedTime = row[3]

            year = detectedTime.year
            dateStr = str(detectedTime.year) + "-" + str(detectedTime.month) + "-" + str(detectedTime.day) + " "\
                      + str(detectedTime.hour) + ":" + str(detectedTime.minute) + ":" + str(detectedTime.second)
            self.defectTableWidget.insertRow(rowCount)
            self.defectTableWidget.setItem(rowCount, 0, QtGui.QTableWidgetItem(row_number))
            self.defectTableWidget.setItem(rowCount, 1, QtGui.QTableWidgetItem(name))
            self.defectTableWidget.setItem(rowCount, 2, QtGui.QTableWidgetItem(belt_number))
            self.defectTableWidget.setItem(rowCount, 3, QtGui.QTableWidgetItem(dateStr))
            self.defectTableWidget.setCellWidget(rowCount, 4, ImgWidget(self))

            rowCount = rowCount + 1

        self.labelTotalDefect.setText(" Total Defect: " + str(rowCount))
        self.labelTotalCell.setText(" Total Cell: " + str(rowCount))

    def openCamera(self):
        self.myOtherWindow.show()

    def openVideo(self):
        global stream_url

        root = tk.Tk()
        root.withdraw()

        stream_url = filedialog.askopenfilename()
        self.urlEdit.setText(stream_url)

    def startLiveStream(self):
        global stream_url
        global imagePath
        self.chart.show()
        self.urlEdit.setText(stream_url)
        cap = cv2.VideoCapture(stream_url)
        if (self.running):
            self.running = False
            rMyIcon = QtGui.QPixmap("res/start.png")
            self.startBtn.setIcon(QtGui.QIcon(rMyIcon))
        else:
            self.running = True
            rMyIcon = QtGui.QPixmap("res/stop.png")
            self.startBtn.setIcon(QtGui.QIcon(rMyIcon))
            self.defectTableWidget.setRowCount(0)

        rowCount = 0
        while self.running:
            ret, frame = cap.read()
            if (ret == False):
                self.running = False
                rMyIcon = QtGui.QPixmap("res/start.png")
                self.startBtn.setIcon(QtGui.QIcon(rMyIcon))
                break
            # frame = np.rot90(frame)
            # frame = cv2.resize(frame,(720,480))

            ww = frame.shape[1]
            hh = frame.shape[0]

            #line1Frame = frame[0:hh-1, 0:int(ww/2)]
           # line2Frame = frame[0:hh-1, int(ww / 2):ww - 1]

            frame = imutils.resize(frame, width=700)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blur, 100, 200)
            th3 = cv2.adaptiveThreshold(edges, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            contours, _ = cv2.findContours(th3, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            height, width = edges.shape
            min_x, min_y = width, height
            max_x = max_y = 0

            
            self.detect1_count=0
            self.detect2_count=0
            self.detect3_count=0
            self.detect4_count=0
            self.detect5_count=0
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 10000 and area > 13000:
                    continue
                (x, y, w, h) = cv2.boundingRect(cnt)
                min_x, max_x = min(x, min_x), max(x + w, max_x)  # if (w< 400 and w>300) and (h<400 and w>300):
                min_y, max_y = min(y, min_y), max(y + h, max_y)
                if (w < 370 and w > 310) and (h < 370 and w > 310):
                    roi = frame[y:y + h, x:x + w]
                    result = tfnet.return_predict(roi)
                    if (len(result) > 0):
                        self.warning_image = cv2.resize(self.warning_image, (self.labelWarning.width(), self.labelWarning.height()))
                        height, width, byteValue = self.warning_image.shape
                        byteValue = byteValue * width

                        self.rgbimage = cv2.cvtColor(self.warning_image, cv2.COLOR_BGR2RGB)
                        self.warning_qimage = QtGui.QImage(self.rgbimage, self.rgbimage.shape[1],
                                                           self.rgbimage.shape[0], byteValue,
                                                           QtGui.QImage.Format_RGB888)
                        self.pix = QtGui.QPixmap.fromImage(self.warning_qimage)
                        self.labelWarning.setPixmap(self.pix)
                    else:
                        self.nowarning_image = cv2.resize(self.nowarning_image, (self.labelWarning.width(), self.labelWarning.height()))
                        height, width, byteValue = self.nowarning_image.shape
                        byteValue = byteValue * width

                        self.rgbimage = cv2.cvtColor(self.nowarning_image, cv2.COLOR_BGR2RGB)
                        self.nowarning_qimage = QtGui.QImage(self.rgbimage, self.rgbimage.shape[1],
                                                           self.rgbimage.shape[0], byteValue,
                                                           QtGui.QImage.Format_RGB888)
                        self.pix = QtGui.QPixmap.fromImage(self.nowarning_qimage)
                        self.labelWarning.setPixmap(self.pix)
                    for elem in result:

                        if(elem['label']=='Bus_Bar_Wrong_Orientation'):
                            self.detect1_count=self.detect1_count+1
                            self.detect1_total=self.detect1_total+1
                        if(elem['label']=='BusBar_Print_Defect'):
                            self.detect2_count=self.detect2_count+1
                            self.detect2_total=self.detect2_total+1
                        if(elem['label']=='ExcessAL_paste_onSilverPad'):
                            self.detect3_count=self.detect3_count+1
                            self.detect3_total=self.detect3_total+1
                        if(elem['label']=='MissingAL_paste'):
                            self.detect4_count=self.detect4_count+1
                            self.detect4_total=self.detect4_total+1
                        if(elem['label']=='Missing_Silver_Pad'):
                            self.detect5_count=self.detect5_count+1
                            self.detect5_total=self.detect5_total+1

                        top_x, top_y = elem["topleft"]["x"], elem["topleft"]["y"]
                        bot_x, bot_y = elem["bottomright"]["x"], elem["bottomright"]["y"]
                        cv2.rectangle(roi, (top_x, top_y), (bot_x, bot_y), (0, 0, 255), 2)
                        cv2.putText(roi, elem["label"], (top_x - 10, top_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                    (255, 255, 255), 2, cv2.LINE_AA)

                        resized = cv2.resize(roi, (100, 100))
                        cv2.imwrite("temp.jpg", resized)
                        with open("temp.jpg", "rb") as image:
                            f = image.read()
                            blob_value = bytearray(f)


                        sql = """insert into defect_database.defect_info (defect_name, belt_number, detectedTime, defect_snapshot)
                                 values (%s, %s, %s, %s) 
                                """
                        cur_dateTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        conn.cursor().execute(sql, ('defect1', 'Line1', cur_dateTime,blob_value))
                        conn.commit()
                        
                        flag = 0
                        for data in self.defect1_data:
                            if(data['x']==cur_dateTime):
                                if(self.detect1_count>=data['y']):
                                    data['y']=self.detect1_count
                                    flag = 1
                        if(flag==0):
                            self.defect1_data.append({'x': cur_dateTime,'y': self.detect1_count})

                        flag = 0
                        for data in self.defect2_data:
                            if(data['x']==cur_dateTime):
                                if(self.detect2_count>=data['y']):
                                    data['y']=self.detect2_count
                                    flag = 1
                        if(flag==0):
                            self.defect2_data.append({'x': cur_dateTime,'y': self.detect2_count})

                        flag = 0
                        for data in self.defect3_data:
                            if(data['x']==cur_dateTime):
                                if(self.detect3_count>=data['y']):
                                    data['y']=self.detect3_count
                                    flag = 1
                        if(flag==0):
                            self.defect3_data.append({'x': cur_dateTime,'y': self.detect3_count})

                        flag = 0
                        for data in self.defect4_data:
                            if(data['x']==cur_dateTime):
                                if(self.detect4_count>=data['y']):
                                    data['y']=self.detect4_count
                                    flag = 1
                        if(flag==0):
                            self.defect4_data.append({'x': cur_dateTime,'y': self.detect4_count})

                        flag = 0
                        for data in self.defect5_data:
                            if(data['x']==cur_dateTime):
                                if(self.detect5_count>=data['y']):
                                    data['y']=self.detect5_count
                                    flag = 1
                        if(flag==0):
                            self.defect5_data.append({'x': cur_dateTime,'y': self.detect5_count})
                        #if(self.detect2_count>0):
                        #self.defect2_data.append({'x': cur_dateTime,'y': self.detect2_count})
                        #if(self.detect3_count>0):
                        #self.defect3_data.append({'x': cur_dateTime,'y': self.detect3_count})
                        #if(self.detect4_count>0):
                        #self.defect4_data.append({'x': cur_dateTime,'y': self.detect4_count})
                        #if(self.detect5_count>0):
                        #self.defect5_data.append({'x': cur_dateTime,'y': self.detect5_count})

                        #  show display in table
                        imagePath = "current_temp.jpg"
                        cv2.imwrite(imagePath, resized)
                        rowCount = rowCount + 1
                        self.defectTableWidget.insertRow(0)
                        self.defectTableWidget.setItem(0, 0, QtGui.QTableWidgetItem(str(self.total_count)))
                        self.defectTableWidget.setItem(0, 1, QtGui.QTableWidgetItem("defect1"))
                        self.defectTableWidget.setItem(0, 2, QtGui.QTableWidgetItem("Line1"))
                        self.defectTableWidget.setItem(0, 3, QtGui.QTableWidgetItem(cur_dateTime))
                        self.defectTableWidget.setCellWidget(0, 4, ImgWidget(self))
                        self.labelTotalDefect.setText(" Total Defect: " + str(rowCount))
                        self.labelTotalCell.setText(" Total Cell: " + str(rowCount))

                    

                    self.resized_detected = cv2.resize(roi, (self.live1Detect.width(), self.live1Detect.height()))
                    height, width, byteValue = self.resized_detected.shape
                    byteValue = byteValue * width

                    self.resized_detected = cv2.cvtColor(self.resized_detected, cv2.COLOR_BGR2RGB)
                    self.detected_frame = QtGui.QImage(self.resized_detected, self.resized_detected.shape[1], self.resized_detected.shape[0], byteValue, QtGui.QImage.Format_RGB888)
                    self.pix = QtGui.QPixmap.fromImage(self.detected_frame)
                    self.live1Detect.setPixmap(self.pix)

            
            
            cur_dateTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
          
            
            
            
            
              

            self.resized = cv2.resize(frame, (self.liveLine1.width(), self.liveLine1.height()))
            height, width, byteValue = self.resized.shape
            byteValue = byteValue * width

            self.resized = cv2.cvtColor(self.resized, cv2.COLOR_BGR2RGB)
            self.frame_image = QtGui.QImage(self.resized, self.resized.shape[1],
                                               self.resized.shape[0], byteValue, QtGui.QImage.Format_RGB888)
            self.pix = QtGui.QPixmap.fromImage(self.frame_image)
            self.liveLine1.setPixmap(self.pix)
            cv2.waitKey(1)


            #################for line2
            # frame1 = imutils.resize(line2Frame, width=700)
            # gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            # blur1 = cv2.GaussianBlur(gray1, (5, 5), 0)
            # edges1 = cv2.Canny(blur1, 100, 200)
            # th31 = cv2.adaptiveThreshold(edges1, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            # contours1, _ = cv2.findContours(th31, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            # height1, width1 = edges1.shape
            # min_x1, min_y1 = width1, height1
            # max_x1 = max_y1 = 0
            # for cnt1 in contours1:
            #     area1 = cv2.contourArea(cnt1)
            #     if area1 < 10000 and area1 > 13000:
            #         continue
            #     (x1, y1, w1, h1) = cv2.boundingRect(cnt1)
            #     min_x1, max_x1 = min(x1, min_x1), max(x1 + w1, max_x1)  # if (w< 400 and w>300) and (h<400 and w>300):
            #     min_y1, max_y1 = min(y1, min_y1), max(y + h1, max_y1)
            #     if (w1 < 370 and w1 > 310) and (h1 < 370 and w1 > 310):
            #         roi1 = frame1[y1:y1 + h1, x1:x1 + w1]
            #         result1 = tfnet.return_predict(roi1)
            #         if (len(result1) > 0):
            #             self.warning_image = cv2.resize(self.warning_image,
            #                                             (self.labelWarning.width(), self.labelWarning.height()))
            #             height1, width1, byteValue1 = self.warning_image.shape
            #             byteValue1 = byteValue1 * width1
            #
            #             self.rgbimage = cv2.cvtColor(self.warning_image, cv2.COLOR_BGR2RGB)
            #             self.warning_qimage = QtGui.QImage(self.rgbimage, self.rgbimage.shape[1],
            #                                                self.rgbimage.shape[0], byteValue1,
            #                                                QtGui.QImage.Format_RGB888)
            #             self.pix = QtGui.QPixmap.fromImage(self.warning_qimage)
            #             self.labelWarning.setPixmap(self.pix)
            #         else:
            #             self.nowarning_image = cv2.resize(self.nowarning_image,
            #                                               (self.labelWarning.width(), self.labelWarning.height()))
            #             height1, width1, byteValue1 = self.nowarning_image.shape
            #             byteValue1 = byteValue1 * width1
            #
            #             self.rgbimage = cv2.cvtColor(self.nowarning_image, cv2.COLOR_BGR2RGB)
            #             self.nowarning_qimage = QtGui.QImage(self.rgbimage, self.rgbimage.shape[1],
            #                                                  self.rgbimage.shape[0], byteValue1,
            #                                                  QtGui.QImage.Format_RGB888)
            #             self.pix = QtGui.QPixmap.fromImage(self.nowarning_qimage)
            #             self.labelWarning.setPixmap(self.pix)
            #         for elem in result1:
            #             top_x, top_y = elem["topleft"]["x"], elem["topleft"]["y"]
            #             bot_x, bot_y = elem["bottomright"]["x"], elem["bottomright"]["y"]
            #             cv2.rectangle(roi1, (top_x, top_y), (bot_x, bot_y), (0, 0, 255), 2)
            #             cv2.putText(roi1, elem["label"], (top_x - 10, top_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
            #                         (255, 255, 255), 2, cv2.LINE_AA)
            #
            #             resized = cv2.resize(roi1, (100, 100))
            #             cv2.imwrite("temp.jpg", resized)
            #             with open("temp.jpg", "rb") as image:
            #                 f = image.read()
            #                 blob_value = bytearray(f)
            #
            #             sql = """insert into defect_database.defect_info (defect_name, belt_number, detectedTime, defect_snapshot)
            #                                  values (%s, %s, %s, %s)
            #                             """
            #             cur_dateTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            #             conn.cursor().execute(sql, ('defect2', 'Line2', cur_dateTime, blob_value))
            #             conn.commit()
            #             self.total_count = self.total_count + 1
            #
            #             if (self.total_count < 200):
            #                 self.defect1_data.append(
            #                     {'x': self.total_count,
            #                      'y': 20})
            #                 self.defect2_data.append(
            #                     {'x': self.total_count,
            #                      'y': 50})
            #             else:
            #                 self.defect1_data.append(
            #                     {'x': self.total_count,
            #                      'y': 30})
            #                 self.defect2_data.append(
            #                     {'x': self.total_count,
            #                      'y': 60})
            #
            #             #  show display in table
            #             imagePath = "current_temp.jpg"
            #             cv2.imwrite(imagePath, resized)
            #             rowCount = rowCount + 1
            #             self.defectTableWidget.insertRow(0)
            #             self.defectTableWidget.setItem(0, 0, QtGui.QTableWidgetItem(str(self.total_count)))
            #             self.defectTableWidget.setItem(0, 1, QtGui.QTableWidgetItem("defect2"))
            #             self.defectTableWidget.setItem(0, 2, QtGui.QTableWidgetItem("Line2"))
            #             self.defectTableWidget.setItem(0, 3, QtGui.QTableWidgetItem(cur_dateTime))
            #             self.defectTableWidget.setCellWidget(0, 4, ImgWidget(self))
            #             self.labelTotalDefect.setText(" Total Defect: " + str(rowCount))
            #             self.labelTotalCell.setText(" Total Cell: " + str(rowCount))
            #
            #         self.resized_detected = cv2.resize(roi1, (self.live1Detect.width(), self.live1Detect.height()))
            #         height1, width1, byteValue1 = self.resized_detected.shape
            #         byteValue1 = byteValue1 * width1
            #
            #         self.resized_detected = cv2.cvtColor(self.resized_detected, cv2.COLOR_BGR2RGB)
            #         self.detected_frame = QtGui.QImage(self.resized_detected, self.resized_detected.shape[1],
            #                                            self.resized_detected.shape[0], byteValue1,
            #                                            QtGui.QImage.Format_RGB888)
            #         self.pix = QtGui.QPixmap.fromImage(self.detected_frame)
            #         self.live2Detect.setPixmap(self.pix)
            #
            # self.resized = cv2.resize(frame1, (self.liveLine2.width(), self.liveLine2.height()))
            # height1, width1, byteValue1 = self.resized.shape
            # byteValue1 = byteValue1 * width1
            #
            # self.resized = cv2.cvtColor(self.resized, cv2.COLOR_BGR2RGB)
            # self.frame_image = QtGui.QImage(self.resized, self.resized.shape[1],
            #                                 self.resized.shape[0], byteValue1, QtGui.QImage.Format_RGB888)
            # self.pix = QtGui.QPixmap.fromImage(self.frame_image)
            # self.liveLine2.setPixmap(self.pix)
            # cv2.waitKey(1)
            ###############################

    def minimizeWindow(self):
        self.showMinimized()
    def closeWindow(self):
        if (self.running):
            easygui.msgbox("Please stop stream!", title="Warning")
            return
        self.close()


app = QtWidgets.QApplication(sys.argv)
window = Ui()
window.showFullScreen()
app.exec_()