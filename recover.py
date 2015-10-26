#!/usr/bin/env python

import binascii
import sys, getopt
import os
import gc
import mimetypes
from progressbar import AnimatedMarker, Bar, BouncingBar, Counter, ETA, \
    FileTransferSpeed, FormatLabel, Percentage, \
    ProgressBar, ReverseBar, RotatingMarker, \
    SimpleProgress, Timer
from codecs import encode, decode

#define a list
start = []
end = []
debug = True

def inline(needle, haystack):
    try:
        return haystack.index(needle)
    except:
        return -1

def get_file_size(filename):
    fd= os.open(filename, os.O_RDONLY)
    try:
        return os.lseek(fd, 0, os.SEEK_END)
    finally:
        os.close(fd)

def parse_jpeg(index, values):
    tags = ["\xFF\xDB", "\xFF\xC0", "\xFF\xC4", "\xFF\xDA"]
    for tag in tags:
        if(debug):
            print("********" + tag.encode("hex") + "**********")
        DQT = values.find(tag, index)
        while(DQT != -1):
            DQT_size = int(str(values[DQT + 2]) + str(values[DQT + 3])) + 2
            if(debug):
                print(format(values[DQT],'02x') + format(values[DQT+1],'02x') + " - index: " + str(index) + " - size: " + str(DQT_size))
            if (tag == "\xFF\xDA"):
                index = index + 2
            else:
                index = int(index + DQT_size)
            DQT = values.find(tag, index)
    index = values.find("\xFF\xD9", index) + 2
    print(index)
    return index

def findfile(index, values):
    try:
        SOI = values.find("\xFF\xD8", index)
        while(SOI != -1):
            APP0_size = int(str(values[SOI + 4]) + str(values[SOI + 5]))
            index = index + SOI + 4 + APP0_size 
            index = parse_jpeg(index, values)
            if(debug):
                print("index: " + str(index))
            start.append(SOI)
            end.append(index)
            SOI = values.find("\xFF\xD8", index)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(fname, exc_tb.tb_lineno)
        print(e)
    return index
       

def run(filename, outfile):
    #open our image file as binary
    with open(filename, 'rb') as f:
        index = 0
        f_size = get_file_size(filename)
        print(f_size)
        print("Recovering Files...\n")
        pbar = ProgressBar(widgets=[Percentage(), Bar(), ETA()], maxval=f_size+1).start()
        s = 0
        e = 0
        try:
            garbage = 0
            while 1:
                #read file into byte array
                ba = bytearray(f.read())
                if not ba:
                    break
                findfile(index, ba)
                index += len(ba)
                garbage += len(ba)
                pbar.update(index)
                ba = None
                if garbage >= 50000000:
                    gc.collect()
                    garbage = 0
        except Exception as e:
            pbar.update(index)
            print(str(len(start)))
            print(str(index))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Memory Failure - " + str(e))
            print(fname, exc_tb.tb_lineno)
        pbar.finish()
    print ("Recovering " + str(len(start)) + " Images")
    #print (str(start) + '\n' + str(end))
    count = -1
    #loop for each picture
    for i in start:
        count += 1
        try:
            print("pic" + str(count) + ": " + str(start[count]) + "-" + str(end[count]))
            with open(filename, 'rb') as f: 
                f.seek(start[count])
                length = (end[count] - start[count])
                if length < -1:
                    length = 0
                else:
                    pic = f.read(length)
                    #print (pic)
                    #open write file
                    f = open(outfile + '/pic' + str(count+1) + '.jpeg','wb')
                    #Write from the begining of the picture to the end    
                    f.write(pic) 
                    f.close() 
            
        except Exception as e:
            print("An Error Occured - " + str(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(fname, exc_tb.tb_lineno)
            break

#Check for command line args
if sys.argv[1] == '-h':
    #Show help
    print("usage: recover <image file> -o <outfile>")
elif sys.argv[2] == '-o':
    #run the system
    try:
        run(sys.argv[1], sys.argv[3])
    except Exception as e:
        print("*** " + str(e) + " ***")
else:
    #wrong format so show help
    print("usage: recover <image file> -o <outfile>")
print("")

    
    
