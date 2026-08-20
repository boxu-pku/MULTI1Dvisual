#!/usr/bin/env python
# Program to read the binary data files created by MULTI1D
# Creates arrays with data
# Enables interactive plotting with Pylab routines

import struct

# Global constants:
# Number of bytes used for an integer value:
NBI = 4
# Number of bytes used for a name string:
NBC = 8
# Number of bytes used for a float value:
NBF = 8

# Function to read size of arrays in binary data file:
def readSizeArray(file):
    dummy = file.read(NBI)
    size = file.read(NBI)
    dummy = file.read(NBI)
    sizeN = struct.unpack("i", size)[0]
    return sizeN

# Function to read array of strings -> names of data array
def readNameArray(file, Nstrings):
    nameList = []
    dummy = file.read(NBI)
    for i in range(0, Nstrings):
        varName = file.read(NBC)
        decodevarName = varName.decode(encoding='utf-8')
        nameList.append(decodevarName)  #modify on 4.4
    dummy = file.read(NBI)
    return nameList

# Function to read data array -> returns list of doubles
def readDataArray(file, Nfloats):
    floatList = []
    dummy = file.read(NBI)
    if dummy == b"":
        return floatList      # end-of-file !
    #tmp = file.readline()
    for i in range(0, Nfloats):
        #floatBin = file.read(NBF)
        floatBin = file.read(8)
        if len(floatBin) == 8:
           floatVar = struct.unpack('d',floatBin)[0]
           floatList.append(floatVar)
            #floatVar = struct.unpack_from("d", floatBin,0)[0]
            #print(floatVar)
        else:
            print('报错的是：'+str(floatBin)+',长度是：'+str(len(floatBin)))
            #floatVar = struct.unpack('d',floatBin)[0]
            #floatList.append(floatVar)
    dummy = file.read(NBI)
    return floatList

# Function to create a dictionary out of the arrays with variable names
# and floating point numbers:
def createDictionary(sizeOfArrays, nameArray, dataArray):
    dictionary = {}
    nameList = []
    dataList = []
    nameList.append(nameArray[0])
    dataList.append(dataArray[0])
    for i in range(1, sizeOfArrays):
        if not(nameArray[i] in nameList):
            dictionary[nameArray[i-1]] = dataList
            nameList.append(nameArray[i])
            dataList = []
            dataList.append(dataArray[i])
        else:
            dataList.append(dataArray[i])
    dictionary[nameArray[i]] = dataList
    return dictionary

# Function to create time series for given variable from list of dictionaries
# returns list of tuples: [(t0, f(t0)), (t1, f(t1)), ...]
# Key for time value is 'TIME    '
def createTimeSeries(dictList, keyForVariable):
    timeSeries = []
    for i in range(0, len(dictList)):
        timeVal = dictList[i]['TIME    '][0]
        funcVal = dictList[i][keyForVariable][0]
        timeSeries.append((timeVal, funcVal))
    return timeSeries

# Create spatial curves from a given list of dictionaries
# returns array with list of tuples (list of tuples: [(x0, f(x0)), ...])
# Key for the spatial coordinate is 'X      '
# Returns the spatial curve
def createSpatialCurve(dictList, keyForVariable, timeIndex):
    spatialSeries = []
    #timeVal = dictList[timeIndex]['TIME    ']
    for i in range(0, len(dictList[timeIndex][keyForVariable])):
        xVal    = dictList[timeIndex]['X       '][i]
        funcVal = dictList[timeIndex][keyForVariable][i]
        spatialSeries.append((xVal, funcVal))
    return spatialSeries


# Function to create array from array of tuples:
def createArray(listOfTuples, indexVariable):
    arr = []
    for i in range(0, len(listOfTuples)):
        dummy = listOfTuples[i][indexVariable]
        arr.append(dummy)
    return arr

# Read the data file and return to lists of dictionaries
# The first list contains the time-independent data
# The second list contains time dependent data,
def readFileContents(filename):
    f = open(filename, 'rb') # Open the file
    # First block of data: time-independent data:
    Ndata = readSizeArray(f)
    print (Ndata)
    varNames = readNameArray(f, Ndata)
    firstVarList = readDataArray(f, Ndata)
    firstData = createDictionary(Ndata, varNames, firstVarList)
    # Second block: time-dependent data
    # first step: number of data points for each step (in time)
    Ndata2 = readSizeArray(f)
    print (Ndata2)
    # Number of time steps is not specified; therefore keep reading until
    # end of file is reached:
    varNames2 = readNameArray(f, Ndata2)
    secondData = []        # store time-dependent data in list of dictionaries
    secondVarList = readDataArray(f, Ndata2)
    while not(secondVarList==[]):
        tempDict = createDictionary(Ndata2, varNames2, secondVarList)
        secondData.append(tempDict)
        secondVarList = readDataArray(f, Ndata2)
    # Close the data file:
    f.close()
    # return both lists of dictionaries:
    return firstData, secondData

# Write the data as an ascii file
# Create file with time series:
def writeAsciiTimeSeries(outputFilename, dictName):
    tval = createArray(createTimeSeries(dictName, 'ENIE    '), 0)
    TSenie   = createArray(createTimeSeries(dictName, 'ENIE    '), 1) # Electron int. energy
    TSenii   = createArray(createTimeSeries(dictName, 'ENII    '), 1) # Ion int. energy
    TSenki   = createArray(createTimeSeries(dictName, 'ENKI    '), 1) # Kinetic energy
    TSenlas  = createArray(createTimeSeries(dictName, 'ENLAS   '), 1) # Incident laser energy
    TSenque  = createArray(createTimeSeries(dictName, 'ENQUE   '), 1) # Absorbed laser energy
    TSealpha = createArray(createTimeSeries(dictName, 'EALFA   '), 1) # Energy in alpha particles
    TSenag   = createArray(createTimeSeries(dictName, 'ENAG    '), 1) # Fusion energy/5
    TSenal   = createArray(createTimeSeries(dictName, 'ENAL    '), 1) # Energy lost in alphas
    TSenrad  = createArray(createTimeSeries(dictName, 'ENRAD   '), 1) # ENRL* - ENRG*
    TSeyield = createArray(createTimeSeries(dictName, 'EYIELD  '), 1) # Number of neutrons
    TSileft  = createArray(createTimeSeries(dictName, 'I-Left  '), 1) # Spectrum on left boundary
    TSiright = createArray(createTimeSeries(dictName, 'I-Right '), 1) # Spectrum on right boundary
    TSenrg1  = createArray(createTimeSeries(dictName, 'ENRG1   '), 1) #
    TSenrg2  = createArray(createTimeSeries(dictName, 'ENRG2   '), 1) #
    TSenrg3  = createArray(createTimeSeries(dictName, 'ENRG3   '), 1) #
    TSenrg4  = createArray(createTimeSeries(dictName, 'ENRG4   '), 1) #
    TSenrl1  = createArray(createTimeSeries(dictName, 'ENRL1   '), 1)
    TSenrl2  = createArray(createTimeSeries(dictName, 'ENRL2   '), 1)
    TSenrl3  = createArray(createTimeSeries(dictName, 'ENRL3   '), 1)
    TSenrl4  = createArray(createTimeSeries(dictName, 'ENRL4   '), 1)
    # Now write data as table in an ASCII file:
    outfile = open(outputFilename, 'w') # open the file
    outfile.write('#Time-series output from a MULTI1D run\n')
    outfile.write('#t(s)\tEnie\tEnii\tEnki\tEnlas\tEnque\tEalpha\tEnag\tEnal\tEnrad\tEyield\tILeft\tIRight\tEnrg1\tEnrg2\tEnrg3\tEnrg4\tEnrl1\tEnrl2\tEnrl3\tEnrl4\n')
    tab = '\t'
    for i in range(0, len(TSenie)):
        outString = repr(tval[i]) + tab + repr(TSenie[i]) + tab + repr(TSenii[i]) + tab + repr(TSenki[i]) + tab + repr(TSenlas[i]) + tab + repr(TSenque[i]) + tab + repr(TSealpha[i]) + tab + repr(TSenag[i]) + tab + repr(TSenal[i]) + tab + repr(TSenrad[i]) + tab + repr(TSeyield[i]) + tab + repr(TSileft[i]) + tab + repr(TSiright[i]) + tab + repr(TSenrg1[i]) + tab + repr(TSenrg2[i]) + tab + repr(TSenrg3[i]) + tab + repr(TSenrg4[i]) + tab + repr(TSenrl1[i]) + tab + repr(TSenrl2[i]) + tab + repr(TSenrl3[i]) + tab + repr(TSenrl4[i]) + '\n'
        outfile.write(outString)
    outfile.close()

# Write data for curves f(x,t) in ASCII file
def writeAsciiCurves(outputFilename, dictName):
    outfile = open(outputFilename, 'w')
    outfile.write('# Output from MULTI1D; spatial curves\n')
    outfile.write('# Format: First line: time\n')
    outfile.write('# XC\tDENE\tEE\tEI\tP\tPT\tR\tT\tTI\tZI\tTR\tV\tD\tEA\tF\tX\tS\tSplus\tSmin\n')
    numberTimesteps = len(dictName)
    tval = createArray(createTimeSeries(dictName, 'ENIE    '), 0)
    tab = '\t'
    for i in range(0, numberTimesteps):
        SCx    = createArray(createSpatialCurve(dictName, 'X       ', i), 1)
        SCdene = createArray(createSpatialCurve(dictName, 'DENE    ', i), 1)
        SCee   = createArray(createSpatialCurve(dictName, 'EE      ', i), 1)
        SCei   = createArray(createSpatialCurve(dictName, 'EI      ', i), 1)
        SCp    = createArray(createSpatialCurve(dictName, 'P       ', i), 1)
        SCpt   = createArray(createSpatialCurve(dictName, 'PT      ', i), 1)
        SCr    = createArray(createSpatialCurve(dictName, 'R       ', i), 1)
        SCt    = createArray(createSpatialCurve(dictName, 'T       ', i), 1)
        SCti   = createArray(createSpatialCurve(dictName, 'TI      ', i), 1)
        SCzi   = createArray(createSpatialCurve(dictName, 'ZI      ', i), 1)
        SCtr   = createArray(createSpatialCurve(dictName, 'TR      ', i), 1)
        SCv    = createArray(createSpatialCurve(dictName, 'V       ', i), 1)
        SCd    = createArray(createSpatialCurve(dictName, 'D       ', i), 1)
        SCea   = createArray(createSpatialCurve(dictName, 'EA      ', i), 1)
        SCf    = createArray(createSpatialCurve(dictName, 'F       ', i), 1)
        SCxc   = createArray(createSpatialCurve(dictName, 'XC      ', i), 1)
        SCs    = createArray(createSpatialCurve(dictName, 'S       ', i), 1)
        SCsplus= createArray(createSpatialCurve(dictName, 'S+      ', i), 1)
        SCsmin = createArray(createSpatialCurve(dictName, 'S-      ', i), 1)
        outstring = repr(tval[i]) + '\n'
        outfile.write(outstring)
        for j in range(0, len(SCxc)):
            outstring = repr(SCxc[j]) + tab + repr(SCdene[j]) + tab + repr(SCee[j]) + tab + repr(SCei[j]) + tab + repr(SCp[j]) + tab + repr(SCpt[j]) + tab + repr(SCr[j]) + tab + repr(SCt[j]) + tab + repr(SCti[j]) + tab + repr(SCzi[j]) + tab + repr(SCtr[j])+ tab + repr(SCv[j]) + tab + repr(SCd[j]) + tab + repr(SCea[j]) + tab + repr(SCf[j]) + tab + repr(SCx[j]) + tab + repr(SCs[j]) + tab + repr(SCsplus[j]) + tab + repr(SCsmin[j]) + '\n'
            outfile.write(outstring)
        outfile.write('\n')
    outfile.close()







