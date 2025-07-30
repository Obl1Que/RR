# -*- coding: utf-8 -*-

import sys

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMainWindow, QApplication, QGraphicsPixmapItem


class Ui_MainWindow(object):
	def setupUi(self, MainWindow):
		MainWindow.setObjectName("MainWindow")
		MainWindow.resize(1600, 1200)
		MainWindow.setMinimumSize(QtCore.QSize(1600, 1200))

		self.model_path = None
		self.real_path = None

		self.centralwidget = QtWidgets.QWidget(MainWindow)
		self.centralwidget.setObjectName("centralwidget")

		self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.centralwidget)
		self.horizontalLayout_3.setObjectName("horizontalLayout_3")
		self.verticalLayout = QtWidgets.QVBoxLayout()
		self.verticalLayout.setObjectName("verticalLayout")

		self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
		self.graphicsView.setMinimumSize(QtCore.QSize(653, 326))
		self.graphicsView.setMaximumSize(QtCore.QSize(653, 326))
		self.graphicsView.setObjectName("graphicsView")
		self.verticalLayout.addWidget(self.graphicsView)

		self.pushButton_1 = QtWidgets.QPushButton(self.centralwidget)
		self.pushButton_1.setMinimumSize(QtCore.QSize(320, 0))
		self.pushButton_1.setObjectName("pushButton_1")
		self.pushButton_1.clicked.connect(lambda: self.openImg('model'))
		self.verticalLayout.addWidget(self.pushButton_1)

		self.pushButton_2 = QtWidgets.QPushButton(self.centralwidget)
		self.pushButton_2.setObjectName("pushButton_2")
		self.pushButton_2.clicked.connect(lambda: self.openImg('real'))
		self.verticalLayout.addWidget(self.pushButton_2)

		self.line_2 = QtWidgets.QFrame(self.centralwidget)
		self.line_2.setFrameShape(QtWidgets.QFrame.HLine)
		self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
		self.line_2.setObjectName("line_2")
		self.verticalLayout.addWidget(self.line_2)

		self.pushButton_3 = QtWidgets.QPushButton(self.centralwidget)
		self.pushButton_3.setObjectName("pushButton_3")
		self.verticalLayout.addWidget(self.pushButton_3)

		self.pushButton_4 = QtWidgets.QPushButton(self.centralwidget)
		self.pushButton_4.setObjectName("pushButton_4")
		self.verticalLayout.addWidget(self.pushButton_4)

		self.tableWidget = QtWidgets.QTableWidget(self.centralwidget)
		self.tableWidget.setMinimumSize(QtCore.QSize(0, 450))
		self.tableWidget.setMaximumSize(QtCore.QSize(653, 16777215))
		self.tableWidget.setObjectName("tableWidget")
		self.tableWidget.setColumnCount(7)
		self.tableWidget.setRowCount(0)

		for i in range(7):
			item = QtWidgets.QTableWidgetItem()
			self.tableWidget.setHorizontalHeaderItem(i, item)

		self.tableWidget.horizontalHeader().setDefaultSectionSize(93)
		self.verticalLayout.addWidget(self.tableWidget)
		self.horizontalLayout_3.addLayout(self.verticalLayout)

		self.line = QtWidgets.QFrame(self.centralwidget)
		self.line.setFrameShape(QtWidgets.QFrame.VLine)
		self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
		self.line.setObjectName("line")
		self.horizontalLayout_3.addWidget(self.line)

		self.verticalLayout_2 = QtWidgets.QVBoxLayout()
		self.verticalLayout_2.setObjectName("verticalLayout_2")
		self.graphicsView_2 = QtWidgets.QGraphicsView(self.centralwidget)
		self.graphicsView_2.setMinimumSize(QtCore.QSize(820, 0))
		self.graphicsView_2.setObjectName("graphicsView_2")
		self.verticalLayout_2.addWidget(self.graphicsView_2)

		self.graphicsView_1 = QtWidgets.QGraphicsView(self.centralwidget)
		self.graphicsView_1.setMinimumSize(QtCore.QSize(418, 0))
		self.graphicsView_1.setObjectName("graphicsView_1")
		self.verticalLayout_2.addWidget(self.graphicsView_1)
		self.horizontalLayout_3.addLayout(self.verticalLayout_2)

		MainWindow.setCentralWidget(self.centralwidget)

		self.setupUI(MainWindow)
		QtCore.QMetaObject.connectSlotsByName(MainWindow)

	def setupUI(self, MainWindow):
		_translate = QtCore.QCoreApplication.translate
		MainWindow.setWindowTitle(_translate("MainWindow", "Инструмент разметки областей соответствующих контрастов непарных изображений"))
		self.pushButton_1.setText(_translate("MainWindow", "Открыть модельное изображение"))
		self.pushButton_2.setText(_translate("MainWindow", "Открыть реальное изображение"))
		self.pushButton_3.setText(_translate("MainWindow", "Сохранить RGB разметку"))
		self.pushButton_4.setText(_translate("MainWindow", "Сохранить таблицу"))

		self.scene = QtWidgets.QGraphicsScene()
		self.graphicsView.setScene(self.scene)
		self.load_logo("imgs/gosniias.png")

		table_names = ["name", "object_id_model", "class_id_model", "mean_lum_real", "object_id_real", "class_id_real", "mean_lum_real"]

		for idx, name in enumerate(table_names):
			item = self.tableWidget.horizontalHeaderItem(idx)
			item.setText(_translate("MainWindow", name))

	def load_logo(self, image_path):
		pixmap = QPixmap(image_path)
		pixmap = pixmap.scaled(self.graphicsView.width() - 5, self.graphicsView.height() - 5, QtCore.Qt.KeepAspectRatio)
		pixmap_item = QGraphicsPixmapItem(pixmap)
		self.scene.addItem(pixmap_item)

	def openImg(self, type: str):
		dialog = QtWidgets.QFileDialog()
		folder_path = dialog.getExistingDirectory(None, "Выберите папку", "", QtWidgets.QFileDialog.ShowDirsOnly)
		if folder_path:
			if type == "model":
				self.model_path = folder_path + "/test.png"
			elif type == "real":
				self.real_path = folder_path + "/test.png"
			self.setImg(type)

	def setImg(self, type: str):
		path = self.model_path if type == "model" else self.real_path
		if not QtCore.QFile.exists(path):
			print(f"Ошибка: файл {path} не существует!")
			return

		scene = QtWidgets.QGraphicsScene()
		pixmap = QPixmap(path)

		if pixmap.isNull():
			print(f"Ошибка: не удалось загрузить изображение из {path}!")
			return

		pixmap_item = QtWidgets.QGraphicsPixmapItem(pixmap)
		scene.addItem(pixmap_item)

		view = self.graphicsView_2 if type == "model" else self.graphicsView_1
		view.setScene(scene)

		view.fitInView(scene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
		view.setRenderHint(QtGui.QPainter.Antialiasing)



class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)


if __name__ == "__main__":
	app = QApplication(sys.argv)
	window = MainWindow()
	window.showMaximized()
	sys.exit(app.exec_())