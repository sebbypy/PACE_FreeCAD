import paceGeomTools
import FreeCADGui as Gui
import FreeCAD as App
import PySide.QtGui as QtGui
import os

class PACETaskPanel(QtGui.QWidget):

    def __init__(self):
  
        if (App.ActiveDocument.getObject('PACE') == None):
            Gui.doCommand("print('Creae PACE obj')")
            freecadobject=App.ActiveDocument.addObject("App::FeaturePython","PACE")
            
            paceProj=paceGeomTools.paceProject() #init
            paceProj.createShells()
            
            freecadobject.addProperty("App::PropertyPythonObject","PACEProject","paceGeomTools.paceProject","PACE project").PACEProject=paceProj
            freecadobject.Proxy=paceProj

            App.ActiveDocument.addObject("App::DocumentObjectGroup","PACE Group")
     
        else:
            freecadobject=App.ActiveDocument.getObject('PACE')
            freecadobject.Proxy=freecadobject.PACEProject
                       
                       
            if ('linked' not in dir(freecadobject.PACEProject) and 'savedstate' in dir(freecadobject.PACEProject)):
                freecadobject.PACEProject.linkfaces()
            
            elif ('linked' in dir(freecadobject.PACEProject) and freecadobject.PACEProject.linked==False):

                freecadobject.PACEProject.linkfaces()
            
            else:
                print("continue")
                
     
        self.proj=freecadobject.PACEProject
        self.moveAllInGroup()

        self.setUI()    

        self.hideBodies()

        self.change()
        
        
    def hideBodies(self):
        
        for situation in self.proj.VP.keys():
            self.proj.VP[situation].hideBody()
        
    def moveAllInGroup(self):
        
    
        freecadobject=App.ActiveDocument.getObject('PACE')
        
        group=App.ActiveDocument.getObject('PACE_Group')
        
        for v in self.proj.VP.values():
        
            freecadfaces=v.getLabeledFaces()
            for f in freecadfaces:
                
                if (f.freeFace != None):
                    group.addObject(f.freeFace)
 
                if (f.labelObj != None):
                
                    group.addObject(f.labelObj)
        
            if ('legendobj' in dir(v)):
                for k,lv in v.legendobj.items():
                    group.addObject(lv)
                


    def setUI(self):
    
        self.base = QtGui.QWidget()
        self.base.setWindowTitle("PACE tools")     

        self.form = self.base
        self.layout=QtGui.QVBoxLayout()
        self.form.setLayout(self.layout)
        
        titles={'init':'Initial situation',
                'mod': 'Modified situation'}

        iconPath = os.path.join(App.getUserMacroDir(True),'pace_logo.png')
        print(iconPath)
        
        if os.path.exists(iconPath) and os.name != 'posix':
            print("In if")
            paceIcon = QtGui.QIcon(iconPath)
            self.base.setWindowIcon(paceIcon) #dommage, ca fait crasher...

   
        self.situationChoice=QtGui.QComboBox()
        self.situationChoice.addItems([titles[situation] for situation in self.proj.VP.keys()])
        self.situationChoice.currentIndexChanged.connect(self.change)
        
        skinElementsDescriptionButton=QtGui.QPushButton("Skin elements description")
        #skinElementsDescriptionButton.clicked.connect(self.proj.setSkinElementsDescription)
        skinElementsDescriptionButton.clicked.connect(lambda: paceGeomTools.skinElementsConfigurator(self.proj))

        self.compass = paceGeomTools.Compass()
        
        if (hasattr(self.proj,'sectormap')):
            self.compass.sectormap = self.proj.sectormap
        
        setCompassButton=QtGui.QPushButton("Define building orientation")
        setCompassButton.clicked.connect(lambda: self.compass.setCompassFromFace(self.proj))
  
        exportToPaceButton=QtGui.QPushButton("Export geometry to PACE")
        exportToPaceButton.clicked.connect(self.proj.exportToPace)


        self.collayouts={}       
        self.vpwidgets={}

        for situation in self.proj.VP.keys():

            self.vpwidgets[situation]=QtGui.QWidget()
            self.collayouts[situation]=QtGui.QVBoxLayout()
            
                      
            identifySelB=QtGui.QPushButton("Assign SELECTION wall type")
            identifySelB.clicked.connect(self.proj.VP[situation].setSelectionType)
 
 
            #showlabelsB=QtGui.QPushButton("Show/refresh wall types")
            #showlabelsB.clicked.connect(self.proj.VP[situation].showVisibleFacesLabel)

            #hidelabelsB=QtGui.QPushButton("Hide wall types")
            #hidelabelsB.clicked.connect(self.proj.VP[situation].hideAllLabels)

            
            colorbyLabelB=QtGui.QPushButton("Color by Label")
            colorbyLabelB.clicked.connect(self.proj.VP[situation].colorByLabel)
        
            showHideLegend=QtGui.QPushButton("Show/hide color legend")
            showHideLegend.clicked.connect(self.showHideLegend)
            
            #hideL=QtGui.QPushButton("Hide colors legend")
            #hideL.clicked.connect(self.proj.VP[situation].hideLegend)
            
            showAreasAndVolume=QtGui.QPushButton("Show areas per wall type")
            showAreasAndVolume.clicked.connect(self.proj.VP[situation].showAreasAndVolume)

            showAreasWt=QtGui.QPushButton("Show areas per wall type and Facade")
            showAreasWt.clicked.connect(lambda state=False,situation=situation: self.proj.VP[situation].showAreasPerFacade(self.proj.sectormap))
            # see https://stackoverflow.com/questions/35819538/using-lambda-expression-to-connect-slots-in-pyqt
            # I cant avoid lambda if I want to pass a parameter
            # However, the lambda does not record the situation value, but only the reference ! 
            # Have to use default value (situation = situation) to force recording it

            
            exportStep=QtGui.QPushButton("Export step file")
            exportStep.clicked.connect(self.proj.VP[situation].exportStep)
            
            exportPNG=QtGui.QPushButton("Save PNG figure to file")
            exportPNG.clicked.connect(self.proj.VP[situation].exportPNG)

            exportPNGtoPACE=QtGui.QPushButton("Export current view to PACE file ("+situation+" situation)")
            exportPNGtoPACE.clicked.connect(lambda state=False,situation=situation: self.proj.insertCurrentViewInPaceFile(situation))

        
            updateAfterBodyModificationButton = QtGui.QPushButton("Update after body modif")
            updateAfterBodyModificationButton.clicked.connect(lambda state=False,situation=situation :self.updateSituation(situation))
            
        
        
            self.collayouts[situation].addWidget(identifySelB)
 
            #self.collayouts[situation].addWidget(showlabelsB)
            #self.collayouts[situation].addWidget(hidelabelsB)
            
            self.collayouts[situation].addWidget(colorbyLabelB)

            self.collayouts[situation].addWidget(showHideLegend)
           # self.collayouts[situation].addWidget(hideL)
           
            self.collayouts[situation].addWidget(showAreasAndVolume)
            self.collayouts[situation].addWidget(showAreasWt)
            
            self.collayouts[situation].addWidget(exportStep)
            self.collayouts[situation].addWidget(exportPNG)
            self.collayouts[situation].addWidget(exportPNGtoPACE)

            self.collayouts[situation].addWidget(updateAfterBodyModificationButton)


            self.vpwidgets[situation].setLayout(self.collayouts[situation])

            


        if ("mod" in self.proj.VP.keys()):

            mapB=QtGui.QPushButton("Copy types from init to mod")
            mapB.clicked.connect(lambda: self.proj.copyLabelsToOtherSituation('init','mod'))
            self.collayouts['mod'].addWidget(mapB) 


        self.layout.addWidget(self.situationChoice)
        self.layout.addWidget(skinElementsDescriptionButton)
        self.layout.addWidget(setCompassButton)
        self.layout.addWidget(exportToPaceButton)

        self.layout.addWidget(self.vpwidgets['init'])


        if ("mod" in self.proj.VP.keys()):

            self.layout.addWidget(self.vpwidgets['mod'])
            self.vpwidgets['mod'].hide()        


    def showHideLegend(self):
        
        titles={'init':'Initial situation',
                'mod': 'Modified situation'}
        
        reversedTitles = {v:k for k,v in titles.items()}

        currentSituationTitle = self.situationChoice.currentText()
        currentSituation = reversedTitles[currentSituationTitle] 
        
        if self.proj.VP[currentSituation].isLegendShown():

            self.proj.VP[currentSituation].hideLegend()
            
        else:
            self.proj.VP[currentSituation].showLegend()
            

    def updateSituation(self,situation):
        
        self.proj.VP[situation].updateAfterBodyChange()
        self.moveAllInGroup()
        self.proj.VP[situation].colorByLabel()
        self.proj.VP[situation].showLegend()
      
        


    def change(self):


        titles={'init':'Initial situation',
                'mod': 'Modified situation'}

    
        if ('mod' not in self.proj.VP.keys()):
            self.vpwidgets['init'].show()
            self.proj.VP['init'].showFaces()
            self.proj.VP['init'].showLegend()
        
            return
        
        if (self.situationChoice.currentText()==titles['init']):
        
            self.vpwidgets['init'].show()
            self.vpwidgets['mod'].hide()
       

            self.proj.VP['mod'].hideFaces()
            self.proj.VP['mod'].hideLegend()
            
            self.proj.VP['init'].showFaces()
            self.proj.VP['init'].showLegend()
        
        else:
            self.vpwidgets['init'].hide()
            self.vpwidgets['mod'].show()
            self.proj.VP['mod'].showFaces()
            self.proj.VP['init'].hideFaces()
            self.proj.VP['init'].hideLegend()

            self.proj.VP['mod'].showFaces()
            self.proj.VP['mod'].showLegend()

    
        return


    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Ok)

    """def clicked(self, bt):
        if bt == QtGui.QDialogButtonBox.Apply:
            print("Apply")"""

    def accept(self):
        self.hideAll()
        print("Accept")
        self.finish()

    def reject(self):
        self.hideAll()

        print("Reject")
        self.finish()

    def finish(self):
        self.hideAll()

        print("Finish")
        Gui.Control.closeDialog()
        # Gui.ActiveDocument.resetEdit()

        
    def hideAll(self):
        
        for situation in self.proj.VP.keys():
            self.proj.VP[situation].hideFaces()
            self.proj.VP[situation].hideLegend()
        

        
        

Gui.Control.showDialog(PACETaskPanel())



