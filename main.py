# -*- coding: utf-8 -*-
import os
import sys
import cv2
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSlot, Qt, QPoint
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QCursor
from PyQt5.QtWidgets import QMainWindow, QApplication, QGraphicsPixmapItem, QGraphicsScene


class CustomGraphicsView(QtWidgets.QGraphicsView):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setMouseTracking(True)
		self.semantic_mask = None
		self.base_image = None
		self.base_pixmap = None  # Базовое изображение в виде QPixmap
		self.current_class = None  # Текущий подсвеченный класс
		self.scene = QGraphicsScene(self)
		self.setScene(self.scene)
		self.highlight_cache = {}  # Кэш для подсвеченных изображений

	def set_images(self, base_image_path, semantic_mask_path):
		# Очищаем кэш при загрузке новых изображений
		self.highlight_cache.clear()
		self.current_class = None

		# Загружаем основное изображение
		self.base_image = cv2.imread(base_image_path, cv2.IMREAD_COLOR)
		if self.base_image is not None:
			self.base_image = cv2.cvtColor(self.base_image, cv2.COLOR_BGR2RGB)
			height, width, channel = self.base_image.shape
			bytes_per_line = 3 * width
			q_img = QImage(self.base_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
			self.base_pixmap = QPixmap.fromImage(q_img)

		# Загружаем семантическую маску
		if semantic_mask_path and os.path.exists(semantic_mask_path):
			self.semantic_mask = cv2.imread(semantic_mask_path, cv2.IMREAD_GRAYSCALE)

		self.update_display(force_base=True)

	def update_display(self, pixmap=None, force_base=False):
		if force_base and self.base_pixmap:
			self.scene.clear()
			self.scene.addPixmap(self.base_pixmap)
			self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
		elif pixmap:
			self.scene.clear()
			self.scene.addPixmap(pixmap)
			self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

	def highlight_class(self, class_id):
		if class_id == self.current_class:
			return

		if class_id == 0 or class_id is None:
			self.current_class = None
			self.update_display(force_base=True)
			return

		if class_id in self.highlight_cache:
			self.current_class = class_id
			self.update_display(pixmap=self.highlight_cache[class_id])
			return

		# Создаем маску
		mask = (self.semantic_mask == class_id).astype(np.uint8)

		# Создаем изображение с подсветкой
		highlighted = self.base_image.copy()

		# Альфа-смешение с полупрозрачным цветом
		highlight_color = np.array([255, 255, 255], dtype=np.uint8)
		alpha = 0.75  # Прозрачность подсветки

		for c in range(3):
			highlighted[:, :, c] = np.where(
				mask,
				(highlighted[:, :, c] * (1 - alpha) + highlight_color[c] * alpha).astype(np.uint8),
				highlighted[:, :, c]
			)

		# Конвертируем и кэшируем
		height, width, _ = highlighted.shape
		q_img = QImage(highlighted.data, width, height, 3 * width, QImage.Format_RGB888).copy()
		pixmap = QPixmap.fromImage(q_img)
		self.highlight_cache[class_id] = pixmap
		self.current_class = class_id
		self.update_display(pixmap=pixmap)

	def mouseMoveEvent(self, event):
		if self.semantic_mask is None or self.base_image is None:
			return super().mouseMoveEvent(event)

		# Получаем координаты курсора относительно изображения
		pos = self.mapToScene(event.pos())
		x, y = int(pos.x()), int(pos.y())

		# Проверяем границы изображения
		if 0 <= x < self.semantic_mask.shape[1] and 0 <= y < self.semantic_mask.shape[0]:
			class_id = self.semantic_mask[y, x]
			self.highlight_class(class_id)
		else:
			self.highlight_class(None)

		super().mouseMoveEvent(event)

	def leaveEvent(self, event):
		self.highlight_class(None)
		super().leaveEvent(event)


class Ui_MainWindow(object):
	def setupUi(self, MainWindow):
		MainWindow.setObjectName("MainWindow")
		MainWindow.resize(1600, 1200)
		MainWindow.setMinimumSize(QtCore.QSize(1600, 1200))

		self.model_path = None
		self.real_path = None
		self.folder_actual = None
		self.folder_counter = {}

		self.model_instances = []
		self.model_ir = ''
		self.model_semantic = ''

		self.real_instances = []
		self.real_ir = ''
		self.real_semantic = ''

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
		self.graphicsView_2 = CustomGraphicsView(self.centralwidget)
		self.graphicsView_2.setMinimumSize(QtCore.QSize(820, 0))
		self.graphicsView_2.setObjectName("graphicsView_2")
		self.verticalLayout_2.addWidget(self.graphicsView_2)

		self.graphicsView_1 = CustomGraphicsView(self.centralwidget)
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
				self.model_path = folder_path
			elif type == "real":
				self.real_path = folder_path
			self.setImg(type)

	def setImg(self, type: str):
		path = self.model_path if type == "model" else self.real_path
		if not QtCore.QFile.exists(path):
			print(f"Ошибка: файл {path} не существует!")
			return

		for idx, folder in enumerate(os.listdir(path)):
			if os.path.isdir(os.path.join(path, folder)):
				self.folder_counter[idx] = folder

		if self.folder_counter:
			self.folder_actual = self.folder_counter[0]

		def _get_first_file(path, subfolder):
			return os.path.join(path, self.folder_actual, subfolder, os.listdir(os.path.join(path, self.folder_actual, subfolder))[0])

		# Очищаем предыдущие данные
		if type == "real":
			self.real_instances = []
			self.real_ir = _get_first_file(path, 'ir')
			self.real_semantic = _get_first_file(path, 'semantic')
			self.graphicsView_1.set_images(self.real_ir, self.real_semantic)
		elif type == "model":
			self.model_instances = []
			self.model_ir = _get_first_file(path, 'ir')
			self.model_semantic = _get_first_file(path, 'semantic')
			self.graphicsView_2.set_images(self.model_ir, self.model_semantic)



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