# flow_set
simple Set Set-point command

실험장비 Flow & Pressure Controller와 rs232통신<br>
PyQT를 이용하여 시간이 포함된 table을 create/load <br>
table 값을 읽어와서 Controller에 command 전송만 하는 단순한 프로그램

### csv_data
.csv 파일들의 저장소<br>
해당 이름의 폴더가 존재하지 않으면 프로그램 오류<br>

### csv_table.ui
GUI<br>
![pyqt gui](https://github.com/LED-Clock/flow_set/assets/22843082/48192896-56e3-4834-a35e-54d2768ce2db)
<br>
cell이 비어있으면 0으로 처리. time열이 0으로 처리되면 그 행은 모두 0이 되고 그 다음 행부터 동작안함.<br>
연결을 시도하는데 오랫동안 안되면 disconnect 누를것.<br>
disconnect는 진행 중인 상황을 중지하는 기능도 있음.<br>
stop 버튼은 저장하면서 프로그램을 끄는 기능.<br>
윈도우의 x버튼을 눌러도 꺼진다. 하지만 저장은 되지 않는다.<br>
