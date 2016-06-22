import os
import Tkinter
import tkFileDialog

Tkinter.Tk().withdraw()
filez = tkFileDialog.askopenfilenames(title='Choose a file',filetypes=[("VRP Instances", ".svrp")])
fileNames = list(filez)

fileNames.sort()
for name in fileNames:
    newName = name.replace("PS", "PC")
    os.rename(name, newName)