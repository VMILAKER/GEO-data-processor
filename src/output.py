# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'untitled.ui'
##
## Created by: Qt User Interface Compiler version 6.12.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (QLabel, QMainWindow, QMenuBar, QPushButton,
                               QSizePolicy, QSpacerItem, QStatusBar,
                               QVBoxLayout, QWidget)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(800, 600)
        MainWindow.setStyleSheet(u"""
QWidget#centralwidget {
    background-color: #1e1f26;
}
QLabel#titleLabel {
    color: #e8e9ed;
    font-size: 34px;
    font-weight: 700;
}
QLabel#subtitleLabel {
    color: #9aa0a6;
    font-size: 15px;
}
QPushButton#btnOpen {
    background-color: #4a90d9;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 40px;
    font-size: 16px;
    font-weight: 600;
}
QPushButton#btnOpen:hover {
    background-color: #5ba0e6;
}
QPushButton#btnOpen:pressed {
    background-color: #3a7cc0;
}
QLabel#statusLabel {
    color: #6f757d;
    font-size: 13px;
}
        """)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(40, 30, 40, 30)
        self.titleLabel = QLabel(self.centralwidget)
        self.titleLabel.setObjectName(u"titleLabel")
        self.titleLabel.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.verticalLayout.addWidget(self.titleLabel)
        self.subtitleLabel = QLabel(self.centralwidget)
        self.subtitleLabel.setObjectName(u"subtitleLabel")
        self.subtitleLabel.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.verticalLayout.addWidget(self.subtitleLabel)
        self.topSpacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.verticalLayout.addItem(self.topSpacer)
        self.btnOpen = QPushButton(self.centralwidget)
        self.btnOpen.setObjectName(u"btnOpen")
        self.btnOpen.setMinimumSize(QSize(260, 48))
        self.btnOpen.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.verticalLayout.addWidget(
            self.btnOpen, 0, Qt.AlignmentFlag.AlignHCenter)
        self.bottomSpacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.verticalLayout.addItem(self.bottomSpacer)
        self.statusLabel = QLabel(self.centralwidget)
        self.statusLabel.setObjectName(u"statusLabel")
        self.statusLabel.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        self.verticalLayout.addWidget(self.statusLabel)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 24))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(
            QCoreApplication.translate("MainWindow", u"GEO data converter", None))
        self.titleLabel.setText(
            QCoreApplication.translate("MainWindow", u"GEO data converter", None))
        self.subtitleLabel.setText(QCoreApplication.translate(
            "MainWindow",
            u"Конвертация географических данных в формат ODV TXT", None))
        self.btnOpen.setText(
            QCoreApplication.translate("MainWindow", u"Открыть файл", None))
        self.statusLabel.setText(QCoreApplication.translate(
            "MainWindow", u"Выберите входной файл, чтобы начать", None))
    # retranslateUi
