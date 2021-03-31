import os
import xml.etree.ElementTree as ET
import sys
import shutil

currentDir = os.getcwd()
userAppDir = sys.argv[1]


# 1. Copying needed files in the right directories

localMacroDir = os.path.join(currentDir,'Macros')
localIconDir  = os.path.join(currentDir,'icons')
localFontsDir = os.path.join(currentDir,'fonts')

targetMacroDir = os.path.join(userAppDir,'Macro')
targetIconDir  = os.path.join(userAppDir,'icons')
targetFontsDir = os.path.join(userAppDir,'fonts')


if ( not os.path.exists(targetIconDir) ):
    os.mkdir(targetIconDir)

if ( not os.path.exists(targetFontsDir) ):
    os.mkdir(targetFontsDir)


for file in os.listdir(localMacroDir):
    
    if ('.py' in file):
        fullFileName = os.path.join(localMacroDir,file)
        shutil.copy(fullFileName,targetMacroDir)

for file in os.listdir(localIconDir):
    
    fullFileName = os.path.join(localIconDir,file)
    shutil.copy(fullFileName,targetIconDir)

for file in os.listdir(localFontsDir):
    
    fullFileName = os.path.join(localFontsDir,file)
    shutil.copy(fullFileName,targetFontsDir)


# 2. Configuring the user profile to add the PACE button 

userConfig = ET.parse(os.path.join('install','cleanUser.cfg'))

# Forcing user macro dir

macroPref = userConfig.find('.//FCParamGroup[@Name="Preferences"]').find('FCParamGroup[@Name="Macro"]')
macroDirElem = ET.Element('FCText')
macroDirElem.set('Name','MacroPath')
macroDirElem .text=targetMacroDir
macroPref.append(macroDirElem)




# adding icons folder
bitMaps = userConfig.find('.//FCParamGroup[@Name="Bitmaps"]')
iconPathElem = ET.Element('FCText')
iconPathElem.set('Name','CustomPath0')
iconPathElem.text=targetIconDir
bitMaps.append(iconPathElem)

# adding PACE macro
macrosElement = userConfig.find('*[@Name="Root"]').find('*[@Name="BaseApp"]').find('*[@Name="Macro"]').find('*[@Name="Macros"]')

paceMacroElement = ET.Element("FCParamGroup")
paceMacroElement.set('Name','Std_Macro1')


myDict = {'Script':'PACE_FreeCad_GUI.py',
                'Menu':'PACE',
                'Tooltip':'PACE',
                'WhatsThis':'PACE',
                'Statustip':'PACE',
                'Pixmap':'pace_logo',
                'Accel':'none'
                }

for Name,text in myDict.items():
    tmpElem = ET.Element("FCText")
    tmpElem.set("Name",Name)
    tmpElem.text=text
    paceMacroElement.append(tmpElem)

systemElem = ET.Element("FCBool")
systemElem.set('Name','System')
systemElem.set('Value','0')
paceMacroElement.append(systemElem)

macrosElement.append(paceMacroElement)


# Toolbar 

workbenchesElem = userConfig.find('.//FCParamGroup[@Name="Workbench"]')
globalElem = ET.Element('FCParamGroup',{'Name':'Global'})
toolBarElem = ET.Element('FCParamGroup',{'Name':'Toolbar'})
custom1Elem = ET.Element('FCParamGroup',{'Name':'Custom_1'})

textElem = ET.Element('FCText',{'Name':'Name'})
textElem.text = 'PACE_Toolbar'

boolElem = ET.Element('FCBool',{'Name':'Active','Value':'1'})

macroElem = ET.Element('FCText',{'Name':'Std_Macro1'})
macroElem.text = 'FreeCAD'

workbenchesElem.append(globalElem)
globalElem.append(toolBarElem)
toolBarElem.append(custom1Elem)
custom1Elem.append(textElem)
custom1Elem.append(boolElem)
custom1Elem.append(macroElem)


userConfigFileName = os.path.join(userAppDir,'user.cfg')
userConfig.write(userConfigFileName)



