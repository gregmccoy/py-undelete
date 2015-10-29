#!/usr/bin/env python

import binascii
import sys, getopt
import os
import gc
import mmap
import mimetypes
from progressbar import AnimatedMarker, Bar, BouncingBar, Counter, ETA, \
    FileTransferSpeed, FormatLabel, Percentage, \
    ProgressBar, ReverseBar, RotatingMarker, \
    SimpleProgress, Timer
from codecs import encode, decode

#define a list
images = []
debug = True
CHUNK_SIZE = 100000000
progress = 0
chunks = 0

class Image:
    """docstring for ClassName"""
    def __init__(self, start, end, fix, chunk):
        self.start = start
        self.end = end
        self.fix = fix
        self.chunk = chunk
    def add_fix(self, fix):
        self.fix.append(fix)
        return 0
    def set_start(self, start):
        self.start = start
        return 0
    def set_end(self, end):
        self.end = end
        return 0
    def set_chunk(self, chunk):
        self.chunk = chunk
        return 0
    def get_start(self):
        return self.start
    def get_end(self):
        return self.end
    def get_fix(self):
        return self.fix
    def get_chunk(self):
        return self.chunk

        
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

def read_in_chunks(file_object, chunk_size=CHUNK_SIZE):
    """Lazy function (generator) to read a file piece by piece.
    Default chunk size: 200mb."""
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data

def read_bytes(values, index):
    return str(values[index].encode('hex')) + str(values[index+1].encode('hex'))
def parse_jpeg(index, values, temp, SOI):
    tags = ["ffdb", "ffc0", "ffc4", "ffda"]
    try:
        valid = False
        byte_size = read_bytes(values, index)
        index = index + long(byte_size, 16)
        tag = read_bytes(values, index)
        index = index + 2
        while tag in tags:
            byte_size = read_bytes(values, index)
            if(debug):
                print(tag + " - index: " + str(index))
            if (tag == tags[3]):
                end = values.find("\xFF\xD9", index, len(values))
                error = values.find("\xFF\xD8", index, end)
                if(end != -1):
                    valid = True
                    index = end
                else:
                    valid = False
                    if(debug):
                        print("*** BAD END |" + "START = " + str(SOI) + "| End = " + str(end)  + "| Chunk = " + str(chunks) + " ***\n")
                    return -1, valid

                while(error != -1): 
                    temp.add_fix(error - SOI)
                    error = values.find("\xFF\xD8", error + 2, end)
                    if(debug):
                        print("*** CORRUPT IMAGE ***")
                if(debug):
                    print("*** RECOVERED IMAGE |" + "START = " + str(SOI) + "| End = " + str(end)  + "| Chunk = " + str(chunks) + " ***\n")
                tag = 0     
            else:
                index = index + long(byte_size, 16)
                tag = read_bytes(values, index)
                index = index + 2  
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(fname, exc_tb.tb_lineno)
        print(e)  
    return index, valid

def findfile(values):
    try:
        index = 0
        SOI = values.find("\xFF\xD8\xFF", index)
        if(debug):
            print("*** NEW CHUNK " + str(chunks) + " ***")
        while(SOI != -1):
            index = SOI + 4
            temp = Image(0, 0, [], 0)
            index, valid = parse_jpeg(index, values, temp, SOI)
            if(index == -1):
                break
            if(valid):
                temp.set_start(SOI)
                temp.set_end(index + 2)
                temp.set_chunk(chunks)
                images.append(temp)
            SOI = values.find("\xFF\xD8\xFF", index)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(fname, exc_tb.tb_lineno)
        print(e)
    return index
       

def run(filename, outfile):
    #open our image file as binary
    with open(filename, 'rb') as f:
        count = 0
        f_size = get_file_size(filename)
        print(f_size)
        pbar = ProgressBar(widgets=[Percentage(), Bar(), ETA()], maxval=f_size+1).start()
        print("Recovering Files...\n")
        global chunks
        try:
            for values in read_in_chunks(f):
                findfile(values)
                chunks = chunks + 1
                #pbar.update(chunks * CHUNK_SIZE)
                gc.collect()
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(e)
            print(fname, exc_tb.tb_lineno)
        pbar.finish()
    print ("Recovering " + str(len(images)) + " Images")
    #print (str(start) + '\n' + str(end))
    count = -1
    #loop for each picture
    for i in images:
        count += 1
        try:
            start = i.get_start() + (i.get_chunk() * CHUNK_SIZE)
            end = i.get_end() + (i.get_chunk() * CHUNK_SIZE)
            print("pic" + str(count) + ": " + str(start) + "-" + str(end) + "| CHUNK = " + str(i.get_chunk()) + "| ORG_START = " + str(i.get_start()))
            with open(filename, 'rb') as f: 
                f.seek(start)
                length = (end - start)
                if length < -1:
                    length = 0
                else:
                    pic = f.read(length)
                    for fix in i.get_fix():
                        if(debug):
                            print("*** FIXING PIC " + str(count) + "| Index = " + str(fix) + "| Chunk = " + str(i.get_chunk()) + " ***")
                        try:    
                            substr = pic[fix] + pic[fix+1]
                            pic = pic[:fix] + pic[fix:fix+1].replace(substr, "\x00\x00") + pic[fix+2:]
                        except Exception as e:
                            print(e)
                            print("*** FAILED TO FIX PIC " + str(count) + " ***")
                    #print (pic)
                    #open write file
                    w = open(outfile + '/pic' + str(count+1) + '.jpeg','wb')
                    #Write from the begining of the picture to the end    
                    w.write(pic) 
                    w.close() 
            
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

    
    
