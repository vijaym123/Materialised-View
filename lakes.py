import numpy as np
import pylab
import itertools
import math
from matplotlib import pyplot as plt
import timeit

class PolygonsTouching(Exception):

    """ This exception is triggered when two polygons touch at one point.

    This is for internal use only and will be caught before returning.

    """

    def __init__(self, x=0, y=0):
        self.x, self.y = x, y

    def __str__(self):
        return 'The tested polygons at least touch each other at (%f,%f)'\
               % (self.x, self.y)

    def shift(self, dx, dy):
        self.x += dx
        self.y += dy


def pair_overlapping(polygon1, polygon2, digits=None):
    """ Find out if polygons are overlapping or touching.

    The function makes use of the quadrant method to find out if a point is
    inside a given polygon.

    polygon1, polygon2 -- Two arrays of [x,y] pairs where the last and the
        first pair is the same, because the polygon has to be closed.
    digits -- The number of digits relevant for the decision between
        separate and touching or touching and overlapping

    Returns 0 if the given polygons are neither overlapping nor touching,
    returns 1 if they are not overlapping, but touching and
    returns 2 if they are overlapping

    """

    def calc_walk_summand(r1, r2, digits=None):
        """ Calculates the summand along one edge depending on axis crossings.

        Follows the edge between two points and checks if one or both axes are
        being crossed. If They are crossed in clockwise sense, it returns +1
        otherwise -1. Going through the origin raises the PolygonsTouching
        exception.

        Returns one of -2, -1, 0, +1, +2 or raises PolygonsTouching

        """
        x, y = 0, 1  # indices for better readability
        summand = 0  # the return value
        tx, ty = None, None  # on division by zero, set parameters to None
        if r1[x] != r2[x]:
            ty = r1[x] / (r1[x] - r2[x])  # where it crosses the y axis
        if r1[y] != r2[y]:
            tx = r1[y] / (r1[y] - r2[y])  # where it crosses the x axis
        if tx == None:
            tx = ty
        if ty == None:
            ty = tx
        # if tx == ty and tx==None:
        #     print "R1", r1
        #     print "R2", r2
        #     tx = 0
        #     ty = 0
        rsign = pylab.sign
        if digits != None:
            rsign = lambda x: pylab.sign(round(x, digits))
        sign_x = rsign(r1[x] + tx * (r2[x] - r1[x]))
        sign_y = rsign(r1[y] + ty * (r2[y] - r1[y]))
        if (tx >= 0) and (tx < 1):
            if (sign_x == 0) and (sign_y == 0):
                raise PolygonsTouching()
            summand += sign_x * pylab.sign(r2[y] - r1[y])
        if (ty >= 0) and (ty < 1):
            if (sign_x == 0) and (sign_y == 0):
                raise PolygonsTouching()
            summand += sign_y * pylab.sign(r1[x] - r2[x])
        return summand

    def current_and_next(iterable):
        """ Returns an iterator for each element and its following element.

        """
        iterator = iter(iterable)
        item = iterator.next()
        for next in iterator:
            yield (item, next)
            item = next

    def point_in_polygon(xy, xyarray, digits=None):
        """ Checks if a point lies inside a polygon using the quadrant method.

        This moves the given point to the origin and shifts the polygon
        accordingly. Then for each edge of the polygon, calc_walk_summand is
        called. If the sum of all returned values from these calls is +4 or -4,
        the point lies indeed inside the polygon. Otherwise, if a
        PolygonsTouching exception has been caught, the point lies on ond of
        the edges of the polygon.

        Returns the number of nodes of the polygon, if the point lies inside,
        otherwise 1 if the point lies on the polygon and if not, 0.

        """
        moved = xyarray - \
            xy  # move currently checked point to the origin (0,0)
        touching = False  # this is used only if no overlap is found
        walk_sum = 0
        for cnxy in current_and_next(moved):
            try:
                walk_sum += calc_walk_summand(cnxy[0], cnxy[1], digits)
            except PolygonsTouching, (e):
                e.shift(*xy)
                touching = True
        if (abs(walk_sum) == 4):
            return len(xyarray)
        elif touching:
            return 1
        else:
            return 0

    def polygons_overlapping(p1, p2, digits=None):
        """ Checks if one of the nodes of p1 lies inside p2.

        This repeatedly calls point_in_polygon for each point of polygon p1
        and immediately returns if it is the case, because then the polygons
        are obviously overlapping.

        Returns 2 for overlapping polygons, 1 for touching polygons and 0
        otherwise.

        """
        degree_of_contact = 0
        xyarrays = [p1, p2]
        for xy in xyarrays[0]:
            degree_of_contact += point_in_polygon(xy, xyarrays[1], digits)
            if degree_of_contact >= len(xyarrays[1]):
                return 2
        if degree_of_contact > 0:
            return 1
        else:
            return 0

    way1 = polygons_overlapping(polygon1, polygon2, digits)
    way2 = 0
    # Only if the polygons are not already found to be overlapping
    if way1 < 2:
        way2 = polygons_overlapping(polygon2, polygon1, digits)
    return max(way1, way2)


def collection_overlapping_serial(polygons, digits=None):
    """ Similar to the collection_overlapping function, but forces serial
    processing.

    """
    result = []
    pickle_polygons = [p.get_xy() for p in polygons]
    for i in xrange(len(polygons)):
        for j in xrange(i + 1, len(polygons)):
            result.append((i, j,
                           pair_overlapping(
                           pickle_polygons[i], pickle_polygons[j],
                           digits)))
    return result


def __cop_bigger_job(polygons, index, digits=None):
    """ This is a helper to efficiently distribute workload among processors.

    """
    result = []
    for j in xrange(index + 1, len(polygons)):
        result.append((index, j,
                       pair_overlapping(polygons[index], polygons[j], digits)))
    return result


def collection_overlapping_parallel(polygons, digits=None,
                                    ncpus='autodetect'):
    """ Like collection_overlapping, but forces parallel processing.

    This function crashes if Parallel Python is not found on the system.

    """
    import pp
    ppservers = ()
    job_server = pp.Server(ncpus, ppservers=ppservers)
    pickle_polygons = [p.get_xy() for p in polygons]
    jobs = []
    for i in xrange(len(polygons)):
        job = job_server.submit(__cop_bigger_job,
                               (pickle_polygons, i, digits, ),
                               (pair_overlapping, PolygonsTouching, ),
                               ("pylab", ))
        jobs.append(job)
    result = []
    for job in jobs:
        result += job()
    # job_server.print_stats()
    return result


def collection_overlapping(polygons, digits=None):
    """ Look for pair-wise overlaps in a given list of polygons.

    The function makes use of the quadrant method to find out if a point is
    inside a given polygon. It invokes the pair_overlapping function for each
    combination and produces and array of index pairs of these combinations
    together with the overlap number of that pair. The overlap number is 0 for
    no overlap, 1 for touching and 2 for overlapping polygons.

    This function automatically selects between a serial and a parallel
    implementation of the search depending on whether Parallel Python is
    installed and can be imported or not.

    polygons -- A list of arrays of [x,y] pairs where the last and the first
        pair of each array in the list is the same, because the polygons have
        to be closed.
    digits -- The number of digits relevant for the decision between
        separate and touching or touching and overlapping polygons.

    Returns a list of 3-tuples

    """
    try:
        import pp  # try if parallel python is installed
    except ImportError:
        return collection_overlapping_serial(polygons, digits)
    else:
        return collection_overlapping_parallel(polygons, digits)


class Node():
    ROOT = 0
    BRANCH = 1
    LEAF = 2
    #_______________________________________________________
    # In the case of a root node "parent" will be None. The
    # "rect" lists the minx,minz,maxx,maxz of the rectangle
    # represented by the node.

    def __init__(self, parent, lakeids, rect):
        global countLeaf

        self.parent = parent
        self.rect = rect
        self.lakes = lakeids
        self.children = [None, None, None, None]
        
        if parent == None:
            self.depth = 0
        else:
            self.depth = parent.depth + 1
        if self.parent == None:
            self.type = Node.ROOT
        if len(self.lakes) == 1:
            self.type = Node.LEAF
            self.children = None
            countLeaf+=1
            #print (self.rect[0], self.rect[1]), self.rect[2]-self.rect[0], self.rect[3]-self.rect[1]
            drawRect = plt.Rectangle((self.rect[0], self.rect[1]), self.rect[2]-self.rect[0], self.rect[3]-self.rect[1], ec='#000000', color='red')
            ax.add_patch(drawRect)
            #print "Leaf number :", countLeaf
        elif len(self.lakes) == 0:
            self.type = Node.LEAF
            self.children = None
            drawRect = plt.Rectangle((self.rect[0], self.rect[1]), self.rect[2]-self.rect[0], self.rect[3]-self.rect[1], ec='#000000', color='white')
            ax.add_patch(drawRect)
        else:
            self.type = Node.BRANCH
            drawRect = plt.Rectangle((self.rect[0], self.rect[1]), self.rect[2]-self.rect[0], self.rect[3]-self.rect[1], ec='#000000', color='white')
            ax.add_patch(drawRect)
            self.constructQuadtree()
    #_______________________________________________________
    # Recursively subdivides a rectangle. Division occurs
    # ONLY if the rectangle spans a "feature of interest".

    def __createQuadrants__(self):
        quadrants = dict()
        quadrants[0] = np.array([[self.rect[0], self.rect[1]], 
                                [(self.rect[2] + self.rect[0]) / 2,self.rect[1]],
                                [(self.rect[2] + self.rect[0]) / 2, (self.rect[3] + self.rect[1]) / 2],
                                [self.rect[0],(self.rect[3] + self.rect[1]) / 2],
                                [self.rect[0], self.rect[1]]])


        quadrants[1] = np.array([[(self.rect[2] + self.rect[0]) / 2, self.rect[1]], 
                                  [self.rect[2],self.rect[1]],    
                                 [self.rect[2], (self.rect[3] + self.rect[1]) / 2],
                                 [(self.rect[2] + self.rect[0]) / 2,(self.rect[3] + self.rect[1]) / 2],
                                 [(self.rect[2] + self.rect[0]) / 2, self.rect[1]]])


        quadrants[2] = np.array([[(self.rect[2] + self.rect[0]) / 2, (self.rect[3] + self.rect[1]) / 2], 
                                [self.rect[2],(self.rect[3] + self.rect[1]) / 2],
                                [self.rect[2], self.rect[3]],
                                [(self.rect[2] + self.rect[0]) / 2,self.rect[3]],
                                [(self.rect[2] + self.rect[0]) / 2, (self.rect[3] + self.rect[1]) / 2]])


        quadrants[3] = np.array([[self.rect[0], (self.rect[3] + self.rect[1]) / 2], 
                                [(self.rect[2] + self.rect[0]) / 2, (self.rect[3] + self.rect[1]) / 2],
                                [(self.rect[2] + self.rect[0]) / 2, self.rect[3]],
                                [self.rect[0],self.rect[3]],
                                [self.rect[0], (self.rect[3] + self.rect[1]) / 2]])
        return quadrants

    def quardToRect(self, quadrant):
        return [quadrant[0][0], quadrant[0][1], quadrant[2][0], quadrant[2][1]]

    def constructQuadtree(self):
        quadrants = self.__createQuadrants__()
        # print "Self Quad :", self.rect
        # if self.rect[2]-self.rect[0] != self.rect[3] - self.rect[1]:
        #     print "quad 0", quadrants[0]
        #     print "quad 1", quadrants[1]
        #     print "quad 2", quadrants[2]
        #     print "quad 3", quadrants[3]
        
        lakesQuad = dict()
        lakesQuad[0] = []
        lakesQuad[1] = []
        lakesQuad[2] = []
        lakesQuad[3] = []

        for lakeid in self.lakes:
            try :
                if pair_overlapping(lakesDict[lakeid], quadrants[0]) > 0:
                    lakesQuad[0].append(lakeid)
                if pair_overlapping(lakesDict[lakeid], quadrants[1]) > 0:
                    lakesQuad[1].append(lakeid)
                if pair_overlapping(lakesDict[lakeid], quadrants[2]) > 0:
                    lakesQuad[2].append(lakeid)
                if pair_overlapping(lakesDict[lakeid], quadrants[3]) > 0:
                    lakesQuad[3].append(lakeid)
            except TypeError :
                print lakeid
                pass
        print self.depth
        #print self.quardToRect(quadrants[0])
        self.children[0] = Node(self,lakesQuad[0],self.quardToRect(quadrants[0]))
        self.children[1] = Node(self,lakesQuad[1],self.quardToRect(quadrants[1]))
        self.children[2] = Node(self,lakesQuad[2],self.quardToRect(quadrants[2]))
        self.children[3] = Node(self,lakesQuad[3],self.quardToRect(quadrants[3]))


def lakesBoundingRectangle(lakes):
    values = dict()
    values["max-x"] = 0
    values["max-y"] = 0
    values["min-x"] = None
    values["min-y"] = None

    for lid in lakes:
        for v in lakes[lid]:
            if v[0] > values["max-x"]:
                values["max-x"] = v[0]
            if v[1] > values["max-y"]:
                values["max-y"] = v[1]
            if values["min-x"] == None or v[0] < values["min-x"]:
                values["min-x"] = v[0]
            if values["min-y"] == None or v[1] < values["min-y"]:
                values["min-y"] = v[1]

    values["max-x"] = 2 ** (math.ceil(math.log(values["max-x"], 2)))
    values["max-y"] = 2 ** (math.ceil(math.log(values["max-y"], 2)))
    values["min-x"] = 0
    values["min-y"] = 0
    return values


def readLakes(filename):
    lines = [line.strip() for line in open(filename)]
    lakes = dict()
    for i in lines:
        lake_id = int(i.split("  ")[0])
        data = [int(i) for i in i.split("  ")[1].split(" ")]
        lakes[lake_id] = zip(data[::2], data[1::2])
        lakes[lake_id] = np.array([list(pts) for pts in lakes[lake_id]])
    return lakes

def rectToQuad(rect):
    return np.array([[rect[0],rect[1]], [rect[2],rect[1]], [rect[2], rect[3]], [rect[0],rect[3]], [rect[0],rect[1]]])

def samplingLakes(node, region):
    nodePolygon = rectToQuad(node.rect)
    lakeSet = set()
    if pair_overlapping(nodePolygon,region):
        if node.type == Node.LEAF:
            try:
                return set([node.lakes[0]])
            except IndexError:
                return set()
        else:
            lakeSet = lakeSet.union(samplingLakes(node.children[0],region))
            lakeSet = lakeSet.union(samplingLakes(node.children[1],region))
            lakeSet = lakeSet.union(samplingLakes(node.children[2],region))
            lakeSet = lakeSet.union(samplingLakes(node.children[3],region))
            return lakeSet
    else:
        return set()

def queryLakes(node,region):
    lakes = samplingLakes(node,region)
    output = set()
    for lakeid in lakes:
        if pair_overlapping(lakesDict[lakeid],region):
            output.add(lakeid)
    return output

def bruteForce(region):
    output = set()
    for lakeid in lakesDict:
        try :
            if pair_overlapping(lakesDict[lakeid],region):
                output.add(lakeid)
        except :
            pass
    return output

def wrapper(func, *args, **kwargs):
    def wrapped():
        return func(*args, **kwargs)
    return wrapped

def timeSearch(root,region,times=100):
    wrapped = wrapper(queryLakes, root, region)
    print "time for Quad-Tree search : ", timeit.timeit(wrapped, number=times)
    wrapped = wrapper(bruteForce, region)
    print "time for Brute force search : ", timeit.timeit(wrapped, number=times)
    return None

if __name__ == "__main__":
    filename = "../MN_LAKES_400.txt"
    global ax,fig
    global lakesDict, countLeaf

    lakesDict = dict()
    lakesDict = readLakes(filename)
    values = lakesBoundingRectangle(lakesDict)
    rect = [values["min-x"], values["min-y"], values["max-x"], values["max-y"]]


    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    ax.axis((values["min-x"], values["max-x"], values["min-y"], values["max-y"]))
    fig.suptitle('Quad-Tree Example', fontsize=18)
    countLeaf=0

    root = Node(None, lakesDict.keys(), rect)    
    #plt.show()
    region = rectToQuad([200000,200000,400000,400000])
    lakes = queryLakes(root,region)
    print "QuadTree search: ", lakes
    lakes1 = bruteForce(region)
    print "Brute force search ", lakes1
    #timeSearch(root,region)