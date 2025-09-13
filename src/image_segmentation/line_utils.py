import numpy as np


def dist(p1, p2):
    """Returns vector distance between two points."""
    return np.sum(np.subtract(p2, p1) ** 2) ** 0.5


def slope(p1, p2):
    """Returns the slope between the two points. Returns 999 instead of inf."""
    dy, dx = (p1[1] - p2[1]), (p1[0] - p2[0])
    # If line is vertical, return 999 instead of np.inf
    if dx == 0:
        return 999
    # Otherwise, calculate the slope
    else:
        return dy / dx


def line_eqn(p1, p2):
    """Returns the slope and y-intercept of the line defined by the two points."""
    (x1, y1), (x2, y2) = p1, p2
    # Handle vertical line
    if x1 == x2:
        return np.inf, np.nan
    # Calculate slope and y-intercept
    m = (y2 - y1) / (x2 - x1)
    b = y1 - (m * x1)
    return m, b


def point_line_dist(x, y, p1, p2):
    """Given a point (x,y) and a line defined by points p1 and p2, returns the
    perpendicular point-line distance: d = (b + mx - y) / sqrt(1 + m^2)
    """
    # Calculate slope and y-intercept
    m, b = line_eqn(p1, p2)
    # Handle vertical line (return x displacement)
    if m == np.inf:
        return abs(p1[0] - x)
    # Return point-line distance
    return (b + (m * x) - y) / ((1 + m**2) ** 0.5)


def inter_slope_angle(m1, m2):
    """Given two line slopes, returns the acute angle between them."""
    acute_angle = np.degrees(abs(np.arctan((m1 - m2) / (1 + m1 * m2))))
    return acute_angle


def angle_between_vectors(p1, p2, q1, q2):
    """Returns the angle between two vectors defined by pairs of points (p1, p2) and (q1, q2)."""
    # Calculate vectors a and b
    a = np.array(p2) - np.array(p1)
    b = np.array(q2) - np.array(q1)
    # Calculate dot product of a and b
    dot_product = np.dot(a, b)
    # Calculate magnitudes of vectors a and b
    mag_a = np.linalg.norm(a)
    mag_b = np.linalg.norm(b)
    # Calculate cosine of the angle between vectors a and b
    cosine_angle = dot_product / (mag_a * mag_b)
    # Calculate angle in radians
    angle_rad = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    # Convert angle to degrees and return
    angle_deg = np.degrees(angle_rad)
    return angle_deg


# A Python3 program to find if 2 given line segments intersect or not


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


# Given three collinear points p, q, r, the function checks if
# point q lies on line segment 'pr'
def onSegment(p, q, r):
    if (
        (q.x <= max(p.x, r.x))
        and (q.x >= min(p.x, r.x))
        and (q.y <= max(p.y, r.y))
        and (q.y >= min(p.y, r.y))
    ):
        return True
    return False


def orientation(p, q, r):
    # to find the orientation of an ordered triplet (p,q,r)
    # function returns the following values:
    # 0 : Collinear points
    # 1 : Clockwise points
    # 2 : Counterclockwise

    # See https://www.geeksforgeeks.org/orientation-3-ordered-points/amp/
    # for details of below formula.

    val = (float(q.y - p.y) * (r.x - q.x)) - (float(q.x - p.x) * (r.y - q.y))
    if val > 0:

        # Clockwise orientation
        return 1
    elif val < 0:

        # Counterclockwise orientation
        return 2
    else:

        # Collinear orientation
        return 0


# The main function that returns true if
# the line segment 'p1q1' and 'p2q2' intersect.
def line_segments_intersect(p1, q1, p2, q2):

    p1 = Point(*p1)
    q1 = Point(*q1)
    p2 = Point(*p2)
    q2 = Point(*q2)
    # Find the 4 orientations required for
    # the general and special cases
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)

    # General case
    if (o1 != o2) and (o3 != o4):
        return True

    # Special Cases

    # p1 , q1 and p2 are collinear and p2 lies on segment p1q1
    if (o1 == 0) and onSegment(p1, p2, q1):
        return True

    # p1 , q1 and q2 are collinear and q2 lies on segment p1q1
    if (o2 == 0) and onSegment(p1, q2, q1):
        return True

    # p2 , q2 and p1 are collinear and p1 lies on segment p2q2
    if (o3 == 0) and onSegment(p2, p1, q2):
        return True

    # p2 , q2 and q1 are collinear and q1 lies on segment p2q2
    if (o4 == 0) and onSegment(p2, q1, q2):
        return True

    # If none of the cases
    return False
