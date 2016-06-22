import os
import Tkinter
import tkFileDialog
from shutil import move

Tkinter.Tk().withdraw()
filez = tkFileDialog.askopenfilenames(title='Choose a file')
fileNames = list(filez)

fileNames.sort()
for name in fileNames:
    f = open(name, "r")
    f2 = open(name + "_temp", "w")

    for line in f:
        n_line = line.replace("C:/Users/fabian/Desktop/SVRP/","")
        f2.write(n_line)

    f.close()
    f2.close()

    os.remove(name)
    move(name + "_temp", name)