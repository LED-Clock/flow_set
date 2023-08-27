#_*_ coding: utf-8 _*_
import sys
import serial
import serial.tools.list_ports
import threading
import time
import csv

from PyQt5 import uic
from PyQt5.QtCore import QThread, QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import *


#단, UI파일은 Python 코드 파일과 같은 디렉토리에 위치해야한다.
form_class = uic.loadUiType("csv_table.ui")[0]

global available_send_flag, read_result_decoded
#available_send_flag = True
read_result_decoded = []


def send_command(data_lst, mode='SetPoint'):
        global ser
        delay_time = 0.05 #overrun 이슈 확인, 0.008실패,0.01실패, 0.1 성공, 가능한 딜레이의 최소값은?

        #mfc 4개까지 사용한다고 들었음.
        if (mode == 'SetPoint'):
            command_str_lst = []
            command_str_lst.append('#SS1 '+ data_lst[0] + '\r')
            command_str_lst.append('#SS2 '+ data_lst[1] + '\r')
            command_str_lst.append('#SS3 '+ data_lst[2] + '\r')
            command_str_lst.append('#SS4 '+ data_lst[3] + '\r')
        elif(mode == 'SFA'):
            command_str_lst = ['#SFA '+ data_lst[0] + '\r'] #data_lst에 '11110000' or '00000000' 한개만 들어갈 예정
    
        if( ser.is_open ):
            try:
                for command_str in command_str_lst:
                    data = bytes(command_str, encoding='ascii')
                    print(data)
                    ser.write(data) #convert str to bytes
                    time.sleep(delay_time)
                    print("send command sucessfully!")
                
            except Exception as send_ex:
                print('send_command함수에서 오류 : ', send_ex)
                

def read_command(ser):
        global read_result_decoded

        if(ser.readable()):
            read_result = ser.readline().decode()
            
            if(len(read_result) != 0):
                print(read_result)
            


def serial_communication(serial_port, baud_rate, connect_led_var, connect_led_flag, connect_text): #단순히 연결 확인과 readline
    global running, ser
    running = True
    
    def display_led_color(connect_led, connect_text, connect_led_flag): #색깔과 연결상태 출력
        if (connect_led_flag):
            connect_led.setStyleSheet("background-color: #00FF00;"
                                       "border-style: solid;"
                                        "border-width: 2px")
            connect_text.setText('연결 됨')
        else:
            connect_led.setStyleSheet("background-color: #FF0000;"
                                       "border-style: solid;"
                                        "border-width: 2px")
            connect_text.setText('연결 끊김')

    
    #print(type(serial_port),"--status_Thread")

    while running: 
        try:
            ser = serial.Serial(serial_port, baud_rate)
            ser.timeout = 0
            print("ser 생성--status_Thread")

            # 시리얼 통신 상태 확인
            if ser.is_open:
                print(f"{serial_port} 연결됨--status_Thread")

            while running and ser.is_open:
                try:
                # 시리얼 통신 상태 확인
                    if ser.is_open:
                        #print(f"{serial_port} connected.")
                        connect_led_flag = True
                        read_command(ser) #연결을 계속확인하면서 읽을것이 있는지도 확인
                        
                    else:
                        print(f"{serial_port} disconnected.")
                        connect_led_flag = False
                        

                except serial.SerialException:
                    print("Error: Serial communication failed.-- while in while in status_Thread")
                    connect_led_flag = False
                    

                finally: #어떤 상태간에 led불은 설정해야함
                    display_led_color(connect_led_var, connect_text, connect_led_flag)

                time.sleep(0.1)
                # 시리얼 통신 상태 확인 유지
                

        except serial.SerialException:
            print("Error: Serial communication failed.--while in subThread")
            running = False
            print("running을 False로 바꿈")

        finally:
            send_command(['00000000'],'SFA')
            if ser.is_open : #열려있다면 끄고
                ser.close()
                print("ser.close 수행")
                
            connect_led_flag = False
            print(f"{serial_port} 연결 해제됨")
            display_led_color(connect_led_var ,connect_text, connect_led_flag)
            running = False


        print("시리얼통신 쓰레드 종료")


class Command_waiting(QThread):
    time_out = pyqtSignal(list,str)  #일정시간동안 쉬다가 시그널을 보냄 #리스트형을 연결된 slot에 인자로 넘겨준다 
    global ser
    def __init__(self, waiting_time=0):
        super().__init__()
        self.waiting_time = waiting_time
        self.power=0
        self.table_data: any #windowsclass에서 넘겨줘야함
        self.done_time_label: any #windowsclass에서 넘겨줘야함
        self.iteration_row=0
        self.flow_onoff_flag = False
        print('Command_waiting 클래스 생성됨')
        

    #테이블을 읽어서 명령어로 바꿀수 있게 리스트 제작
    def table_data_to_command(self):
        self.lst_for_send=[]
        
        print("현재 테이블의 행 개수: ",self.table_data.rowCount(),"--Command_waiting Class")

        for col in range(5): #요구한 스펙상 4개밖에 없음, 5번째는 시간, 6번째는 state라서 None이있어도 됨
            item = self.table_data.item(self.iteration_row, col)

            if item is not None:
                cell_value = item.text() #str형태로 받아서 list에 저장
                if cell_value=='':
                    cell_value = '0'

                print(f"Row {self.iteration_row}, Column {col}=> {cell_value}")
            else:
                print("cell 이 비어있습니다. 0으로 처리합니다.--Command_waiting Class")
                cell_value = '0'

            self.lst_for_send.append(cell_value)
        
    
        if (self.lst_for_send[4] == '0'):
            print('time이 0이하 입니다.--Command_waiting Class')
            self.lst_for_send=['0','0','0','0'] #채널 1부터 4까지 valuse 0으로 Set set-point
            self.power = False #이번 시퀀스는 통과시키고 다음의 시퀀스부터 작동안되게 꺼버림
            self.waiting_time = 0
        else:
            self.waiting_time = int(self.lst_for_send[4])

        
    def run(self):
        while self.power:
            try:
                if( ser.is_open):
                    self.table_data.setItem(self.iteration_row, 5, QTableWidgetItem('In Progress...'))
                    self.table_data_to_command()

                    if(self.flow_onoff_flag == False): # 최초 flow on 시켜주는 커맨드 보냄
                        self.time_out.emit(['11110000'],'SFA')
                        self.flow_onoff_flag = True
                        time.sleep(0.05) #delay_time

                    self.time_out.emit(self.lst_for_send, 'SetPoint') # 시그널을 방출하고 연결된 slot에 리스트를 넘겨줌

    
                    time.sleep(self.waiting_time)
                    print(f'{self.waiting_time}초 휴식 끝--Command_waiting Class')
                    self.table_data.setItem(self.iteration_row, 5, QTableWidgetItem('Done'))
                    self.iteration_row += 1
                    self.table_data.viewport().update()
                     
                else:
                    print("연결이 끊겨 타이머쓰레드 멈춤--Command_waiting Class")
                    self.power = False
                    self.stop()

            except Exception as comm_class_ex:
                print(comm_class_ex,'--Command_waiting Class')
                self.stop()
        
        self.stop()


    def stop(self):
        # 멀티쓰레드를 종료하는 메소드
        done_time = '종료: \n' + time.strftime('%Y-%m-%d %H:%M:%S')
        self.done_time_label.setText(done_time)
        self.power = False
        self.table_data.setItem(self.iteration_row, 5,  QTableWidgetItem('Fail'))
        self.table_data.viewport().update()
        self.flow_onoff_flag = False
        print("Command_waiting 클래스: 타이머 쓰레드 종료")

        self.quit()
        self.wait(50) #단위 ms
        
    def __del__(self):
        self.flow_onoff_flag = False
        print("Command_waiting 클래스: 타이머 쓰레드 제거")
    
       
        

    
#화면을 띄우는데 사용되는 Class 선언
class WindowClass(QMainWindow, form_class) :
    def __init__(self) :
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Flow Set Command_0.1")
        #타이머 주기마다 시그널을 주는 클래스
        self.command_waiting_class: any
        
        #기기 스펙상 9600
        self.baud_rate = 9600
        

        #초기에 색깔 빨간색으로 ui시작
        self.connect_led_var = self.connect_led
        self.connect_led_flag = False
        self.connect_led.setStyleSheet("background-color: #FF0000;"
                                       "border-style: solid;"
                                        "border-width: 2px")
        
        #scan하면 연결가능한 com 찾음
        self.scan_butt.clicked.connect(self.scan_port)
        

        #스레드 객체 플래그, 중복스레드 생성방지
        self.thread_flag = False

        #COMx연결, 끊기 기능, text추가
        self.connect_butt.clicked.connect(self.connect_com_port)
        self.disconnect_butt.clicked.connect(self.disconnect_com_port)

        #start버튼과 stop버튼 기능 연결
        #self.start_buut.setEnabled(False) #초기엔 연결 안되어 있으니 false로 #테스트단계에서는 잠시 true로
        self.start_butt.clicked.connect(self.start_butt_func)
        self.stop_butt.clicked.connect(self.stop_butt_func)

        #open과 save 버튼 기능
        self.open_file_butt.clicked.connect(self.open_file)
        self.open_file_label.setText("file?")
        self.save_file_butt.clicked.connect(self.save_file_csv)
        # self.save_file_label.setText("none")
        self.save_file_edittext.setText('my_data')
        
        #테이블 수정관련
        self.table_mfc.cellClicked.connect(self.set_label) #셀을 클릭하면
        self.num_rows = 3 #기본으로 3개 설정
        self.cell_cursor_row = self.num_rows #셀 클릭한 영역 #초기에 선택안하면 같게하고
        
        self.add_row_butt.clicked.connect(self.add_row_func)
        self.del_row_butt.clicked.connect(self.del_row_func)
        self.clear_cell_butt.clicked.connect(self.clear_cell_func)

        #수행 끝났다고 알리는 라벨
        self.done_time_label.setText('완료: None')


    # ports scan하고 찾기
    def scan_port(self):
        ports=serial.tools.list_ports.comports()
        self.select_com.clear()
        for port in ports:
            self.select_com.addItem(port.device)
        
        #test용
        self.select_com.addItem('COM_test')
    

    # port 연결하기
    def connect_com_port(self):
        self.com_port = self.select_com.currentText()
        self.connect_text.setText('연결 중...')
        self.scan_butt.setEnabled(False)
        self.select_com.setEnabled(False)

        print(f'{self.com_port} 연결중--WindowClass')
        
        try:
            if(not self.thread_flag):
                self.serial_status_thread = threading.Thread(target=serial_communication, 
                                                        args=(self.com_port, self.baud_rate, self.connect_led_var, self.connect_led_flag, self.connect_text)
                                                        ,daemon=True,)
                #serial_status_thread.daemon = True #daemon으로 threading해주면 메인thread꺼질때 같이 종료됨
                
                print("status 쓰레드 생성 완료--WindowsClass")
                self.serial_status_thread.start()
                print("status 쓰레드.start() 수행--WindowsClass")
                

            else:
                QMessageBox.information(self, '알림', '이미 연결 중입니다.')
        
        except Exception as ex:
            print("Error: Serial communication failed.--WindowsClass")  
            print("받아온 오류: ", ex)

            self.serial_status_thread = None
            self.thread_flag = False
            self.connect_text.setText('연결 실패')
            print('연결실패')

        else:
            self.thread_flag = True


    #port연결 해제
    def disconnect_com_port(self):
        global running
        try:
            send_command(['00000000'],mode='SFA') #연결해제하면 끊기전 flow off
        except Exception as disconn_ex:
            print("disconnect에서 오류: ",disconn_ex)
        
        running = False
        self.thread_flag = False

        #====끊기면 다시 시작할 수 있도록 활성화====
        self.scan_butt.setEnabled(True)
        self.select_com.setEnabled(True)
        self.start_butt.setEnabled(True) 
        self.open_file_butt.setEnabled(True)
        self.add_row_butt.setEnabled(True)
        self.del_row_butt.setEnabled(True)
        self.clear_cell_butt.setEnabled(True)
        self.table_mfc.setEditTriggers(QTableWidget.DoubleClicked)
        
        #====끊기면 다시 시작할 수 있도록 활성화====

        try:
            if (self.serial_status_thread.isAlive()):
                self.connect_text.setText('연결 끊음')
                QMessageBox.information(self, '알림', '연결을 끊었습니다.')
            else:
                QMessageBox.information(self, '알림', '이미 해제 된 상태입니다.')
                print("연결이 애초에 없었음") 
                self.connect_text.setText('연결 끊음')

            print(type(self.command_waiting_class))
            if( self.command_waiting_class.isAlive()):
                QMessageBox.information(self, "알림", "self.command_waiting_class 살아있음 ")

        except Exception as dis_ex:
            print("오류발생", dis_ex)
    

    #csv파일의 경로와 이름 얻기
    def open_file(self): #미완
        File_Open = QFileDialog.getOpenFileName(self, 'Open file', './') #튜플로 반환함
        file_name_display = File_Open[0].split('/')
        self.open_file_label.setText(file_name_display[-1] if len(File_Open[0]) else 'file?')
        
        self.load_csv_to_table(File_Open[0]) #경로 받았으면 이걸로 열어야지

    
    def save_file_csv(self):
        saved_file_name = 'exp_'+ self.save_file_edittext.toPlainText() + '.csv'
        folder_path = './csv_data/'
        csv_file = folder_path + saved_file_name

        #table순회하면서 리스트로 저장
        rows = self.table_mfc.rowCount()
        cols = self.table_mfc.columnCount()
        target_list = [['mfc1','mfc2','mfc3','mfc4','time(sec)','state']]
        for i in range(rows):
            temp_lst = []
            for j in range(cols):
                if(self.table_mfc.item(i,j) == None):
                    continue
                temp_lst.append(self.table_mfc.item(i,j).text())
            target_list.append(temp_lst)

        # CSV 파일에 데이터 저장
        with open(csv_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(target_list)

        print(f'CSV 파일 {csv_file} 저장 완료')
        QMessageBox.information(self, '저장', saved_file_name + ' 로 저장했습니다.')
        

    #csv파일을 table로 보여주기
    def load_csv_to_table(self, file_path):
        try:
            with open(file_path, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                next(reader, None)#csv파일에 열 이름 무시

                data = list(reader)

                # 행과 열의 개수 설정
                self.num_rows = len(data)
                self.num_cols = 6 #요구사양 4개의 채널이라서 
                self.table_mfc.setRowCount(self.num_rows)
                self.table_mfc.setColumnCount(self.num_cols)

                # 데이터를 테이블에 추가
                for row in range(self.num_rows):
                    for col in range(self.num_cols):
                        item = QTableWidgetItem(data[row][col]) #해당 위치에 있는 값 가지는 item객체
                        self.table_mfc.setItem(row, col, item) #마지막row,col에서 에러를 띄우긴함
                        

        except FileNotFoundError:
            print("Error: CSV file not found.")

        except Exception as tableex:
            print("table로 불러오는데 오류 발생 : ",tableex)        

    
    #모든 cell 클리어
    def clear_cell_func(self):
        self.table_mfc.clearContents()
        print("모든 데이터 제거")
        self.table_mfc.setRowCount(3)
        self.table_mfc.setColumnCount(6)
        self.num_rows = 3
        self.num_cols = 6
        self.table_mfc.setHorizontalHeaderLabels(['mfc1', 'mfc2', 'mfc3', 'mfc4', 'time(sec)', 'state'])

    #행 추가
    def add_row_func(self):
        
        self.table_mfc.insertRow(self.cell_cursor_row + 1)


    #선택 행 삭제
    def del_row_func(self): 
        self.table_mfc.removeRow(self.cell_cursor_row)


    # 셀 선택 했을때 row,col,value 읽음       
    def set_label(self, row, column):
        item = self.table_mfc.item(row, column)
        try:
            value = item.text()
        except: 
            value = ''
        label_str = 'Row: ' + str(row+1) + ', Column: ' + str(column+1) + ', Value: ' + str(value)
        self.cell_cursor_label.setText(label_str)
        self.cell_cursor_row = row


    #시작버튼 동작
    def start_butt_func(self):
        response = QMessageBox.information(self, '시작', 'Set Set-point명령을 송신합니다.', QMessageBox.Yes | QMessageBox.Cancel)
        
        if response == QMessageBox.Yes:
            print("데이터 읽는 중--windowclass")
            print("현재 row: ",self.table_mfc.rowCount(),'--windowclass')
            print("현재 col: ",self.table_mfc.columnCount(),'--windowclass')
            
            try:
                if(ser.is_open):
                    self.command_waiting_class = Command_waiting()
                    self.command_waiting_class.table_data = self.table_mfc
                    self.command_waiting_class.done_time_label = self.done_time_label
                    print("table 위젯, label 객체 넘김--windowclass")
                else:
                    raise Exception("ser.is_open이 false라서 예외발생--windowclass")
                #직접 대기시간에 접근해서 값 넣고
                # #다음 명령어를 보낼 때가 되면 시그널을 주는 클래스
                
                if (self.command_waiting_class.power == 0):
                    self.command_waiting_class.power = 1
                    self.command_waiting_class.waiting_time = 2 
                    print("시간설정함--windowsclass")
                    self.command_waiting_class.time_out.connect(send_command)
                    print("slot연결함--windowsclass")
                    self.command_waiting_class.start()
                
                else:
                    print('이미 명령을 실행 중!')
                
                #정상적으로 시작하면 다시 못누르게 비활성화, 수정불가
                self.start_butt.setEnabled(False) #정상적으로 시작하면 다시 못누르게 비활성화
                self.open_file_butt.setEnabled(False)
                self.add_row_butt.setEnabled(False)
                self.del_row_butt.setEnabled(False)
                self.clear_cell_butt.setEnabled(False)
                self.table_mfc.setEditTriggers(QTableWidget.NoEditTriggers)
                

            except Exception as start_butt_ex:
                print(start_butt_ex)
                QMessageBox.critical(self, '오류', '송신불가. 연결을 확인하세요.')         
        
        else:
            QMessageBox.information(self, '시작 취소', '취소하였습니다.')
    
    
    #stop버튼 동작
    def stop_butt_func(self):
        QMessageBox.information(self, '종료', '저장하고 종료합니다.')
        try:
            send_command(['00000000'],mode='SFA') #연결해제하면 끊기전 flow off
        except Exception as stop_ex:
            print("disconnect에서 오류: ",stop_ex)
        
        try:
            self.save_file_csv()
            self.command_waiting_class.power = 0
        except Exception as stop_butt_ex:
            print("stop_butt에서: ",stop_butt_ex)
        # 버튼 클릭 후 프로그램을 종료함
        QCoreApplication.instance().quit()


    # 윈도우의 x버튼을 누르면 실행
    def closeEvent(self, event):
        try:
            send_command(['00000000'],mode='SFA') #연결해제하면 끊기전 flow off
        except Exception as close_ex:
            print("disconnect에서 오류: ",close_ex)

        QMessageBox.information(self, '종료', '종료합니다.')

            

    
        

if __name__ == "__main__" :
    
    #QApplication : 프로그램을 실행시켜주는 클래스
    app = QApplication(sys.argv) 
    #WindowClass의 인스턴스 생성
    myWindow = WindowClass() 

    #프로그램 화면을 보여주는 코드
    myWindow.show()
    
    #여기에 반복문을 넣게되면 처리될때까지 창이 멈춤

    #프로그램을 이벤트루프로 진입시키는(프로그램을 작동시키는) 코드
    sys.exit(app.exec_())


    
