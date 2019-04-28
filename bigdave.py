# This is a quick demo of a part of dave ported to python for 3ds Max.  Currently written for maya, needs actually, y'know, porting

'''
daveObject:
    Class data structure that handles individual objects used by the tool itself, contains their relevant methods
'''
class daveObject:
    def __init__(self, transform, id):
        print "Object added with name "+str(transform)+" and ID "+str(id)
        #Object's transform name (THIS MEANS THAT THE TOOL NEEDS EVERY KNOWN OBJECT TO HAVE A UNIQUE NAME, THIS CAN BE CHANGED TO BE INDEPENDANT AND WORK WITH HEIRARCHIES)
        self.transform = transform
        #The object's position in DAVE's 'sessionObjects' list.
        self.index = id
        #Dictionary to store properties for the object's hull (if needed)
        self.hull = {
            "tris": [], #The triangular convex hulls that make up this hull's mesh
            "outer": [], #The vertices in order (either clockwise or anticlockwise) around the hull's edge
            "placementVerts": [], #The vertices that form 'edges' of at least the correct length for this object type
            "height": 0.0, #Vertical pos of the hull
            "transform": "" #The hull mesh's transform name
        }
        #Generally unused flag that is true when the hull is generated incorrectly.  Could be used to prompt user to give correct hull but as of all tests has not been required.
        self.wrongBox = False
        #Hash used to store object in databases relevant to DAVE.  Can be expanded to be used in possible output file that can be interpreted by other scripts.
        self.hash = 0
        #What the object's type is (e.g, WALL, DOOR, TABLE etc)
        self.tag = None
        #Initialised to false signifying the object has not yet been successfully and fully imported to the session.  Remains false until it is imported, and 
        # then is set to false if it is then deleted.
        self.enabled = False
        #Whether any processing (e.g, decorating if it is a table) has been performed to stop double processing.
        self.processed = False
        #Whether it even is processable, e.g a wall cannot (at least currently) be decorated, so it is not 'processable'.
        self.processable = True

        #We should look for any hulls that may have been supplied by either the user or older sessions.
        self.searchForHull()

    '''
    grabVerts:
        Used to 'grab' the topmost 10% of verts of an object, as we assume that's there the placable surface is
    '''
    def grabVerts(self):
        self.topVerts = []
        allVPos = []
        #Use maxint as a stupidly large magnitude float to make later code tidier (if you could call it tidy)
        maxVPos = -sys.maxint
        minVPos = sys.maxint
        numVerts = cmds.polyEvaluate(self.transform, v = True)
        for i in range(numVerts):
            allVPos.append(cmds.pointPosition(self.transform + ".vtx[" + str(i) + "]", w = True))
            maxVPos = max(maxVPos, allVPos[i][1])
            minVPos = min(minVPos, allVPos[i][1])
        topMargin = maxVPos - ((maxVPos - minVPos) * 0.3)
        self.hull["height"] = maxVPos
        upperVerts = []
        upperVertsIndex = []
        for i in range(numVerts):
            if round(allVPos[i][1], 2) >= round(topMargin, 2):
                upperVerts.append(allVPos[i])
                upperVertsIndex.append(i)
        delIndices = []
        for i in range(len(self.topVerts)):
            for j in range(len(self.topVerts)):
                if i == j:
                    continue
                #If vert I and J are on top of each other in the XZ plane (unlikely)
                if upperVerts[i][0] == upperVerts[j][0] and upperVerts[i][2] == upperVerts[j][2]:
                    #Keep the higher one
                    if upperVerts[i][1] > upperVerts[j][1]:
                        delIndices.append(j)
                    else:
                        delIndices.append(i)
        #This is required to ensure we're deleting the correct index and we don't access non-existant elements
        for i in range(len(delIndices)):
            del upperVerts[delIndices[i] - i]
            del upperVertsIndex[delIndices[i] - i]
        self.topVerts = upperVerts

    '''
    genConvexHull:
        Generates a convex hull using a graham scan algorithm (modified from https://en.wikipedia.org/wiki/Graham_scan#Pseudocode)
    '''
    def genConvexHull(self):
        #Again ENSURE we have the verts for this
        self.grabVerts()
        #Make sure we don't have both the data and hull for this object still
        if self.hull["tris"] != [] and cmds.objExists(self.hull["transform"]):
            return
        #We need at least 3 verts for this
        if len(self.topVerts) < 3:
            self.hull["outer"] = []
            print "Not enough verts to construct BBox"
            self.wrongBox = True
            return
        #Local function to check if going from p1 -> p2 -> p3 is clockwise, anticlockwise or colinear
        def ccw(p1, p2, p3):
            for d in p1:
                d = round(d, 2)
            for d in p2:
                d = round(d, 2)
            for d in p3:
                d = round(d, 2)
            return (p2[0] - p1[0]) * (p3[2] - p1[2]) - (p2[2] - p1[2]) * (p3[0] - p1[0])
        #Another local function to find the polar angle between two points a and b
        def polarAngle(a, b):
            x = a[0] - b[0]
            y = a[2] - b[2]
            if (x > 0 and y > 0):
                return math.atan(y / x)
            elif (x < 0 and y > 0):
                return math.atan(-x / y) + math.pi / 2.0
            elif (x < 0 and y < 0):
                return math.atan(y / x) + math.pi
            elif (x > 0 and y < 0):
                return math.atan(-x / y) + math.pi / 2.0 + math.pi
            elif (x == 0 and y > 0):
                return math.pi / 2.0
            elif (x < 0 and y == 0):
                return math.pi
            elif (x == 0 and y < 0):
                #Order of operations is correct
                return math.pi / 2.0 + math.pi
            else:
                return 0.0
        points = self.topVerts
        pointsIndex =[]
        for i in range(len(points)):
            pointsIndex.append(i)
        #Sort the points by how left they are first
        pointsIndex = [x for y, x in sorted(zip(self.topVerts, pointsIndex), key = lambda var: var[0][2])]
        #Then by their polar angle to the leftmost point
        pointsIndex = sorted(pointsIndex, key = lambda var: polarAngle(self.topVerts[var], self.topVerts[pointsIndex[0]]))
        stack = []
        stack.append(pointsIndex[0])
        stack.append(pointsIndex[1])
        for i in range(2, len(points)):
            while len(stack) >= 2 and ccw(points[stack[len(stack) - 2]], points[stack[len(stack) - 1]], points[pointsIndex[i]]) <= 0:
                stack.pop()
            stack.append(pointsIndex[i])
        #Create a polygonal surface to represent the hull
        facetList = []
        for i in range(len(stack)):
            pos = self.topVerts[stack[i]]
            facetList.append((pos[0], self.hull["height"], pos[2]))
        #Double check we got at least a triangle from the verts
        if len(facetList) < 3:
            self.hull["outer"] = []
            self.wrongBox = True
            return
        #Create and scale the hull to be correct for Maya's current units (DAVE is reccomended to run on meters)
        #There is no built in support for imperial units currently.
        cmds.polyCreateFacet(name = self.transform+"_cvxHull", p = facetList)
        sf = 100
        currentUnit = cmds.currentUnit(q = True, linear = True)
        if currentUnit == "cm" or currentUnit == "centimeter":
            sf = 1
        elif currentUnit == "mm" or currentUnit == "millimeter":
            sf = 0.1
        cmds.scale(sf, sf, sf)
        #As the hull is defined in a clockwise manner, we should flip the normals so that it looks correct in Maya
        cmds.polyNormal(nm = 0)
        cmds.setAttr(self.transform+".DAVEHULLFLIPPED", "True", type = "string")
        cmds.polyTriangulate(self.transform+"_cvxHull")
        #Send the relevant data to the object's hull storage
        cmds.select(self.transform+"_cvxHull.vtx[0:]")
        self.hull["outer"] = cmds.ls(cmds.polyListComponentConversion(tv = True), fl = True)
        numFaces = cmds.getAttr(self.transform+"_cvxHull.face", size=1)
        self.hull["tris"] = []
        for j in range(numFaces):
            cmds.select(self.transform+"_cvxHull.f["+str(j)+"]")
            verts = cmds.ls(cmds.polyListComponentConversion(tv = True), fl = True)
            self.hull["tris"].append(verts)
        #This should never evaluate to true as we test it earlier, but JUST IN CASE CHECK AGAIN
        if len(facetList) == 3:
            print "Hull has only 3 verts, may be incorrect."
            self.wrongBox = True
        #No verts of the hull should lie outside of the AABB formed by 'topVerts'
        elif (max(facetList, key = lambda x: x[0])[0] > max(self.topVerts, key = lambda x: x[0])[0] or
            max(facetList, key = lambda x: x[2])[2] > max(self.topVerts, key = lambda x: x[2])[2] or
            min(facetList, key = lambda x: x[0])[0] < min(self.topVerts, key = lambda x: x[0])[0] or
            max(facetList, key = lambda x: x[2])[2] < min(self.topVerts, key = lambda x: x[2])[2]):
            print "BBOX ERROR!"
            self.wrongBox = True
        else:
            self.wrongBox = False
        self.hull["transform"] = self.transform+"_cvxHull"
        cmds.addAttr(self.hull["transform"], longName = "DAVEHULL", dataType = "string", hidden = False)
        cmds.setAttr(self.hull["transform"]+".DAVEHULL", self.transform, type = "string")