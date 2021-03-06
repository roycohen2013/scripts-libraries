#================================================================================================
#
#	@file			FC3DM_utils.py
#
#	@brief			Python script functions to help create electronics 3D models in FreeCAD.
#
#	@details		
#
#    @version		0.4.22
#					   $Rev::                                                                        $:
#	@date			  $Date::                                                                        $:
#	@author			$Author::                                                                        $:
#					    $Id::                                                                          $:
#
#	@copyright      Copyright (c) 2012 Sierra Photonics, Inc.  All rights reserved.
#	
#***************************************************************************
# * The Sierra Photonics, Inc. Software License, Version 1.0:
# *  
# * Copyright (c) 2012 by Sierra Photonics Inc.  All rights reserved.
# *  Author:        Jeff Collins, jcollins@sierraphotonics.com
# *  Author:        $Author$
# *  Check-in Date: $Date$ 
# *  Version #:     $Revision$
# *  
# * Redistribution and use in source and binary forms, with or without
# * modification, are permitted provided that the following conditions
# * are met and the person seeking to use or redistribute such software hereby
# * agrees to and abides by the terms and conditions below:
# *
# * 1. Redistributions of source code must retain the above copyright
# * notice, this list of conditions and the following disclaimer.
# *
# * 2. Redistributions in binary form must reproduce the above copyright
# * notice, this list of conditions and the following disclaimer in
# * the documentation and/or other materials provided with the
# * distribution.
# *
# * 3. The end-user documentation included with the redistribution,
# * if any, must include the following acknowledgment:
# * "This product includes software developed by Sierra Photonics Inc." 
# * Alternately, this acknowledgment may appear in the software itself,
# * if and wherever such third-party acknowledgments normally appear.
# *
# * 4. The Sierra Photonics Inc. names or marks must
# * not be used to endorse or promote products derived from this
# * software without prior written permission. For written
# * permission, please contact:
# *  
# *  Sierra Photonics Inc.
# *  attn:  Legal Department
# *  7563 Southfront Rd.
# *  Livermore, CA  94551  USA
# * 
# * IN ALL CASES AND TO THE FULLEST EXTENT PERMITTED UNDER APPLICABLE LAW,
# * THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESSED OR IMPLIED
# * WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# * OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# * DISCLAIMED.  IN NO EVENT SHALL SIERRA PHOTONICS INC. OR 
# * ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# * USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# * OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# * SUCH DAMAGE.
# *
# * This software consists of voluntary contributions made by many
# * individuals on behalf of the Altium Community Software.
# *
# * See also included file SPI_License.txt.
# * 
# * THEORY OF OPERATIONS
# * This script is part of a multiscript process that will create a footprint and 3D
# * model and attach them all together in an Altium component library file (PcbLib).
# * This script is called by FC3DM_IC.py when it is run SPI_Cleanup_LPW_Footprint.pas
# * writes an ini file describing the dimensions of the IC package that FC3DM_IC.py
# * should create. 
# * 
# * WHAT THIS SCRIPT DOES
# * This script provides the functions for which FC3DM_IC.py calls in order to create
# * the 3D model as defined by the ini file created by SPI_Cleanup_LPW_Footprint.pas. 
# * It also contains functions that help the functions called by FC3DM_IC.py. 
# * These helper functions include:
# *     A function to create a box
# *     A function to cut an object with a box
# *     A function to cut an object with a filleted box
# *     A function to cut an object with a pre-defined object
# *     A function to rotate an object about the Z axis
# *     A function to fillet the edges of an object
# *     A function to create a cylinder
# * 
# * 
# ***************************************************************************


import FreeCAD, Draft
import Part
import math
import string
import cStringIO
import sys
import os
import re
import ast
from FreeCAD import Base

scriptPathUtils = ""

# Fudge factor used by QFN packages to have pins and body be in ever so slightly different planes
tinyDeltaForQfn = 0.000001
deltaForBodyCutsLength = 0.2
deltaForBodyCutsPosition = 0.1
debugFilePath = "null"
 
###################################################################
# FC3DM_OpenDebugFile()
#	Open a debug file to which we will write debug messages
###################################################################
def FC3DM_OpenDebugFile(parms):

    # Retrieve the debug file path from parms
    global debugFilePath
    debugFilePath = parms["debugFilePath"]

    # Open the debug file in "write" mode to overwrite any existing "FC3DM_Debug.txt"
    debugFile = open(debugFilePath, "w")
    
    debugFile.write("We finally have a debug file!\n")

    debugFile.write("Debug File Path is " + debugFilePath + "\n\n")

    # Close the file to save the changes
    debugFile.close()

###################################################################
# FC3DM_WriteToDebugFile()
# 	Write necessary debug messages to "FC3DM_Debug.txt" in the working directory
###################################################################
def FC3DM_WriteToDebugFile(msg):

    # Open the debug file in append mode to add the message to the existing debug file
    global debugFilePath
    debugFile = open(debugFilePath, "a")
    
    # Write message to the debug file  
    debugFile.write(msg + "\n")

    # Close the file to save the changes
    debugFile.close()
    
    
###################################################################
# FC3DM_CloseDebugFile()
#	Function to save and close debug file
###################################################################
def FC3DM_CloseDebugFile():

    
    # Open the debug file in append mode so that we may close it
    global debugFilePath
    debugFile = open(debugFilePath, "a")

    # Close the file to save the changes
    debugFile.close()

    return 0


###################################################################
# is_number()
# 	Function below was stolen from Daniel Goldberg's post at:
#  http://stackoverflow.com/questions/354038/how-do-i-check-if-a-string-is-a-number-in-python
###################################################################
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


###################################################################
# FC3DM_SortPinNames()
#	Function to do custom comparison for pin names.
###################################################################
def FC3DM_SortPinNames(a, b):

    # See if we're even sorting a pair of valid pin names
    if (a.startswith("Pin") and b.startswith("Pin")):

        # Strip off anything after an '=' char.
        tup = a.partition('=')
        a = tup[0];
        tup = b.partition('=')
        b = tup[0];

        # Strip off leading "Pin" from a & b pin names
        aStr = a.replace("Pin", "");
        bStr = b.replace("Pin", "");

        ## TODO:  Support BGA pin names!

        # Try to convert remaining names to integer
        try:
            aInt = int(aStr);
            bInt = int(bStr);

            if aInt > bInt:
                return 1
            elif aInt == bInt:
                return 0
            else:
                return -1
            
        # This failed, so one or both has a BGA or EP style name.  Use cmp() builtin.
        except ValueError:
            return cmp(aStr, bStr)

    # Else at least one of these is not a valid pin name.  Do simple comparison using builtin.
    else:
        return cmp(a, b)
    

###################################################################
# FC3DM_NormalizeAbsPath()
#	Function to normalize an absolute path.  Interpret any "../foo/bar" type of
# things.  Change path separators to unix style.
###################################################################
def FC3DM_NormalizeAbsPath(myPath):

    # Interpret any "../foo/bar" structures, remove redundant path separators, etc.
    myPath = os.path.abspath(myPath)
#    FC3DM_WriteToDebugFile("myPath is now: " + myPath)

    # Change to unix style path separators
    myPath = myPath.replace("\\", "/")
#    FC3DM_WriteToDebugFile("myPath is now: " + myPath)

    return myPath


###################################################################
# FC3DM_NormalizeRelPath()
#	Function to normalize a relative path.  Interpret any "../foo/bar" type of
# things.  Change path separators to unix style.
###################################################################
def FC3DM_NormalizeRelPath(myPath):

    # Interpret any "../foo/bar" structures, remove redundant path separators, etc.
    myPath = os.path.relpath(myPath)
#    FC3DM_WriteToDebugFile("myPath is now: " + myPath)

    # Change to unix style path separators
    myPath = myPath.replace("\\", "/")
#    FC3DM_WriteToDebugFile("myPath is now: " + myPath)

    return myPath


###################################################################
# FC3DM_ReadIniFile()
#	Function to read an ini file.  File format is "key=value".
# 	Debug messages should not be written in this function because
#	debug file has not yet been created.
###################################################################
def FC3DM_ReadIniFile(iniFileName,
                      parms):

    # Open ini file with our paths and parameters
    print ("About to open ini file :" + iniFileName + ":")

    #ins = open(iniFileName, "rb" )
    lines = [line.strip() for line in open(iniFileName, "r")]

    array = []
    for line in lines:
        array.append( line )

        # Exclude all lines beginning with '#' comment character
        if (not (line.startswith('#'))):
#            print line

            # Split at '#' char to strip off any within-line comments
            tup = line.partition('#')
            line = tup[0];

            # Look for '=' sign to indicate name=value pair
            if (line.find('=') > -1):
#                print "Found name=value pair!"

                # Split at '=' sign and strip off leading/trailing whitespace
                tup = line.partition('=')
                name = tup[0].strip()
                value = tup[2].strip()
#                print("name=:" + name + ":")
#                print("value=:" + value + ":")

                # Use AST library to safely evaluate type (int, float, string, tuple, etc.) and then add to parms list.
                parms[name] = ast.literal_eval(value)

    return 0

                
###################################################################
# FC3DM_ReadIniFiles()
#	Function to read both global and component-specific ini files.
# 	Debug messages should not be written in this function because
#	debug file has not yet been created.
###################################################################
def FC3DM_ReadIniFiles(scriptPath, parms):

    # Store to global variable
    global scriptPathUtils
    scriptPathUtils = scriptPath

    ## Prepare to read global ini file.
    # Append ini file name.
    iniFileName = scriptPath + "\\" + "FC3DM_global.ini"

    # Read global ini file
    FC3DM_ReadIniFile(iniFileName,
                      parms)

    # Write parms to console window
    print "Parms are:"
    print parms

    ## Prepare to read component-specific ini file.
    # Extract relevant parameter values from parms associative array
    # TODO:  Currently no error checking!
    # Note:  Assumes that iniFileName from file is a relative directory!
    #  Thus, we must pre-pend our path to this.
    iniFileName = FC3DM_NormalizeRelPath(scriptPath + "\\" + parms["iniFileName"])
    parms["iniFileName"] = iniFileName

    # Read component-specific ini file
    FC3DM_ReadIniFile(iniFileName,
                      parms)

    ## Set standard colors for our component (if they are not defined in ini file!)
    if (not "colorPin1Mark" in parms):
        parms["colorPin1Mark"] = ((1.00,1.00,1.00)) # White for pin1Mark

    if (not "colorPins" in parms):
        parms["colorPins"] = ((0.80,0.80,0.75)) 	# Bright tin for all pins

    if (not "colorBody" in parms):
        parms["colorBody"] = ((0.10,0.10,0.10))		# Black for body    


    ## Extract relevant parameter values from parms associative array
    # TODO:  Currently no error checking!

    # See if we've been given a relative path for the new model
    if ("newModelPathRel" in parms):
        newModelPath = FC3DM_NormalizeAbsPath(scriptPath + "\\" + parms["newModelPathRel"])
        newModelPath = newModelPath + "/"
        parms["newModelPath"] = newModelPath

    # Else we expect an absolute path in the ini file.
    else:
        newModelPath = parms["newModelPath"]
        
    # TODO:  Currently no error checking!
    newModelName = parms["newModelName"]
    stepSuffix = parms["stepSuffix"]
    stepExt = parms["stepExt"]

    ## Calculate derived strings
    newModelPathNameExt = newModelPath + newModelName + ".FCStd"
    newStepPathNameExt = newModelPath + newModelName + stepSuffix + stepExt
    logFilePathNameExt = newModelPath + newModelName + ".log"
    debugFilePath = newModelPath + "FC3DM_Debug.txt"

    # Strip out all "-" characters for use as the FreeCAD document name
    docName = string.replace(newModelName + stepSuffix, "-", "_")

    ## Store derived strings to parms
    parms["newModelPathNameExt"] = newModelPathNameExt
    parms["newStepPathNameExt"] = newStepPathNameExt
    parms["logFilePathNameExt"] = logFilePathNameExt
    parms["docName"] = docName

    # This is a derived parm. All derived parms should be excluded when writing to the log file in FC3DM_DescribeObjectsToLogFile()
    parms["debugFilePath"] = debugFilePath

    ## Remove bogus parms
    del parms["foo"]

    # Write parms to console window
    print "Parms are:"
    print parms

    return 0


###################################################################
# FC3DM_FilletObjectEdges()
# 	Function to fillet edges of a given object.
###################################################################
def FC3DM_FilletObjectEdges(App, Gui,
                            docName, filletMe, edges, radius):

    FC3DM_WriteToDebugFile("Hello from FC3DM_FilletObjectEdges()")
    FC3DM_WriteToDebugFile("About to fillet " + filletMe)

    # Init
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)

    # Fillet the sharp edges of the termination sheet metal
    Gui.activateWorkbench("PartDesignWorkbench")
    App.activeDocument().addObject("PartDesign::Fillet","Fillet")
    App.activeDocument().Fillet.Base = (App.ActiveDocument.getObject(filletMe),edges)
    Gui.activeDocument().hide(filletMe)
#    Gui.activeDocument().Fusion.Visibility=False
    Gui.activeDocument().setEdit('Fillet')
    App.ActiveDocument.Fillet.Radius = radius
    App.ActiveDocument.recompute()
    Gui.activeDocument().resetEdit()

    # Remove the objects that made up the fillet
    App.getDocument(docName).removeObject(filletMe)

    # Copy the cut object and call it the original cutMe name
    newTermShape = FreeCAD.getDocument(docName).getObject("Fillet").Shape.copy()
    newTermObj = App.activeDocument().addObject("Part::Feature",filletMe)
    newTermObj.Shape = newTermShape
    
    # Remove the fillet itself
    App.getDocument(docName).removeObject("Fillet")

    return 0


###################################################################
# FC3DM_ChamferObjectEdges()
# 	Function to chamfer edges of a given object.
#
# NOTE:  This function is less useful than you may think.  If you
#  want a 45 deg chamfer, then the two planes meeting at the edge
#  that you want to chamfer must be perpendicular!  If, on the
#  other hand, one is angled by the mold angle, then calling this
#  function will NOT give you a 45 degree absolute chamfer!
###################################################################
def FC3DM_ChamferObjectEdges(App, Gui,
                             docName, chamferMe, edges, size):

    # Init
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)

    # Chamfer the specified edge(s)
    Gui.activateWorkbench("PartDesignWorkbench")
    App.activeDocument().addObject("PartDesign::Chamfer","Chamfer")
    App.activeDocument().Chamfer.Base = (App.ActiveDocument.getObject(chamferMe),edges)
    Gui.activeDocument().hide(chamferMe)
#    Gui.activeDocument().Fusion.Visibility=False
    Gui.activeDocument().setEdit('Chamfer')
    App.ActiveDocument.Chamfer.Size = size
    App.ActiveDocument.recompute()
    Gui.activeDocument().resetEdit()

    # Remove the objects that made up the chamfer
    App.getDocument(docName).removeObject(chamferMe)

    # Copy the cut object and call it the original cutMe name
    newTermShape = FreeCAD.getDocument(docName).getObject("Chamfer").Shape.copy()
    newTermObj = App.activeDocument().addObject("Part::Feature",chamferMe)
    newTermObj.Shape = newTermShape
    
    # Remove the chamfer itself
    App.getDocument(docName).removeObject("Chamfer")

    return 0


###################################################################
# FC3DM_DescribeObjectsToLogFile()
#	Function to describe all objects to a log file.
###################################################################
def FC3DM_DescribeObjectsToLogFile(App, Gui,
                                   parms, pinNames,
                                   docName):

    # Extract relevant parameter values from parms associative array
    # TODO:  Currently no error checking!
    bodyName = parms["bodyName"]
    pin1MarkName = parms["pin1MarkName"]
    logFilePathNameExt = parms["logFilePathNameExt"]
    stepSuffix = parms["stepSuffix"]

    # Init
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)

    ## Analyze stepSuffix so that we can strip the trailing digits from this from all parms.
    ## This way, our generated logfile will not encode the rev number of this STEP file.
    # Strip off the trailing digits.  Eg. convert "_TRT1" to "_TRT".
    stepSuffixStripped = re.sub('[0-9]+$', '', stepSuffix)

    ## Dump all parms to string list
    strList = list()

    # Loop over all parms
    for name in parms:

        # Strip off any trailing digits from stepSuffix and derived strings (eg. convert "_TRT1" to "_TRT")
        value = str(parms[name])
        valueStripped = re.sub(stepSuffix, stepSuffixStripped, value)

        # Append this to string list
        strList.append(name + "=" + valueStripped)

    # Sort the string list
    strList.sort(FC3DM_SortPinNames)

    ## Open the logfile
    fileP = open(logFilePathNameExt, 'w')

    # Log all the parms to logfile
    fileP.write("Parms:\n")
    for i in strList:
    
        #FC3DM_WriteToDebugFile(i)
        # We will exclude some of the derived parms when writing to the log file.
        if ( (not i.startswith("debugFilePath")) and (not i.startswith("footprintType")) and (not i.startswith("hasEp")) and (not i.startswith("newModelPathRel")) ):
            fileP.write(i + '\n')

    ## Log all pin vertices to logfile.
    # Loop over all the pin names.
    for pin in pinNames:

        # Initialize an array that will store the vertices and be sorted
        pinVertexArray = []
        
        FC3DM_WriteToDebugFile("About to describe pin " + pin + " to log file")
        print("About to describe pin " + pin + " to log file!")

        # Declare the name of this object
        fileP.write("\n" + pin + ':\n')

        # Declare the soon-to-be color of this object
        fileP.write("Color " + str(parms["colorPins"]) + "\n")

        # Loop over all the faces in this pin.
        for face in App.ActiveDocument.getObject(pin).Shape.Faces:

            # Loop over all the vertexes in this pin
            for vertex in face.Vertexes:
            
                # Add this pin vertex to an array that will be sorted and printed to the log file
                pinVertexArray.append(str(vertex.Point))
                
        # FC3DM_WriteToDebugFile(pin + " vertices: ")
        # Write the sorted array to the log file if the line is not null
        pinVertexArray.sort(FC3DM_SortPinNames)
        for line in pinVertexArray:
            if (line != ""):
                # FC3DM_WriteToDebugFile(line)
                fileP.write(line + "\n")
        fileP.write("")
                

    ## Log all body vertices to logfile.
    # Declare the name of this object
    fileP.write("\n" + bodyName + ':\n')
    FC3DM_WriteToDebugFile("About to describe " + bodyName + " to log file")

    # Declare the soon-to-be color of this object
    fileP.write("Color " + str(parms["colorBody"]) + "\n")

    # Initialize an array that will store the vertices and be sorted
    bodyVertexArray = []
    
    # Loop over all the faces in this body.
    for face in App.ActiveDocument.getObject(bodyName).Shape.Faces:

        # Loop over all the vertexes in this body
        for vertex in face.Vertexes:
            # Add this vertex to an array that will be sorted and written to the log file.
            bodyVertexArray.append(str(vertex.Point))

    # FC3DM_WriteToDebugFile("Body vertices: ")
    # Write the sorted array to the log file if the line is not null
    bodyVertexArray.sort(FC3DM_SortPinNames)
    for line in bodyVertexArray:
        if (line != ""):
            # FC3DM_WriteToDebugFile(bodyVertexArray[i])
            fileP.write(line + "\n")
    fileP.write("")

    ## Log all pin1Mark vertices to logfile.
    # Declare the name of this object
    fileP.write("\n" + pin1MarkName + ':\n')

    # Declare the soon-to-be color of this object
    fileP.write("Color " + str(parms["colorPin1Mark"]) + "\n")

    # Initialize an array that will store the vertices and be sorted
    pin1MarkerVertexArray = []

    # Loop over all the faces in this pin1Mark.
    for face in App.ActiveDocument.getObject(pin1MarkName).Shape.Faces:

        # Loop over all the vertexes in this pin1Mark
        for vertex in face.Vertexes:

                        
            # Add this pin vertex to an array that will be sorted and printed to the log file
            pin1MarkerVertexArray.append(str(vertex.Point))
                
    # FC3DM_WriteToDebugFile("Pin1 Mark vertices: ")
    # Write the sorted array to the log file if the line is not null
    pin1MarkerVertexArray.sort(FC3DM_SortPinNames)
    for line in pin1MarkerVertexArray:
        if (line != ""):
            # FC3DM_WriteToDebugFile(line)
            fileP.write(line + "\n")
    fileP.write("")


    # Close the logfile
    fileP.close()
        
    return 0


###################################################################
# FC3DM_FuseObjects()
#	Function to fuse two objects together.
###################################################################
def FC3DM_FuseObjects(App, Gui,
                      docName, fuseMe, addMeToFusion):

    # Fuse two objects
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)
    App.activeDocument().addObject("Part::MultiFuse","Fusion")
    App.activeDocument().Fusion.Shapes = [App.ActiveDocument.getObject(fuseMe), App.ActiveDocument.getObject(addMeToFusion)]
    App.ActiveDocument.recompute()

    # Remove the objects that made up the fusion
    App.getDocument(docName).removeObject(fuseMe)
    App.getDocument(docName).removeObject(addMeToFusion)

    # Copy the fusion object and call it the original fuseMe name
    newTermShape = FreeCAD.getDocument(docName).getObject("Fusion").Shape.copy()
    newTermObj = App.activeDocument().addObject("Part::Feature",fuseMe)
    newTermObj.Shape = newTermShape
    
    # Remove the fusion itself
    App.getDocument(docName).removeObject("Fusion")

    return 0


###################################################################
# FC3DM_FuseSetOfObjects()
#	Function to fuse a set of objects together and preserve face colors.
###################################################################
def FC3DM_FuseSetOfObjects(App, Gui,
                           parms,
                           docName, objNameList, fusionName):

    FC3DM_WriteToDebugFile("Hello from FC3DM_FuseSetOfObjects()")

    # Extract relevant parameter values from parms associative array
    # TODO:  Currently no error checking!
    bodyName = parms["bodyName"]
    pin1MarkName = parms["pin1MarkName"]
    FC3DM_WriteToDebugFile("pin1MarkName is: " + pin1MarkName + ":")


    # Configure active document
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)
    
    FC3DM_WriteToDebugFile("Creating an object list")
    # Create list of objects, starting with object names
    objs=[]
    for i in objNameList:
        
        FC3DM_WriteToDebugFile("Adding new obj from objNameList: " + i + ":.")
        objs.append(App.activeDocument().getObject(i))

    # Do the multi-fusion.  Write to new "Temp" object.
    FC3DM_WriteToDebugFile("Writing multi-fusion to \"Temp\"")
    Gui.activateWorkbench("PartWorkbench")
    FC3DM_WriteToDebugFile("Activated workbench")
    App.activeDocument().addObject("Part::MultiFuse","Temp")
    FC3DM_WriteToDebugFile("Added object")
    App.activeDocument().getObject("Temp").Shapes = objs
    FC3DM_WriteToDebugFile("Got object")
    FC3DM_WriteToDebugFile("The following step may take as long as 5 minutes. Be patient for complicated components")
    App.ActiveDocument.recompute()

    # Copy the temp fusion object and call it the desired fusion name
    FC3DM_WriteToDebugFile("Copying \"Temp\" to " + fusionName)
    newTermShape = FreeCAD.getDocument(docName).getObject("Temp").Shape.copy()
    newTermObj = App.activeDocument().addObject("Part::Feature", fusionName)
    newTermObj.Shape = newTermShape
    App.ActiveDocument.recompute()
    FC3DM_WriteToDebugFile("Done with multi-fusion.")


    ### Preserve face colors for the body and pin1Mark!
    # Cache vertex lists for the body and pin1Mark, so that we may find them later
    # in the fused object.
    FC3DM_WriteToDebugFile("About to loop over pin1Mark faces")
    ## Loop over all faces in the pin1Mark object
    pin1MarkVerts=[]
    for i in App.ActiveDocument.getObject(pin1MarkName).Shape.Faces:
        FC3DM_WriteToDebugFile("Found face in pin1Mark object!")

        # Loop over all the vertexes in this face
        bufList = []
        for j in i.Vertexes:

            bufList.append(str(j.Point))

        # Sort bufList so that we can reliably pattern match against it later on.
        bufList.sort()

        # Write bufList to debug file
        FC3DM_WriteToDebugFile("Vertexes for this face are: " + str(bufList))

        # Store all the vertexes for this face as a string array
        pin1MarkVerts.append(str(bufList))


    FC3DM_WriteToDebugFile("About to loop over body faces")
    ## Loop over all faces in the body object
    bodyVerts=[]
    for i in App.ActiveDocument.getObject(bodyName).Shape.Faces:
        FC3DM_WriteToDebugFile("Found face in body object!")

        # Loop over all the vertexes in this face
        bufList = []
        for j in i.Vertexes:

            bufList.append(str(j.Point))

        # Sort bufList so that we can reliably pattern match against it later on.
        bufList.sort()

        # Write bufList to debug file
        FC3DM_WriteToDebugFile("Vertexes for this face are: " + str(bufList))

        # Store all the vertexes for this face as a string array
        bodyVerts.append(str(bufList))


    FC3DM_WriteToDebugFile("About to loop over pin faces")
    ## Loop over all faces in the pin objects
    pinVerts=[]
    for k in objNameList:

        # See if this object name is the body or pin 1 marker.
        if ( (k != bodyName) and (k != pin1MarkName) ):

            FC3DM_WriteToDebugFile("Found pin object named " + k + ".")

            # Loop over all the vertexes in this face
            for i in App.ActiveDocument.getObject(k).Shape.Faces:
                FC3DM_WriteToDebugFile("Found face in pin object!")

                # Loop over all the vertexes in this face
                bufList = []
                for j in i.Vertexes:

                    bufList.append(str(j.Point))

                # Sort bufList so that we can reliably pattern match against it later on.
                bufList.sort()

                # Write bufList to debug file
                FC3DM_WriteToDebugFile("Vertexes for this face are: " + str(bufList))

                # Store all the vertexes for this face as a string array
                pinVerts.append(str(bufList))


    ## Prepare to compare all faces in the fusion with pin1Mark, pin, and body faces
    faceColors=[]

    # Loop over all the faces in the fusion object
    for xp in App.ActiveDocument.getObject(fusionName).Shape.Faces:
        FC3DM_WriteToDebugFile("")
        FC3DM_WriteToDebugFile("Found face in fusion object!")

        # Clear found flags for pin1Mark, body, and pin
        isPin1Mark = False;
        isBody = False;
        isPin = False;

        # Loop over all the vertexes in this fusion shape face
        buf = cStringIO.StringIO()
        bufList = []
        for j in xp.Vertexes:

            # Record this vertex in a string buffer
            print >> buf, j.Point
            bufList.append(str(j.Point))

        # Sort bufList so that we can reliably pattern match against it later on.
        bufList.sort()
        
        # Write bufList to debug file
        FC3DM_WriteToDebugFile("Vertexes for this face are:"  + str(bufList))

        # Convert this vertex to a string.
        thisVert = ""
        thisVert = str(bufList)


        # See if this face is the same as a face from the pin1Mark object
        for i in pin1MarkVerts:

            # I can't get Faces.isSame() to actually work.  That's why I'm doing this
            # kludge with sprint'ing vertex info to a string.
#            FC3DM_WriteToDebugFile(xp.isSame(i))
        
            # See if the i string (from a pin1Mark vertex string) equals our current vertex string
            if (thisVert == i):
                isPin1Mark = True;

        # See if this face is the same as a face from the pin1Mark object
        for i in pinVerts:

            # I can't get Faces.isSame() to actually work.  That's why I'm doing this
            # kludge with sprint'ing vertex info to a string.
#            FC3DM_WriteToDebugFile(xp.isSame(i))
        
            # See if the i string (from a pin vertex string) equals our current vertex string
            if (thisVert == i):
                isPin = True;

        # See if this face is the same as a face from the body object
        for i in bodyVerts:

            # I can't get Faces.isSame() to actually work.  That's why I'm doing this
            # kludge with sprint'ing vertex info to a string.
#            FC3DM_WriteToDebugFile(xp.isSame(i))
        
            # See if the i string (from a body vertex string) equals our current vertex string
            if (thisVert == i):
                isBody = True;


        # See if we found a face that derives from our pin1Mark
        if (isPin1Mark):

            FC3DM_WriteToDebugFile("This face in fusion exactly matched a pin1Mark face.")

            # Color Pin1Mark white
            faceColors.append(parms["colorPin1Mark"])

        # See if we found a face that derives from a pin
        elif (isPin):

            FC3DM_WriteToDebugFile("This face in fusion exactly matched a pin face.")

            # Color pin bright tin.
            faceColors.append(parms["colorPins"])
        
        # See if we found a face that derives from our body
        elif (isBody):

            FC3DM_WriteToDebugFile("This face in fusion exactly matched a body face.")

            # Color body black
            faceColors.append(parms["colorBody"])

        # Else we're not sure what it is.  Assume that it's part of the body
        # that got modified as pins fused to it, and thus wasn't an exact match.
        else:

            FC3DM_WriteToDebugFile("This face in fusion didn't match a known face!")

            # Count the number of vertex lines in this string.
            numLines = len(buf.getvalue().splitlines())

            # Empirically I've seen that unmatched pin faces have only 4 vertexes.
            # TODO:  Will this simple distinction be true for non-gullwing ICs???
            isChipResistor = False
            if ("compType" in parms):
                if (parms["compType"] == "chipResistor"):
                    isChipResistor = True
            FC3DM_WriteToDebugFile(" isChipResistor = " + str(isChipResistor))

            if ( (numLines <= 4) and (isChipResistor == False) ):
                FC3DM_WriteToDebugFile(" numLines is " + str(numLines) + ".  Hoping it's part of a pin!")

                # Color pin bright tin.
                faceColors.append(parms["colorPins"])
        
            # Else we assume that it's part of the body.
            else:
           
                FC3DM_WriteToDebugFile(" numLines is " + str(numLines) + ".  Hoping it's part of the body!")

                # Color body black
                faceColors.append(parms["colorBody"])


    # Now that we have a list of all the face colors that we want, proceed to apply it
    # to the fusion shape.
    # A special thanks here to FC guru/author WMayer for his forum post at
    # https://sourceforge.net/apps/phpbb/free-cad/viewtopic.php?f=19&t=4117
    # which pointed me in the right direction to make this actually work.                
    FC3DM_WriteToDebugFile("Attempting to set fusion face colors")
    FC3DM_WriteToDebugFile("Attempting to set fusion face colors")
    Gui.ActiveDocument.getObject(fusionName).DiffuseColor=faceColors
    App.ActiveDocument.recompute()
    FC3DM_WriteToDebugFile("Attempted to set fusion face colors")

    FC3DM_WriteToDebugFile("Deleting the original objects that made up the fusion")
    # Delete the original objects that comprised the fusion
    for i in objNameList:

        App.activeDocument().removeObject(i)

    # Remove the temp fusion
    App.getDocument(docName).removeObject("Temp")
    App.ActiveDocument.recompute()

    # Deallocate list
    del objs

    return 0


###################################################################
# FC3DM_CutWithSpecified Object()
#	Function to cut an object with an object that was created earlier.
###################################################################
def FC3DM_CutWithSpecifiedObject(App, Gui,
                                 docName, cutMe, cutter):

    # Perform cut
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)
    App.activeDocument().addObject("Part::Cut","Cut000")
    App.activeDocument().Cut000.Base = FreeCAD.getDocument(docName).getObject(cutMe)
    App.activeDocument().Cut000.Tool = App.activeDocument().Cutter
    Gui.activeDocument().hide(cutMe)
    Gui.activeDocument().hide(cutter)
    App.ActiveDocument.recompute()
    
    # Remove the objects that made up the cut
    App.getDocument(docName).removeObject(cutMe)
    App.getDocument(docName).removeObject(cutter)

    # Copy the cut object and call it the original cutMe name
    newTermShape = FreeCAD.getDocument(docName).getObject("Cut000").Shape.copy()
    newTermObj = App.activeDocument().addObject("Part::Feature",cutMe)
    newTermObj.Shape = newTermShape

    # Remove the cut itself
    App.getDocument(docName).removeObject("Cut000")
                             
    return 0

###################################################################
# FC3DM_CutWithFilletedBox()
#	Function to cut an object with a filleted box that we create for this purpose.
###################################################################
def FC3DM_CutWithFilletedBox(App, Gui,
                             docName, cutMe,
                             L, W, H, x, y, ppH,
                             r0, r1, r2, r3,
                             edges, radius):
    
    # Create box to use to cut away at body
    App.ActiveDocument.addObject("Part::Box", "Cutter")
    App.ActiveDocument.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    FreeCAD.getDocument(docName).getObject("Cutter").Length = L
    FreeCAD.getDocument(docName).getObject("Cutter").Width = W
    FreeCAD.getDocument(docName).getObject("Cutter").Height = H
    FreeCAD.getDocument(docName).getObject("Cutter").Placement = App.Placement(App.Vector(x, y, ppH),App.Rotation(r0, r1, r2, r3))

    Gui.activateWorkbench("PartWorkbench")

    # See if we need to filet the cutting box
    if (radius != 0.0) :

        # Fillet the selected edges of this cutting box
        FC3DM_FilletObjectEdges(App, Gui,
                                docName, "Cutter", edges, radius)

    # Pass cutMe and the "Cutter" to FC3DM_CutWithSpecifiedObject() to do all the cutting
    FC3DM_CutWithSpecifiedObject(App, Gui,
                                 docName, cutMe, "Cutter")

    return 0


###################################################################
# FC3DM_CutWithBox()
#	Function to cut an object with a box that we create for this purpose.
###################################################################
def FC3DM_CutWithBox(App, Gui,
                     docName, cutMe,
                     L, W, H, x, y, ppH,
                     r0, r1, r2, r3):


    edges = []
    radius = 0.0

    # Call FC3DM_CutWithFilletedBox() to do all the real work
    FC3DM_CutWithFilletedBox(App, Gui,
                             docName, cutMe,
                             L, W, H, x, y, ppH,
                             r0, r1, r2, r3,
                             edges, radius)
    
    return 0


###################################################################
# FC3DM_CutObjectWithToolAndKeepTool()
#	Function to cut an object with a tool object, but keep tool
# object when we're all done.
###################################################################
def FC3DM_CutObjectWithToolAndKeepTool(App, Gui,
                                       docName, cutMe, cuttingTool):
    
    # Copy the tool object
    newTermShape = FreeCAD.getDocument(docName).getObject(cuttingTool).Shape.copy()
    newTermObj = App.activeDocument().addObject("Part::Feature","newCuttingTool")
    newTermObj.Shape = newTermShape

    # Perform cut
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)
    App.activeDocument().addObject("Part::Cut","Cut000")
    App.activeDocument().Cut000.Base = FreeCAD.getDocument(docName).getObject(cutMe)
    App.activeDocument().Cut000.Tool = FreeCAD.getDocument(docName).getObject("newCuttingTool")
    Gui.activeDocument().hide(cutMe)
    Gui.activeDocument().hide("newCuttingTool")
    App.ActiveDocument.recompute()

    # Remove the objects that made up the cut
    App.getDocument(docName).removeObject(cutMe)
    App.getDocument(docName).removeObject("newCuttingTool")

    # Copy the cut object and call it the original cutMe name
    newTermShape = FreeCAD.getDocument(docName).getObject("Cut000").Shape.copy()
    newTermObj = App.activeDocument().addObject("Part::Feature",cutMe)
    newTermObj.Shape = newTermShape

    # Remove the cut itself
    App.getDocument(docName).removeObject("Cut000")

    return 0


###################################################################
# FC3DM_CutObjectWithToolAndDiscardTool
#	Function to cut an object with a tool object, and discard
# tool object when we're all done.
###################################################################
def FC3DM_CutObjectWithToolAndDiscardTool(App, Gui,
                                          docName, cutMe, cuttingTool):

    # Call FC3DM_CutObjectWithToolAndKeepTool() to do all the real work
    FC3DM_CutObjectWithToolAndKeepTool(App, Gui,
                                       docName, cutMe, cuttingTool)

    # Remove the tool
    App.getDocument(docName).removeObject(cuttingTool)

    return 0
    


###################################################################
# FC3DM_TranslateObjectAndRotateAboutZ()
#	Function to translate an object in x,y and then rotate it about Z axis.
###################################################################
def FC3DM_TranslateObjectAndRotateAboutZ(App, Gui,
                                         docName, rotMe,
                                         x, y, rotDeg):

    # Convert to radians
    rot = math.radians(rotDeg)

    # Rotate about the Z-axis.  Do the specified x,y translations.
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)
    FreeCAD.getDocument(docName).getObject(rotMe).Placement = App.Placement(App.Vector(x,y,0),App.Rotation(0,0,math.sin(rot/2),math.cos(rot/2)))

    return 0


###################################################################
# FC3DM_RotateObjectAboutZ()
#	Function to rotate an object about Z axis.
###################################################################
def FC3DM_RotateObjectAboutZ(App, Gui,
                             docName, rotMe, rotDeg):

    # Call FC3DM_TranslateObjectAndRotateAboutZ() to do all the real work
    FC3DM_TranslateObjectAndRotateAboutZ(App, Gui,
                                         docName, rotMe,
                                         0, 0, rotDeg)

    return 0


###################################################################
# FC3DM_CreateBox()
#	Function to create and place a box.
#
# Parameter names are per Mentor LP Wizard tool:
# L == width of body
# W == length of body
# H == height of body
# K == standoff height of body
#
# Other parameters
# x == x coordinate of body
# y == y coordinate of body
# rotDeg == rotation about Z axis, in degrees
###################################################################
def FC3DM_CreateBox(App, Gui,
                    L, W, H, K,
                    x, y, rotDeg, 
                    docName,
                    bodyName):
    
    # Constant pi
    pi = 3.141592654

    # Create box to model IC body
    App.ActiveDocument.addObject("Part::Box",bodyName)
    App.ActiveDocument.recompute()
    Gui.SendMsgToActiveView("ViewFit")

    # Set body size
    FreeCAD.getDocument(docName).getObject(bodyName).Length = L
    FreeCAD.getDocument(docName).getObject(bodyName).Width = W
    FreeCAD.getDocument(docName).getObject(bodyName).Height = (H-K)

    # Compute initial rotation about z axis
    rot = math.radians(rotDeg)

    # Center the body at (0,0), set standoff height, and set initial rotation about Z-axis
    FreeCAD.getDocument(docName).getObject(bodyName).Placement = App.Placement(App.Vector(x, y, K),App.Rotation(0,0,math.sin(rot/2),math.cos(rot/2)))
    
    return 0


###################################################################
# FC3DM_CreateAndCenterBox()
#	Function to create and center a box
#
# Parameter names are per Mentor LP Wizard tool:
# L == width of body
# W == length of body
# H == height of body
# K == standoff height of body
#
# Other parameters:
# rotDeg == rotation about Z axis, in degrees
###################################################################
def FC3DM_CreateAndCenterBox(App, Gui,
                             L, W, H, K,
                             rotDeg, 
                             docName,
                             bodyName):
    
    # Compute x and y coordinates
    # FIXME:  Do we have to account for rotation as we do this???
    x = -1*(L/2)
    y = -1*(W/2)

    # Call FC3DM_CreateBox() to do all the real work.
    FC3DM_CreateBox(App, Gui,
                    L, W, H, K,
                    x, y, rotDeg, 
                    docName,
                    bodyName)
    
    return 0


###################################################################
# FC3DM_CreateCylinderVert()
#	Function to create a vertical (oriented in Z-axis) cylinder.
###################################################################
def FC3DM_CreateCylinderVert(App, Gui,
                             docName, cylName, x, y, z, radius, height):

    Gui.activateWorkbench("PartWorkbench")
    App.ActiveDocument.addObject("Part::Cylinder",cylName)
    App.ActiveDocument.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    FreeCAD.getDocument(docName).getObject(cylName).Radius = radius
    FreeCAD.getDocument(docName).getObject(cylName).Height = height
    FreeCAD.getDocument(docName).getObject(cylName).Placement = App.Placement(App.Vector(x,y,z),App.Rotation(0,0,0,1))

    return 0


###################################################################
# FC3DM_CreateIcBody()
# 	Function to create an IC body
#
# Parameter names are per Mentor LP Wizard tool:
# A == width of body
# B == length of body
# H == height of body
# K == standoff height of body
#
# Other parameters:
# maDeg == mold angle in degrees
# Hpph == height of high pivot point
# Hppl == height of low pivot point
# Frbody == fillet radius (for top and bottom faces)
# P1markOffset == Offset in X and Y from pin1 corner to start of pin 1 marker
###################################################################
def FC3DM_CreateIcBody(App, Gui,
                       parms,
                       docName):

    FC3DM_WriteToDebugFile("Hello from FC3DM_CreateIcBody()")

    # Extract relevant parameter values from parms associative array
    # TODO:  Currently no error checking!
    A = parms["A"]
    B = parms["B"]
    H = parms["H"]
    K = parms["K"]
    maDeg = parms["maDeg"]
    Hpph = parms["Hpph"]
    Hppl = parms["Hppl"]
    Frbody = parms["Frbody"]
    P1markOffset = parms["P1markOffset"]
    P1markRadius = parms["P1markRadius"]
    P1markIndent = parms["P1markIndent"]
    markHeight = parms["markHeight"]
    bodyName = parms["bodyName"]
    pin1MarkName = parms["pin1MarkName"]
    newModelName = parms["newModelName"]

    # Figure out the footprintType for the current IC model.
    # Do this by extracting just the leading characters in the newModelName.
    # footprintType = echo $newModelName | sed 's/[0-9]+.*//g'
    footprintType = re.sub('[0-9]+.*', '', newModelName)
    # This is a derived parm. All derived parms should be excluded when writing the log file in FC3DM_DescribeObjectsToLogFile()
    parms["footprintType"] = footprintType
    print footprintType

    print "docName is :" + docName + ":"
    print "bodyName is:" + bodyName + ":"
    print "B is       :" + str(B) + ":"


    # See if this package has an EP (exposed pad)
    if ("Tt" in parms):

        # Flag that this package has an EP
        hasEp = True

        # Enforce that the body is not allowed to go all the way to the PCB surface.
        # This is necessary in order to get the coloring right for pins vs. body.
        K = max(K, tinyDeltaForQfn)
        parms["K"] = K        

    else:
        hasEp = False

    # Store whether or not we have an EP pad.
    # This is a derived parm. All derived parms should be excluded when writing the log file in FC3DM_DescribeObjectsToLogFile()
    parms["hasEp"] = hasEp

    
    # For SOIC packages, chamfer the upper long edge along pin 1        
    if (footprintType == "SOIC"):

        # Retrieve chamfer offset
        P1chamferOffset = parms["P1chamferOffset"]

    # Handle QFN packages.
    elif (footprintType == "QFN"):

        # Set for no pin 1 chamfer
        P1chamferOffset = 0

        # Enforce that the body is not allowed to go all the way to the PCB surface.
        # This is necessary in order to get the coloring right for pins vs. body.
        K = max(K, tinyDeltaForQfn)
        parms["K"] = K        

    # Other packages have no chamfer of the body upper long edge along pin 1        
    else:
        P1chamferOffset = 0

    # Constant pi
    pi = 3.141592654

    # Mold angle (in radians)
    ma = math.radians(maDeg)

    # Chamfer angle in degrees and radians
    caDeg = 45
    ca = math.radians(caDeg)

    # The pin 1 chamfer is referenced to the cut-away body, not at the rectangular prism prior to all the cuts.
    # moldOffset === offset due to mold angle
    # tan (maDeg) = moldOffset / (H-Hpph)
    # moldOffset = (H-Hpph) * tan(maDeg)
    moldOffset = (H-Hpph) * math.tan(ma)

    # Configure active document
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)

    # Prepare to call FC3DM_CreateBox() to create a box to for the IC body
    # Choose initial rotation of 90 degrees about z axis
    # We want pin 1 to be in the upper left corner to match the assumptions in Mentor LP Wizard
    lBox = B
    wBox = A
    xBox = 1*(A/2)
    yBox = -1*(B/2)
    rotDeg = 90.0
    FC3DM_CreateBox(App, Gui,
                    lBox, wBox, H, K,
                    xBox, yBox, rotDeg, 
                    docName,
                    bodyName)
    
    # Useless cut to reset the coordinates of the body
    FC3DM_CutWithBox(App, Gui,
                     docName, bodyName,
                     A, H-K, H-K, -1*(A/2), B/2, K,
                     0, 0, 0, 0)

    ## Make 2 cuts to each side of body, to model mold angle
    # Only do the cuts if we have a mold angle
    if (maDeg > 0):    

        # Perform a cut at the north side of the IC body (pivot point high)
        FC3DM_CutWithBox(App, Gui,
                         docName, bodyName,
                         A + deltaForBodyCutsLength, A, A, -1*(A/2) - deltaForBodyCutsPosition, 1*(B/2), Hpph,
                         math.sin(ma/2),0,0,math.cos(ma/2))

        # Perform a cut at the north side of the IC body (pivot point low)
        FC3DM_CutWithBox(App, Gui,
                         docName, bodyName,
                         A + deltaForBodyCutsLength, A, A, -1*(A/2) - deltaForBodyCutsPosition, 1*(B/2), Hppl,
                         math.sin(((3*pi)/4)-(ma/2)),0,0,math.cos(((3*pi)/4)-(ma/2)))


        # Rotate the IC body 180 degrees about the z axis
        FC3DM_RotateObjectAboutZ(App, Gui,
                                 docName, bodyName, 180)

        # Perform a cut at the north side of the IC body (pivot point high)
        FC3DM_CutWithBox(App, Gui,
                         docName, bodyName,
                         A + deltaForBodyCutsLength, A, A, -1*(A/2) - deltaForBodyCutsPosition, 1*(B/2), Hpph,
                         math.sin(ma/2),0,0,math.cos(ma/2))

        # Perform a cut at the north side of the IC body (pivot point low)
        FC3DM_CutWithBox(App, Gui,
                         docName, bodyName,
                         A + deltaForBodyCutsLength, A, A, -1*(A/2) - deltaForBodyCutsPosition, 1*(B/2), Hppl,
                         math.sin(((3*pi)/4)-(ma/2)),0,0,math.cos(((3*pi)/4)-(ma/2)))


        # Rotate the IC body 90 degrees about the z axis
        FC3DM_RotateObjectAboutZ(App, Gui,
                                 docName, bodyName, 90)

        # Perform a cut at the north side of the IC body (pivot point high)
        FC3DM_CutWithBox(App, Gui,
                         docName, bodyName,
                         B + deltaForBodyCutsLength, B, B, -1*(B/2) - deltaForBodyCutsPosition, 1*(A/2), Hpph,
                         math.sin(ma/2),0,0,math.cos(ma/2))

        # Perform a cut at the north side of the IC body (pivot point low)
        FC3DM_CutWithBox(App, Gui,
                         docName, bodyName,
                         B + deltaForBodyCutsLength, B, B, -1*(B/2) - deltaForBodyCutsPosition, 1*(A/2), Hppl,
                         math.sin(((3*pi)/4)-(ma/2)),0,0,math.cos(((3*pi)/4)-(ma/2)))

    
        # Rotate the IC body 180 degrees about the z axis
        FC3DM_RotateObjectAboutZ(App, Gui,
                                 docName, bodyName, 180)

        # Perform a cut at the north side of the IC body (pivot point high)
        FC3DM_CutWithBox(App, Gui,
                         docName, bodyName,
                         B + deltaForBodyCutsLength, B, B, -1*(B/2) - deltaForBodyCutsPosition, 1*(A/2), Hpph,
                         math.sin(ma/2),0,0,math.cos(ma/2))


        # See if we need to do the pin 1 chamfer on the body
        if (P1chamferOffset > 0):

            # TODO:  Add sanity check to ensure that the chamfer doesn't cut into the body below the
            # level of where the top-most part of the pin enters the body.  If it does, then we
            # would break our underlying assumption that the pins are symmetric side-to-side.
            # Detect this and abort on error!

            # Perform a cut at the north side of the IC body (chamfer on pin 1 long side of body)
            FC3DM_CutWithBox(App, Gui,
                             docName, bodyName,
                             B, B, B, -1*(B/2), (1*(A/2) - moldOffset - P1chamferOffset), H,
                             math.sin(-1*(ca/2)),0,0,math.cos(ca/2))

        # Perform a cut at the north side of the IC body (pivot point low)
        FC3DM_CutWithBox(App, Gui,
                         docName, bodyName,
                         B + deltaForBodyCutsLength, B, B, -1*(B/2) - 2*deltaForBodyCutsPosition, 1*(A/2), Hppl,
                         math.sin(((3*pi)/4)-(ma/2)),0,0,math.cos(((3*pi)/4)-(ma/2)))

    
        # Do final rotation of the IC body 90 degrees about the z axis
        FC3DM_RotateObjectAboutZ(App, Gui,
                                 docName, bodyName, 90)

    # endif (maDeg > 0)

    ## Attempt to analyze the faces in the body, to find which ones to fillet.
    # Loop over all the faces in this pin.
    print("Here are the edges!")
    numEdges = len(App.ActiveDocument.getObject(bodyName).Shape.Edges)
    print(" Number of edges is " + str(numEdges))

    # Workaround for the fact that edge.Name doesn't work.
    # Since we now know the number of edges, and we know FC's naming convention, we shall
    # iterate through the edges by name, rather than by reference.
#    for edgeNum in range(1, numEdges):

#        edgeName = "Edge" + str(edgeNum)
#        print("Examining " + edgeName)

#        edge = App.ActiveDocument.getObject(edgeName)


    # Attempt to iterate over all the edges in the shape.
    # For each edge, analyze its vertexes and find ones that are on the top or bottom faces.
    # Then select such edges for filleting.
    # The problem is that I can't find a way to extract the edge name.
    # Thus, this is currently useless.
    for edge in App.ActiveDocument.getObject(bodyName).Shape.Edges:
        print edge #.PropertiesList #Label #str(edge)

        # Loop over all the vertexes in this edge
        for vertex in edge.Vertexes:
            
            # Write this vertex
            print(str(vertex.Point))

    # endfor loop over edges            

    # If we had a pin 1 chamfer, we only have 7 edges to fillet, not 8.
    if (P1chamferOffset > 0):

        # Set the faces that need to be filleted
        edges=["Edge4","Edge6","Edge9","Edge11","Edge14","Edge17","Edge21"]

    else:

        # Set the faces that need to be filleted
        edges=["Edge4","Edge6","Edge14","Edge11","Edge9","Edge17","Edge19","Edge20"]

    ## Fillet all non-chamfered edges on the top & bottom faces
    # Note:  Do them all at once, because I've had a hard time with finding edge names on
    # the top face after filleting the bottom face, and vice versa.
    # TODO:  This is currently hardcoded!
    # TODO:  This must be revisited for BGA, etc.!
    # Only do the filleting if we have a mold angle
    #if ( (maDeg > 0) and (footprintType <> "SOIC") ):    
    #
    #    FC3DM_FilletObjectEdges(App, Gui,
    #                            docName, bodyName, edges, Frbody)


    ## Prepare to make pin 1 marker

    # Create a cylinder to use for cutting out for pin 1 marker
    cylName = "CylCuttingTool"
    FC3DM_CreateCylinderVert(App, Gui,
                             docName, cylName, (-1*(A/2))+moldOffset+P1chamferOffset+Frbody+P1markOffset+P1markRadius, (B/2)-moldOffset-Frbody-P1markOffset-P1markRadius, (H-P1markIndent), P1markRadius, H)

    # Use this dummy cylinder to cut into the IC body
    FC3DM_CutObjectWithToolAndDiscardTool(App, Gui,
                                          docName, bodyName, cylName)

    # Apply pin 1 marker ink inside cut
    FC3DM_CreateCylinderVert(App, Gui,
                             docName, pin1MarkName, (-1*(A/2))+moldOffset+P1chamferOffset+Frbody+P1markOffset+P1markRadius, (B/2)-moldOffset-Frbody-P1markOffset-P1markRadius, (H-P1markIndent), P1markRadius, markHeight)

    return 0


###################################################################
# FC3DM_CreateIcPinGullwing()
#	Function to create a gullwing IC pin.
#
# Parameter names are per Mentor LP Wizard tool:
# L == Overall component width (pin tip to pin tip)
# A == Overall body width
# B == Overall body length
# W == Pin width
# T == Pin landing length
#
# Other parameters:
# Tp == Pin thickness (z dimension)
# Fr == Fillet radius for pin edges
# Hpe == Height of pin entry to body (center)
###################################################################
def FC3DM_CreateIcPinGullwing(App, Gui,
                              parms,
                              docName):
                
    FC3DM_WriteToDebugFile("Hello from FC3DM_CreateIcPinGullwing()")

    # Extract relevant parameter values from parms associative array
    # TODO:  Currently no error checking!
    L = parms["L"]
    A = parms["A"]
    B = parms["B"]
    W = parms["W"]
    T = parms["T"]
    K = parms["K"]
    Tp = parms["Tp"]
    Fr = parms["Fr"]
    Hpe = parms["Hpe"]
    maDeg = parms["maDeg"]
    Hpph = parms["Hpph"]
    Hppl = parms["Hppl"]
    pinName = parms["pinName"]
    bodyName = parms["bodyName"]
    footprintType = parms["footprintType"]
    
    pinTemplateNorth = "pinTemplateNorth"
    
    # Configure active document
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)

    # Prepare to call FC3DM_CreateBox() to create a box for the template pin
    FC3DM_WriteToDebugFile("About to create box for template pin")
    maRad = math.radians(maDeg)
    x = A/2.0 -  (Tp*math.tan(maRad))
    y = -1*(W/2)
    H = (Hpe + (Tp/2.0))
    K = 0.0
    rotDeg = 0.0
    boxLength = (L/2.0) - (A/2.0) + (Tp*math.tan(maRad))
    FC3DM_WriteToDebugFile("boxLength: " + str(boxLength))
    FC3DM_CreateBox(App, Gui,
                    boxLength, W, H, K,
                    x, y, rotDeg, 
                    docName,
                    pinName)
    
    # Cut away top-right part of the IC pin solid
    edges=["Edge4"]
    radius=0.3*Fr	# FIXME:  How to compute the inner radius (here) as a function of outer radius (Fr)???
    FC3DM_CutWithFilletedBox(App, Gui,
                             docName, pinName,
                             L, L, L, (L/2)-T+Tp, -1*(W/2), Tp,
                             0, 0, 0, 0,
                             edges, radius)
    
    # Cut away lower-left part of the IC pin solid
    FC3DM_WriteToDebugFile("About to cut lower-left part of the IC pin solid")
    edges=["Edge6"]
    FC3DM_CutWithFilletedBox(App, Gui,
                             docName, pinName,
                             (L/2)-T, W, Hpe-(Tp/2.0), 0, -1*(W/2), 0,
                             0, 0, 0, 0,
                             edges, radius)

    # Fillet (round) some of the gullwing pin edges
    FC3DM_WriteToDebugFile("About to fillet gullwing pin edges")
    edges=["Edge4","Edge30"]
    FC3DM_FilletObjectEdges(App, Gui,
                            docName, pinName, edges, Fr)

    FC3DM_WriteToDebugFile("About to cut gullwing pin that exists within IC body")

    ## Before we were using FC3DM_CutWithToolAndKeepTool() to perform this cut but we were experiencing unknown problems with a handful of packages
    ## The following process makes the assumption that the pin starts and ends within the upper mold angle cut in the z direction. If this condition is not met, the script will abort.

    # Sanity check to validate our assumption
    if ((Hpe - (Tp/2.0)) < Hpph ):
        FC3DM_WriteToDebugFile("Abort message: In FC3DM_CreateIcPinGullwing(), lower entry point of pin is below mold angle cut. This violates the assumption that the pin will enter the body above the mold angle cut.")
        FC3DM_MyExit(-1)

    FC3DM_WriteToDebugFile("A is: " + str(A) + " W is: " + str(W) + " Hpe is: " + str(Hpe) + " Tp is: " + str(Tp))
    FC3DM_WriteToDebugFile("A/2.0 is: " + str(A/2.0) + "-(W/2.0) is: " + str(-(W/2.0)) + " Hpe - Tp/2.0 is: " + str( Hpe - Tp/2.0))
    FC3DM_WriteToDebugFile("maRad: " + str(maRad))

    # Create a box that will be used to cut the pin so that the pin does not over lap with the body
    FC3DM_CreateBox(App, Gui,
                    A, A, A, Hpe - (Tp/2.0),
                    A/2.0, -(W/2.0), 0, 
                    docName, "Cutter")

    # Rotate the box just created
    Draft.rotate(FreeCAD.getDocument(docName).getObject("Cutter"), -90 - maDeg, Base.Vector(A/2.0, -(W/2.0), Hpe - (Tp/2.0)), Base.Vector(0,1,0))

    # Cutting the pin with the box just created so that the pin can fuse with the body later
    FC3DM_CutWithSpecifiedObject(App, Gui,
                                 docName, pinName, "Cutter")

    # Zoom in on pin model
    Gui.SendMsgToActiveView("ViewFit")


    ## Copy this to give us a template north side IC pin
    if ( footprintType == "QFP" ):
        FC3DM_WriteToDebugFile("Copying the east side template pin to create a north side template pin")
        if (A <> B):
            FC3DM_WriteToDebugFile("Package is rectangular")
            y = (B/2.0) - (A/2.0)
        else:
            FC3DM_WriteToDebugFile("Package is square")
            y = 0.0
            
        x = 0.0   
        rotDeg = 90.0
        FC3DM_WriteToDebugFile("Dumping params to debug file: " + str(x) + " "  + str(y) + " " + str(rotDeg) + " " + docName + " " + pinName + " " + pinTemplateNorth)
        FC3DM_CopyObject(App, Gui,
                         x, y, rotDeg,
                         docName,
                         pinName,
                         pinTemplateNorth)
        FC3DM_WriteToDebugFile("Back from copying template pin to north side")
        

        
        # Perform a useless cut on the north side pin so that the coordinates are reset
        FC3DM_CreateBox(App, Gui,
                        A, A, A, 0,
                        W/2.0, B/2.0 -( Tp*(math.tan(maRad))), 0, 
                        docName, "Cutter")
        
        FC3DM_CutWithSpecifiedObject(App, Gui,
                                     docName, pinTemplateNorth, "Cutter")
        
        # Color north pin red.  FIXME--remove this!
        FC3DM_WriteToDebugFile("Changing the north template gullwing pin red...")
        Gui.getDocument(docName).getObject(pinTemplateNorth).ShapeColor = (1.00,0.00,0.00)
        
        
    
    # Color east pin red.  FIXME--remove this!
    FC3DM_WriteToDebugFile("Changing the east template gullwing pin red...")
    Gui.getDocument(docName).getObject(pinName).ShapeColor = (1.00,0.00,0.00)
    
    return 0


###################################################################
# FC3DM_CreateIcPinQfn()
#	Function to create a QFN IC pin.
#
# Parameter names are per Mentor LP Wizard tool:
# L == Overall component width (pin tip to pin tip)
# W == Pin width
# T == Pin landing length
#
# Other parameters:
# Tp == Pin thickness (z dimension)
###################################################################
def FC3DM_CreateIcPinQfn(App, Gui,
                         parms,
                         docName):
                
    FC3DM_WriteToDebugFile("Hello from FC3DM_CreateIcPinQfn()")

    # Extract relevant parameter values from parms associative array
    # TODO:  Currently no error checking!
    L = parms["L"]
    A = parms["A"]
    B = parms["B"]
    W = parms["W"]
    T = parms["T"]
    Tp = parms["Tp"]
    hasDshapePads = parms["hasDshapePads"]
    pinName = parms["pinName"]
    bodyName = parms["bodyName"]

    pinTemplateEast = pinName
    pinTemplateNorth = "pinTemplateNorth"
    
    # Configure active document
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)

    # Prepare to call FC3DM_CreateBox() to create a box for the template pin
    FC3DM_WriteToDebugFile("About to create box for template pin")
    xBox = ((L/2)-T)
    yBox = -1*(W/2)
    H = Tp
    K = 0.0
    rotDeg = 0.0
    FC3DM_CreateBox(App, Gui,
                    L, W, H, K,
                    xBox, yBox, rotDeg, 
                    docName,
                    pinName)

    # See if we need to fillet to create D-shaped pins
    if (hasDshapePads <> 0):

        FC3DM_WriteToDebugFile("QFN has D-shape pads")
        
        # Set the faces that need to be filleted
        edges=["Edge1", "Edge3"]

        # Compute fillet radius.
        # We must subtract a small amount or else the filleting operation fails.
        Fr = (W/2) - 0.00001

        # Do the filleting
        FC3DM_FilletObjectEdges(App, Gui,
                                docName, pinName, edges, Fr)

    # Perform an unnecessary cut just to reset the baseline location for this pin.
    # Allow the pins to extend ever so slightly beyond the body in x, so that after all is said
    # and done, we can distinguish body vs. pin for purposes of coloring the fusion.
    FC3DM_CutWithBox(App, Gui,
                     docName, pinName,
                     L, W, W, (L/2)+tinyDeltaForQfn, -1*(W/2), 0,
                     0, 0, 0, 0)

    ## Copy this to give us a template north side IC pin
    FC3DM_WriteToDebugFile("Copying the east side template pin to create a north side template pin")
    if (A <> B):
        y = (B/2.0) - (A/2.0)
    else:
        y = 0.0
        
    x = 0.0   
    rotDeg = 90.0
    FC3DM_CopyObject(App, Gui,
                     x, y, rotDeg,
                     docName,
                     pinTemplateEast,
                     pinTemplateNorth)

    # Perform an unnecessary cut just to reset the baseline location for this pin.
    FC3DM_CutWithBox(App, Gui,
                    docName, pinTemplateNorth,
                    W, L, T, -1*(W/2), (B/2)+tinyDeltaForQfn, 0.0, 
                    0, 0, 0, 0)

    # Zoom in on pin model
    Gui.SendMsgToActiveView("ViewFit")

    # Color pin red.  FIXME--remove this!
    Gui.getDocument(docName).getObject(pinName).ShapeColor = (1.00,0.00,0.00)
    Gui.getDocument(docName).getObject(pinTemplateNorth).ShapeColor = (0.00,0.00,1.00)

    return 0


###################################################################
# FC3DM_CreateIcPinEp()
#	Function to create an exposed pad (EP) underneath the IC body.
#
# Other parameters:
# Tp == Pin thickness (z dimension)
###################################################################
def FC3DM_CreateIcPinEp(App, Gui,
                        parms,
                        length, width, x, y,
                        epName,
                        pinType,
                        docName):
                
    FC3DM_WriteToDebugFile("Hello from FC3DM_CreateIcPinEp()")

    # Assume that the EP does not have rounded corners
    roundedCorners = False

    # Extract relevant parameter values from parms associative array
    # TODO:  Currently no error checking!
    Tp = parms["Tp"]
    bodyName = parms["bodyName"]
    Ft = parms["Ft"] #pkgDimsEpChamfer
    Rt = parms["Rt"] #pkgDimsEpCornerRadius
    
    if ("epPin1ChamferRadius" in parms):
        epPin1ChamferRadius = parms["epPin1ChamferRadius"]
    else:
        epPin1ChamferRadius = 0.0

	# If there are different types of EPs in this component, extract the parameters from parms
    if (pinType.startswith("Type")):
        Ft = parms[pinType + "_Ft"]
        Rt = parms[pinType + "_Rt"]
        epPin1ChamferRadius = parms[pinType + "_epPin1ChamferRadius"]

    FC3DM_WriteToDebugFile("Ep length: " + str(length))
    FC3DM_WriteToDebugFile("Ep width: " + str(width))
    FC3DM_WriteToDebugFile("Ep chamfer: " + str(Ft))
    FC3DM_WriteToDebugFile("Ep corner radius: " + str(Rt))
    FC3DM_WriteToDebugFile("Ep chamfer radius: " + str(epPin1ChamferRadius))
    
    # Prepare parameters for FC3DM_CreateBox()
    FC3DM_WriteToDebugFile("Creating box for EP...")
    L = length
    W = width
    xBox = (-1*(W/2) + x)
    yBox = (-1*(L/2) + y)
    H = Tp
    K = 0.0
    rotDeg = 0.0
    FC3DM_CreateBox(App, Gui,
                    W, L, H, K,
                    xBox, yBox, rotDeg, 
                    docName,
                    epName)

    if (Rt > 0.0):
        FC3DM_WriteToDebugFile("About to fillet EP corners")
        FC3DM_WriteToDebugFile("EP corner radius is: " + str(Rt))
        
        # Select the edges to be filleted. If there is not a pin 1 chamfer, we will
        # fillet all the edges. Otherwise, we will fillet all the edges except for
        # the pin 1 chamfer edge
        if ((Ft > 0.0) or (epPin1ChamferRadius > 0.0)):
            edges = ["Edge1", "Edge5", "Edge7"]
        else:
            edges = ["Edge1", "Edge3", "Edge5", "Edge7"]

        # Call FC3DM_FilletObjectEdges to actually do the filleting
        FC3DM_FilletObjectEdges(App, Gui,
                                docName, epName, edges, Rt)
        
        FC3DM_WriteToDebugFile("Back from FC3DM_FilletObjectEdges()")

    # Sanity check: Ft and epPin1ChamferRadius cannot both be greater than 0.0
    if ( (Ft > 0.0) and (epPin1ChamferRadius > 0.0) ):
        FC3DM_WriteToDebugFile("Both Ft and epPin1ChamferRadius are greater than zero!")
        FC3DM_MyExit(-1)

    # See if we need to chamfer the pin 1 edge of the EP
    if (Ft > 0.0) :

        FC3DM_WriteToDebugFile("About to chamfer EP")
        FC3DM_WriteToDebugFile("Chamfer dimension is: " + str(Ft))
        
        # Select a priori the edge that needs to be chamfered (determined experimentally).
        # The pin 1 chamfer edge is the same regardless of whether or not the EP corners
        # were filleted. 
        edges=["Edge3"]
            
        # Call FC3DM_ChamferObjectEdges() to actually do the chamfering
        FC3DM_ChamferObjectEdges(App, Gui,
                                 docName, epName, edges, Ft)
        
        FC3DM_WriteToDebugFile("Back from FC3DM_ChamferObjectEdges()")

    # If the EP has a rounded pin 1 chamfer, cut the EP with a cylinder of the specified radius
    elif ( epPin1ChamferRadius > 0.0 ) :

        FC3DM_WriteToDebugFile("About the chamfer EP using rounded chamfer")
        FC3DM_WriteToDebugFile("epPin1ChamferRadius is: " + str(epPin1ChamferRadius))
        
        # Create a cylinder to use for cutting out for pin 1 marker
        cylName = "Cutter"
        FC3DM_CreateCylinderVert(App, Gui,
                                 docName, cylName, x - (W/2.0), y + L/2.0, 0, epPin1ChamferRadius, Tp)
        # FC3DM_WriteToDebugFile("Back from FC3DM_CreateCylinderVert()")
        
        FC3DM_CutWithSpecifiedObject(App, Gui,
                                     docName, epName, cylName)
        FC3DM_WriteToDebugFile("Back from FC3DM_CutWithSpecifiedObject()")
    
    # Zoom in on pin model
    Gui.SendMsgToActiveView("ViewFit")

    # Color pin red.  FIXME--remove this!
    FC3DM_WriteToDebugFile("Coloring the EP red")
    Gui.getDocument(docName).getObject(epName).ShapeColor = (1.00,0.00,0.00)

    return 0


###################################################################
# FC3DM_CreateIcPins()
#	Function to create all gullwing IC pins.
###################################################################
def FC3DM_CreateIcPins(App, Gui,
                       parms, pinNames,
                       docName):
                
    FC3DM_WriteToDebugFile("Hello from FC3DM_CreateIcPins()")

    # Extract relevant parameter values from parms associative array
    # TODO:  Currently no error checking!
    pinTemplateEast = parms["pinName"]
    pinTemplateNorth = "pinTemplateNorth"
    bodyName = parms["bodyName"]
    footprintType = parms["footprintType"]
    hasEp = parms["hasEp"]

    # Retrieve EP parameters if needed
    if (hasEp):
        FC3DM_WriteToDebugFile("Footprint has an EP")
        Tt = parms["Tt"] # pkgDimsEpLengthMax
        Wt = parms["Wt"] # pkgDimsEpWidthMax
        Ft = parms["Ft"] # pkgDimsEpChamfer
        Rt = parms["Rt"] # pkgDimsEpCornerRad

    print("Hello from FC3DM_CreateIcPins()!")

    ## Call the appropriate function to create the prototype IC pin
    # Handle Gullwing ICs        
    if ( (footprintType == "SOP") or (footprintType == "SOIC") or (footprintType == "SOT") or (footprintType == "QFP") ):

        # Call CreateIcPin() to create template east side Gullwing IC pin
        FC3DM_CreateIcPinGullwing(App, Gui,
                                  parms,
                                  docName)

    # Handle QFN ICs        
    elif (footprintType == "QFN"):

        # Call CreateIcPinQfn() to create template east side and north side QFN IC pins
        FC3DM_CreateIcPinQfn(App, Gui,
                             parms,
                             docName)

    # Else unsupported!
    else:
        print("Unsupported footprintType " + footprintType)
        FC3DM_WriteToDebugFile("Abort message: Footprint type is unsupported!")
        FC3DM_MyExit(-1)

    FC3DM_WriteToDebugFile("Back from creating template IC pin")
    print("Back from creating template IC pin.")


    # Configure active document
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)

    # Loop over all the entries in the parms array
    for parm in parms:

        print("Examining parm " + parm + ".")

        # See if this parm is a pin definition
        if parm.startswith("Pin"):

            # Add this pin to the pinNames list.
            print("Found pin named " + parm + ".")
            pinNames.append(parm)

    # end loop over all the entries in the parms array

    # Sort the list of pinNames, using our custom pin name sort function.
    pinNames.sort(FC3DM_SortPinNames)

    print("pinNames is:")
    print(pinNames)

    FC3DM_WriteToDebugFile("Examining pin types")
    # Loop over all the pin names.
    for pin in pinNames:

        # Split the pin definition string on ',' chars.
        # Format is "type, side, x, y"
        lis = []
        lis = parms[pin].rsplit(",")

        # Sanity check that we have exactly 4 fields in the list
        if (len(lis) != 4):
            print("Expected to find 4 fields in pin description.  Actually saw " + str(len(lis)) + "!")
            FC3DM_WriteToDebugFile("Abort message: Expected to find 4 fields in pin description.  Actually saw " + str(len(lis)) + "!")
            FC3DM_MyExit(-1)

        print("Found pin named " + pin + ", lis is:")
        print(lis)

        ## Examine pin type
        if ( (lis[0] == "Gullwing") or (lis[0] == "QFN") ):

            ## Get pin x coordinate
            x = float(lis[2])

            ## Get pin y coordinate
            y = float(lis[3])

            ## Examine pin side
            # Look for an east side pin.
            if (lis[1] == "East"):
                FC3DM_WriteToDebugFile("Found east pin")
                # Our template pin was created on the east side, so no rotation required.
                rotDeg = 0.0

                # Currently we're ignoring this datum from the ini file.
                # TODO:  Revisit this for QFNs, QFPs, BGAs, etc.!
                x = 0.0

                ## Copy template pin to the commanded location
                FC3DM_CopyObject(App, Gui,
                                 x, y, rotDeg,
                                 docName,
                                 pinTemplateEast,
                                 pin)
                
            # Else see if this is a west side pin.
            elif (lis[1] == "West"):

                FC3DM_WriteToDebugFile("Found west pin")
                # Our template pin was created on the east side, so rotate 180 degrees
                rotDeg = 180.0

                # Currently we're ignoring this datum from the ini file.
                # TODO:  Revisit this for QFNs, QFPs, BGAs, etc.!
                x = 0.0

                ## Copy template pin to the commanded location
                FC3DM_CopyObject(App, Gui,
                                 x, y, rotDeg,
                                 docName,
                                 pinTemplateEast,
                                 pin)
                
            # Else see if this is a north side pin.
            elif (lis[1] == "North"):

                FC3DM_WriteToDebugFile("Found north pin")
                # Our template pin was created on the north side, so no rotation
                rotDeg = 0.0

                # Currently we're ignoring this datum from the ini file.
                # TODO:  Revisit this for QFNs, QFPs, BGAs, etc.!
                y = 0.0

                ## Copy template pin to the commanded location
                FC3DM_CopyObject(App, Gui,
                                 x, y, rotDeg,
                                 docName,
                                 pinTemplateNorth,
                                 pin)
                
            # Else see if this is a south side pin.
            elif (lis[1] == "South"):

                FC3DM_WriteToDebugFile("Found south pin")
                # Our template pin was created on the south side, so rotate 180 degrees!
                rotDeg = 180.0

                # Currently we're ignoring this datum from the ini file.
                # TODO:  Revisit this for QFNs, QFPs, BGAs, etc.!
                y = 0.0

                ## Copy template pin to the commanded location
                FC3DM_CopyObject(App, Gui,
                                 x, y, rotDeg,
                                 docName,
                                 pinTemplateNorth,
                                 pin)
                
            # Else unsupported!
            else:
                print("Unsupported pin side " + lis[1])
                FC3DM_WriteToDebugFile("Abort message: Pin side was not north, south, east or west. Current pin side is unsupported")
                FC3DM_MyExit(-1)

            ## For certain package types, we need to cut the pin out of the body
            if (lis[0] == "QFN"):
                FC3DM_CutObjectWithToolAndKeepTool(App, Gui,
                                                   docName, bodyName, pin)

        # endif is gullwing or QFN

        # Handle EP pin type
        elif (lis[1] == "Ep"):

            ## Get pin x & y coordinates
            x = float(lis[2])
            y = float(lis[3])

            # Set the name of the EP to whatever was used in the ini file
            epName = pin
			# If there are different types of EPs, handle them as defined in the ini file
            if (lis[0].startswith("Type")):

                # Pull the length and width of the split EP from parms
                # Note: There should never be situations where parms["Tt"] and parms["TypeEP?_Tt"] are used. Currently no check for this. 
                Tt = parms[lis[0] + "_Tt"]
                Wt = parms[lis[0] + "_Wt"]

                # Set the pin type to whatever was used in the ini file
                pinType = lis[0]
			
			# Otherwise, proceed as usual (using Tt, Wt, Ft, and Rt) as defined in the ini file
            else:

                # Set the pin type to whatever was used in the ini file
                pinType = lis[0]
                
            # Call FC3DM_CreateIcPinEp() to create EP pin from scratch
            FC3DM_CreateIcPinEp(App, Gui, 
								parms,
                                Tt, Wt, x, y,
                                epName,
                                pinType,
                                docName)

            # Cut the body with the EP pin and keep both
            FC3DM_CutObjectWithToolAndKeepTool(App, Gui,
                                               docName, bodyName, epName)


        # Else unknown pin type.  Abort
        else:
            print("Unsupported pin type " + lis[0])
            FC3DM_WriteToDebugFile("Abort message: Pin type is unsupported")
            FC3DM_MyExit(-1)


    # end loop over all the pin names.

    # Remove the pin template object(s)
    App.getDocument(docName).removeObject(pinTemplateEast)

    if ( (footprintType == "QFN") or (footprintType == "QFP") ):
        App.getDocument(docName).removeObject(pinTemplateNorth)

    return 0


###################################################################
# FC3DM_CopyObject()
#	Function to copy a FreeCAD object, then translate in x,y
# and rotate in z.
###################################################################
def FC3DM_CopyObject(App, Gui,
                     x, y, rotDeg,
                     docName,
                     objName,
                     newObjName):
    
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)

    # Copy the object
    newTermShape = FreeCAD.getDocument(docName).getObject(objName).Shape.copy()
    newTermObj = App.activeDocument().addObject("Part::Feature",newObjName)
    newTermObj.Shape = newTermShape

    # Translate the copy in x,y and rotate about the z axis as needed.
    FC3DM_TranslateObjectAndRotateAboutZ(App, Gui,
                                         docName, newObjName,
                                         x, y, rotDeg)

    # Copy the original object's color to the new object
    Color = Gui.getDocument(docName).getObject(objName).ShapeColor
    Gui.getDocument(docName).getObject(newObjName).ShapeColor = Color
    
    return 0


###################################################################
# FC3DM_SaveAndExport()
#	Function to save a FreeCAD native CAD file, as well as export
# the specified objects to a STEP file.
###################################################################
def FC3DM_SaveAndExport(App, Gui,
                        docName,
                        parms,
                        objNameList):

    FC3DM_WriteToDebugFile("Hello from FC3DM_SaveAndExport()")

    # Extract relevant parameter values from parms associative array
    # TODO:  Currently no error checking!
    newModelPathNameExt = parms["newModelPathNameExt"]
    newStepPathNameExt = parms["newStepPathNameExt"]

    ## Save to disk in native format
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)
    App.getDocument(docName).FileName = newModelPathNameExt
    App.getDocument(docName).Label = docName
    Gui.SendMsgToActiveView("Save")
    App.getDocument(docName).save()
    
    ## Export to STEP
    App.ActiveDocument=None
    Gui.ActiveDocument=None
    App.setActiveDocument(docName)
    App.ActiveDocument=App.getDocument(docName)
    Gui.ActiveDocument=Gui.getDocument(docName)
    App.getDocument(docName).save()

    # Create list of objects, starting with object names
    objs=[]
    for i in objNameList:
        
        objs.append(FreeCAD.getDocument(docName).getObject(i))

    # Do export to STEP
    import ImportGui
    ImportGui.export(objs,newStepPathNameExt)
    del objs
    
    return 0


###################################################################
# FC3DM_MyExit()
#	Function to write our return code to "rc file" and then exit.
###################################################################
def FC3DM_MyExit(rc):    

    ## Open the rc file
    fileP = open(scriptPathUtils + '\\python.rc', 'w')

    # Write return code to file
    fileP.write(str(rc))

    # Close the rc file
    fileP.close()

    # Actually do the sys.exit() call
    sys.exit(rc)

    return 0

