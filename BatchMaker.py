import Tkinter
import tkFileDialog

Tkinter.Tk().withdraw()
filez = tkFileDialog.askopenfilenames(title='Choose a file',filetypes=[("VRP Instances", ".svrp")])
fileNames = list(filez)

f = open("_batch.bat", "w")

fileNames.sort()
for name in fileNames:
    f.write("python Main.py " + name.replace("C:/Users/fabian/Desktop/SVRP/","") + "\n")

f.close()