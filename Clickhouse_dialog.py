# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Clickhouse_dialog_base.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_ClickhouseDialogBase(object):
    def setupUi(self, ClickhouseDialogBase):
        ClickhouseDialogBase.setObjectName("ClickhouseDialogBase")
        ClickhouseDialogBase.resize(393, 731)
        self.displaybutton = QtWidgets.QPushButton(ClickhouseDialogBase)
        self.displaybutton.setGeometry(QtCore.QRect(300, 690, 88, 27))
        self.displaybutton.setObjectName("displaybutton")
        self.usernamebox = QtWidgets.QLineEdit(ClickhouseDialogBase)
        self.usernamebox.setGeometry(QtCore.QRect(10, 150, 381, 27))
        self.usernamebox.setObjectName("usernamebox")
        self.passwordbox = QtWidgets.QLineEdit(ClickhouseDialogBase)
        self.passwordbox.setGeometry(QtCore.QRect(10, 200, 381, 27))
        self.passwordbox.setObjectName("passwordbox")
        self.databaselabel = QtWidgets.QLabel(ClickhouseDialogBase)
        self.databaselabel.setGeometry(QtCore.QRect(10, 290, 111, 19))
        self.databaselabel.setObjectName("databaselabel")
        self.hostlabel = QtWidgets.QLabel(ClickhouseDialogBase)
        self.hostlabel.setGeometry(QtCore.QRect(10, 10, 161, 19))
        self.hostlabel.setObjectName("hostlabel")
        self.portbox = QtWidgets.QLineEdit(ClickhouseDialogBase)
        self.portbox.setGeometry(QtCore.QRect(10, 90, 381, 27))
        self.portbox.setObjectName("portbox")
        self.Connectbutton = QtWidgets.QPushButton(ClickhouseDialogBase)
        self.Connectbutton.setGeometry(QtCore.QRect(300, 240, 88, 27))
        self.Connectbutton.setObjectName("Connectbutton")
        self.passwordlabel = QtWidgets.QLabel(ClickhouseDialogBase)
        self.passwordlabel.setGeometry(QtCore.QRect(10, 180, 81, 19))
        self.passwordlabel.setObjectName("passwordlabel")
        self.portlabel = QtWidgets.QLabel(ClickhouseDialogBase)
        self.portlabel.setGeometry(QtCore.QRect(10, 70, 151, 19))
        self.portlabel.setObjectName("portlabel")
        self.hostbox = QtWidgets.QLineEdit(ClickhouseDialogBase)
        self.hostbox.setGeometry(QtCore.QRect(10, 30, 381, 27))
        self.hostbox.setObjectName("hostbox")
        self.tablelabel = QtWidgets.QLabel(ClickhouseDialogBase)
        self.tablelabel.setGeometry(QtCore.QRect(10, 350, 111, 19))
        self.tablelabel.setObjectName("tablelabel")
        self.usernamelabel = QtWidgets.QLabel(ClickhouseDialogBase)
        self.usernamelabel.setGeometry(QtCore.QRect(10, 130, 81, 19))
        self.usernamelabel.setObjectName("usernamelabel")
        self.databasebox = QtWidgets.QComboBox(ClickhouseDialogBase)
        self.databasebox.setGeometry(QtCore.QRect(10, 310, 381, 27))
        self.databasebox.setObjectName("databasebox")
        self.tablebox = QtWidgets.QComboBox(ClickhouseDialogBase)
        self.tablebox.setGeometry(QtCore.QRect(10, 370, 381, 27))
        self.tablebox.setObjectName("tablebox")
        self.locationbox = QtWidgets.QComboBox(ClickhouseDialogBase)
        self.locationbox.setGeometry(QtCore.QRect(10, 430, 381, 27))
        self.locationbox.setObjectName("locationbox")
        self.locationlabel = QtWidgets.QLabel(ClickhouseDialogBase)
        self.locationlabel.setGeometry(QtCore.QRect(10, 410, 291, 19))
        self.locationlabel.setObjectName("locationlabel")
        self.timestampbox = QtWidgets.QComboBox(ClickhouseDialogBase)
        self.timestampbox.setGeometry(QtCore.QRect(10, 490, 381, 27))
        self.timestampbox.setObjectName("timestampbox")
        self.timestamplabel = QtWidgets.QLabel(ClickhouseDialogBase)
        self.timestamplabel.setGeometry(QtCore.QRect(10, 470, 291, 19))
        self.timestamplabel.setObjectName("timestamplabel")
        self.querybox = QtWidgets.QTextEdit(ClickhouseDialogBase)
        self.querybox.setGeometry(QtCore.QRect(10, 550, 381, 131))
        self.querybox.setObjectName("querybox")
        self.querylabel = QtWidgets.QLabel(ClickhouseDialogBase)
        self.querylabel.setGeometry(QtCore.QRect(10, 530, 121, 19))
        self.querylabel.setObjectName("querylabel")
        self.clearbutton = QtWidgets.QPushButton(ClickhouseDialogBase)
        self.clearbutton.setGeometry(QtCore.QRect(10, 690, 88, 27))
        self.clearbutton.setObjectName("clearbutton")
        self.progressbar = QtWidgets.QProgressBar(ClickhouseDialogBase)
        self.progressbar.setGeometry(QtCore.QRect(10, 240, 381, 31))
        self.progressbar.setProperty("value", 24)
        self.progressbar.setObjectName("progressbar")
        self.savecredentialscheck = QtWidgets.QCheckBox(ClickhouseDialogBase)
        self.savecredentialscheck.setGeometry(QtCore.QRect(10, 240, 191, 25))
        self.savecredentialscheck.setObjectName("savecredentialscheck")
        self.displaybutton.raise_()
        self.usernamebox.raise_()
        self.passwordbox.raise_()
        self.databaselabel.raise_()
        self.hostlabel.raise_()
        self.portbox.raise_()
        self.Connectbutton.raise_()
        self.passwordlabel.raise_()
        self.portlabel.raise_()
        self.hostbox.raise_()
        self.tablelabel.raise_()
        self.usernamelabel.raise_()
        self.databasebox.raise_()
        self.tablebox.raise_()
        self.locationbox.raise_()
        self.locationlabel.raise_()
        self.timestampbox.raise_()
        self.timestamplabel.raise_()
        self.querybox.raise_()
        self.querylabel.raise_()
        self.clearbutton.raise_()
        self.savecredentialscheck.raise_()
        self.progressbar.raise_()

        self.retranslateUi(ClickhouseDialogBase)
        QtCore.QMetaObject.connectSlotsByName(ClickhouseDialogBase)
        ClickhouseDialogBase.setTabOrder(self.hostbox, self.portbox)
        ClickhouseDialogBase.setTabOrder(self.portbox, self.usernamebox)
        ClickhouseDialogBase.setTabOrder(self.usernamebox, self.passwordbox)
        ClickhouseDialogBase.setTabOrder(self.passwordbox, self.savecredentialscheck)
        ClickhouseDialogBase.setTabOrder(self.savecredentialscheck, self.Connectbutton)
        ClickhouseDialogBase.setTabOrder(self.Connectbutton, self.databasebox)
        ClickhouseDialogBase.setTabOrder(self.databasebox, self.tablebox)
        ClickhouseDialogBase.setTabOrder(self.tablebox, self.locationbox)
        ClickhouseDialogBase.setTabOrder(self.locationbox, self.timestampbox)
        ClickhouseDialogBase.setTabOrder(self.timestampbox, self.querybox)
        ClickhouseDialogBase.setTabOrder(self.querybox, self.clearbutton)
        ClickhouseDialogBase.setTabOrder(self.clearbutton, self.displaybutton)

    def retranslateUi(self, ClickhouseDialogBase):
        _translate = QtCore.QCoreApplication.translate
        ClickhouseDialogBase.setWindowTitle(_translate("ClickhouseDialogBase", "Clickhouse_Connector"))
        self.displaybutton.setText(_translate("ClickhouseDialogBase", "Display AIS"))
        self.databaselabel.setText(_translate("ClickhouseDialogBase", "Select Database"))
        self.hostlabel.setText(_translate("ClickhouseDialogBase", "Enter Clickhouse Host"))
        self.Connectbutton.setText(_translate("ClickhouseDialogBase", "Connect"))
        self.passwordlabel.setText(_translate("ClickhouseDialogBase", "Password"))
        self.portlabel.setText(_translate("ClickhouseDialogBase", "Enter Clikchouse Port"))
        self.tablelabel.setText(_translate("ClickhouseDialogBase", "Select Table"))
        self.usernamelabel.setText(_translate("ClickhouseDialogBase", "Username"))
        self.locationlabel.setText(_translate("ClickhouseDialogBase", "Select Parameter with location information"))
        self.timestamplabel.setText(_translate("ClickhouseDialogBase", "Select Parameter with time information"))
        self.querylabel.setText(_translate("ClickhouseDialogBase", "Basic Query Tool"))
        self.clearbutton.setText(_translate("ClickhouseDialogBase", "Clear Query"))
        self.savecredentialscheck.setText(_translate("ClickhouseDialogBase", "Save Database Credentials"))
