import numpy as np


class Point:
    def __init__(self, x, y):
        self.x = float(x) if x is not None else None
        self.y = float(y) if y is not None else None

    def set(self, x, y):
        self.x = float(x) if x is not None else None
        self.y = float(y) if y is not None else None

    def x(self):
        return self.x

    def y(self):
        return self.y
        
    def tuppleize(self):
        return (self.x, self.y)


class PolyLine:
    
    def __init__(self):
        self.points = None
        self.xs = None
        self.ys = None
        self.xsSortedByY = None
        self.ysSortedByY = None
        self._min_x = None
        self._max_x = None
        self._min_y = None
        self._max_y = None

    def add(self, point):
        if self.points is None:
            self.points = []
        if len(self.points) > 0:
            for p in reversed(self.points):
                if p.x == point.x and p.y == point.y:
                    return
        doSort = False
        #if len(self.points) > 0 and point.y < self.points[-1].y:
        if len(self.points) > 0 and point.x < self.points[-1].x:
            doSort = True
            
        self.points.append(point)
        if doSort:
            #self.points = sorted(self.points, key=Point.y) # should sort by xs? screws things up if we do...
            self.points = sorted(self.points, key=Point.x)
        self.xs = None
        self.ys = None
        if point.x is not None and point.y is not None:
            self._min_x = PolyLine.min(self._min_x, point.x)
            self._min_y = PolyLine.min(self._min_y, point.y)
            self._max_x = PolyLine.max(self._max_x, point.x)
            self._max_y = PolyLine.max(self._max_y, point.y)
        
    @staticmethod
    def min(x1, x2):
        if x1 is None:
            return x2
        if x2 is None:
            return x1
        return min(x1, x2)
    
    @staticmethod
    def max(x1, x2):
        if x1 is None:
            return x2
        if x2 is None:
            return x1
        return max(x1, x2)
    
    @staticmethod
    def sum(x1, x2):
        if x1 is None:
            return x2
        if x2 is None:
            return x1
        return x1 + x2

    def x(self, y, left=None, right=None):
        if self.points == None:
            return None
        if y is None:
            return None
        self.vectorize()
        #return np.interp(y, self.ys, self.xs) #, right=0.) .. we learned that this gave weird results previously
        #ascending = self.ys[0]<self.ys[-1]
        #ys = self.ys if ascending else self.ys[::-1]
        #xs = self.xs if ascending else self.xs[::-1]
        r = np.interp(y, self.ysSortedByY, self.xsSortedByY, left=left, right=right)
        return None if np.isnan(r) else r

    def y(self, x, left=None, right=None):
        if self.points == None:
            return None
        if x is None:
            return None
        self.vectorize()
        #return np.interp(x, self.xs, self.ys) # this probably doesn't work b/c the xs are not neccesarily in the right order...
        #ascending = self.xs[0]<self.xs[-1]
        #ys = self.ys if ascending else self.ys[::-1]
        #xs = self.xs if ascending else self.xs[::-1]
        r = np.interp(x, self.xs, self.ys, left=left, right=right)
        return None if np.isnan(r) else r
 
        
    # probably replace w/ zip()
    def vectorize(self):
        if self.points == None:
            return None, None
        if (self.xs == None or self.ys == None):
            xs = [None] * len(self.points)
            ys = [None] * len(self.points)
            c = 0
            for p in self.points:
                xs[c] = p.x
                ys[c] = p.y
                c += 1
            self.xs = xs
            self.ys = ys
            if self.ys[0]<self.ys[-1]:
                self.xsSortedByY = self.xs
                self.ysSortedByY = self.ys
            else:
                self.xsSortedByY = self.xs[::-1]
                self.ysSortedByY = self.ys[::-1]
        return self.xs, self.ys
       
        
    def tuppleize(self):
        if self.points == None:
            return None
        ps = [None] * len(self.points)
        c = 0
        for p in self.points:
            ps[c] = p.tuppleize()
            c += 1
        return ps


    def clear(self):
        self.points = None
        self.xs = None
        self.ys = None
        self.xsSortedByY = None
        self.ysSortedByY = None
        self._min_x = None
        self._max_x = None
        self._min_y = None
        self._max_y = None


    def min_y(self):
        return self._min_y


    def max_y(self):
        return self._max_y
    
    
    def min_x(self):
        return self._min_x


    def max_x(self):
        return self._max_x
    
    
    @staticmethod
    def determinant(point1, point2):
        return point1[0] * point2[1] - point1[1] * point2[0]
    
    
    @staticmethod
    def segment_intersection(line1, line2):
        xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
        ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])
        div = PolyLine.determinant(xdiff, ydiff)
        if div == 0:
            return None
        d = (PolyLine.determinant(*line1), PolyLine.determinant(*line2))
        x = PolyLine.determinant(d, xdiff) / div
        y = PolyLine.determinant(d, ydiff) / div
        return x, y
    
    
    @staticmethod
    def ccw(p1, p2, p3):
        return (p3[1]-p1[1])*(p2[0]-p1[0]) > (p2[1]-p1[1])*(p3[0]-p1[0])
    
    
    @staticmethod
    def segment_intersects(l1, l2):
        if l1[0][0] is None or l1[0][1] is None or  l1[1][0] is None or l1[1][1] is None:
            return None
        if l2[0][0] is None or l2[0][1] is None or  l2[1][0] is None or l2[1][1] is None:
            return None
        if (PolyLine.ccw(l1[0], l2[0], l2[1]) != PolyLine.ccw(l1[1], l2[0], l2[1]) 
            and PolyLine.ccw(l1[0], l1[1], l2[0]) != PolyLine.ccw(l1[0], l1[1], l2[1])):
            return True
        if (l1[0][0] == l2[0][0] and l1[0][1] == l2[0][1]) or (l1[0][0] == l2[1][0] and l1[0][1] == l2[1][1]):
            return True
        if (l1[1][0] == l2[0][0] and l1[1][1] == l2[0][1]) or (l1[1][0] == l2[1][0] and l1[1][1] == l2[1][1]):
            return True
        
        
    @staticmethod
    def between(a, b, c):
        if (a[0] is None or a[1] is None or b[0] is None or b[1] is None or c[0] is None or c[1] is None):
            return None
        crossproduct = (c[1] - a[1]) * (b[0] - a[0]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(crossproduct) > 1e-12:
            return False
        dotproduct = (c[0] - a[0]) * (b[0] - a[0]) + (c[1] - a[1])*(b[1] - a[1])
        if dotproduct < 0:
            return False
        squaredlengthba = (b[0] - a[0])*(b[0] - a[0]) + (b[1] - a[1])*(b[1] - a[1])
        if dotproduct > squaredlengthba:
            return False
        return True
    
    
    @staticmethod 
    def intersection(pl_1, pl_2):
        
        # we have two points
        if len(pl_1) == 1 and len(pl_2) == 1:
            if pl_1[0][0] == pl_2[0][0] and pl_1[0][1] == pl_2[0][1]:
                return pl_1[0][0], pl_1[0][1]
            
        # we have one point and line segments
        elif len(pl_1) == 1 or len(pl_2) == 1:
            if len(pl_1) == 1:
                point = pl_1[0]
                line = pl_2
            else:
                point = pl_2[0]
                line = pl_1
            for j, pl_2_1 in enumerate(line[:-1]):
                    pl_2_2 = line[j + 1]
                    if PolyLine.between(pl_2_1, pl_2_2, point):
                        return point[0], point[1]
        
        # we have line segments
        elif len(pl_1) > 1 and len(pl_2) > 1:
            for i, pl_1_1 in enumerate(pl_1[:-1]):
                pl_1_2 = pl_1[i + 1]
                for j, pl_2_1 in enumerate(pl_2[:-1]):
                    pl_2_2 = pl_2[j + 1]
                    if PolyLine.segment_intersects((pl_1_1, pl_1_2), (pl_2_1, pl_2_2)):
                        return PolyLine.segment_intersection((pl_1_1, pl_1_2), (pl_2_1, pl_2_2))
        
        return None, None
        
class PolyLineFactory(object):
    
    @staticmethod
    def combine(lines, increment):
    
        # we return a new PolyLine which is a composite (summed horizontally) of inputs
        composite = PolyLine()
    
        # find the range defined by the curves
        minY = None
        maxY = None
        for l in lines:
            minY = PolyLine.min(minY, l.min_y())
            maxY = PolyLine.max(maxY, l.max_y())
            
        # special case if the lines are already horizontal or None
        if minY == maxY:
            minSumX = None
            maxSumX = None
            for line in lines:
                minX = None
                maxX = None
                for point in line.points:
                    minX = PolyLine.min(minX, point.x)
                    maxX = PolyLine.max(maxX, point.x)
                minSumX = PolyLine.sum(minSumX, minX)
                maxSumX = PolyLine.sum(maxSumX, maxX)
            composite.add(Point(minSumX, minY))
            if minX != maxX:
                composite.add(Point(maxSumX, maxY))
            return composite

        # create an array of ys in equal increments, with highest first
        # this is assuming that price decreases with increase in demand (buyers!)
        # but seems to work with multiple suppliers?
        ys = sorted(np.linspace(minY, maxY, num=increment), reverse=True)
        #print ys
        #print minY, maxY

        # now find the cumulative x associated with each y in the array
        # starting with the highest y
        for y in ys:
            xt = None
            for line in lines:
#                x = line.x(y, left=np.nan)
                x = line.x(y)
                #print x, y
                if x is not None:
                    xt = x if xt is None else xt + x
            composite.add(Point(xt, y))

        return composite
    
    @staticmethod
    def fromTupples(points):
        polyLine = PolyLine()
        for p in points:
            if p is not None and len(p) == 2:
                polyLine.add(Point(p[0], p[1]))
        return polyLine
    
    