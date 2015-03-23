from __future__ import print_function
import binascii
import sys, getopt
import os
import gc
from progressbar import AnimatedMarker, Bar, BouncingBar, Counter, ETA, \
    FileTransferSpeed, FormatLabel, Percentage, \
    ProgressBar, ReverseBar, RotatingMarker, \
    SimpleProgress, Timer, AdaptiveETA, AdaptiveTransferSpeed
from codecs import encode, decode

def inline(needle, haystack):
    try:
        return haystack.index(needle)
    except:
        return -1

def get_file_size(filename):
    "Get the file size by seeking at end"
    fd= os.open(filename, os.O_RDONLY)
    try:
        return os.lseek(fd, 0, os.SEEK_END)
    finally:
        os.close(fd)

def run(filename, outfile):
    #define a list
    start = []
    end = []
    #open our image file as binary
    with open(filename, 'rb') as f:
        index = 0;
        looking_for_end = 0
        f_size = get_file_size(filename)
        print(f_size)
        print("\nRecovering Files...\n")
        pbar = ProgressBar(widgets=[Percentage(), Bar(), ETA()], maxval=f_size+1).start()
        s = 0
        e = 0
        try:
            garbage = 0
            while 1:
                ba = f.readline(128000)
                if not ba:
                    break
                #read file into byte array
                found = inline(b'\xFF\xD8', ba)
                if found != -1:
                    s += 1
                    found = inline(b'\xFF\xD8\xFF\xE1', ba)
                    if found == -1:
                        if looking_for_end>=1:
                            looking_for_end += 1
                            #x = 0
                    else:
                        if looking_for_end==0:
                            start.append(index + found + 1)
                            #print("Start - " + str(len(start)))
                            #print("End - " + str(len(end)))
                            looking_for_end = 1
                
                found = inline(b'\xFF\xD9', ba)
                if found != -1:
                    e += 1
                    if looking_for_end==1:
                        end.append(index + found + 3)
                        looking_for_end = 0
                        #print(byte)
                    elif looking_for_end>1:
                        looking_for_end -= 1
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
            print("Memory Failure - " + str(e))
        pbar.finish()
    print ("Recovering " + str(len(start)) + " Images")
    print("Ends - " + str(e))
    print("Starts - " + str(s))
    #print (str(start) + '\n' + str(end))
    count = -1
    #loop for each picture
    for i in start:
        count += 1
        try:
            print("pic" + str(count) + ": " + str(start[count]) + "-" + str(end[count]))
            with open(filename, 'rb') as f:
                f.seek(start[count]-1)
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
            print (str(len(start)))
            print (str(len(end)))
            print (str(end[count] - start[count]))
            print("An Error Occured - " + str(e))
            break

#Check for command line args
if sys.argv[1] == '-h':
    #Show help
    print("usage: recover <image file> -o <outfile>")
elif sys.argv[2] == '-o':
    #run the system
    run(sys.argv[1], sys.argv[3])
else:
    #wrong format so show help
    print("usage: recover <image file> -o <outfile>")
print("")

    
    
