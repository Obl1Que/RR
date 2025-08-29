# -*- coding: utf-8 -*-
import os
import sys
import cv2
import numpy as np
import json

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSlot, Qt, QPoint, QSize
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QCursor
from PyQt5.QtWidgets import QMainWindow, QApplication, QGraphicsPixmapItem, QGraphicsScene, QSizePolicy, QSpacerItem, \
	QPushButton, QLabel


class CustomGraphicsView(QtWidgets.QGraphicsView):
	last_clicks = {"model": None, "real": None}

	def __init__(self, parent=None, view_type=None, table=None):
		super().__init__(parent)
		self.setMouseTracking(True)
		self.type = view_type
		self.table = table

		self.semantic_mask = None
		self.instance_masks = []
		self.instance_paths = []

		self.base_image = None
		self.base_pixmap = None

		self.current_class = None
		self.current_instance = None

		self.scene = QGraphicsScene(self)
		self.setScene(self.scene)

		self.highlight_cache = {}
		self.instance_cache = {}

		self.last_ctrl_pressed = False

	def set_images(self, base_image_path, semantic_mask_path, instance_paths=None):
		self.highlight_cache.clear()
		self.instance_cache.clear()
		self.current_class = None
		self.current_instance = None
		self.instance_paths = instance_paths if instance_paths else []

		# Загружаем основное изображение
		self.base_image = cv2.imread(base_image_path, cv2.IMREAD_COLOR)
		if self.base_image is not None:
			self.base_image = cv2.cvtColor(self.base_image, cv2.COLOR_BGR2RGB)
			height, width, channel = self.base_image.shape
			q_img = QImage(self.base_image.data, width, height, 3 * width, QImage.Format_RGB888)
			self.base_pixmap = QPixmap.fromImage(q_img)

		# Загружаем семантическую маску
		if semantic_mask_path and os.path.exists(semantic_mask_path):
			self.semantic_mask = cv2.imread(semantic_mask_path, cv2.IMREAD_GRAYSCALE)

		# Загрузка масок инстансов
		self.instance_masks = []
		if instance_paths:
			self.instance_paths = instance_paths
			for path in instance_paths:
				mask = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
				if mask is not None:
					self.instance_masks.append(mask)

		self.update_display(force_base=True)

	def update_display(self, pixmap=None, force_base=False):
		if force_base and self.base_pixmap:
			self.scene.clear()
			item = self.scene.addPixmap(self.base_pixmap)
			self.scene.setSceneRect(item.boundingRect())
		elif pixmap:
			self.scene.clear()
			item = self.scene.addPixmap(pixmap)
			self.scene.setSceneRect(item.boundingRect())

		self.fitInView(self.scene.sceneRect(), QtCore.Qt.KeepAspectRatio)
		self.viewport().update()

	def highlight_area(self, pos, ctrl_pressed):
		if self.base_image is None:
			return

		x, y = int(pos.x()), int(pos.y())

		# Проверяем границы изображения
		if not (0 <= x < self.base_image.shape[1] and 0 <= y < self.base_image.shape[0]):
			self.current_instance = None
			self.current_class = None
			self.update_display(force_base=True)
			return

		if ctrl_pressed:
			self.current_class = None
			if self.instance_masks:
				for i, mask in enumerate(self.instance_masks):
					if mask is not None and 0 <= x < mask.shape[1] and 0 <= y < mask.shape[0] and mask[y, x] > 0:
						if i == self.current_instance:
							return

						self.current_instance = i
						if i in self.instance_cache:
							self.update_display(pixmap=self.instance_cache[i])
							return

						highlighted = self.base_image.copy()
						mask_bool = (mask > 0)
						highlight_color = np.array([255, 255, 255], dtype=np.uint8)
						alpha = 0.75
						for c in range(3):
							highlighted[:, :, c] = np.where(
								mask_bool,
								(highlighted[:, :, c] * (1 - alpha) + highlight_color[c] * alpha).astype(np.uint8),
								highlighted[:, :, c]
							)

						height, width, _ = highlighted.shape
						q_img = QImage(highlighted.data, width, height, 3 * width, QImage.Format_RGB888).copy()
						pixmap = QPixmap.fromImage(q_img)
						self.instance_cache[i] = pixmap
						self.update_display(pixmap=pixmap)
						return
		else:
			self.current_instance = None
			if self.semantic_mask is not None and 0 <= x < self.semantic_mask.shape[1] and 0 <= y < self.semantic_mask.shape[0]:
				class_id = self.semantic_mask[y, x]
				self.highlight_class(class_id)
				return

		self.current_instance = None
		self.current_class = None
		self.update_display(force_base=True)

	def get_pixel_info(self, x, y):
		name = None
		object_id_model, class_id_model = None, None
		object_id_real, class_id_real = None, None
		mean_lum_model, mean_lum_real = None, None

		if self.instance_masks:
			for i, mask in enumerate(self.instance_masks, 1):
				if mask is not None and mask[y, x] > 0:
					name = os.path.basename(self.instance_paths[i - 1])
					object_id_model = i
					break

		if self.semantic_mask is not None:
			class_id_model = int(self.semantic_mask[y, x])

		if self.base_image is not None:
			pixel = self.base_image[y, x]
			mean_lum_real = float(np.mean(pixel))

		return [name, object_id_model, class_id_model, mean_lum_real,
				object_id_real, class_id_real, mean_lum_real]

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

		mask = (self.semantic_mask == class_id).astype(np.uint8)
		highlighted = self.base_image.copy()
		highlight_color = np.array([255, 255, 255], dtype=np.uint8)
		alpha = 0.75
		for c in range(3):
			highlighted[:, :, c] = np.where(
				mask,
				(highlighted[:, :, c] * (1 - alpha) + highlight_color[c] * alpha).astype(np.uint8),
				highlighted[:, :, c]
			)

		height, width, _ = highlighted.shape
		q_img = QImage(highlighted.data, width, height, 3 * width, QImage.Format_RGB888).copy()
		pixmap = QPixmap.fromImage(q_img)
		self.highlight_cache[class_id] = pixmap
		self.current_class = class_id
		self.update_display(pixmap=pixmap)

	def mousePressEvent(self, event):
		if event.button() == Qt.LeftButton and self.base_image is not None:
			pos = self.mapToScene(event.pos())
			x, y = int(pos.x()), int(pos.y())

			if not (0 <= x < self.base_image.shape[1] and 0 <= y < self.base_image.shape[0]):
				return

			info = {
				"name": None,
				"object_id": None,
				"class_id": None,
				"mean_lum": None
			}

			# instance
			if self.instance_masks:
				for i, mask in enumerate(self.instance_masks, 1):
					if mask is not None and mask[y, x] > 0:
						info["name"] = os.path.basename(self.instance_paths[i - 1])
						info["object_id"] = i
						break

			# semantic
			if self.semantic_mask is not None:
				info["class_id"] = int(self.semantic_mask[y, x])

			# luminance
			if self.base_image is not None:
				pixel = self.base_image[y, x]
				info["mean_lum"] = round(float(np.mean(pixel)), 2)

			CustomGraphicsView.last_clicks[self.type] = info

			if CustomGraphicsView.last_clicks["real"] and CustomGraphicsView.last_clicks["model"]:
				real = CustomGraphicsView.last_clicks["real"]
				model = CustomGraphicsView.last_clicks["model"]

				if self.table:
					row_idx = self.table.rowCount()
					self.table.insertRow(row_idx)
					values = [
						model['name'],
						model['object_id'],
						model['class_id'],
						real['mean_lum'],
						real['object_id'],
						real['class_id'],
						real['mean_lum']
					]
					for col, val in enumerate(values):
						item = QtWidgets.QTableWidgetItem(str(val) if val is not None else "")
						self.table.setItem(row_idx, col, item)

				CustomGraphicsView.last_clicks = {"model": None, "real": None}

		super().mousePressEvent(event)

	def mouseMoveEvent(self, event):
		if self.base_image is None:
			return super().mouseMoveEvent(event)

		new_ctrl_pressed = event.modifiers() & Qt.ControlModifier
		if self.last_ctrl_pressed != new_ctrl_pressed:
			self.current_class = None
			self.current_instance = None
		self.last_ctrl_pressed = new_ctrl_pressed

		pos = self.mapToScene(event.pos())
		self.highlight_area(pos, new_ctrl_pressed)
		super().mouseMoveEvent(event)

	def leaveEvent(self, event):
		if self.current_class is not None or self.current_instance is not None:
			self.current_class = None
			self.current_instance = None
			self.update_display(force_base=True)
		super().leaveEvent(event)


class Ui_MainWindow(object):
	def setupUi(self, MainWindow):
		MainWindow.resize(1600, 1200)
		MainWindow.setMinimumSize(QSize(1600, 1200))

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

		self.model_current_idx = 0
		self.real_current_idx = 0

		self.centralwidget = QtWidgets.QWidget(MainWindow)

		self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.centralwidget)
		self.verticalLayout = QtWidgets.QVBoxLayout()

		self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
		self.graphicsView.setMinimumSize(QSize(653, 326))
		self.graphicsView.setMaximumSize(QSize(653, 326))
		self.verticalLayout.addWidget(self.graphicsView)

		self.pushButton_1 = QPushButton(self.centralwidget)
		self.pushButton_1.setMinimumSize(QSize(320, 0))
		self.pushButton_1.clicked.connect(lambda: self.openImg('model'))
		self.verticalLayout.addWidget(self.pushButton_1)

		self.pushButton_2 = QPushButton(self.centralwidget)
		self.pushButton_2.clicked.connect(lambda: self.openImg('real'))
		self.verticalLayout.addWidget(self.pushButton_2)

		self.line_2 = QtWidgets.QFrame(self.centralwidget)
		self.line_2.setFrameShape(QtWidgets.QFrame.HLine)
		self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
		self.verticalLayout.addWidget(self.line_2)

		self.pushButton_3 = QPushButton(self.centralwidget)
		self.pushButton_3.clicked.connect(self.save_rgb_masks)
		self.verticalLayout.addWidget(self.pushButton_3)

		self.pushButton_4 = QPushButton(self.centralwidget)
		self.pushButton_4.clicked.connect(self.save_table)
		self.verticalLayout.addWidget(self.pushButton_4)

		self.tableWidget = QtWidgets.QTableWidget(self.centralwidget)
		self.tableWidget.setMinimumSize(QSize(0, 450))
		self.tableWidget.setMaximumSize(QSize(653, 16777215))
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
		self.horizontalLayout_3.addWidget(self.line)

		self.verticalLayout_2 = QtWidgets.QVBoxLayout()
		self.graphicsView_2 = CustomGraphicsView(self.centralwidget, view_type="model", table=self.tableWidget)
		self.graphicsView_2.setMinimumSize(QSize(820, 0))
		self.verticalLayout_2.addWidget(self.graphicsView_2)

		self.graphicsView_1 = CustomGraphicsView(self.centralwidget, view_type="real", table=self.tableWidget)
		self.graphicsView_1.setMinimumSize(QSize(418, 0))
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

	def save_table(self):
		import csv
		file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self.centralwidget, "Сохранить таблицу", "",
															 "CSV Files (*.csv)")
		if not file_path:
			return

		with open(file_path, "w", newline="") as f:
			writer = csv.writer(f)
			for row in range(self.tableWidget.rowCount()):
				writer.writerow(
					[self.tableWidget.item(row, c).text() if self.tableWidget.item(row, c) else "" for c in
					 range(7)])

		QtWidgets.QMessageBox.information(self.centralwidget, "Успех", f"Таблица сохранена в {file_path}")

	def save_rgb_masks(self):
		if self.model_path:
			self.generate_rgb_masks('model')
		if self.real_path:
			self.generate_rgb_masks('real')

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

		if type == "real":
			self.real_instances = []
			instance_dir = os.path.join(path, self.folder_actual, 'instance')
			instance_paths = [os.path.join(instance_dir, f) for f in os.listdir(instance_dir)]

			self.real_ir = _get_first_file(path, 'ir')
			self.real_semantic = _get_first_file(path, 'semantic')
			self.graphicsView_1.set_images(self.real_ir, self.real_semantic, instance_paths)
		elif type == "model":
			self.model_instances = []
			instance_dir = os.path.join(path, self.folder_actual, 'instance')
			instance_paths = [os.path.join(instance_dir, f) for f in os.listdir(instance_dir)]

			self.model_ir = _get_first_file(path, 'ir')
			self.model_semantic = _get_first_file(path, 'semantic')
			self.graphicsView_2.set_images(self.model_ir, self.model_semantic, instance_paths)

	def get_rgb_mask(self, type):
		rgb_dir = os.path.join(self.model_path if type == 'model' else self.real_path, self.folder_actual, 'RGB')
		rgb_file = os.path.join(rgb_dir, f"{type}_rgb.png")
		if os.path.exists(rgb_file):
			mask = cv2.imread(rgb_file, cv2.IMREAD_COLOR)
			return cv2.cvtColor(mask, cv2.COLOR_BGR2RGB)
		return None

	def generate_rgb_masks(self, type: str):
		base_path = self.model_path if type == "model" else self.real_path
		if not base_path:
			QtWidgets.QMessageBox.warning(self.centralwidget, "Ошибка", "Сначала загрузите изображения")
			return

		instance_dir = os.path.join(base_path, self.folder_actual, 'instance')
		semantic_path = os.path.join(base_path, self.folder_actual, 'semantic', os.listdir(os.path.join(base_path, self.folder_actual, 'semantic'))[0])

		semantic_mask = cv2.imread(semantic_path, cv2.IMREAD_COLOR)
		semantic_mask = cv2.cvtColor(semantic_mask, cv2.COLOR_BGR2RGB)

		with open("colors.json", "r", encoding="utf-8") as f:
			color_map = json.load(f)

		class_to_id = {tuple(v): idx + 1 for idx, (k, v) in enumerate(color_map.items())}

		# Загружаем инстансы
		instance_masks, instance_paths = [], []
		for f in sorted(os.listdir(instance_dir)):
			path = os.path.join(instance_dir, f)
			mask = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
			if mask is not None:
				instance_masks.append(mask)
				instance_paths.append(path)

		# Пустое RGB (R=obj_id, G=class_id, B=0)
		h, w = semantic_mask.shape[:2]
		rgb_mask = np.zeros((h, w, 3), dtype=np.uint8)

		object_info = {}
		for obj_id, (mask, path) in enumerate(zip(instance_masks, instance_paths), 1):
			obj_name = os.path.splitext(os.path.basename(path))[0]
			object_info[obj_id] = obj_name
			obj_area = mask > 0

			# R канал — id объекта
			rgb_mask[..., 0][obj_area] = obj_id

			# G канал — id класса
			colors_in_obj = semantic_mask[obj_area]
			for (y, x), col in zip(np.argwhere(obj_area), colors_in_obj):
				col_tuple = tuple(int(c) for c in col)
				class_id = class_to_id.get(col_tuple, 0)
				rgb_mask[y, x, 1] = class_id

		rgb_dir = os.path.join(base_path, self.folder_actual, 'RGB')
		os.makedirs(rgb_dir, exist_ok=True)
		rgb_output_path = os.path.join(rgb_dir, f"{type}_rgb.png")
		cv2.imwrite(rgb_output_path, cv2.cvtColor(rgb_mask, cv2.COLOR_RGB2BGR))

		json_path = os.path.join(rgb_dir, f"{type}_objects.json")
		with open(json_path, 'w', encoding="utf-8") as f:
			json.dump(object_info, f, indent=4, ensure_ascii=False)

		QtWidgets.QMessageBox.information(self.centralwidget, "Успех", f"RGB-разметка сохранена в {rgb_output_path}")


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