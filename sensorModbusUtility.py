from tkinter import *
from tkinter import ttk
import serial
import codecs
import time
import sys
import struct
import csv
from datetime import datetime

from tkinter import filedialog
import os
global selected
global filename

def connect():
    """
        This function is for connecting the application."""
    global x

    port = txt13.get()
    baud = txt9.get()
    try:
        x = serial.Serial(port='COM' + str(port), baudrate=baud, bytesize=8, parity='N', stopbits=2, timeout=0.05)
        print("Serial port opened:" + "COM", port)
        if btn8["state"] == "normal":
            btn8["state"] = "disabled"
            btn10["state"] == "normal"

    except ValueError:
        print("Com Port is already Open")
        return


def disconnect():
    """
    This function is for disconnecting the application."""

    try:
        x.close()
        if btn10["state"] == "normal":
            btn8["state"] = "normal"
        print("serial port Closed")
    except AttributeError:
        print("Closed without Using it -_-")


def browseFiles():
    global filename
    filename = filedialog.askopenfilename(initialdir="/",
                                          title="Select a File",
                                          filetypes=(("Bin File",
                                                      "*.bin*"),
                                                     ("all files",
                                                      "*.*")))

    # Change label contents
    lbl15.configure(text=filename)
    print(filename)

def clicked():
    global selected
    return str(selected.get())


def upload_File(file_path,Serport,ByteSize,Sensor_ID):
	chunksize = int(ByteSize)
	TimeStart = time.time()
	print("Requested Serial Port is " + Serport)
	print("Requested File Path is " + file_path)
	print("Requested Byte Size is " + ByteSize)
	print("Requested Sensor ID " + Sensor_ID)
	if os.path.splitext(file_path)[1] == ".bin":

		if chunksize == 128 or chunksize == 16:
				try:
					file = open(file_path, "rb")
					SID = int(Sensor_ID)
					bootbuff = SID.to_bytes(1, 'big')
					bootbuff += b'\x03\x80\x60\x00\x01'
					crc = crc16(bootbuff)
					bootbuff += crc.to_bytes(2, 'little')
					print("Check for availability of the sensor on port "+ Serport)
					print("TX -> ", end= ' ')
					print(codecs.encode(bootbuff,"HEX"))
					x.write(bootbuff)
					rx = x.read(15)
					print("RX -> ", end=' ')
					print(codecs.encode(rx, "HEX"))
					if rx != b'':
						print("Sensor is Present")
						#Check BOB byte if not DE then change it to DE
						if rx[1] == 3 and rx[4] != 222:
							# Jump to boot section first
							bootbuff = SID.to_bytes(1, 'big')
							bootbuff += b'\x06\x80\x60\x00\xDE'
							crc = crc16(bootbuff)
							bootbuff += crc.to_bytes(2, 'little')
							print("Writng BOB 0xDE")
							print("TX -> ", end=' ')
							print(codecs.encode(bootbuff, "HEX"))
							x.write(bootbuff)
							rx = x.read(15)
							print("RX -> ", end=' ')
							print(codecs.encode(rx, "HEX"))

						#reset uC to ensure it is on BOOT Mode
						if rx[1] == 3 or rx[1] == 6:
							# RESET uC
							bootbuff = SID.to_bytes(1, 'big')
							bootbuff += b'\x06\x90\x60\x00\x40'
							crc = crc16(bootbuff)
							bootbuff += crc.to_bytes(2, 'little')
							print("Reseting Sensor")
							print("TX -> ", end=' ')
							print(codecs.encode(bootbuff, "HEX"))
							x.write(bootbuff)
							rx = x.read(15)
							print("RX -> ", end=' ')
							print(codecs.encode(rx, "HEX"))

						if rx[1] == 6:
							time.sleep(0.1)

							size = os.path.getsize(file_path)
							print(size)
							idx = 0

							Pageaddress = idx * chunksize  # page address info
							if chunksize == 128:
								flashLimit = 0x6F80
							else:
								flashLimit = 0x6FF0
							while Pageaddress <= flashLimit:

								serbuff = SID.to_bytes(1, 'big')
								serbuff += b'\x10'
								serbuff += Pageaddress.to_bytes(2, 'big')

								Quantity_of_bytes = int(chunksize / 2)
								# print(codecs.encode(Quantity_of_bytes.to_bytes(2, 'big'), "HEX"))
								serbuff += Quantity_of_bytes.to_bytes(2, 'big')
								serbuff += chunksize.to_bytes(1, 'big')
								byte = file.read(chunksize)
								if len(byte) != chunksize:
									while len(byte) < chunksize:
										byte += b'\xFF'
								serbuff += byte

								crc = crc16(serbuff)
								serbuff += crc.to_bytes(2, 'little')

								retry = 0
								while retry <= 5:
									x.write(serbuff)
									print("TX ->",end=' ')
									print(codecs.encode(serbuff, "HEX"))
									rx = x.read(10)
									if rx == b'':
										print("Retrying, No data Received")
										retry += 1
									else:
										print("RX ->", end=' ')
										print(codecs.encode(rx, "HEX"))
										if rx[1] == 0x10:
											retry = 11
										elif rx[1] == 0x90 and rx[2] == 0x11:
											print("Low voltage error occurred, Voltage Value is ->", end=' ')
											print((rx[3]<<8|rx[4])*0.01539713542, end=' ')
											print("V")
											retry = 11
											idx = 2000
										else:
											print("retrying, Exception received RX ->", end=' ')
											print(rx)
											retry += 1
									time.sleep(0.003)
								idx += 1
								Pageaddress = idx * chunksize  # page address info
							if idx == 2000:
								print("Program upload Fail please check log")
							else:
								print("Program Uploaded Successfully in ",end='')
								print((time.time() - TimeStart), end=' ')
								print("Seconds")
						else:
							print("Something went wrong")
					else:
						print("Sensor Not available on given Port " + Serport)
				except:
					print("Unable to Open file please check the path and try again.")
		else:
			print("Sorry!!! Our Sensor do not support byte size "+ByteSize+ " Allowable byte size is '16' and '128'.")
	else:
		print("Bin file expected!!!")

def fetch():
	Port = 'COM'+ txt13.get()
	FileLocation = filename
	SenID = txt5.get().zfill(2)
	ByteCo = clicked()
	print(Port +"   "+FileLocation +"    "+SenID +"    "+ByteCo)
	upload_File(FileLocation,Port,ByteCo,SenID)

def test():
    DataToWrite = makeByteBuff(txt31.get())  # change function here
    print("Request Frame -> ", end=""),
    print(codecs.encode(DataToWrite, "HEX"))
    DataWrite = codecs.encode(DataToWrite, "HEX")
    recvdata = codecs.encode(ModbusUnicast(DataToWrite,20), "HEX")
    labeldata = splitString(recvdata.upper())
    print("Response Frame -> ", end=""),
    print(recvdata)
    print(labeldata)
    lbl33.configure(text=labeldata)
    return recvdata

################################## write Multiple register ######################################
def writestddr(a, b):
    id = a
    funcode = "10"
    address = "8400"
    quantreg = "0002"
    noofby = "04"
    data = b
    return (id + funcode + address + quantreg + noofby + data)


def writerstddr(a, b):
    id = a
    funcode = "10"
    address = "8402"
    quantreg = "0002"
    noofby = "04"
    data = b
    return (id + funcode + address + quantreg + noofby + data)


def writemrsp(a, b):
    id = a
    funcode = "10"
    address = "8404"
    quantreg = "0001"
    noofby = "02"
    data = b
    return (id + funcode + address + quantreg + noofby + data)


def writesamptime(a, b):
    id = a
    funcode = "10"
    address = "8405"
    quantreg = "0001"
    noofby = "02"
    data = b
    return (id + funcode + address + quantreg + noofby + data)


def write_max_samples(a, b):
    id = a
    funcode = "10"
    address = "8406"
    quantreg = "0001"
    noofby = "02"
    data = b
    return (id + funcode + address + quantreg + noofby + data)


def changebaud(a, b):
    id = a
    funcode = "10"
    address = "8407"
    quantreg = "0001"
    noofby = "02"
    data = b
    return (id + funcode + address + quantreg + noofby + data)


########################################## Read Multiple Register ##################################################

def readmultiple(a):
    id = a
    funcode = "03"
    address = "8500"
    quantreg = "0007"
    return (id + funcode + address + quantreg)


########################################## Controller functions #######################################

def jtob(a):
    id = a
    funcode = "06"
    address = "8060"
    data = "00DE"
    return (id + funcode + address + data)


def jtoa(a):
    id = a
    funcode = "06"
    address = "8060"
    data = "00CA"
    return (id + funcode + address + data)


def resetCommand(a):
    id = a
    funcode = "06"
    address = "9060"
    data = "0040"
    return (id + funcode + address + data)


###################################### Modbus Poll ############################################
def ModbusUnicast(DataToWrite,b):  # function to Write and Receive data
    revdata = ""
    #    timedata1 = time.time()
    x.flush()
    x.write(DataToWrite)

    revdata = x.read(b)
    # timedata2 = time.time()
    # print("Time to transmitt ----> " + str(timedata2 - timedata1))
    return revdata


def splitString(data):  # function split the frame 1byte  list
    a_string = data
    split_strings = []
    n = 2
    for index in range(0, len(a_string), n):
        split_strings.append(a_string[index: index + n])
    return split_strings


def crc16(ptrToArray):  # //A standard CRC algorithm
    out = 0xffff
    carry = 0
    inputSize = len(ptrToArray)
    inputSize += 1
    for l in range(0, inputSize - 1):
        out ^= ptrToArray[l]
        for n in range(0, 8):
            carry = out & 1
            out >>= 1
            if (carry):
                out ^= 0xA001
    return out


def makeByteBuff(string):  # returns tx buffer after adding crc to byte array
    # string with encoding 'utf-8'
    #    print("string length -> " + str(len(string)))
    arr = bytearray(string, 'utf-8')
    for i in range(0, len(arr)):
        if arr[i] <= 57:
            arr[i] = arr[i] - 48
        elif arr[i] >= 65 and arr[i] <= 70:
            arr[i] = arr[i] - 55
    pos = 0
    for i in range(0, len(arr)):
        arr[i] = arr[pos] << 4 | arr[pos + 1]
        if pos + 2 == len(arr):
            pos = i + 1
            break
        pos += 2
    # if pos == 2:
    # pos = 4
    crc = crc16(arr[:pos])
    arr[pos] = crc % 256
    arr[pos + 1] = crc // 256
    #    print("Data length -> " + str(len(arr[:pos + 2])))
    #    print("Data With CRC -> "),
    #    print(codecs.encode(arr[:pos + 2], "HEX"))
    return arr[:pos + 2]


############################################### UI Function ########################################
def float_to_hex(a):
    return hex(struct.unpack('<I', struct.pack('<f', a))[0])


def stdr():
    ID = txt5.get().zfill(2)
    stdr = splitString(float_to_hex(float(txt1.get())).upper())
    print(stdr)
    stdr1 = stdr[1] + stdr[2] + stdr[3] + stdr[4]
    print(stdr1)
    DataToWrite = makeByteBuff(writestddr(ID, stdr1))  # change function here
    print("Request Frame -> ", end=""),
    print(codecs.encode(DataToWrite, "HEX"))
    DataWrite = codecs.encode(DataToWrite, "HEX")
    recvdata = codecs.encode(ModbusUnicast(DataToWrite,10), "HEX")
    print("Response Frame -> ", end=""),
    print(recvdata)

    time.sleep(0.05)


def rstdr():
    ID = txt5.get().zfill(2)
    rstdr = splitString(float_to_hex(float(txt2.get())).upper())
    print(rstdr)
    rstdr1 = rstdr[1] + rstdr[2] + rstdr[3] + rstdr[4]
    print(rstdr1)
    DataToWrite = makeByteBuff(writerstddr(ID, rstdr1))  # change function here
    print("Request Frame -> ", end=""),
    print(codecs.encode(DataToWrite, "HEX"))
    DataWrite = codecs.encode(DataToWrite, "HEX")
    recvdata = codecs.encode(ModbusUnicast(DataToWrite,10), "HEX")
    print("Response Frame -> ", end=""),
    print(recvdata)
    time.sleep(0.05)


def maxrate():
    ID = txt5.get().zfill(2)
    maxrate = str(hex(int(txt3.get()))).upper()
    result = maxrate[2:].zfill(4)
    print(result)
    DataToWrite = makeByteBuff(writemrsp(ID, result))  # change function here
    print("Request Frame -> ", end=""),
    print(codecs.encode(DataToWrite, "HEX"))
    DataWrite = codecs.encode(DataToWrite, "HEX")
    recvdata = codecs.encode(ModbusUnicast(DataToWrite,10), "HEX")
    print("Response Frame -> ", end=""),
    print(recvdata)
    time.sleep(0.05)


def samtime():
    ID = txt5.get().zfill(2)
    newtime = str(hex(int(txt4.get()))).upper()
    result = newtime[2:].zfill(4)

    DataToWrite = makeByteBuff(writesamptime(ID, result))  # change function here
    print("Request Frame -> ", end=""),
    print(codecs.encode(DataToWrite, "HEX"))
    DataWrite = codecs.encode(DataToWrite, "HEX")
    recvdata = codecs.encode(ModbusUnicast(DataToWrite,10), "HEX")
    print("Response Frame -> ", end=""),
    print(recvdata)
    time.sleep(0.05)


def sam_uc():
    ID = txt5.get().zfill(2)
    newtime = str(hex(int(txt12.get()))).upper()
    result = newtime[2:].zfill(4)

    DataToWrite = makeByteBuff(write_max_samples(ID, result))  # change function here
    print("Request Frame -> ", end=""),
    print(codecs.encode(DataToWrite, "HEX"))
    DataWrite = codecs.encode(DataToWrite, "HEX")
    recvdata = codecs.encode(ModbusUnicast(DataToWrite,10), "HEX")
    print("Response Frame -> ", end=""),
    print(recvdata)
    time.sleep(0.05)


def baudrate_uC():
    ID = txt5.get().zfill(2)
    if len(txt6.get()) == 2:
        newtime = str(hex(int(txt6.get()))).upper()
        result = newtime[2:].zfill(4)
        DataToWrite = makeByteBuff(changebaud(ID, result))  # change function here
        print("Request Frame -> ", end=""),
        print(codecs.encode(DataToWrite, "HEX"))
        DataWrite = codecs.encode(DataToWrite, "HEX")
        recvdata = codecs.encode(ModbusUnicast(DataToWrite,10), "HEX")
        print("Response Frame -> ", end=""),
        print(recvdata)
        time.sleep(0.05)

    else:
        pass
    baud = txt6.get()
    # main loops#


########################################################################################################################
def bobyte():
    ID = txt5.get()
    bob = txt7.get().upper()
    print(bob)
    if bob == 'CA':
        DataToWrite = makeByteBuff(jtoa(ID))  # change function here
        print("Request Frame -> "),
        print(codecs.encode(DataToWrite, "HEX"))
        DataWrite = codecs.encode(DataToWrite, "HEX")
        recvdata = codecs.encode(ModbusUnicast(DataToWrite,10), "HEX")
        print("Response Frame -> "),
        print(recvdata)
        time.sleep(0.05)

    if bob == 'DE':
        DataToWrite = makeByteBuff(jtob(ID))  # change function here
        print("Request Frame -> "),
        print(codecs.encode(DataToWrite, "HEX"))
        DataWrite = codecs.encode(DataToWrite, "HEX")
        recvdata = codecs.encode(ModbusUnicast(DataToWrite,10), "HEX")
        print("Response Frame -> "),
        print(recvdata)
        time.sleep(0.05)


def resetUC():
    ID = txt5.get()
    print(ID)
    DataToWrite = makeByteBuff(resetCommand(ID))  # change function here
    print("Request Frame -> "),
    print(codecs.encode(DataToWrite, "HEX"))
    DataWrite = codecs.encode(DataToWrite, "HEX")
    recvdata = codecs.encode(ModbusUnicast(DataToWrite,10), "HEX")
    print("Response Frame -> "),
    print(recvdata)
    time.sleep(0.05)


def getmultipledata():
    
    timev = []
    alarmv = []
    meanv = []
    stdrv = []
    rstdrv = []
    maxratev = []
    response = []

    ID = txt5.get().zfill(2)
    t1 = float(txt11.get())
    sample_no = int(txt10.get())
    a = makeByteBuff(readmultiple(ID))

    filename = datetime.now().strftime('Raw_Data-%Y-%m-%d-%H.%M.csv')

    fields = [' Time', 'alarm status', 'mean value', 'stdr', 'rstdr', 'max rate']
    file = open(filename,"w+",newline='')
    writer = csv.writer(file, delimiter=",")
    writer.writerow(fields)

    t2 = time.time()

    for i in range(0, sample_no):

        t = datetime.now()

        DataToWrite = a  # change function here
        # print("Request Frame for multiple Resistors-   -> "),
        print(codecs.encode(DataToWrite, "HEX"))
        recvdata = str(codecs.encode(ModbusUnicast(DataToWrite,19), "HEX")).upper()
        if recvdata == "":
            continue
        lastresult = str(codecs.encode(makeByteBuff(recvdata[2:(len(recvdata) - 5)]), "HEX")).upper()
        print(recvdata)

        timev.append(str(t.hour) + ':' +str(t.minute) + ':' + str(t.second) + ':' + str(t.microsecond))
        # print(lastresult)
        if recvdata == lastresult:
            response.append(recvdata[8:(len(recvdata) - 5)])

        else:
            pass

        time.sleep(t1)

    for i in range(0, len(response)):

        z = splitString(response[i])
        alarmv.append(z[0] + z[1])
        meanv.append(int(z[2] + z[3], 16))
        stdrv.append(struct.unpack('!f', bytes.fromhex(z[4] + z[5] + z[6] + z[7]))[0])
        rstdrv.append(struct.unpack('!f', bytes.fromhex(z[8] + z[9] + z[10] + z[11]))[0])
        maxratev.append(int(z[12] + z[13], 16))


    t3 = time.time()
    t4 = t3 - t2
    print(t4)
    print(timev)
    print(alarmv)
    print(meanv)
    print(stdrv)
    print(rstdrv)
    print(maxratev)


    for i in range(sample_no):

        writer.writerow([timev[i], "'" + alarmv[i], meanv[i], stdrv[i], rstdrv[i], maxratev[i]])

if __name__ == "__main__":
    window = Tk()
    window.title("Sensor Modbus Utility")
    window.geometry('700x280')
    selected = IntVar()

    pane = Frame(window)
    pane.pack(side = TOP,fill=BOTH, expand=True)

    pane2 = Frame(window)
    pane2.pack(side=TOP, fill=BOTH, expand=True)

#########################################  main window buttons ######################################################

    lbl13 = Label(pane, text='Enter COM port')
    lbl13.pack(side = LEFT, padx = 20)
    txt13 = Entry(pane, width=10)
    txt13.pack(side = LEFT, padx = 15)
    lbl9 = Label(pane, text='Enter Utility Baudrate')
    lbl9.pack(side = LEFT)
    txt9 = Entry(pane, width=10)
    txt9.pack(side=LEFT,padx = 20 )
    btn8 = Button(pane, text="Connect", command=connect)
    btn8.pack(side=LEFT,padx = 20)
    btn10 = Button(pane, text="Disonnect", command=disconnect)
    btn10.pack(side=LEFT,padx = 20)

    lbl5 = Label(pane2, text='Enter Sensor ID')
    lbl5.pack(side=LEFT,padx=20)
    txt5 = Entry(pane2, width=10)
    txt5.pack(side=LEFT,padx=20)

    tab_control = ttk.Notebook(window)
    tab1 = ttk.Frame(tab_control)
    tab2 = ttk.Frame(tab_control)
    tab3 = ttk.Frame(tab_control)

    tab_control.add(tab1, text='Configuration')
    tab_control.add(tab2, text='Flash')
    tab_control.add(tab3, text='Test Center')
    tab_control.pack(expand=1, fill='both')

    lbl1 = Label(tab1, text='Set stdr')
    lbl1.grid(column=1, row=5)
    txt1 = Entry(tab1, width=10)
    txt1.grid(column=2, row=5)
    btn1 = Button(tab1, text="Set", command=stdr)
    btn1.grid(column=4 , row=5)

    lbl2 = Label(tab1, text='Set rstdr')
    lbl2.grid(column=1, row=6)
    txt2 = Entry(tab1, width=10)
    txt2.grid(column=2, row=6)
    btn2 = Button(tab1, text="Set", command=rstdr)
    btn2.grid(column=4, row=6)

    lbl3 = Label(tab1, text='Set Maxrate')
    lbl3.grid(column=1, row=7)
    txt3 = Entry(tab1, width=10)
    txt3.grid(column=2, row=7)
    btn3 = Button(tab1, text="Set", command=maxrate)
    btn3.grid(column=4, row=7)

    lbl4 = Label(tab1, text='Sampling time')
    lbl4.grid(column=1, row=8)
    txt4 = Entry(tab1, width=10)
    txt4.grid(column=2, row=8)
    btn4 = Button(tab1, text="Set", command=samtime)
    btn4.grid(column=4, row=8)

    lbl12 = Label(tab1, text='Max no. of Samples(uC)')
    lbl12.grid(column=1, row=9)
    txt12 = Entry(tab1, width=10)
    txt12.grid(column=2, row=9)
    btn12 = Button(tab1, text="Set", command=sam_uc)
    btn12.grid(column=4, row=9)

    lbl6 = Label(tab1, text='Baudrate')
    lbl6.grid(column=1, row=10)
    txt6 = Entry(tab1, width=10)
    txt6.grid(column=2, row=10)
    btn6 = Button(tab1, text="Set", command=baudrate_uC)
    btn6.grid(column=4, row=10)

    lbl7 = Label(tab1, text='Change BOB Byte')
    lbl7.grid(column=5, row=5,padx=20)
    txt7 = Entry(tab1, width=10)
    txt7.grid(column=6, row=5)
    btn7 = Button(tab1, text="Change", command=bobyte)
    btn7.grid(column=7, row=5, ipadx=20)

    lbl10 = Label(tab1, text='Number of Samples')
    lbl10.grid(column=5, row=6)
    txt10 = Entry(tab1, width=10)
    txt10.grid(column=6, row=6)

    lbl11 = Label(tab1, text='Polling Time Interval')
    lbl11.grid(column=5, row=7)
    txt11 = Entry(tab1, width=10)
    txt11.grid(column=6, row=7)

    btn9 = Button(tab1, text="Reset Controller", command=resetUC)
    btn9.grid(column=6, row=10)
    btn9.config(anchor=W)

    btn12 = Button(tab1, text="Get Data", command=getmultipledata)
    btn12.grid(column=7, row=10, ipadx=20)

    btn17 = Button(tab1, text="Quit", command=window.quit)
    btn17.grid(column=8, row=10, ipadx=35)

    lbl14 = Label(tab2, text='Select File Path')
    lbl14.grid(column=1, row=1)
    lbl15 = Label(tab2, text="")
    lbl15.grid(column=4, row=1, ipadx=20, padx=20, pady=20)
    btn14 = Button(tab2, text="Browse bin file", command=browseFiles)
    btn14.grid(column=3, row=1, ipadx=30)

    lbl16 = Label(tab2, text='Select no of bytes to write')
    lbl16.grid(column=1, row=2)
    rad1 = Radiobutton(tab2, text='16 Bytes', value=16, variable=selected)
    rad1.grid(column=3, row=2)
    rad2 = Radiobutton(tab2, text='128 Bytes', value=128, variable=selected)
    rad2.grid(column=4, row=2)

    btn18 = Button(tab2, text="Flash bin File", command=fetch)
    btn18.grid(column=1, row=4, pady=30)
    btn18.config(anchor=W)

    btn16 = Button(tab2, text="Quit", command=window.quit)
    btn16.grid(column=3, row=4, ipadx=30)

    lbl31 = Label(tab3, text='Request Frame')
    lbl31.grid(column=1, row=5,padx = 20,pady =20)
    txt31 = Entry(tab3, width=10)
    txt31.grid(column=2, row=5,ipadx=100)
    btn31 = Button(tab3, text="Send", command=test)
    btn31.grid(column=4, row=5,padx = 20)

    lbl32 = Label(tab3, text='Response Frame')
    lbl32.grid(column=1, row=6,)
    lbl33 = Label(tab3, text='')
    lbl33.grid(column=2, row=6)

    window.mainloop()
