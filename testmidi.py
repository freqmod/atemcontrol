import pypm
print "Init pypm"
INPUT=0
OUTPUT=1
def PrintDevices(InOrOut):
    for loop in range(pypm.CountDevices()):
        interf,name,inp,outp,opened = pypm.GetDeviceInfo(loop)
        if ((InOrOut == INPUT) & (inp == 1) |
            (InOrOut == OUTPUT) & (outp ==1)):
            print loop, name," ",
            if (inp == 1): print "(input) ",
            else: print "(output) ",
            if (opened == 1): print "(opened)"
            else: print "(unopened)"
    print
#PrintDevices(0)
interf,name,inp,outp,opened = pypm.GetDeviceInfo(0)
print "Got devinfo"
midiin = pypm.Input(0)
while True:
    pkg = midiin.Read(1) 
    if pkg:
        data, counter = pkg[0]
        bank, instrument, value, val2 = data
        print bank,instrument,value, int(value*7.88)
#    	print midi_msg