'''

This module provides a UI element which can display gcode on a Kivy canvas element. It also provides panning 
and zooming features. It was not originally written as a stand alone module which might create some weirdness.

'''

from kivy.uix.floatlayout                    import FloatLayout
from kivy.properties                         import NumericProperty, ObjectProperty
from kivy.graphics                           import Color, Ellipse, Line
from kivy.clock                              import Clock
from DataStructures.makesmithInitFuncs       import MakesmithInitFuncs
from UIElements.positionIndicator            import PositionIndicator
from UIElements.viewMenu                     import ViewMenu
from kivy.graphics.transformation            import Matrix
from kivy.core.window                        import Window

import re
import math

class GcodeCanvas(FloatLayout, MakesmithInitFuncs):
    
    scatterObject     = ObjectProperty(None)
    scatterInstance   = ObjectProperty(None)
    positionIndicator = ObjectProperty(None)
    
    offsetX = NumericProperty(0)
    offsetY = NumericProperty(0)
    
    canvasScaleFactor = 1 #scale from mm to pixels
    INCHES            = 25.4
    MILLIMETERS       = 1 
    
    xPosition = 0
    yPosition = 0
    zPosition = 0
    
    lineNumber = 0  #the line number currently being processed
    
    def initialize(self):

        self.drawWorkspace()
            
        Window.bind(on_resize = self.centerCanvas)
        Window.bind(on_motion = self.zoomCanvas)

        self.data.bind(gcode = self.updateGcode)
        self.data.bind(gcodeShift = self.reloadGcode)
        self.data.bind(gcodeFile = self.reloadGcode)
        
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        
        self.reloadGcode()
    
    def _keyboard_closed(self):
        '''
        
        If the window looses focus.
        
        '''
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        '''
        
        Called when a button is pressed.
        
        '''
        scaleFactor = .03
        anchor = (0,0)
        
        if keycode[1] == self.data.config.get('Ground Control Settings', 'zoomIn'):
            mat = Matrix().scale(1-scaleFactor, 1-scaleFactor, 1)
            self.scatterInstance.apply_transform(mat, anchor)
        if keycode[1] == self.data.config.get('Ground Control Settings', 'zoomOut'):
            mat = Matrix().scale(1+scaleFactor, 1+scaleFactor, 1)
            self.scatterInstance.apply_transform(mat, anchor)
    
    def reloadGcode(self, *args):
        '''
        
        This reloads the gcode from the hard drive in case it has been updated. 
        
        '''
        
        filename = self.data.gcodeFile
        try:
            filterfile = open(filename, 'r')
            rawfilters = filterfile.read()
            filtersparsed = re.sub(r'\(([^)]*)\)','',rawfilters) #removes mach3 style gcode comments
            filtersparsed = re.sub(r';([^\n]*)\n','',filtersparsed) #removes standard ; initiated gcode comments
            filtersparsed = re.split(r'\s(?=G)|\n|\s(?=g)|\s(?=M)', filtersparsed) #splits the gcode into elements to be added to the list
            filtersparsed = [x + ' ' for x in filtersparsed] #adds a space to the end of each line
            filtersparsed = [x.lstrip() for x in filtersparsed]
            filtersparsed = [x.replace('X ','X') for x in filtersparsed]
            filtersparsed = [x.replace('Y ','Y') for x in filtersparsed]
            filtersparsed = [x.replace('Z ','Z') for x in filtersparsed]
            filtersparsed = [x.replace('I ','I') for x in filtersparsed]
            filtersparsed = [x.replace('J ','J') for x in filtersparsed]
            filtersparsed = [x.replace('F ','F') for x in filtersparsed]
            
            self.data.gcode = "[]"
            self.data.gcode = filtersparsed
            
            filterfile.close() #closes the filter save file
        except:
            if filename is not "":
                print "Cannot reopen gcode file. It may have been moved or deleted. To locate it or open a different file use File > Open G-code"
            self.data.gcodeFile = ""
        
    def centerCanvas(self, *args):
        '''
        
        Return the canvas to the center of the screen.
        
        '''
        mat = Matrix().translate(Window.width/2, Window.height/2, 0)
        self.scatterInstance.transform = mat
        
        anchor = (0,0)
        mat = Matrix().scale(.45, .45, 1)
        self.scatterInstance.apply_transform(mat, anchor)
    
    def zoomCanvas(self, callback, type, motion, *args):
        if motion.is_mouse_scrolling:
            scaleFactor = .03
            anchor = (0,0)
            
            if motion.button == 'scrollup':
                mat = Matrix().scale(1-scaleFactor, 1-scaleFactor, 1)
                self.scatterInstance.apply_transform(mat, anchor)
            elif motion.button == 'scrolldown':
                mat = Matrix().scale(1+scaleFactor, 1+scaleFactor, 1)
                self.scatterInstance.apply_transform(mat, anchor)

    def drawWorkspace(self, *args):

        self.scatterObject.canvas.remove_group('workspace')
 
        with self.scatterObject.canvas:
            Color(1, 1, 1)

            #create the bounding box
            height = float(self.data.config.get('Maslow Settings', 'bedHeight'))
            width  = float(self.data.config.get('Maslow Settings', 'bedWidth'))
            Line(points = ( -width/2 , -height/2 ,  width/2 , -height/2), dash_offset = 5, group='workspace')
            Line(points = ( -width/2 ,  height/2 ,  width/2 ,  height/2), dash_offset = 5, group='workspace')
            Line(points = ( -width/2 , -height/2 , -width/2 ,  height/2), dash_offset = 5, group='workspace')
            Line(points = (  width/2 , -height/2 ,  width/2 ,  height/2), dash_offset = 5, group='workspace')
            
            #create the axis lines
            Line(points = (-width/2,0,width/2,0), dash_offset = 5, group='workspace')
            Line(points = (0, -height/2,0,height/2), dash_offset = 5, group='workspace')

    def calcAngle(self, X, Y, centerX, centerY):
        '''
        
        calcAngle returns the angle from the positive x axis to a point given the center of the circle 
        and the point. Angle returned in degrees.
    
        '''

        #Special cases at quadrant boundaries (resolves /div0 errors)
        if X == centerX:
            if Y >= centerY: theta = -0.5*math.pi
            if Y < centerY:  theta = 0.5*math.pi
        elif Y == centerY:
            if X > centerX: theta = 0.0*math.pi
            if X < centerX: theta = 1.0*math.pi

        #Normal cases
        if X > centerX and Y > centerY: #quadrant one
            theta = math.atan((centerY - Y)/(X - centerX))
        if X < centerX and Y > centerY: #quadrant two
            theta = math.atan((Y - centerY)/(X - centerX))
            theta = 1.0*math.pi - theta
        if X < centerX and Y < centerY: #quadrant three
            theta = math.atan((Y - centerY)/(X - centerX))
            theta = 1.0*math.pi - theta
        if X > centerX and Y < centerY: #quadrant four
            theta = math.atan((centerY - Y)/(X - centerX))
        
        return(math.degrees(theta + 0.5*math.pi))   
    
    def drawLine(self,gCodeLine,command):
        '''
        
        drawLine draws a line using the previous command as the start point and the xy coordinates
        from the current command as the end point. The line is styled based on the command to allow
        visually differentiating between normal and rapid moves. If the z-axis depth is changed a
        circle is placed at the location of the depth change to alert the user. 
    
        '''
        
        xTarget = self.xPosition
        yTarget = self.yPosition
        zTarget = self.zPosition
        
        x = re.search("X(?=.)([+-]?([0-9]*)(\.([0-9]+))?)", gCodeLine)
        if x:
            xTarget = float(x.groups()[0])*self.canvasScaleFactor
        
        y = re.search("Y(?=.)([+-]?([0-9]*)(\.([0-9]+))?)", gCodeLine)
        if y:
            yTarget = float(y.groups()[0])*self.canvasScaleFactor
        
        z = re.search("Z(?=.)([+-]?([0-9]*)(\.([0-9]+))?)", gCodeLine)
        if z:
            zTarget = float(z.groups()[0])*self.canvasScaleFactor
        
        
        #Draw lines for G1 and G0
        with self.scatterObject.canvas:
            Color(1, 1, 1)
            if command == 'G00':
                Line(points = (self.offsetX + self.xPosition , self.offsetY + self.yPosition , self.offsetX +  xTarget, self.offsetY  + yTarget), width = 1, group = 'gcode', dash_length = 4, dash_offset = 2)
            elif command == 'G01':
                Line(points = (self.offsetX + self.xPosition , self.offsetY + self.yPosition , self.offsetX +  xTarget, self.offsetY  + yTarget), width = 1, group = 'gcode')
       
        #If the zposition has changed, add indicators
        tol = 0.05 #Acceptable error in mm
        if abs(zTarget - self.zPosition) >= tol:
            with self.scatterObject.canvas:
                if zTarget - self.zPosition > 0:
                    Color(0, 1, 0)
                    radius = 2
                else:
                    Color(1, 0, 0)
                    radius = 4
                Line(circle=(self.offsetX + self.xPosition , self.offsetY + self.yPosition, radius), width = 2, group = 'gcode')
        
        self.xPosition = xTarget
        self.yPosition = yTarget
        self.zPosition = zTarget
    
    def drawArc(self,gCodeLine,command):
        '''
        
        drawArc draws an arc using the previous command as the start point, the xy coordinates from
        the current command as the end point, and the ij coordinates from the current command as the
        circle center. Clockwise or counter-clockwise travel is based on the command. 
    
        '''
        
        xTarget = self.xPosition
        yTarget = self.yPosition
        iTarget = 0
        jTarget = 0
        
        x = re.search("X(?=.)([+-]?([0-9]*)(\.([0-9]+))?)", gCodeLine)
        if x:
            xTarget = float(x.groups()[0])*self.canvasScaleFactor
        y = re.search("Y(?=.)([+-]?([0-9]*)(\.([0-9]+))?)", gCodeLine)
        if y:
            yTarget = float(y.groups()[0])*self.canvasScaleFactor
        i = re.search("I(?=.)([+-]?([0-9]*)(\.([0-9]+))?)", gCodeLine)
        if i:
            iTarget = float(i.groups()[0])*self.canvasScaleFactor
        j = re.search("J(?=.)([+-]?([0-9]*)(\.([0-9]+))?)", gCodeLine)
        if j:
            jTarget = float(j.groups()[0])*self.canvasScaleFactor
        
        radius = math.sqrt(iTarget**2 + jTarget**2)
        centerX = self.xPosition + iTarget
        centerY = self.yPosition + jTarget
        
        angle1 = self.calcAngle(self.xPosition, self.yPosition, centerX, centerY)
        angle2 = self.calcAngle(xTarget, yTarget, centerX, centerY)
        
        if command == 'G02':
            angleStart = angle2
            angleEnd = angle1
        elif command == 'G03':
            angleStart = angle1
            angleEnd = angle2
        
        if angleStart < angleEnd:
            angleEnd = angleEnd - 360
        
        #Draw arc for G02 and G03
        with self.scatterObject.canvas:
            Color(1, 1, 1)
            Line(circle=(self.offsetX + centerX , self.offsetY + centerY, radius, angleStart, angleEnd), group = 'gcode')

        self.xPosition = xTarget
        self.yPosition = yTarget

    def clearGcode(self):
        '''
        
        clearGcode deletes the lines and arcs corresponding to gcode commands from the canvas. 
    
        '''
        self.scatterObject.canvas.clear()#remove_group('gcode')
        
        self.drawWorkspace()
    
    def moveLine(self, gcodeLine):
        
        originalLine = gcodeLine
        
        try:
            gcodeLine = gcodeLine.upper() + " "
            
            
            x = gcodeLine.find('X')
            if x != -1:
                space = gcodeLine.find(' ', x)
                number = float(gcodeLine[x+1:space]) + self.data.gcodeShift[0]
                gcodeLine = gcodeLine[0:x+1] + str(number) + gcodeLine[space:]
            
            y = gcodeLine.find('Y')
            if y != -1:
                space = gcodeLine.find(' ', y)
                number = float(gcodeLine[y+1:space]) + self.data.gcodeShift[1]
                gcodeLine = gcodeLine[0:y+1] + str(number) + gcodeLine[space:]
            
            return gcodeLine
        except ValueError:
            print "line could not be moved:"
            print originalLine
            return originalLine
    
    def updateOneLine(self):
        '''
        
        Draw the next line on the gcode canvas
        
        '''
        validPrefixList = ['G00','G0 ','G1 ','G01','G2 ','G02','G3 ','G03']
        
        self.lineNumber = self.lineNumber + 1
        
        try:
            self.data.gcode[self.lineNumber] = self.moveLine(self.data.gcode[self.lineNumber])    #move the line if the gcode has been moved
            fullString = self.data.gcode[self.lineNumber]
        except:
            return #we have reached the end of the file
        
        fullString = fullString + " " #ensures that there is a space at the end of the line
        
        #find 'G' anywhere in string
        gString = fullString[fullString.find('G'):fullString.find('G') + 3]
        
        if gString in validPrefixList:
            prependString = gString
        
        if fullString.find('G') == -1: #this adds the gcode operator if it is omitted by the program
            fullString = self.prependString + fullString
        
        if gString in validPrefixList:
            self.prependString = fullString[0:3] + " "
        
        if gString == 'G00' or gString == 'G0 ':
            self.drawLine(fullString, 'G00')

        if gString == 'G01' or gString == 'G1 ':
            self.drawLine(fullString, 'G01')
                    
        if gString == 'G02' or gString == 'G2 ':
            self.drawArc(fullString, 'G02')
                           
        if gString == 'G03' or gString == 'G3 ':
            self.drawArc(fullString, 'G03')
        
        if gString == 'G18':
            print "G18 not supported"
        
        if gString == 'G20':
            self.canvasScaleFactor = self.INCHES
            self.data.units = "INCHES"
            
        if gString == 'G21':
            self.canvasScaleFactor = self.MILLIMETERS
            self.data.units = "MM"
            
        if gString == 'G90':
            self.absoluteFlag = 1
            
        if gString == 'G91':
            self.absoluteFlag = 0
        
    def callBackMechanism(self, callback) :
        '''
        
        Call the updateOneLine function periodically in a non-blocking way to
        update the gcode.
        
        '''
        
        #Draw numberOfTimesToCall lines on the canvas
        numberOfTimesToCall = 50
        
        for _ in range(numberOfTimesToCall):
            self.updateOneLine()
        
        #Repeat until end of file
        if self.lineNumber < min(len(self.data.gcode),20000):
            Clock.schedule_once(self.callBackMechanism)
    
    def updateGcode(self, *args):
        '''
        
        updateGcode parses the gcode commands and calls the appropriate drawing function for the 
        specified command. 
    
        '''
        
        #reset variables 
        self.xPosition = 0
        self.yPosition = 0
        self.zPosition = 0

        self.prependString = "G00 "
        self.lineNumber = 0
        
        self.clearGcode()
        
        #Check to see if file is too large to load
        if len(self.data.gcode) > 20000:
            errorText = "The current file contains " + str(len(self.data.gcode)) + "lines of gcode.\nrendering all " +  str(len(self.data.gcode)) + " lines simultaneously may crash the\n program, only the first 20000 lines are shown here.\nThe complete program will cut if you choose to do so."
            print errorText
        else:
            self.callBackMechanism(self.updateGcode)
        
