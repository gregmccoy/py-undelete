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
import random

images = []
debug = True
CHUNK_SIZE = 100000000
progress = 0
chunks = 0


JPEG_SOI = "\xFF\xD8\xFF"
PNG_SOI = "\x89\x50\x4E\x0D\x0A\x1A"

class Recover:

    filename = None
    outfile = None
    image_count = 0
    debug = False
    chunks = 0

    def __init__(self, filename, outfile, image_count=0, debug=False):
        self.filename = filename
        self.outfile = outfile
        self.image_count = image_count
        self.chunks = 0
        self.debug = debug

    def inc_image_count(self):
        self.image_count += 1
        return self.image_count

    def run(self):
        #open our image file as binary
        with open(self.filename, 'rb') as f:
            f_size = get_file_size(self.filename)

            pbar = ProgressBar(widgets=[Percentage(), Bar(), ETA()], maxval=f_size+1).start()
            print("Recovering Files...\n")

            try:
                for values in read_in_chunks(f):
                    self.findfile(values)
                    self.chunks = self.chunks + 1
                    #pbar.update(chunks * CHUNK_SIZE)
                    gc.collect()

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(e)
                print(fname, exc_tb.tb_lineno)

            pbar.finish()

    def recover_image(self, image):
        #print (str(start) + '\n' + str(end))

        #loop for each picture
        try:
            start = image.get_start() + (image.get_chunk() * CHUNK_SIZE)
            end = image.get_end() + (image.get_chunk() * CHUNK_SIZE)
            print("pic" + str(image.count) + ": " + str(start) + "-" + str(end) + "| CHUNK = " + str(image.get_chunk()) + "| ORG_START = " + str(image.get_start()))

            with open(self.filename, 'rb') as f:
                f.seek(start)
                length = (end - start)
                if length < -1:
                    length = 0
                else:
                    pic = f.read(length)
                    for fix in image.get_fix():
                        if(debug):
                            print("*** FIXING PIC " + str(image.count) + "| Index = " + str(fix) + "| Chunk = " + str(image.get_chunk()) + " ***")
                        try:
                            substr = pic[fix] + pic[fix+1]
                            pic = pic[:fix] + pic[fix:fix+1].replace(substr, "\x00\x00") + pic[fix+2:]
                        except Exception as e:
                            print(e)
                            print("*** FAILED TO FIX PIC " + str(image.count) + " ***")
                    #print (pic)
                    #open write file
                    w = open(self.outfile + '/pic' + str(image.count) + '.jpeg','wb')
                    #Write from the begining of the picture to the end
                    w.write(pic)
                    w.close()

        except Exception as e:
            print("An Error Occured - " + str(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(fname, exc_tb.tb_lineno)

    def findfile(self, values):

        try:
            index = 0
            # find Start of Image
            jpeg = True
            SOI = values.find(JPEG_SOI, index)
            #if SOI == -1:
            #    jpeg = False
            #    SOI = values.find(PNG_SOI, index)

            if(self.debug):
                print("*** NEW CHUNK " + str(self.chunks) + " ***")

            tags = []
            while(SOI != -1):
                index = SOI + 4
                temp = Image(0, 0, [], 0, 0)
                if jpeg:
                    tags = ["ffdb", "ffc0", "ffc4", "ffda"]
                else:
                    tags = ["49454e44ae426082"]
                index, valid = self.parse_jpeg(index, values, temp, SOI, tags)

                if(index == -1):
                    break

                if(valid):
                    temp.set_start(SOI)
                    temp.set_end(index + 2)
                    temp.set_chunk(self.chunks)
                    temp.set_count(str(self.inc_image_count()))
                    images.append(temp)
                    self.recover_image(temp)

                SOI = values.find("\xFF\xD8\xFF", index)
                if SOI == -1:
                    SOI = values.find(PNG_SOI, index)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(fname, exc_tb.tb_lineno)
            print(e)
        return index

    def parse_jpeg(self, index, values, temp, SOI,tags):
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
                            print("*** BAD END |" + "START = " + str(SOI) + "| End = " + str(end)  + "| Chunk = " + str(self.chunks) + " ***\n")
                        return -1, valid

                    while(error != -1):
                        temp.add_fix(error - SOI)
                        error = values.find("\xFF\xD8", error + 2, end)
                        if(debug):
                            print("*** CORRUPT IMAGE ***")
                    if(debug):
                        print("*** RECOVERED IMAGE |" + "START = " + str(SOI) + "| End = " + str(end)  + "| Chunk = " + str(self.chunks) + " ***\n")
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


class Image:
    """docstring for ClassName"""
    def __init__(self, start, end, fix, chunk, count):
        self.start = start
        self.end = end
        self.fix = fix
        self.chunk = chunk
        self.count = count

    def add_fix(self, fix):
        self.fix.append(fix)

    def set_start(self, start):
        self.start = start

    def set_end(self, end):
        self.end = end

    def set_chunk(self, chunk):
        self.chunk = chunk

    def set_count(self,count):
        self.count = count

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


#Check for command line args
if sys.argv[1] == '-h':
    #Show help
    print("usage: recover <image file> -o <outfile>")
elif sys.argv[2] == '-o':
    #run the system
    try:
        recover = Recover(sys.argv[1], sys.argv[3], debug=False)
        recover.run()
    except Exception as e:
        print("*** " + str(e) + " ***")
else:
    #wrong format so show help
    print("usage: recover <image file> -o <outfile>")

print("")



