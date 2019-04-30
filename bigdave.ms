-- This is a quick demo of a part of dave ported to python for 3ds Max.  Currently written for maya, needs actually, y'know, porting

    /*
    grabVerts:
        Used to 'grab' the topmost 10% of verts of an object, as we assume that's there the placable surface is
    */
    fn grabVerts =
	(
        topVerts = #()
        allVPos = #()
        numVerts = meshOp.getNumVerts(selection[1].mesh)
		-- Temp fix as I couldn't understand the error with using #1.INF?
		maxVPos = -100000.f
		minVPos = 100000.f
        for i = 1 to numVerts do
		(
			append allVPos(getVert selection[1].mesh i)
			if maxVPos < allVPos[i][3] then maxVPos = allVPos[i][3]
			if minVpos > allVPos[i][3] then minVpos = allVPos[i][3]
		)
        topMargin = maxVPos - ((maxVPos - minVPos) * 0.1f)
        upperVerts = #()
        upperVertsIndex = #()
        for i = 1 to numVerts do
		(
			
            if allVPos[i][3] >= topMargin do
			(
                append upperVerts allVPos[i]
                append upperVertsIndex i
			)
		)
        delIndices = #()
        for i = 1 to topVerts.count do
		(
            for j = 1 to topVerts.count do
			(
                if i == j do
				(
                    continue
				)
                -- If vert I and J are on top of each other in the XZ plane (unlikely)
                if upperVerts[i][1] == upperVerts[j][1] and upperVerts[i][2] == upperVerts[j][2] do
				(
                    --Keep the higher one
                    if upperVerts[i][3] > upperVerts[j][3] then append delIndices j else append delIndices i
				)
			)
		)
        --This is required to ensure we're deleting the correct index and we don't access non-existant elements
        for i = 1 to delIndices.count do
		(
			deleteItem upperVerts (delIndices[i] - i + 1)
			deleteItem upperVertsIndex (delIndices[i] - i + 1)
		)
        topVerts = upperVerts
		return topVerts
	)

    /*
    genConvexHull:
        Generates a convex hull using a graham scan algorithm (modified from https://en.wikipedia.org/wiki/Graham_scan#Pseudocode)
    */
    fn genConvexHull =
	(
        topVerts = grabVerts()
        --We need at least 3 verts for this
        if topVerts.count < 3 then
		(
            print "Not enough verts to construct BBox"
            return False
		)
        -- Local function to check if going from p1 -> p2 -> p3 is clockwise, anticlockwise or colinear
        fn ccw p1 p2 p3 =
		(
            return (p2[1] - p1[1]) * (p3[2] - p1[2]) - (p2[2] - p1[2]) * (p3[1] - p1[1])
		)
        -- Another local function to find the polar angle between two points a and b
        fn polarAngle a b =
		(
            x = a[1] - b[1]
            y = a[2] - b[2]
            if (x > 0 and y > 0) then
                return math.atan(y / x)
			else if (x < 0 and y > 0) then
                return math.atan(-x / y) + math.pi / 2.0
            else if (x < 0 and y < 0) then
                return math.atan(y / x) + math.pi
            else if (x > 0 and y < 0) then
                return math.atan(-x / y) + math.pi / 2.0 + math.pi
            else if (x == 0 and y > 0) then
                return math.pi / 2.0
            else if (x < 0 and y == 0) then
                return math.pi
            else if (x == 0 and y < 0) then
                --Order of operations is correct
                return math.pi / 2.0 + math.pi
            else
                return 0.0
		)
        points = topVerts
        pointsIndex = #()
        for i = 1 to points.count do append pointsIndex i
		--This part is essential for the rest to work
		/*
		--Sort the points by how left they are first
		pointsIndex = [x for y, x in sorted(zip(self.topVerts, pointsIndex), key = lambda var: var[0][2])]
		#Then by their polar angle to the leftmost point
		pointsIndex = sorted(pointsIndex, key = lambda var: polarAngle(self.topVerts[var], self.topVerts[pointsIndex[0]]))
		*/
        stk = #()
        append stk pointsIndex[1]
        append stk pointsIndex[2]
        for i = 3 to points.count do
		(
            while stk.count >= 2 and (ccw points[stk[stk.count - 1]] points[stk[stk.count]] points[pointsIndex[i]]) <= 0 do
			(
				deleteItem stk stk.count
			)
            append stk pointsIndex[i]
		)
        --Create a polygonal surface to represent the hull
        facetList = #()
        for i = 1 to stk.count do
		(
            pos = topVerts[stk[i]]
            append facetList(#(pos[1], 40, pos[3]))
		)
        --Double check we got at least a triangle from the verts
        if facetList.count < 3 then
		(
            print "Not enough verts to construct BBox"
            return False
		)
        return pointsIndex
	)
		
points = genConvexHull()