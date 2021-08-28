import FreeCADGui as Gui
import FreeCAD as App
import Draft

from matplotlib import path

import os

import paceTools

import numpy as np


from PySide import QtGui,QtCore

from pivy import coin

zvector=App.Base.Vector(0,0,1)
xvector=App.Base.Vector(1,0,0)
yvector=App.Base.Vector(0,1,0)


class paceProject():

    def __init__(self):
     
        self.VP={} #dictionnary to handle init and mod

        bodynames={'init':'VP','mod':'VPmod'}

        for situation in bodynames.keys():

            bodies=App.ActiveDocument.getObjectsByLabel(bodynames[situation])

            if (bodies!=None):
                if (len(bodies)>0):
                    self.VP[situation]=ProtectedVolume(bodies[0])
        
        self.createShells()
    
        if ('skinDescriptions' not in dir(self)):
            self.skinDescriptions={}

    
    def reset(self,situation):
   
        bodynames={'init':'VP','mod':'VPmod'}
    
        self.VP[situation].delete()

        body=App.ActiveDocument.getObjectsByLabel(bodynames[situation])[0]
 
        self.VP[situation]=ProtectedVolume(body)
        self.VP[situation].createShell()

          
    def updateAfterBodyChange(self,situation):


        self.VP[situation].updateAfterBodyChange()
        
        """oldListOfFaces = self.VP[situation].getLabeledFaces()  #will continue pointing towards old "freefaces"
        
        self.VP[situation].removeLegend()
        self.VP[situation].setFaces()     # Listing faces of current Solid Body and resetting list
        self.VP[situation].createShell()  # create new shell from current Solid Body
        
        newListOfFaces = self.VP[situation].getLabeledFaces()
        
        self.matchLabels(oldListOfFaces,newListOfFaces)
        
        for oldFace in oldListOfFaces:
            oldFace.delFreeFace()
        """

    
    def linkfaces(self):
    
        #when reloading a saved file, the link between the volume and the shell faces are not conserved
        # the faces should be relinked
        # !! this cannot be done in the __setstate__ because all objects are possibly not yet loaded. 
        # This sould be done at several moments:
        #  -> when starting the "PACE" tab   --> will be called when starting the menu
        #  -> before saving to be sure everyghing is well linked  --> will be called in get_state
        #  
    
        VPbody=App.ActiveDocument.getObjectsByLabel("VP")[0]  #first of list
        
        self.VP={}         
        self.VP['init']=ProtectedVolume(VPbody)

        VPmodbody=App.ActiveDocument.getObjectsByLabel("VPmod")
        
        if (len(VPmodbody)>0):
            self.VP['mod']=ProtectedVolume(VPmodbody[0])
    
        
        list_of_faces={} # dict containing maximum two lists: one for init, one for mod
        list_of_labels={} # dict containing maximum two lists: one for init, one for mod

        for k in self.VP.keys():
            
            list_of_faces[k] = [ x['freefaceobject'] for x in self.savedstate[k]['surfaces'] ]
            self.VP[k].recoverShell(list_of_faces[k])
        
            list_of_labels[k] = [ x['label'] if 'label' in x.keys() else None for x in self.savedstate[k]['surfaces']  ]
        
            self.VP[k].recoverLabel(list_of_labels[k])
        
            #self.VP[k].recoverLabel(list_of_labels[k])
        
            if ('legends' in self.savedstate[k].keys()):
                self.VP[k].legendobj={ key:App.ActiveDocument.getObject(value) for key,value in self.savedstate[k]['legends'].items() }
                

        if ('skinDescriptions' in self.savedstate.keys()):
            self.skinDescriptions=self.savedstate['skinDescriptions']
        else:
            self.skinDescriptions={}

        if ('sectormap' in self.savedstate.keys()):
            self.sectormap=self.savedstate['sectormap']
            self.sectormap = { int(k):v for k,v in self.sectormap.items()}
            
        else:
            self.sectormap={}



        #Hiding/showing legends to link the camera callback function
                
        for k in self.VP.keys():
            self.VP[k].hideLegend()   
            self.VP[k].showLegend()

        if 'mod' in self.VP.keys():
            self.VP['mod'].hideLegend()

    
        self.linked=True
    


    def copyLabelsToOtherSituation(self,sourceSituation,targetSituation):

        self.VP[targetSituation].matchLabels(self.VP[sourceSituation].getLabeledFaces())
            



    def setSkinElementsDescription(self):

        #new structure
        #skinDescription{'key': {'description':'some text','environment':'env'}}
        
        neededFields = ['description','environment','type','subtype']
        
        
        #Filling older versions to have all required keys
        for key,subDict in self.skinDescriptions.items():
            
            for field in neededFields:
                if field not in subDict.keys():
                    subDict[field]=''
        
        
        environmentDict = {'Exterieur':'OPEN_AIR',
                            'Espace non chauffe' : 'NON_HEATED_SPACE',
                            'Sol' :'GROUND',
                            'Cave avec ouverture':'CELLAR_WITH_OPENINGS',
                            'Cave sans ouverture':'CELLAR_WITHOUT_OPENINGS',
                            'Espace chauffe':'HEATED_SPACE'
                            }
        
        subTypes={'Mur':
                    {'Plein':'FULL',
                     'Creux':'HOLLOW',
                     },
                 'Toiture':
                     {
                     'Inclinée': 'INCLINED',
                     'Plate':'FLAT'
                     },
                 'Plancher':{},
                 'Ouverture':{}
                 }
        
        skinTypes=[]      
        for k,v in self.VP.items():
            skinTypes+=v.getLabels()
        
        skinTypes=list(set(skinTypes))
        if (None in skinTypes):
            skinTypes.remove(None)
       
        skinTypes.sort() #inplace
      
        self.saveElemDialog=QtGui.QDialog()
        self.saveElemDialog.setWindowTitle('Elements descritption and environment')
        mainLayout=QtGui.QVBoxLayout()
        #formLayout=QtGui.QFormLayout()
        gridLayout = QtGui.QGridLayout()
        
        self.elemLineEditDict={}
        self.elemDropdownDict={}
        self.typeDropdownDict={}    #Mur,Toiture,Plancher
        self.subTypeDropdownDict={}



        gridLayout.addWidget(QtGui.QLabel('Code'),0,0)
        gridLayout.addWidget(QtGui.QLabel('Description'.ljust(50)),0,1) # dirty trick to force column width
        gridLayout.addWidget(QtGui.QLabel('Environnement'),0,2)
        gridLayout.addWidget(QtGui.QLabel('Type'),0,3)
        gridLayout.addWidget(QtGui.QLabel('Sous-type'),0,4)
        

        lineNumber=1
        
        for skT in skinTypes:
            self.elemLineEditDict[skT]=QtGui.QLineEdit()
            self.elemLineEditDict[skT].setMinimumWidth(300)
            #self.elemLineEditDict[skT].setFixedWidth(1500)
            self.elemDropdownDict[skT]=QtGui.QComboBox()
            self.elemDropdownDict[skT].addItems(list(environmentDict.keys()))

            self.typeDropdownDict[skT]=QtGui.QComboBox()
            self.typeDropdownDict[skT].addItems(list(subTypes.keys()))

            self.subTypeDropdownDict[skT]=QtGui.QComboBox()
            #self.subTypeDropdownDict[skT].addItems(list(subTypes.keys()))


            if (skT in self.skinDescriptions.keys()):
                #setting description
                 
                # new version with sub-fields
                if ( type(self.skinDescriptions[skT])==dict ):
                    self.elemLineEditDict[skT].setText(self.skinDescriptions[skT]['description'])
                
                    #setting environment
                    index = self.elemDropdownDict[skT].findText(self.skinDescriptions[skT]['environment'], QtCore.Qt.MatchFixedString)
                    self.elemDropdownDict[skT].setCurrentIndex(index)
            
                    # look for saved value
                    index = self.typeDropdownDict[skT].findText(self.skinDescriptions[skT]['type'], QtCore.Qt.MatchFixedString)
                    if (index>=0):
                        self.typeDropdownDict[skT].setCurrentIndex(index)
                    else:
                        #if not, default proposition depending on the name
                        if (self.elemLineEditDict[skT].text()[0] == 'M'):            
                            index = self.typeDropdownDict[skT].findText('Mur', QtCore.Qt.MatchFixedString)
                        elif (self.elemLineEditDict[skT].text()[0] == 'T'):            
                            index = self.typeDropdownDict[skT].findText('Toiture', QtCore.Qt.MatchFixedString)
                        elif (self.elemLineEditDict[skT].text()[0] == 'P'):            
                            index = self.typeDropdownDict[skT].findText('Plancher', QtCore.Qt.MatchFixedString)
                        elif (self.elemLineEditDict[skT].text()[0] == 'F'):            
                            index = self.typeDropdownDict[skT].findText('Ouverture', QtCore.Qt.MatchFixedString)
                        else:
                            index=0

                        self.typeDropdownDict[skT].setCurrentIndex(index)


                    
                
                else: #old version with only text description
                    self.elemLineEditDict[skT].setText(self.skinDescriptions[skT])

        
                

            #formLayout.addRow(skT,self.elemLineEditDict[skT])
            gridLayout.addWidget(QtGui.QLabel(skT),lineNumber,0)
            gridLayout.addWidget(self.elemLineEditDict[skT],lineNumber,1)
            gridLayout.addWidget(self.elemDropdownDict[skT],lineNumber,2)
            gridLayout.addWidget(self.typeDropdownDict[skT],lineNumber,3)

                
                
            lineNumber += 1
        
        OkButton=QtGui.QPushButton('Ok')
        mainLayout.addLayout(gridLayout)
        mainLayout.addWidget(OkButton)       
        self.saveElemDialog.setLayout(mainLayout)
        
        
        OkButton.clicked.connect(self.saveElementDescription)
        
        self.saveElemDialog.exec()

        
    def saveElementDescription(self):
    
        #self.skinDescriptions[k] = { 'description':'','environment':''}
        
        for skT in self.elemLineEditDict.keys():
            self.skinDescriptions[skT] = {}
            self.skinDescriptions[skT]['description']=self.elemLineEditDict[skT].text()
            self.skinDescriptions[skT]['environment']=self.elemDropdownDict[skT].currentText()
            self.skinDescriptions[skT]['type']=self.typeDropdownDict[skT].currentText()


        self.saveElemDialog.close()
        

    
    def createShells(self):
    
        for k in self.VP.keys():
            self.VP[k].createShell()
    
        self.linked=True #boolean to check that everything is well linked


    def exportToPace(self):

        #setting template
        templateWithoutPath = selectTemplate()
        if (templateWithoutPath == None):
            return
        else:
            template = os.path.join(os.path.join(App.getUserMacroDir(True),'paceTemplates',templateWithoutPath))
        
        
        method = selectMeasurementMethod()
            
        PaceXML = paceTools.PACEXML(template)
        PaceXML.setTemplatesDir(os.path.join(App.getUserMacroDir(True),'paceTemplates'))

        
        environmentDict = {'Exterieur':'OPEN_AIR',
                           'Espace non chauffe' : 'NON_HEATED_SPACE',
                           'Sol' :'GROUND',
                           'Cave avec ouverture':'CELLAR_WITH_OPENINGS',
                           'Cave sans ouverture':'CELLAR_WITHOUT_OPENINGS',
                           'Espace chauffe':'HEATED_SPACE'
                           }
        
        
        typeDict = {'Mur':'wall',
                    'Toiture':'roof',
                    'Plancher':'floor',
                    'Ouverture':'transparentElement'
                    }
        
        subTypeDict = {'Plein':'FULL',
                       'Creux':'HOLLOW',
                       'Inclinée': 'INCLINED',
                       'Plate':'FLAT',
                       '':''
                       }
    
        
        initAreas=self.VP['init'].getAreasByLabel() # returnes area dict of style {'M1':34,'M2':45}
        initHeatedVolume = self.VP['init'].getVolume()
        
        
        modAreas = {}
        modHeatedVolume = None
        if  'mod' in self.VP.keys() :
            modAreas = self.VP['mod'].getAreasByLabel()
            modHeatedVolume = self.VP['mod'].getVolume()
            
        
        listToExport=[]
        
        
        for label in self.skinDescriptions.keys():
            
            if label in initAreas.keys():
                initGrossArea = initAreas[label]
            else:
                initGrossArea = 0
                
            if label in modAreas.keys():
                modGrossArea = modAreas[label]               
            else:
                modGrossArea = 0
        
        
            listToExport.append({   'label':label,
                                    'description':self.skinDescriptions[label]['description'],
                                    'environment':environmentDict[self.skinDescriptions[label]['environment']], 
                                    'type':typeDict[self.skinDescriptions[label]['type']],
                                    'subtype':subTypeDict[self.skinDescriptions[label]['subtype']],
                                    'grossArea':initGrossArea,
                                    'grossAreaMod':modGrossArea
                                })
        

        if (method == 'netSurface'):
            
            if ( not self.hasCompassSet()):
                msgBox = QtGui.QMessageBox()
                msgBox.setIcon(QtGui.QMessageBox.Information)
                msgBox.setText("You have to define the project orientation before exporting a model with windows")
                msgBox.setWindowTitle("Define orientaton first")
                msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
                msgBox.exec()

                return
            
            PaceXML.setMeasurementMethod('surfacesnettes')
            PaceXML.addNetSurfaces(listToExport)
        elif (method == 'grossSurface'):
            PaceXML.setMeasurementMethod('surfacesbrutes')
            PaceXML.addSurfaces(listToExport)
        
        #get openings, and add openings
        
        initOpenings = self.VP['init'].getOpenings(self.skinDescriptions,self.sectormap)

        if 'mod' in self.VP.keys():
            modOpenings  = self.VP['mod'].getOpenings(self.skinDescriptions,self.sectormap)

        allOpenings = initOpenings.copy()
        for op in allOpenings:
            op['init']=True         
       
        for op in modOpenings:
            modOnly = True
            for opInit in initOpenings:
                if op==opInit:
                    op['mod']=True
                    modOnly = False
            if modOnly:
                allOpenings.append(op)
                # STATE ADDED IN PACE FILE
                
        openingLabelCounter = {}
        
        for opening in initOpenings:
            if opening['label'] in openingLabelCounter.keys():
                openingLabelCounter[opening['label']] += 1
            else:
                openingLabelCounter[opening['label']] = 1
            
            openingName = opening['label']+'/'+str(openingLabelCounter[opening['label']])
            PaceXML.addOpeningNetMethod(openingName,opening['label'],opening['orientation'],inclination=90,area=opening['area'])

        PaceXML.setMeasurementMethod('surfacesbrutes')
        PaceXML.addSurfaces(listToExport)

        PaceXML.setHeatedVolume(initHeatedVolume,modHeatedVolume)        
        PaceXML.setInsideTemperature(18)        
        
        defpath=os.path.dirname(App.ActiveDocument.FileName) 
        filename=os.path.basename(App.ActiveDocument.FileName) 
        pacename=filename.replace('.FCStd','.pae')
        fullname=os.path.join(defpath,pacename)
      
        fileName = QtGui.QFileDialog.getSaveFileName(None,"SavePACE",fullname,"PACE (*.pae *.pce)")[0]
        
        if (fileName !=''):
        
            PaceXML.writePaceFile(fileName)
    
    
    def insertCurrentViewInPaceFile(self,situation):
        
        defPath=os.path.dirname(App.ActiveDocument.FileName) 
        
        existingPACEFile = QtGui.QFileDialog.getOpenFileName(None,"Open existing PACE file",defPath,"PACE (*.pae *.pce)")[0]

        workingDirectory = os.path.dirname(existingPACEFile)

        PaceXML = paceTools.PACEXML(existingPACEFile)
        
        temporaryPNG = os.path.join(workingDirectory,'tmp.png')

        
        screenWidth,screenHeight=Gui.ActiveDocument.activeView().getSize(); #screen wiew - get size
       
        Gui.activeDocument().activeView().saveImage(temporaryPNG,screenWidth,screenHeight,'White')

        PaceXML.setPicture(temporaryPNG,situation)
        
        PaceXML.writePaceFile(existingPACEFile.replace('.pae','-pic.pae'))
        
        os.remove(temporaryPNG)

        
    def hasCompassSet(self):
        
        if (hasattr(self,'sectormap')):
            
            if (len(self.sectormap) >0 ):
            
                return True

        return False

    
    def todict(self):
    
        projectdict={}
    
        if ('skinDescriptions' in dir(self)):
            projectdict['skinDescriptions']=self.skinDescriptions
        
        
        if ('sectormap' in dir(self)):
            projectdict['sectormap']=self.sectormap
        
        
        for k in self.VP.keys():

            projectdict[k]=self.VP[k].todict()
    
        return projectdict
    
    def __getstate__(self):
       
        '''When saving the document this object gets stored using Python's json module.\
                Since we have some un-serializable parts here -- the Coin stuff -- we must define this method\
                to return a tuple of all serializable objects or None.'''
        
        
        if (self.linked==False):
            self.linkfaces()
            
                
        return (self.todict())
     
    
    def __setstate__(self,saveddict):

        self.linked=False #force false at reload
        self.savedstate=saveddict
        

        #self.linkfaces()

        '''When restoring the serialized object from document we have the chance to set some internals here.\
                Since no data were serialized nothing needs to be done here.'''
        return None


class skinElementsConfigurator:
    
    
        def __init__(self,project):

            self.skinDescriptions = project.skinDescriptions #reference to the project var
                  
            neededFields = ['description','environment','type','subtype']

        
            #Filling older versions to have all required keys
            for key,value in self.skinDescriptions.items():
                
                if type(value)!=dict:
                    value = {}
                
                for field in neededFields:
                    if field not in value.keys():
                        value[field]=''
            
        
            self.environmentDict = {'Exterieur':'OPEN_AIR',
                                'Espace non chauffe' : 'NON_HEATED_SPACE',
                                'Sol' :'GROUND',
                                'Cave avec ouverture':'CELLAR_WITH_OPENINGS',
                                'Cave sans ouverture':'CELLAR_WITHOUT_OPENINGS',
                                'Espace chauffe':'HEATED_SPACE'
                                }
            
            self.subTypes={
                        'Mur':     {'Plein':'FULL','Creux':'HOLLOW'},
                        'Toiture': {'Inclinée': 'INCLINED', 'Plate':'FLAT'},
                        'Plancher':{},
                        'Ouverture':{}
                          }


            self.getExistingSkinTypes(project)            
            
            self.saveElemDialog=QtGui.QDialog()
            self.setDialog()
            self.saveElemDialog.exec()



        def getExistingSkinTypes(self,project):   

            projectVPDict = project.VP

            self.skinTypes=[]      
            for k,v in projectVPDict.items():
                self.skinTypes+=v.getLabels()
            
            self.skinTypes=list(set(self.skinTypes))
            if (None in self.skinTypes):
                self.skinTypes.remove(None)
           
            self.skinTypes.sort() #inplace

            
        def setDialog(self):
            
            self.saveElemDialog.setWindowTitle('Elements descritption and environment')
            mainLayout=QtGui.QVBoxLayout()
            gridLayout = QtGui.QGridLayout()
            
            self.elemLineEditDict={}
            self.elemDropdownDict={}
            self.typeDropdownDict={}    #Mur,Toiture,Plancher
            self.subTypeDropdownDict={}
        
            gridLayout.addWidget(QtGui.QLabel('Code'),0,0)
            gridLayout.addWidget(QtGui.QLabel('Description'.ljust(50)),0,1) # dirty trick to force column width
            gridLayout.addWidget(QtGui.QLabel('Environnement'),0,2)
            gridLayout.addWidget(QtGui.QLabel('Type'),0,3)
            gridLayout.addWidget(QtGui.QLabel('Sous-type'),0,4)
            
    
            lineNumber=1
            
            for skT in self.skinTypes:
                
                #creating and adding all widgets in the grid
                self.elemLineEditDict[skT]=QtGui.QLineEdit()
                self.elemLineEditDict[skT].setMinimumWidth(300)
                self.elemDropdownDict[skT]=QtGui.QComboBox()
                self.elemDropdownDict[skT].addItems(list(self.environmentDict.keys()))
    
                self.typeDropdownDict[skT]=QtGui.QComboBox()
                self.typeDropdownDict[skT].addItems(list(self.subTypes.keys()))
    
                self.subTypeDropdownDict[skT]=QtGui.QComboBox()
    
                gridLayout.addWidget(QtGui.QLabel(skT),lineNumber,0)
                gridLayout.addWidget(self.elemLineEditDict[skT],lineNumber,1)
                gridLayout.addWidget(self.elemDropdownDict[skT],lineNumber,2)
                gridLayout.addWidget(self.typeDropdownDict[skT],lineNumber,3)
                gridLayout.addWidget(self.subTypeDropdownDict[skT],lineNumber,4)
    
                lineNumber += 1
            
            OkButton=QtGui.QPushButton('Ok')
            mainLayout.addLayout(gridLayout)
            mainLayout.addWidget(OkButton)       
            self.saveElemDialog.setLayout(mainLayout)


            OkButton.clicked.connect(self.saveElementDescription)
            

            self.fillLines()


        def fillLines(self):
            
            for skT in self.skinTypes:
                
                if (skT not in self.skinDescriptions.keys()):

                    self.skinDescriptions[skT]={'description': '', 'environment': '', 'type': '', 'subtype': ''}
                    
                    # new version with sub-fields
                if ( type(self.skinDescriptions[skT])==dict ):

                    
                    self.setDescription(skT)
                    self.setEnvironment(skT)                        
                    self.setType(skT)
                    self.setSubType(skT)
                                            
                
                else: #old version with only text description
                    self.elemLineEditDict[skT].setText(self.skinDescriptions[skT])

                


        def setDescription(self,skT):
            
            self.elemLineEditDict[skT].setText(self.skinDescriptions[skT]['description'])
            
        def setEnvironment(self,skT):
            
            index = self.elemDropdownDict[skT].findText(self.skinDescriptions[skT]['environment'], QtCore.Qt.MatchFixedString)
            self.elemDropdownDict[skT].setCurrentIndex(index)
                
    
        def setType(self,skT):
            
            # look for saved value
            index = self.typeDropdownDict[skT].findText(self.skinDescriptions[skT]['type'], QtCore.Qt.MatchFixedString)
            if (index>=0):
                self.typeDropdownDict[skT].setCurrentIndex(index)
            else:
                self.setDefaultTypeFromName(skT)

            self.setSubType(skT)

            self.typeDropdownDict[skT].currentIndexChanged.connect(lambda index,skT=skT: self.setSubType(skT))
            


        def setDefaultTypeFromName(self,skT):
            
            defaultTypes = {'M':'Mur','T':'Toiture','P':'Plancher','F':'Ouverture'}

            if (skT[0] in defaultTypes.keys()):
                index = self.typeDropdownDict[skT].findText(defaultTypes[skT[0]], QtCore.Qt.MatchFixedString)
            else:
                index =0                

            self.typeDropdownDict[skT].setCurrentIndex(index)



        def setSubType(self,skT):
            
            currentType = self.typeDropdownDict[skT].currentText()

            self.subTypeDropdownDict[skT].clear()
            self.subTypeDropdownDict[skT].addItems(list(self.subTypes[currentType].keys()))

            index = self.subTypeDropdownDict[skT].findText(self.skinDescriptions[skT]['subtype'], QtCore.Qt.MatchFixedString)
            if (index>=0):
                self.subTypeDropdownDict[skT].setCurrentIndex(index)
            
            else:
                self.subTypeDropdownDict[skT].setCurrentIndex(0)
                        



        
        def saveElementDescription(self):
        
            #self.skinDescriptions[k] = { 'description':'','environment':''}
            
            for skT in self.elemLineEditDict.keys():
                self.skinDescriptions[skT] = {}
                self.skinDescriptions[skT]['description']=self.elemLineEditDict[skT].text()
                self.skinDescriptions[skT]['environment']=self.elemDropdownDict[skT].currentText()
                self.skinDescriptions[skT]['type']=self.typeDropdownDict[skT].currentText()
                self.skinDescriptions[skT]['subtype']=self.subTypeDropdownDict[skT].currentText()
    
    
            self.saveElemDialog.close()
        













      

class Compass:
    
        
    def setCompassFromFace(self,project):
    
        
        sel=Gui.Selection.getSelection() 
        
        if (len(sel) != 1):
            msgBox = QtGui.QMessageBox()
            msgBox.setIcon(QtGui.QMessageBox.Information)
            msgBox.setText("Please select one single surface to define a reference orientation")
            msgBox.setWindowTitle("Surface selection to define compas")
            msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
            msgBox.exec()
            return
        
        part=sel[0]
        normal=part.Shape.normalAt(0,0)
        
        referenceorientation=np.degrees(np.arctan2(normal.y,normal.x))
        
        orientations=['N','NNE','NE','ENE','E','ESE','SE','SSE','S',
                       'SSW','SW','WSW','W','WNW','NW','NNW']
        
        worldangles=np.arange(0,360,22.5)
        
        orientationmap={}
        
        item, ok = QtGui.QInputDialog.getItem(None, "Orientation of the selected face", "Orientation", orientations, 0, False)
        
        for o,w in zip(orientations,worldangles):
            
            orientationmap[o]=self.cardinal_to_trigo(w)
            
        reflabel=item
        shift=orientationmap[reflabel]-round(referenceorientation/22.5)*22.5
        
        orientationmap={o:(w-shift)%360 for o,w in orientationmap.items()}
        
        
        
        dalpha=22.5
        
        self.sectormap={ int((az%360)/dalpha)%16:k for k,az in orientationmap.items() }
            
        self.drawCompass(orientationmap['N'])

        project.sectormap = self.sectormap


    def show(self):
        
        compass=App.ActiveDocument.getObject('Compass')
        compass.ViewObject.Visibility=True

    def hide(self):
        compass=App.ActiveDocument.getObject('Compass')
        compass.ViewObject.Visibility=False


    def drawCompass(self,northdir):

        compass=App.ActiveDocument.getObject('Compass')

        if (compass!=None):
            compass.removeObjectsFromDocument()
            App.ActiveDocument.removeObject(compass.Name)

        compass=App.ActiveDocument.addObject("App::DocumentObjectGroup","Compass")
        
        xc=-5000
        yc=-5000
        centerV = App.Vector(xc,yc,0)

        compassRadius=2500
        arrowLength=500     #mm

        pl=App.Placement()
        pl.Rotation.Q=(0.0,-0.0,-0.0,1.0)
        pl.Base=centerV
        circle = Draft.makeCircle(radius=compassRadius,placement=pl,face=False,support=None)
        Draft.autogroup(circle)

        compass.addObject(circle)
           
        dirVals= [ northdir+i*90 for i in range(4) ]
        dirLabs= [ 'N','W','S','E']
        
        for dirVal,dirLab in zip(dirVals,dirLabs):
           
            xN=np.cos(np.radians(dirVal))
            yN=np.sin(np.radians(dirVal))
            
            radialV     = App.Vector(xN,yN,0)           
            tangentialV = App.Vector(yN,-xN,0)
            
            p1 = centerV + radialV *(compassRadius+arrowLength)
            p2 = centerV + radialV * compassRadius                + tangentialV*arrowLength
            p3 = centerV + radialV * compassRadius                - tangentialV*arrowLength


            line = Draft.makeWire([p1,p2,p3],placement=pl,closed=True,face=True,support=None)
            Draft.autogroup(line)
            line.ViewObject.ShapeColor=(0.0,0.0,0.0)


            LSize= 1000

            fontFile=os.path.join(App.getUserMacroDir(True),'fonts','arial.ttf')
            # App.getUserMacroDir() is equivalent to App.getUserMacroDir(False) and it returns de DEFAULT MACRO path of FreeCAD

            ss=Draft.makeShapeString(String=dirLab,FontFile=fontFile,Size=LSize,Tracking=0.0)
            plm=App.Placement()
            plm.Base=App.Vector( xc + xN*(compassRadius+2*arrowLength) - yN*(LSize/2) ,yc + yN*(compassRadius+2*arrowLength) + xN*(LSize/2) ,0.0)
            plm.Rotation.Axis=(0,0,1)
            plm.Rotation.Angle=(np.radians(dirVal-90))
            ss.Placement=plm
            ss.Support=None
            Draft.autogroup(ss)
            ss.ViewObject.ShapeColor=(0.0,0.0,0.0)

            compass.addObject(line)
            compass.addObject(ss)
        
        App.ActiveDocument.recompute()
    
    
        
    def trigo_to_cardinal(self,alpha_trigo):
    
        #returns angle from trigo system to cardinal system = 0 = Norht, with horlogic rotation
    
        alpha_cardinal = (90 - alpha_trigo)%360
    
        return alpha_cardinal
        
    def cardinal_to_trigo(self,alpha_cardinal):
    
        alpha_trigo = (90 - alpha_cardinal)%360
    
        return alpha_trigo
    



class ProtectedVolume():

    def __init__(self,obj):
    
        self.body=None
        self.labeledFaces=[]
    
        self.body=obj

        self.setFaces()
        
        self.LegendShown = False
        
    def reset(self):
    
        self.deleteShell()
        self.show()
        
    def showBody(self):

        Gui.ActiveDocument.getObject(self.body.Name).show()
        
    def hideBody(self):
    
        Gui.ActiveDocument.getObject(self.body.Name).hide()
        
    def hideFaces(self):
        for f in self.getLabeledFaces():
        
            try:
                Gui.ActiveDocument.getObject(f.freeFace.Name).hide()
            except:
                print("Warning, one of the freefaces could not be hidden")
                print("probably cause it doesnt exist anymore")
    

            #if hiding faces also hide labels
        
            #self.hideAllLabels()

    def showFaces(self):
          
        for f in self.getLabeledFaces():
        
            try:
                Gui.ActiveDocument.getObject(f.freeFace.Name).show()
            except:
                print("Warning, one of the freefaces could not be shown")
                print("probably cause it doesnt exist anymore")


    
    def setFaces(self):
    
        self.labeledFaces=[]
                    
        for f in self.body.Shape.Faces:
            
            if (f.Area/1e6 > 0.5):
                self.labeledFaces.append(labeledSurface(f))
        
        App.ActiveDocument.recompute()

        
    def recoverShell(self,shell_objects_names):
        #function to recover existing shells after reload
        #shell_objects= list of face parts
        
        for f,part_name in zip(self.labeledFaces,shell_objects_names):
            face_part=App.ActiveDocument.getObject(part_name)
            f.attachFreeFace(face_part)

    def recoverLabel(self,labels_list):
        #function to recover existing shells after reload
        #shell_objects= list of face parts
        
        for f,part_name in zip(self.labeledFaces,labels_list):
            if part_name is not None:
                label_part=App.ActiveDocument.getObject(part_name)
                f.labelObj = label_part
                f.label = label_part.LabelText

                

    def createShell(self):
        for f in self.labeledFaces:

            f.createFreeFace()

        App.ActiveDocument.recompute()

    def deleteShell(self):
    
        for f in self.labeledFaces:
        
            f.delFreeFace()

        App.ActiveDocument.recompute()


    def getLabels(self):
    
        return [ lface.getLabel() for lface in self.labeledFaces ]
        
        

    def getVolume(self):
    
        return(self.body.Shape.Volume/1e9)
        
    def getLabeledFaces(self):
    
        return(list(self.labeledFaces))
        
                
    def setSelectionType(self):
     
        sel=Gui.Selection.getSelection() 
    
        nameslist=[ x.Name for x in sel]

        label=QtGui.QInputDialog.getText(None, "Set label for selection", "Label")[0]
        
        for lface in self.labeledFaces:
            
            if lface.freeFace.Name in nameslist:
                
                lface.setLabel(label)
      
        self.colorByLabel()
        self.showLegend()
        
                
    def setAllTypesFromList(self,labellist):
    
        self.hide()
        self.createShell()
       
        for lface,label in zip(self.labeledFaces,labellist):
            lface.setLabel(label)
                    
                    
    """def hideAllLabels(self):
    
        for lface in self.labeledFaces:
        
            lface.hideLabel()
            
    def showAllLabels(self):
    
        for lface in self.labeledFaces:
        
            lface.showLabel()
          
    def showVisibleFacesLabel(self):
    
        self.showAllLabels()
    
        viewdir=Gui.ActiveDocument.ActiveView.getViewDirection()
        
        for lface in self.labeledFaces:
        
            fnormal=lface.solidFace.normalAt(0,0)
    
            if (viewdir*fnormal > -0.3 ): #ceux qui sont dans la directin opposée, valeur de 0.3 empirique
                lface.hideLabel()
    """           
    
    def showAreasAndVolume(self):
    
        areas=self.getAreasByLabel()
        
        texttoprint=''
        
        for k,v in areas.items():
            texttoprint+=str(k).ljust(10)+str(round(v,2))+' m2 \n'
                      
        volume=self.getVolume()
        
        texttoprint+=str('Volume').ljust(10)+str(round(volume,2))+' m3 \n'
                  
        dialog=QtGui.QDialog()
        dialog.setWindowTitle("Areas and volume of the model")
        lo=QtGui.QVBoxLayout()
        dialog.setLayout(lo)
        
        textE=QtGui.QTextEdit()
        lo.addWidget(textE)
        
        textE.setText(texttoprint)
        dialog.exec()
    
    def getVolume(self):
    
        return self.body.Shape.Volume/1e9
    
    def getAreasByLabel(self):
    
        definedlabels=[ x if x != None else 'No Label' for x in self.getLabels() ]
        uniquelabels=list(set(definedlabels))
        uniquelabels.sort() #inplace sorting

        areas={ label:0 for label in uniquelabels }
        areas["Total"]=0
    
        for lface in self.labeledFaces:
        
            area=lface.freeFace.Shape.Area/1e6
            
            lab=lface.getLabel()
            
            if lab != None:
                key=lab
            else:
                key='No Label'
                
            areas[key]+=area       
            areas["Total"]+=area
        
        return areas
    
    
    def getOpenings(self,projectSkinDescription,sectorMap):
        
        definedlabels=[ x if x != None else 'No Label' for x in self.getLabels() ]
        uniquelabels=list(set(definedlabels))
        uniquelabels.sort() #inplace sorting

        N=16
        dalpha=360/N

        #self.sectormap

        openings=[]
        skTOpeningsCount = { skT:0 for skT in projectSkinDescription.keys()}     

        for lface in self.labeledFaces:

            skT=lface.getLabel()
            
            if ( projectSkinDescription[skT]['type']  == 'Ouverture'):
                
                    skTOpeningsCount[skT] += 1
                
                    azimuth = lface.getAzimuth()
                    sector=int((azimuth%360+dalpha/2)/dalpha)%N
                    cardinalDir = sectorMap[sector]
                   
                    #openingChar = {'name':skT+'/'+str(skTOpeningsCount[skT]), 'label':skT,'orientation':cardinalDir,'area':lface.getArea()}
                    #naming should not be done here, since it's also project dependent
                    openingChar = {'label':skT,'orientation':cardinalDir,'area':lface.getArea(),'center':lface.getCenterOfMass()}
                    
                    openings.append(openingChar)
                    
        return openings
    
    def showAreasPerFacade(self,sectormap):
    
        N=16
        dalpha=360/N

        
        labels=[ x if x != None else 'No Label' for x in self.getLabels() ]
        uniquelabels=list(set(labels))
        uniquelabels.sort() #inplace sorting

        azimuths = [ lface.getAzimuth() for lface in self.labeledFaces ]
        
        
        incl= [ lface.getInclination() for lface in self.labeledFaces ]
        areas= [ lface.freeFace.Shape.Area/1e6 for lface in self.labeledFaces ]
        sectors=[ int((az%360+dalpha/2)/dalpha)%N for az in azimuths ]

        unique_sectors=[]
        unique_roofpanes=[]


        for s,i in zip(sectors,incl):

            if (i>100):
                continue #ground, do nothing              
            
            elif (i > 80 ):
                unique_sectors.append(s)  #FACADES

            elif (i<5):
                unique_roofpanes.append((0,0)) # FLAT ROOF --> same sector 0 per default

                
            else:
                unique_roofpanes.append((s,i)) #inclined roof

        
        unique_sectors=list(set(unique_sectors))
        unique_roofpanes=list(set(unique_roofpanes))

        
        fdict={ k:{} for k in unique_sectors }  #fdict = facade dict
        rdict={ k:{} for k in unique_roofpanes} #rdict = roofpane dict

        floors={}
        
        for a,s,l,i in zip(areas,sectors,labels,incl):
        
        
            if (i>100):
                if (l not in floors.keys()):
                    floors[l]=a
                else:
                    floors[l]+=a                    
        
        
            elif (i>80):
        
                if (l not in fdict[s].keys()):
                    fdict[s][l]=a
                else:
                    fdict[s][l]+=a

            elif (i<5):

                if (l not in rdict[(0,0)].keys()):
                    rdict[(0,0)][l]=a
                else:
                    rdict[(0,0)][l]+=a

            else:
            
                if (l not in rdict[(s,i)].keys()):
                    rdict[(s,i)][l]=a
                else:
                    rdict[(s,i)][l]+=a
            
         
        strprint=""
         
        for facade in fdict.keys():
        
            facadename=sectormap[facade]
        
            strprint+="Facade "+str(facadename)+"\n"
            
            for wtype in fdict[facade].keys():
            
                strprint+="   "+wtype+" : "+str(round(fdict[facade][wtype],2))+" m2 \n"

     
        for rpane in rdict.keys():

            roofInclination = round(rpane[1],0)

            if (roofInclination < 5):
                roofCardinalDirection = "Aucune (toit plat)"
            else:
                roofCardinalDirection=sectormap[rpane[0]]   
            

            strprint+="Pan de toit: direction "+roofCardinalDirection+", inclinaison "+str(roofInclination)+"\n"
            
            for rtype in rdict[rpane].keys():
            
                strprint+="   "+rtype+" : "+str(round(rdict[rpane][rtype],2))+" m2 \n"



        strprint+="Planchers \n"
        for ptype in floors.keys():
            strprint+="    "+ptype+" : "+str(round(floors[ptype],2))+" m2\n"
     

        dialog=QtGui.QDialog()
        dialog.setWindowTitle("Areas of the model")
        lo=QtGui.QVBoxLayout()
        dialog.setLayout(lo)
        
        textE=QtGui.QTextEdit()
        lo.addWidget(textE)
        
        textE.setText(strprint)
        dialog.exec()

    
    
    def exportStep(self):

        defpath=os.path.dirname(App.ActiveDocument.FileName) #path of the currrently loaded file
        filename=os.path.basename(App.ActiveDocument.FileName) #filename without path
        stepname=filename.replace('.FCStd','-'+self.body.Label+'.step')
        fullstepname=os.path.join(defpath,stepname)

        fileName = QtGui.QFileDialog.getSaveFileName(None,"Save Step geometry",fullstepname,"STEP (*.stp *.step)")[0]
     
        import ImportGui
        objs=[]
    
        for lface in self.labeledFaces:
            objs.append(lface.freeFace)
            
        ImportGui.export(objs,fileName)
 
        del objs
    
    def exportPNG(self):
    
        #self.choice.addItems(['Situation initiale','Situation modifiee'])
        defpath=os.path.dirname(App.ActiveDocument.FileName) #path of the currrently loaded file
        filename=os.path.basename(App.ActiveDocument.FileName) #filename without path
        pngname=filename.replace('.FCStd','-'+self.body.Label)
        fullpngname=os.path.join(defpath,pngname)
        
        
        w,h=Gui.ActiveDocument.activeView().getSize(); #screen wiew - get size
        Gui.activeDocument().activeView().viewIsometric()

        for i in range(4):
        
            if (i>0):
                RotateView(0,0,1,90)
                    
            self.hideLegend()
            Gui.SendMsgToActiveView("ViewFit")
            self.showLegend()

            Gui.activeDocument().activeView().saveImage(fullpngname+'-'+str(i)+'.png',w,h,'White')



    
    def todict(self):
    
        vpdict={}
        vpdict['bodyname']=self.body.Name
        vpdict['surfaces']=[]
        vpdict['legends']={}
        
        
        for lface in self.labeledFaces:
            vpdict['surfaces'].append(lface.todict())
            
            
        #print("dir self",dir(self))
        #print(self.body.Name)
        if ('legendobj' in dir(self)):
            #print("in if legendobj")
            for k,v in self.legendobj.items():
                vpdict['legends'][k]=v.Name
                
            
        return(vpdict)
        
    
    def resizeLabels(self,size):
        
        for lface in self.labelledFaces:
            lface.resizeLabel(size)
        
            
    def colorByLabel(self):

        import colorsys
        
        definedlabels=[ x for x in self.getLabels() if x != None]
        
        uniquelabels=list(set(definedlabels))
        uniquelabels.sort() #inplace sorting
        
        N=len(uniquelabels)
        
        HSV_tuples = [(x*1.0/N, 0.8, 0.8) for x in range(N)]
        RGB_tuples = map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples)

        RGB_list=list(RGB_tuples)

        colordict={}
        
        for label,rgbtuple in zip(uniquelabels,RGB_list):
            
            rgb=list(rgbtuple)
            rgb.append(0) #transparency
            
            colordict[label]=rgb
        
        
        self.colordict=colordict
        
        for lf in self.labeledFaces:
            flabel=lf.getLabel()
            
            if (flabel!=None):
            
                lf.colorFreeFace(colordict[flabel][0],colordict[flabel][1],colordict[flabel][2],colordict[flabel][3])


    def createLegend(self):
        #create colored labels 
        
        if ('colordict' not in dir(self)):
            self.colorByLabel()
        
        bbox=self.body.Shape.BoundBox
        xmin=bbox.XMin-2000  #units in mm
        ymin=bbox.YMin-2000  #units in mm
        zmin=bbox.ZMin
        
        self.legendobj={}

        group=App.ActiveDocument.getObject('PACE_Group')
        
        #uniquelabels=list(set(self.getLabels()))
    
        for l,c in self.colordict.items():
               
            #print(l)
               
            if (l==None):
                continue
               
            lab=App.ActiveDocument.addObject("App::AnnotationLabel","legend")
            lab.BasePosition=App.Vector(xmin,ymin,zmin)
            lab.LabelText=l
            zmin+=750
            labview=Gui.ActiveDocument.getObject(lab.Name)
            labview.FontSize=10
            labview.BackgroundColor=tuple(c[0:3])
               
            self.legendobj[l]=lab

            group.addObject(self.legendobj[l])



    def removeLegend(self):
    
        if ('legendobj' in dir(self)):
    
            for k,v in self.legendobj.items():
                
                App.ActiveDocument.removeObject(v.Name)    

            del(self.legendobj)

    def hideLegend(self):
    
        if 'legendobj' not in dir(self):
            return
    
        for k,v in self.legendobj.items():
        
            Gui.ActiveDocument.getObject(v.Name).hide()

        self.stopCameraCallBack()
     
        self.LegendShown = False
        
            
    def showLegend(self):
    
        #on supprime on recrée
        self.removeLegend()
    
        if "legendobj" not in dir(self):
            self.createLegend()


        self.adjustLegendPosition()
        self.startCameraCallBack()
        
        self.LegendShown = True
        
    def isLegendShown(self):
        
        return self.LegendShown
        

    def adjustLegendPosition(self,*args):

        av=Gui.ActiveDocument.ActiveView
        ndx,ndy=av.getSize()

        xpos=int(0.05*ndx)
        ypos=int(0.02*ndy)
        
        yShift = 50
        xShift = 80

        for k,v in self.legendobj.items():
           
            if (ypos > (ndy-yShift) ):
                #if higher than max screen y --> second column
                ypos = int(0.02*ndy)
                xpos += xShift
            
            v.BasePosition=(av.getPoint(xpos,ypos))       
            Gui.ActiveDocument.getObject(v.Name).show()
            Gui.ActiveDocument.getObject(v.Name).FontSize=20

            ypos += yShift



    def startCameraCallBack(self):


        cam = Gui.ActiveDocument.ActiveView.getCameraNode()
        
        if ('sensor' not in dir(self)):
        
            #self.sensor = coin.SoFieldSensor(self.adjustLegendPosition,cam)
            self.sensor = coin.SoNodeSensor(self.adjustLegendPosition,cam)       
            self.sensor.setPriority(0)
    
        #self.sensor.attach(cam.orientation)
        self.sensor.attach(cam)
         
                    
    def stopCameraCallBack(self):
    
        if ('sensor' in dir(self)):
    
            self.sensor.detach()
    

    def updateAfterBodyChange(self):
    
        oldListOfFaces = self.getLabeledFaces()  #will continue pointing towards old "freefaces"
        
        self.removeLegend()
        self.setFaces()     # Listing faces of current Solid Body and resetting list
        self.createShell()  # create new shell from current Solid Body
        
        self.matchLabels(oldListOfFaces)
        
        for oldFace in oldListOfFaces:
            oldFace.delFreeFace()
        
    def matchLabels(self,sourceFacesList):
     
        targetFacesList=self.getLabeledFaces()
           
        sourceFacesListCopy = [ x for x in sourceFacesList ] # elements are removed from the list as they are matched, using a copy to keep original list unchanged
           
        #print(len(sourceFacesListCopy))
        #print(len(targetFacesList))
        
        for targetFace in targetFacesList:
            
            for sourceFace in sourceFacesListCopy:
                
                if targetFace.isComparable(sourceFace):        
                
                    #print(targetFace.freeFace.Name,"and ",sourceFace.freeFace.Name," are considered identical")
                    
                    targetFace.setLabel(sourceFace.getLabel())
                    sourceFacesListCopy.remove(sourceFace)  #if identical found, then is removed
                    continue
                
                if targetFace.isSubFaceOf(sourceFace):
                    #print(targetFace.freeFace.Name,"is a part of ",sourceFace.freeFace.Name)

                    targetFace.setLabel(sourceFace.getLabel()) #if only subface found, should not be removed from source list
                    continue

                    



    def delete(self):
    
        self.removeLegend()
    
        for lsurf in self.labeledFaces:
        
            lsurf.delete()


class labeledSurface():

    def __init__(self,solidFace):
    
        #self.SurfaceObject=Sobject
        self.surftype=''  #Wall, Roof, Floor
        self.surfCode=''
        #self.area='0'
        #self.azimuth='0'
        #self.inclination='0'
        self.labelObj=None
        self.solidFace=None
        self.freeFace=None
        
        self.label=None
        
        self.solidFace=solidFace


    def getArea(self):
    
        return(self.solidFace.Area/1e6)
        
    def getInclination(self):

        zvector=App.Vector(0,0,1)    
        normal=self.solidFace.normalAt(0,0)    
                
        #azimuth=np.degrees(np.arctan2(normal.y,normal.x))
    
        #return(self.solidFace
            
        return np.degrees(np.arccos(normal*zvector))
    
    def getAzimuth(self):

        normal=self.solidFace.normalAt(0,0)    
    
        xvector=App.Vector(1,0,0)
        yvector=App.Vector(0,1,0)
        azimuth=np.degrees(np.arctan2(normal.y,normal.x))
        
        return(azimuth)
    
    def getCenterOfMass(self):
        return self.solidFace.CenterOfMass
    
            
    def createFreeFace(self):

        if (self.freeFace == None):
            self.freeFace=App.ActiveDocument.addObject("Part::Feature","Face")
            self.freeFace.Shape=self.solidFace
    
    
    def attachFreeFace(self,face_part):
        
        self.freeFace=face_part
    

    def delFreeFace(self):
    
        if (self.freeFace != None):
    
            name=self.freeFace.Name
            App.ActiveDocument.removeObject(name)
            
        if (self.labelObj!=None):
        
            App.ActiveDocument.removeObject(self.labelObj.Name)

    def createLabel(self):
    
        self.labelObj = App.ActiveDocument.addObject("App::AnnotationLabel","surveyLabel")
        self.labelObj.BasePosition = self.solidFace.CenterOfMass
        
        Gui.ActiveDocument.getObject(self.labelObj.Name).FontSize=10
        self.labelObj.ViewObject.Visibility=False

    
    def resizeLabel(self,size):
        Gui.ActiveDocument.getObject(self.labelObj.Name).FontSize=size
    
        #self.labelObj.LabelText = str(self.surfCode)

    def setLabel(self,label):
    
        if ( not self.hasLabel()):
            self.createLabel()
        
        if (label != None):
        
            self.label=label
            
            self.labelObj.LabelText=self.label
            self.labelObj.Label=self.labelObj.Label+"_"+self.label

    def hasLabel(self):
        
        if (self.labelObj == None):
            return False

        else:
            return True
        

    def getLabel(self):
    
        if self.hasLabel():
        
            label=self.label
            
            if (type(label)==list):
                label=label[0]

        else:
            label = None
        
        # if (label.__class__==list):
        #     label=label[0]
    
        return label

    """def hideLabel(self):
    
        if (self.labelObj is not None):
            Gui.ActiveDocument.getObject(self.labelObj.Name).hide()

    def showLabel(self):
        if (self.labelObj is not None):
            Gui.ActiveDocument.getObject(self.labelObj.Name).show()
    """        

    def setLabelDialog(self):
   
        if (self.labelObj==None):
            self.createLabel()
   
        label=QtGui.QInputDialog.getText(None, "Get text", "Input:")[0]
        
        self.setLabel(label)
        

    def colorFreeFace(self,r,g,b,t):
    
        fname=self.freeFace.Name 
        fview=Gui.ActiveDocument.getObject(fname)
        fview.DiffuseColor=(r,g,b)
        fview.Transparency=t

    def todict(self):
    
        fdict={}
        fdict['freefaceobject']=self.freeFace.Name

        if (self.labelObj != None):
            fdict['label']=self.labelObj.Name

        return (fdict)

    def delete(self):
    
        self.delFreeFace()
        
    def isComparable(self,otherFace):
        
        try:
        
            CenterOfMass = self.freeFace.Shape.CenterOfMass
            Area   = self.freeFace.Shape.Area
            Normal   = self.freeFace.Shape.normalAt(0,0)
                
            otherCenterOfMass = otherFace.freeFace.Shape.CenterOfMass
            otherArea   = otherFace.freeFace.Shape.Area
            otherNormal   = otherFace.freeFace.Shape.normalAt(0,0)
                    
            centersDistance= (CenterOfMass-otherCenterOfMass).Length  
            areaRelativeDifference = np.abs ((Area-otherArea)/otherArea)     
            NormalDot = Normal*otherNormal        
            
            
            #units in mm --> Distance 
            if ( centersDistance < 1000 and areaRelativeDifference < 0.05 and NormalDot > 0.95):                
                return True
            else:
                return False

        except:
            print("Could not compare with face ",otherFace)
            return False            


    def isSubFaceOf(self,otherFace):
       
        # 3 criteria to determine if the face is a subface of otherFace
        # normal are the same --> they are parallel
        # distance between both faces is small (they are considered co-planar)
        # the vertices of the current face are within the boundaries of the Otheface

        #succesive check (instead of "and") to avoid evaluate all functions each time  

        
        if self.isParallel(otherFace):
            
            if self.isDistanceSmall(otherFace):
                
                if self.areVerticesInShape(otherFace):
                    
                    return True
                
        return False
        

    def isParallel(self,otherFace):
        
        Normal   = self.freeFace.Shape.normalAt(0,0)
        otherNormal   = otherFace.freeFace.Shape.normalAt(0,0)
         
        normalDot = Normal*otherNormal   

        if (normalDot > 0.95):
            return True
        else:
            return False


    def isDistanceSmall(self,otherFace,targetDistance=50):
        #default distance : 50 mm
        
        CenterOfMass = self.freeFace.Shape.CenterOfMass
        
        u,v = otherFace.freeFace.Shape.Surface.parameter(CenterOfMass) 
        #projection of Center of Mass on otherface, in face parametric coordinates
        
        projectedPoint = otherFace.freeFace.Shape.Surface.value(u,v) 
        # 3D coordinates of projected point
        
        
        #distance between face true CoM and its projection on otherFace
        # --> this is the distance between the two faces
        actualDistanceBetweenFaces = (CenterOfMass - projectedPoint).Length 
        
        if (actualDistanceBetweenFaces < targetDistance):
            return True
        else:
            return False
        
    def areVerticesInShape(self,otherFace):

        #Check if current face (projected) verticees are in the OtherFace. 
        # If yes, it means the current face is a subFace of otherFace
        
        otherGeometricalFace = otherFace.freeFace.Shape.Faces[0]
        otherFaceVertices = otherGeometricalFace.OuterWire.OrderedVertexes  
        #only solution to have ordered vertices --> otherwise, they are in random order! 

        otherFacePoints = [ v.Point for v in otherFaceVertices]
        
        points2D = [ otherFace.freeFace.Shape.Surface.parameter(point) for point in otherFacePoints ]
        

        p = path.Path(points2D)
       
        facePoints = [ v.Point for v in self.freeFace.Shape.Vertexes ]
        
        for point in facePoints:
            
            u,v = otherFace.freeFace.Shape.Surface.parameter(point)
            #projection of currentFace vertices on the otherFace 
            # projection is required because
            #    1/ there might be a small offset between faces
            #    2/ we need to be in 2D space to check if point is in shape

            if (not p.contains_point([u,v],None,50)):
                # if one point outside otherFace --> false
                # 50 = tolerance in mm --> the path is slightly enlarged
                
                return False

        #if all points in --> return True

        return True
        

def selectTemplate():

        
    templatesDict = {'Vierge' : 'audit_vierge.xml',
                     'Chauffage Mazout radiateurs et thermostat': 'ccMazout_template.xml',
                     'Aucun système initial': 'aucunSysteme_template.xml'
                     }
        
    items = list(templatesDict.keys())
		
    item, ok = QtGui.QInputDialog.getItem(None, "Choose a template", "Available template", items, 0, False)
			
    if ok and item:
          
        return templatesDict[item]

    else:
        return None


def selectMeasurementMethod():

        
    choiceDict = {'Methode des surfaces nettes' : 'netSurface',
                  'Methode des surfaces brutes' : 'grossSurface'
                  }
        
    items = list(choiceDict.keys())
		
    text = ''
    text+= 'Methode des surfaces netttes: à choisir si les fenêtres ont été dessinées dans le modèle 3D.\n\n'
    text+= 'Methode des surfaces brutes: à choisir si les fenêtres n\'ont pas été dessinées et doivent être rajoutées par après dans PACE.\n'
    
    item, ok = QtGui.QInputDialog.getItem(None, "Choisir une méthode de mesure pour l'export", text, items, 0, False)
			
    if ok and item:
          
        return choiceDict[item]

    else:
        return None









def RotateView(axisX=1.0,axisY=0.0,axisZ=0.0,angle=45.0):

    #Gui.ActiveDocument.ActiveView.getViewDirection()

    import math
    from pivy import coin
    try:
        cam = Gui.ActiveDocument.ActiveView.getCameraNode()
        rot = coin.SbRotation()
        rot.setValue(coin.SbVec3f(axisX,axisY,axisZ),math.radians(angle))
        nrot = cam.orientation.getValue() * rot
        cam.orientation = nrot
    except Exception:
        print( "Not ActiveView ")




def getColors(N):
    
    # see map of colors on following adress
    #https://stackoverflow.com/questions/2328339/how-to-generate-n-different-colors-for-any-natural-number-n
    # 19th colors was deleted because too close to white
    
    hexcolors = ["#000000", "#FFFF00", "#1CE6FF", "#FF34FF", "#FF4A46", "#008941", "#006FA6", "#A30059",
                "#FFDBE5", "#7A4900", "#0000A6", "#63FFAC", "#B79762", "#004D43", "#8FB0FF", "#997D87",
                "#5A0007", "#809693",  "#1B4400", "#4FC601", "#3B5DFF", "#4A3B53", "#FF2F80",
                "#61615A", "#BA0900", "#6B7900", "#00C2A0", "#FFAA92", "#FF90C9", "#B903AA", "#D16100",
                "#DDEFFF", "#000035", "#7B4F4B", "#A1C299", "#300018", "#0AA6D8", "#013349", "#00846F",
                "#372101", "#FFB500", "#C2FFED", "#A079BF", "#CC0744", "#C0B9B2", "#C2FF99", "#001E09",
                "#00489C", "#6F0062", "#0CBD66", "#EEC3FF", "#456D75", "#B77B68", "#7A87A1", "#788D66",
                "#885578", "#FAD09F", "#FF8A9A", "#D157A0", "#BEC459", "#456648", "#0086ED", "#886F4C",
                "#34362D", "#B4A8BD", "#00A6AA", "#452C2C", "#636375", "#A3C8C9", "#FF913F", "#938A81",
                "#575329", "#00FECF", "#B05B6F", "#8CD0FF", "#3B9700", "#04F757", "#C8A1A1", "#1E6E00",
                "#7900D7", "#A77500", "#6367A9", "#A05837", "#6B002C", "#772600", "#D790FF", "#9B9700",
                "#549E79", "#FFF69F", "#201625", "#72418F", "#BC23FF", "#99ADC0", "#3A2465", "#922329",
                "#5B4534", "#FDE8DC", "#404E55", "#0089A3", "#CB7E98", "#A4E804", "#324E72", "#6A3A4C",
                "#83AB58", "#001C1E", "#D1F7CE", "#004B28", "#C8D0F6", "#A3A489", "#806C66", "#222800",
                "#BF5650", "#E83000", "#66796D", "#DA007C", "#FF1A59", "#8ADBB4", "#1E0200", "#5B4E51",
                "#C895C5", "#320033", "#FF6832", "#66E1D3", "#CFCDAC", "#D0AC94", "#7ED379", "#012C58"]

    rgb_colors=[]
    
    for c in range(N):
    
        #colors 0 (black) and 1 (yellow) not used becaus not nice
        
        h = hexcolors[c+2].lstrip('#')
        rgbcolor = tuple(float(int(h[i:i+2], 16))/256 for i in (0, 2, 4))

        rgb_colors.append(rgbcolor)

    return rgb_colors







