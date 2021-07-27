from tkinter import *
from tkinter import ttk
from tkinter.ttk import *
import serial
import codecs
import time
import struct
import csv
from datetime import datetime
import os
global selected
global filename
from tkinter import filedialog
from tkinter import messagebox
from tkinter import scrolledtext
import serial.tools.list_ports
import threading

flashed = []
unflashed = []

def serial_ports():
    return serial.tools.list_ports.comports()

def on_select(event=NONE):

    if cb.index("end") == 0:
        print("PLease select Proper Port")
        messagebox.showinfo('Error', 'PLease select Proper Port')
    else:
        return cb.get()[0:5]

def baud():

    if cb2.index("end") == 0:
        print("PLease select Proper Baudrate")
        messagebox.showinfo('Error', 'PLease select Proper Baudrate')
    else:
        return cb2.get()

def crc_check(a):
    buff = a[len(a)-2:len(a)]
    int_val = int.from_bytes(buff,"little")
    bytebuff_crc = crc16(a[:len(a)-2])

    if int_val == bytebuff_crc:
        return True
    else:
        return False

def clicked():
    global selected
    return str(selected.get())

###########################################Flash Firmware##########################################################
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
    txt.insert(INSERT, "File Selected:" + " " + filename + '\n')

def upload_File(file_path, Serport, ByteSize, Frm,to):
    global x
    flashed.clear()
    unflashed.clear()
    chunksize = 128

    txt.delete('1.0', END)

    print("Requested Serial Port is " + Serport)
    print("Requested File Path is " + file_path)
    print("Requested Byte Size is " + ByteSize)
    print("Starting ID " + Frm)
    print("Ending ID " + to)

    if os.path.splitext(file_path)[1] == ".bin":

        if serial.Serial(port=on_select(), baudrate=baud(), bytesize=8, parity='N', stopbits=2, timeout=0.03):
            x = serial.Serial(port=on_select(), baudrate=baud(), bytesize=8, parity='N', stopbits=2, timeout=0.03)
            print("Serial port opened:" + cb.get()[0:5])

            if open(file_path, "rb"):

                for Sensor_ID in range(int(Frm), int(to)+1):
                    begin = time.time()
                    print("flashing started")
                    file = open(file_path, "rb")
                    SID = Sensor_ID
                    print(SID)
                    txt.insert(INSERT, "INFO : Flashing:" + " " + str(SID) + '\n')
                    bootbuff = SID.to_bytes(1, 'big')
                    bootbuff += b'\x03\x80\x60\x00\x01'
                    crc = crc16(bootbuff)
                    bootbuff += crc.to_bytes(2, 'little')
                    print("Check for availability of the sensor on port " + Serport)
                    # print("TX -> ", end= ' ')
                    print(codecs.encode(bootbuff,"HEX"))
                    x.write(bootbuff)
                    time.sleep(0.12)
                    rx = x.read(15)
                    # print("RX -> ", end=' ')
                    print(codecs.encode(rx, "HEX"))
                    if rx != b'':
                        print("Sensor is Present")

                        progress1['value'] = 0
                        window.update_idletasks()

                        # Check BOB byte if not DE then change it to DE
                        if rx[1] == 3 and rx[4] != 222:
                            # Jump to boot section first
                            bootbuff = SID.to_bytes(1, 'big')
                            bootbuff += b'\x06\x80\x60\x00\xDE'
                            crc = crc16(bootbuff)
                            bootbuff += crc.to_bytes(2, 'little')
                            print("Writng BOB 0xDE")
                            # ("TX -> ", end=' ')
                            # print(codecs.encode(bootbuff, "HEX"))
                            x.write(bootbuff)
                            rx = x.read(15)
                            print("RX -> ", end=' ')
                            print(codecs.encode(rx, "HEX"))

                        # reset uC to ensure it is on BOOT Mode
                        if rx[1] == 3 or rx[1] == 6:
                            # RESET uC
                            bootbuff = SID.to_bytes(1, 'big')
                            bootbuff += b'\x06\x90\x60\x00\x40'
                            crc = crc16(bootbuff)
                            bootbuff += crc.to_bytes(2, 'little')
                            print("Reseting Sensor")
                            # print("TX -> ", end=' ')
                            # print(codecs.encode(bootbuff, "HEX"))
                            x.write(bootbuff)
                            rx = x.read(15)
                            # print("RX -> ", end=' ')
                            # print(codecs.encode(rx, "HEX"))

                        if rx[1] == 6:
                            time.sleep(0.1)

                            progress1['value'] = 40
                            window.update_idletasks()

                            size = os.path.getsize(file_path)
                            # print(size)
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
                                    # print("TX ->",end=' ')
                                    # print(codecs.encode(serbuff, "HEX"))
                                    rx = x.read(10)
                                    if rx == b'':
                                        print("Retrying, No data Received")
                                        retry += 1
                                    else:
                                        # print("RX ->", end=' ')
                                        # print(codecs.encode(rx, "HEX"))
                                        if rx[1] == 0x10:
                                            retry = 11
                                        elif rx[1] == 0x90 and rx[2] == 0x11:
                                            print("Low voltage error occurred, Voltage Value is ->", end=' ')
                                            print((rx[3]<<8|rx[4])*0.01539713542, end=' ')
                                            print("V")
                                            txt.insert(INSERT, "ERROR: Low voltage error occurred" + "\n")
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
                                txt.insert(INSERT,"ERROR: Program upload Fail please check log" + "\n")
                            else:
                                end = time.time()
                                print("Program Uploaded Successfully in ", end='')
                                print((end - begin), end=' ')
                                print("Seconds")
                                flashed.append(Sensor_ID)
                                txt.insert(INSERT,"INFO : BIN file Uploaded Successfully in: " + str(end - begin) + '\n')

                            progress1['value'] = 80
                            window.update_idletasks()

                            time.sleep(0.1)
                            # Jump to App section after flash
                            bootbuff = SID.to_bytes(1, 'big')
                            bootbuff += b'\x06\x80\x60\x00\xCA'
                            crc = crc16(bootbuff)
                            bootbuff += crc.to_bytes(2, 'little')
                            print("Writng BOB 0xCA")
                            # print("TX -> ", end=' ')
                            # print(codecs.encode(bootbuff, "HEX"))
                            x.write(bootbuff)
                            rx = x.read(15)
                            # print("RX -> ", end=' ')
                            # print(codecs.encode(rx, "HEX"))
                            txt.insert(INSERT, "       Jumped to App Section Successfully" + '\n')

                            # RESET uC
                            bootbuff = SID.to_bytes(1, 'big')
                            bootbuff += b'\x06\x90\x60\x00\x40'
                            crc = crc16(bootbuff)
                            bootbuff += crc.to_bytes(2, 'little')
                            print("Reseting Sensor")
                            # print("TX -> ", end=' ')
                            # print(codecs.encode(bootbuff, "HEX"))
                            x.write(bootbuff)
                            rx = x.read(15)
                            # print("RX -> ", end=' ')
                            # print(codecs.encode(rx, "HEX"))
                            txt.insert(INSERT, "       Sensor Resetted Successfully" + '\n')
                            progress1['value'] = 100
                            window.update_idletasks()
                            txt.see("end")
                        else:
                            print("Something went wrong")
                            txt.insert(INSERT,"ERROR : Something went wrong" + '\n')
                    else:
                        print("Sensor Not available on given Port " + Serport)
                        txt.insert(INSERT, "ERROR : Sensor Not available on given Port:" + "  " + Serport + '\n')
                        unflashed.append(Sensor_ID)

                print("Flashing Complete")
                txt.insert(INSERT,"INFO : Flashing Complete" + '\n')
                txt.insert(INSERT, "Firmware flashed Successfully :" + "  " + str(flashed) + '\n')
                txt.insert(INSERT,"ERROR : FIRMWARE FLASHING FAILED:" + "  " + str(unflashed) + '\n')
                txt.see("end")
                messagebox.showinfo('Flashing Complete', 'The Required Operation has Completed')

            else:
                print("Unable to Open file please check the path and try again.")
                txt.insert(INSERT," ERROR : Unable to Open file please check the path and try again." + '\n')
                messagebox.showinfo('Flashing error', 'Unable to Open file please check the path and try again.')
        else:
            print(
                "Port is unavailable, Please make sure port is available. Also Port name entry is CaSe Sensitive so check for that also.")
            txt.insert(INSERT," ERROR : Port is unavailable, Please make sure port is available. Also Port name entry is CaSe Sensitive so check for that also." + '\n')
            messagebox.showinfo('Flashing error', 'Port is unavailable, Please make sure port is available. Also Port name entry is CaSe Sensitive so check for that also.')
    else:
        print("Bin file expected!!!")
        txt.insert(INSERT," ERROR : Bin file expected!!!" + "\n")
        messagebox.showinfo('Flashing error',"Bin file expected!!!")

    print(flashed)
    print(unflashed)
    txt.see("end")
    x.close()

def fetch():

    Port = on_select()
    FileLocation = filename
    From = txt_r1.get().zfill(2)
    ByteCo = "128"

    if txt_r2.index("end") == 0:
        to = txt_r1.get().zfill(2)
    else:
        to = txt_r2.get().zfill(2)

    print(Port + "   " + FileLocation + "    " + From + "    " + to + "    " + ByteCo)
    t2 = threading.Thread(target=upload_File, args=(FileLocation, Port, ByteCo, From, to))
    t2.start()

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

###########################################################################################################################

def test():


    lbl33.configure(text="")

    x = serial.Serial(port=on_select(), baudrate=baud(), bytesize=8, parity='N', stopbits=2, timeout=0.2)
    print("Serial port opened:" + cb.get()[0:5])

    def ModbusUnicast(DataToWrite):  # function to Write and Receive data
        revdata = ""
        #    timedata1 = time.time()
        x.flush()
        x.write(DataToWrite)
        revdata = x.read(100)
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

        if (len(arr)%2) == 0 and (len(arr)>=4):
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
        else:
            print("Please Enter a Correct Request string")
            messagebox.showinfo('Error',
                                'Invalid Request, Please make sure you Enter a proper string')
            x.close()

    print(txt31.get())
    DataToWrite = makeByteBuff(txt31.get().upper())  # change function here
    # print("Request Frame -> ", end=""),
    # print(codecs.encode(DataToWrite, "HEX"))
    crcdata = ModbusUnicast(DataToWrite)
    recvdata = codecs.encode(crcdata, "HEX")
    labeldata = splitString(recvdata.upper())
    # print("Response Frame -> ", end=""),
    print(recvdata)

    if crc_check(crcdata) == True:
        # print(labeldata)
        lbl33.configure(text=labeldata)
        x.close()
        return recvdata

    else:
        print("CRC error")
        x.close()
        return recvdata

################################## write Multiple register #############################################################

def writestddr(a, b):
    id = format(int(a),'02X')
    funcode = "10"
    address = "8400"
    quantreg = "0002"
    noofby = "04"
    data = b
    return (id + funcode + address + quantreg + noofby + data)

def readstddr(a):
    id = format(int(a), '02X')
    funcode = "03"
    address = "8400"
    quantreg = "0002"
    return (id + funcode + address + quantreg)

def writerstddr(a, b):
    id = format(int(a),'02X')
    funcode = "10"
    address = "8402"
    quantreg = "0002"
    noofby = "04"
    data = b
    return (id + funcode + address + quantreg + noofby + data)

def readrstddr(a):
    id = format(int(a), '02X')
    funcode = "03"
    address = "8402"
    quantreg = "0002"
    return (id + funcode + address + quantreg)

def writemrsp(a, b):
    id = format(int(a),'02X')
    funcode = "10"
    address = "8404"
    quantreg = "0001"
    noofby = "02"
    data = b
    return (id + funcode + address + quantreg + noofby + data)

def readmrsp(a):
    id = format(int(a), '02X')
    funcode = "03"
    address = "8404"
    quantreg = "0001"
    return (id + funcode + address + quantreg)

def writesamptime(a, b):
    id = format(int(a),'02X')
    funcode = "10"
    address = "8405"
    quantreg = "0001"
    noofby = "02"
    data = b
    return (id + funcode + address + quantreg + noofby + data)

def readsamptime(a):
    id = format(int(a), '02X')
    funcode = "03"
    address = "8405"
    quantreg = "0001"
    return (id + funcode + address + quantreg)

def write_max_samples(a, b):
    id = format(int(a),'02X')
    funcode = "10"
    address = "8406"
    quantreg = "0001"
    noofby = "02"
    data = b
    return (id + funcode + address + quantreg + noofby + data)

def readmax(a):
    id = format(int(a), '02X')
    funcode = "03"
    address = "8406"
    quantreg = "0001"
    return (id + funcode + address + quantreg)

def changebaud(a, b):
    id = format(int(a),'02X')
    funcode = "10"
    address = "8407"
    quantreg = "0001"
    noofby = "02"
    data = b
    return (id + funcode + address + quantreg + noofby + data)

def readbaud(a):
    id = format(int(a), '02X')
    funcode = "03"
    address = "8407"
    quantreg = "0001"
    return (id + funcode + address + quantreg)

def readmultiple(a):
    id = format(int(a),'02X')
    funcode = "03"
    address = "8501"
    quantreg = "0017"
    return (id + funcode + address + quantreg)

########################################## Controller functions #######################################

def jtob(a):
    id = format(int(a),'02X')
    funcode = "06"
    address = "8060"
    data = "00DE"
    return (id + funcode + address + data)

def jtoa(a):
    id = format(int(a),'02X')
    funcode = "06"
    address = "8060"
    data = "00CA"
    return (id + funcode + address + data)

def resetCommand(a):
    id = format(int(a),'02X')
    funcode = "06"
    address = "9060"
    data = "0040"
    return (id + funcode + address + data)

###################################### Modbus Poll ############################################
def ModbusUnicast(DataToWrite,b):  # function to Write and Receive data
    x = serial.Serial(port=on_select(), baudrate=baud(), bytesize=8, parity='N', stopbits=2, timeout=0.03)
    revdata = ""
    #    timedata1 = time.time()
    x.flush()
    x.write(DataToWrite)
    revdata = x.read(b)
    # timedata2 = time.time()
    # print("Time to transmitt ----> " + str(timedata2 - timedata1))
    x.close()
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

def makeByteBuff(string) -> object:  # returns tx buffer after adding crc to byte array
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
    ID = txt21.get().zfill(2)
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
    ID = txt21.get().zfill(2)
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
    ID = txt21.get().zfill(2)
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
    ID = txt21.get().zfill(2)
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
    ID = txt21.get().zfill(2)
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
    ID = txt21.get().zfill(2)
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
    # main loops#

def bobyte():
    ID = txt21.get()
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
    ID = txt21.get()
    print(ID)
    DataToWrite = makeByteBuff(resetCommand(ID))  # change function here
    print("Request Frame -> "),
    print(codecs.encode(DataToWrite, "HEX"))
    DataWrite = codecs.encode(DataToWrite, "HEX")
    recvdata = codecs.encode(ModbusUnicast(DataToWrite,10), "HEX")
    print("Response Frame -> "),
    print(recvdata)
    time.sleep(0.05)

########################################################################################################################

def read_stdr():
    txt1.delete(0, END)
    ID = txt21.get()
    print(ID)
    DataToWrite = makeByteBuff(readstddr(ID))  # change function here
    print("Request Frame -> "),
    print(codecs.encode(DataToWrite, "HEX"))
    recvdata = str(codecs.encode(ModbusUnicast(DataToWrite, 10), "HEX"))
    print("Response Frame -> "),
    print(recvdata[8:(len(recvdata) - 5)])
    b = (struct.unpack('!f', bytes.fromhex(recvdata[8:(len(recvdata) - 5)]))[0])
    print(b)
    txt1.insert(END,b)
    time.sleep(0.05)

def read_rstdr():
    txt2.delete(0, END)
    ID = txt21.get()
    print(ID)
    DataToWrite = makeByteBuff(readrstddr(ID))  # change function here
    print("Request Frame -> "),
    print(codecs.encode(DataToWrite, "HEX"))
    recvdata = str(codecs.encode(ModbusUnicast(DataToWrite, 10), "HEX"))
    print("Response Frame -> "),
    print(recvdata[8:(len(recvdata) - 5)])
    b = (struct.unpack('!f', bytes.fromhex(recvdata[8:(len(recvdata) - 5)]))[0])
    print(b)
    txt2.insert(END,b)
    time.sleep(0.05)

def read_mrsp():
    txt3.delete(0, END)
    ID = txt21.get()
    print(ID)
    DataToWrite = makeByteBuff(readmrsp(ID))  # change function here
    print("Request Frame -> "),
    print(codecs.encode(DataToWrite, "HEX"))
    recvdata = str(codecs.encode(ModbusUnicast(DataToWrite, 10), "HEX"))
    print("Response Frame -> "),
    print(recvdata)
    b = int(recvdata[8:(len(recvdata) - 5)],16)
    print(b)
    txt3.insert(END,b)
    time.sleep(0.05)

def read_samptime():
    txt4.delete(0, END)
    ID = txt21.get()
    print(ID)
    DataToWrite = makeByteBuff(readsamptime(ID))  # change function here
    print("Request Frame -> "),
    print(codecs.encode(DataToWrite, "HEX"))
    recvdata = str(codecs.encode(ModbusUnicast(DataToWrite, 10), "HEX"))
    print("Response Frame -> "),
    print(recvdata)
    b = int(recvdata[8:(len(recvdata) - 5)],16)
    print(b)
    txt4.insert(END,b)
    time.sleep(0.05)

def read_baud():
    txt6.delete(0, END)
    ID = txt21.get()
    print(ID)
    DataToWrite = makeByteBuff(readbaud(ID))  # change function here
    print("Request Frame -> "),
    print(codecs.encode(DataToWrite, "HEX"))
    recvdata = str(codecs.encode(ModbusUnicast(DataToWrite, 10), "HEX"))
    print("Response Frame -> "),
    print(recvdata)
    b = int(recvdata[8:(len(recvdata) - 5)], 16)
    print(b)
    if b == 1:
        txt6.insert(END, 230400)
    elif b == 3:
        txt6.insert(END, 115200)
    elif b == 5:
        txt6.insert(END, 76800)
    elif b == 7:
        txt6.insert(END, 57600)
    elif b == 11:
        txt6.insert(END, 38400)
    elif b == 15:
        txt6.insert(END, 28800)
    elif b == xx:
        txt6.insert(END, 28800)

def read_max():
    txt12.delete(0, END)
    ID = txt21.get()
    print(ID)
    DataToWrite = makeByteBuff(readmax(ID))  # change function here
    print("Request Frame -> "),
    print(codecs.encode(DataToWrite, "HEX"))
    recvdata = str(codecs.encode(ModbusUnicast(DataToWrite, 10), "HEX"))
    print("Response Frame -> "),
    print(recvdata)
    b = int(recvdata[8:(len(recvdata) - 5)], 16)
    print(b)
    txt12.insert(END, b)
    time.sleep(0.05)

def getmultipledata():
    #regdiaganosticData_Idx = 0
    reg_Voltage_Idx = 0
    regmagneticData_Idx = 1
    reg_temperature_Idx = 2

    reg_Status_Idx = 3
    prev_reg_Status_Idx = 4

    z_reg_avg_Idx = 5
    z_reg_stddr_MSB_Idx = 6
    z_reg_stddr_LSB_Idx = 7
    z_reg_rstddr_MSB_Idx = 8
    z_reg_rstddr_LSB_Idx = 9
    z_reg_maxRate_Idx = 10

    y_reg_avg_Idx = 11
    y_reg_stddr_MSB_Idx = 12
    y_reg_stddr_LSB_Idx = 13
    y_reg_rstddr_MSB_Idx = 14
    y_reg_rstddr_LSB_Idx = 15
    y_reg_maxRate_Idx = 16

    x_reg_avg_Idx = 17
    x_reg_stddr_MSB_Id = 18
    x_reg_stddr_LSB_Idx =19
    x_reg_rstddr_MSB_Idx= 20
    x_reg_rstddr_LSB_Idx = 21
    x_reg_maxRate_Idx = 22

    timev = []
    Voltage = []
    Temperature = []
    Crr_Status = []
    PreV_Status = []

    Zmeanv = []
    Zstdrv = []
    Zrstdrv = []
    Zmaxratev = []

    Ymeanv = []
    Ystdrv = []
    Yrstdrv = []
    Ymaxratev = []

    Xmeanv = []
    Xstdrv = []
    Xrstdrv = []
    Xmaxratev = []
    response = []

    if txt21.index("end") == 0:
        print("Enter proper Sensor ID")
        messagebox.showinfo('Error', 'Please enter Proper sensor ID')
    else:
        ID = txt21.get().zfill(2)

    if txt11.index("end") == 0:
        print("Enter proper polling interval")
        messagebox.showinfo('Error', 'Please enter Proper polling interval')
    else:
        t1 = float(txt11.get())

    if txt10.index("end") == 0:
        print("Enter proper Sample number")
        messagebox.showinfo('Error', 'Please enter Proper Sample number')
    else:
        sample_no = int(txt10.get())

    a = makeByteBuff(readmultiple(ID))



    filename = datetime.now().strftime('Raw_Data-%Y-%m-%d-%H.%M.csv')

    fields = [' Time', 'Voltage', 'Temperature', 'Current_Status', 'Prev_Status', 'Z-Mean Value', 'Z-Stdr', 'Z-Rstdr', 'Z-Max Rate','Y-Mean Value', 'Y-Stdr', 'Y-Rstdr', 'Y-Max Rate','X-Mean', 'X-Stdr', 'X-Rstdr', 'X-Max Rate']
    file = open(filename,"w+",newline='')
    writer = csv.writer(file, delimiter=",")
    writer.writerow(fields)

    t2 = time.time()

    for i in range(0, sample_no):

        t = datetime.now()

        DataToWrite = a  # change function here
        # print("Request Frame for multiple Resistors-   -> "),
        print(codecs.encode(DataToWrite, "HEX"))
        recvdata = str(codecs.encode(ModbusUnicast(DataToWrite,51), "HEX")).upper()
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
        #alarmv.append(z[0] + z[1])
        #meanv.append(int(z[2] + z[3], 16))
        #stdrv.append(struct.unpack('!f', bytes.fromhex(z[4] + z[5] + z[6] + z[7]))[0])
        #rstdrv.append(struct.unpack('!f', bytes.fromhex(z[8] + z[9] + z[10] + z[11]))[0])
        #maxratev.append(int(z[12] + z[13], 16))
        print((float)(int(z[reg_Voltage_Idx],16)*0x100+int(z[reg_Voltage_Idx + 1],16))*(1047 / 47) * (1.114 / 1024))
        Voltage.append(str(round((float)(int(z[0],16)*0x100+int(z[1],16))*(1047 / 47) * (1.114 / 1024),2)))
        Temperature.append(int(z[reg_temperature_Idx*2] + z[reg_temperature_Idx*2+1], 16))
        Crr_Status.append(z[reg_Status_Idx*2] + z[reg_Status_Idx*2+1])
        PreV_Status.append(z[prev_reg_Status_Idx*2] + z[prev_reg_Status_Idx*2+1])

        Zmeanv.append(int(z[z_reg_avg_Idx*2] + z[z_reg_avg_Idx*2+1], 16))
        Zstdrv.append(struct.unpack('!f', bytes.fromhex(z[z_reg_stddr_MSB_Idx*2] + z[z_reg_stddr_MSB_Idx*2+1] + z[z_reg_stddr_LSB_Idx*2] + z[z_reg_stddr_LSB_Idx*2+1]))[0])
        Zrstdrv.append(struct.unpack('!f', bytes.fromhex(z[z_reg_rstddr_MSB_Idx*2] + z[z_reg_rstddr_MSB_Idx*2+1] + z[z_reg_rstddr_LSB_Idx*2] + z[z_reg_rstddr_LSB_Idx*2+1]))[0])
        Zmaxratev.append(int(z[z_reg_maxRate_Idx*2] + z[z_reg_maxRate_Idx*2+1], 16))

        Ymeanv.append(int(z[y_reg_avg_Idx*2] + z[y_reg_avg_Idx*2+1], 16))
        Ystdrv.append(struct.unpack('!f', bytes.fromhex(z[y_reg_stddr_MSB_Idx*2] + z[y_reg_stddr_MSB_Idx*2+1] + z[y_reg_stddr_LSB_Idx*2] + z[y_reg_stddr_LSB_Idx*2+1]))[0])
        Yrstdrv.append(struct.unpack('!f', bytes.fromhex(z[y_reg_rstddr_MSB_Idx*2] + z[y_reg_rstddr_MSB_Idx*2+1] + z[y_reg_rstddr_LSB_Idx*2] + z[y_reg_rstddr_LSB_Idx*2+1]))[0])
        Ymaxratev.append(int(z[y_reg_maxRate_Idx*2] + z[y_reg_maxRate_Idx*2+1], 16))

        Xmeanv.append(int(z[x_reg_avg_Idx*2] + z[x_reg_avg_Idx*2+1], 16))
        Xstdrv.append(struct.unpack('!f', bytes.fromhex(z[x_reg_stddr_MSB_Id*2] + z[x_reg_stddr_MSB_Id*2+1] + z[x_reg_stddr_LSB_Idx*2] + z[x_reg_stddr_LSB_Idx*2+1]))[0])
        Xrstdrv.append(struct.unpack('!f', bytes.fromhex(z[x_reg_rstddr_MSB_Idx*2] + z[x_reg_rstddr_MSB_Idx*2+1] + z[x_reg_rstddr_LSB_Idx*2] + z[x_reg_rstddr_LSB_Idx*2+1]))[0])
        Xmaxratev.append(int(z[x_reg_maxRate_Idx*2] + z[x_reg_maxRate_Idx*2+1], 16))


    t3 = time.time()
    t4 = t3 - t2
    print(t4)

    print(Voltage)
    print(Temperature)
    print(Crr_Status)
    print(PreV_Status)

    print(Zmeanv)
    print(Zstdrv)
    print(Zrstdrv)
    print(Zmaxratev)

    print(Ymeanv)
    print(Ystdrv)
    print(Yrstdrv)
    print(Ymaxratev)

    print(Xmeanv)
    print(Xstdrv)
    print(Xrstdrv)
    print(Xmaxratev)


    for i in range(sample_no):

        writer.writerow([timev[i], "'" + Voltage[i], Temperature[i],"'" + Crr_Status[i],"'" + PreV_Status[i], Zmeanv[i], Zstdrv[i], Zrstdrv[i], Zmaxratev[i],
                         Ymeanv[i], Ystdrv[i], Yrstdrv[i], Ymaxratev[i],
                         Xmeanv[i], Xstdrv[i], Xrstdrv[i], Xmaxratev[i]])

########################################################################################################################

if __name__ == "__main__":
    window = Tk()
    window.title("Sensor Modbus Utility V1.1.0")
    window.geometry('740x410')
    window.resizable(0, 0)
    photo = PhotoImage(file="a1.png")
    window.iconphoto(False, photo)
    selected = IntVar()
    style = ttk.Style()

    pane = Frame(window)
    pane.pack(side = TOP,fill=BOTH, expand=True)

#########################################  main window buttons ######################################################

    lbl13 = Label(pane, text='Select COM port')
    lbl13.grid(column =1 ,row =1, padx = 10,pady=20)
    cb = ttk.Combobox(pane, values=serial_ports())
    cb.grid(column=2, row=1, padx=5, pady=20)
    cb.bind('<<ComboboxSelected>>', on_select)

    lbl9 = Label(pane, text='Enter Utility Baudrate')
    lbl9.grid(column =3 ,row =1, padx = 10)
    txt9 = Entry(pane, width=10)

    cb2 = ttk.Combobox(pane)
    cb2['values'] = (230400,115200,76800,57600,38400,28800,9600)
    cb2.grid(column=4, row=1, padx=5, pady=10)
    cb2.bind('<<ComboboxSelected>>', on_select)

    tab_control = ttk.Notebook(window)
    tab1 = ttk.Frame(tab_control)
    tab2 = ttk.Frame(tab_control)
    tab3 = ttk.Frame(tab_control)

    tab_control.add(tab1, text='Configuration')
    tab_control.add(tab2, text='Firmware Upgrade')
    tab_control.add(tab3, text='Test Center')
    tab_control.pack(expand=1, fill='both')

    lbl21 = Label(tab1, text='Enter Sensor ID')
    lbl21.grid(column=1, row=5,pady=20)
    txt21 = Entry(tab1, width=10)
    txt21.grid(column=2, row=5)

    separator = ttk.Separator(tab1, orient='horizontal')
    separator.grid(row=6, columnspan=13, ipadx=370, pady=10)

    lbl1 = Label(tab1, text='Set stdr')
    lbl1.grid(column=1, row=7,pady=10)
    txt1 = Entry(tab1, width=10)
    txt1.grid(column=2, row=7)
    btn1 = Button(tab1, text="Set", command=stdr)
    btn1.grid(column=4 , row=7,padx=10)
    btn41 = Button(tab1, text="Read", command=read_stdr)
    btn41.grid(column=5 , row=7)

    lbl2 = Label(tab1, text='Set rstdr')
    lbl2.grid(column=1, row=8,pady=10)
    txt2 = Entry(tab1, width=10)
    txt2.grid(column=2, row=8)
    btn2 = Button(tab1, text="Set", command=rstdr)
    btn2.grid(column=4, row=8)
    btn42 = Button(tab1, text="Read", command=read_rstdr)
    btn42.grid(column=5 , row=8)

    lbl3 = Label(tab1, text='Set Maxrate')
    lbl3.grid(column=1, row=9,pady=10)
    txt3 = Entry(tab1, width=10)
    txt3.grid(column=2, row=9)
    btn3 = Button(tab1, text="Set", command=maxrate)
    btn3.grid(column=4, row=9)
    btn42 = Button(tab1, text="Read", command=read_mrsp)
    btn42.grid(column=5 , row=9)

    lbl4 = Label(tab1, text='Sampling time')
    lbl4.grid(column=1, row=10,pady=10)
    txt4 = Entry(tab1, width=10)
    txt4.grid(column=2, row=10)
    btn4 = Button(tab1, text="Set", command=samtime)
    btn4.grid(column=4, row=10)
    btn43 = Button(tab1, text="Read", command=read_samptime)
    btn43.grid(column=5 , row=10)

    lbl12 = Label(tab1, text='Max no. of Samples(uC)')
    lbl12.grid(column=1, row=11,pady=10)
    txt12 = Entry(tab1, width=10)
    txt12.grid(column=2, row=11)
    btn12 = Button(tab1, text="Set", command=sam_uc)
    btn12.grid(column=4, row=11)
    btn44 = Button(tab1, text="Read", command=read_max)
    btn44.grid(column=5 , row=11)

    lbl6 = Label(tab1, text='Baudrate')
    lbl6.grid(column=1, row=12,pady=10)
    txt6 = Entry(tab1, width=10)
    txt6.grid(column=2, row=12)
    btn6 = Button(tab1, text="Set", command=baudrate_uC)
    btn6.grid(column=4, row=12)
    btn45 = Button(tab1, text="Read", command=read_baud)
    btn45.grid(column=5 , row=12)

    lbl7 = Label(tab1, text='Change BOB Byte')
    lbl7.grid(column=6, row=7,padx=20,pady=10)
    txt7 = Entry(tab1, width=10)
    txt7.grid(column=7, row=7)
    btn7 = Button(tab1, text="Change", command=bobyte)
    btn7.grid(column=8, row=7, ipadx=20)

    lbl10 = Label(tab1, text='Number of Samples')
    lbl10.grid(column=6, row=8)
    txt10 = Entry(tab1, width=10)
    txt10.grid(column=7, row=8)

    lbl11 = Label(tab1, text='Polling Time Interval')
    lbl11.grid(column=6, row=9)
    txt11 = Entry(tab1, width=10)
    txt11.grid(column=7, row=9)

    btn9 = Button(tab1, text="Get Data", command=getmultipledata)
    btn9.grid(column=8, row=10,ipadx=30)

    btn12 = Button(tab1, text="Reset Controller", command=resetUC)
    btn12.grid(column=8, row=11, ipadx=21)

    btn17 = Button(tab1, text="Quit", command=window.quit)
    btn17.grid(column=8, row=12, ipadx=30)


#######################################################################################################################

    pane = Frame(tab2)
    pane.pack(side=TOP, fill=BOTH)

    pane2 = Frame(tab2)
    pane2.pack(side=TOP, fill=BOTH)

    pane3 = Frame(tab2)
    pane3.pack(side=TOP, fill=BOTH)

    pane6 = Frame(tab2)
    pane6.pack(side=TOP, fill=BOTH)

    lbl5 = Label(pane, text='Enter Sensor range')
    lbl5.grid(column=1, row=1, padx=10, pady=20)
    txt_r1 = Entry(pane, width=7)
    txt_r1.grid(column=2, row=1, padx=30, pady=20)

    lbl7 = Label(pane, text='to')
    lbl7.grid(column=3, row=1, pady=10)
    txt_r2 = Entry(pane, width=7)
    txt_r2.grid(column=4, row=1, padx=18, pady=10)

    lbl55 = Label(pane2, text='Select File Path')
    lbl55.grid(column=1, row=3, padx=10, pady=10)
    lbl15 = Label(pane2, text="")
    lbl15.grid(column=5, row=3, padx=25, ipadx=10, pady=10)
    btn14 = Button(pane2, text="Browse bin file", command=browseFiles)
    btn14.grid(column=2, row=3, ipadx=37, padx=23)

    btn4 = Button(pane2, text="Flash bin File", command=fetch)
    btn4.grid(column=1, row=4, ipadx=15, padx=10, pady=10)

    txt = scrolledtext.ScrolledText(pane6, width=95, height=10)
    txt.grid(column=1, row=1)

    # Progress1 bar widget
    progress1 = Progressbar(pane2, orient=HORIZONTAL,
                            length=12, mode='determinate')
    progress1.grid(column=2, row=4, padx=24, ipadx=74, pady=20)

####################################################################################################

    pane5 = Frame(tab3)
    pane5.pack(side=TOP, fill=BOTH)
    pane6 = Frame(tab3)
    pane6.pack(side=TOP, fill=BOTH)

    lbl31 = Label(pane5, text='Request Frame')
    lbl31.grid(column=1, row=1, pady=20)
    txt31 = Entry(pane5, width=10)
    txt31.grid(column=2, row=1, ipadx=100)
    btn31 = Button(pane5, text="Send", command=test)
    btn31.grid(column=3, row=1, padx=10)

    lbl32 = Label(pane5, text='Response Frame')
    lbl32.grid(column=1, row=2)
    lbl33 = Label(pane5, text='')
    lbl33.grid(column=2, row=2)

    separator = ttk.Separator(pane5, orient='horizontal')
    separator.grid(row=3, columnspan=8, ipadx=370, pady=10)

window.mainloop()
