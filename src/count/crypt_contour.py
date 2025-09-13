from PIL import Image
import numpy as np
import cv2
from matplotlib import pyplot as plt
from pathlib import Path
import logging

import src.parameters
from src.image_segmentation.utils import plot_labelmap
from src.image_segmentation.line_utils import (
    dist,
    slope,
    line_eqn,
    point_line_dist,
    inter_slope_angle,
    angle_between_vectors,
    line_segments_intersect,
)

logger = logging.getLogger(__name__)


MIN_CRYPT_SIZE = src.parameters.MIN_CRYPT_SIZE
DEFECT_THRESHOLD = src.parameters.DEFECT_THRESHOLD

logger.debug(
    f"Module loaded with MIN_CRYPT_SIZE={MIN_CRYPT_SIZE}, DEFECT_THRESHOLD={DEFECT_THRESHOLD}"
)


class CryptContour:

    def __init__(
        self,
        cv2_contour,
        defect_thresh=DEFECT_THRESHOLD,
        min_crypt_size=MIN_CRYPT_SIZE,
    ):
        """Class to analyze a cv2 contour object of a crypt."""
        self.defect_threshold = defect_thresh
        self.contour = cv2_contour
        self.large_enough = cv2.contourArea(cv2_contour) >= min_crypt_size

    def defect_Coords(self, defect):
        """Returns a tuple of the (start, end, far) coords of the defect."""
        start, end, far = [tuple(self.contour[x][0]) for x in defect[:3]]
        return start, end, far

    def hull_Line_Slope(self, defect):
        """Given the cv2 defect of the contour, returns the slope of the line
        connecting the convex hull to the defect point.
        """
        start, end, _ = self.defect_Coords(defect)
        # Slope of the hull line will be perp to the line between start and end
        m_along = slope(start, end)  # slope of start-end line
        # Return negative reciprocal unless start-end is horizontal, return 999
        return -1 / m_along if m_along != 0 else 999

    def hull_Intersection(self, defect):
        """Returns the coordinate where the hull-line intersects the hull."""
        start, end, far = self.defect_Coords(defect)
        # Get m, b of hull line
        m_hull = self.hull_Line_Slope(defect)
        b_hull = far[1] - m_hull * far[0]
        # Get m, b of start-end line (along-hull-line) segment
        m_along = slope(start, end)
        b_along = end[1] - m_along * end[0]
        # Get intersection coord.
        x_int = (b_hull - b_along) / (m_along - m_hull)
        y_int = m_hull * x_int + b_hull
        return (x_int, y_int)

    def linear_Fit(self):
        """Returns the m, b of an y=mx+b fit through interior mass of contour."""
        vx, vy, x, y = cv2.fitLine(self.contour, cv2.DIST_L2, 0, 0.01, 0.01)
        m = vy / vx
        b = y - m * x
        return m[0], b[0]

    def intercepts_from_line_eqn(self, m, b):
        """Returns the intercepts of the line y=mx+b going through the contour."""
        # Get the bounding box
        x, y, width, height = cv2.boundingRect(self.contour)
        # Get the coords of the line going through that bounding box
        # Handle vertical lines
        if m >= 999:
            p1, p2 = (int(x + width / 2), y), (int(x + width / 2), y + height)
        # Handle non-vertical lines
        else:
            p1, p2 = (x, int(m * x + b)), (x + width, int((m * (x + width)) + b))
        # Get the coords at the line intersection with the contour.
        intersection_coords = line_contour_intersects(p1, p2, self.contour)
        return intersection_coords

    @property
    def hull(self):
        """Returns the convex hull."""
        if hasattr(self, "_hull"):
            return self._hull
        hull = cv2.convexHull(self.contour, returnPoints=False)
        self._hull = hull
        return hull

    @property
    def hull_points(self):
        """Returns the convex hull points."""
        if hasattr(self, "_hull_points"):
            return self._hull
        hull_points = cv2.convexHull(self.contour, returnPoints=True)
        self._hull_points = hull_points
        return hull_points

    @property
    def separated_contours(self):
        """Returns a list of separated contours using defect_threshold, each
        greater in size than min_crypt_size. Returns empty list if none.
        """
        # Return attribute if already has been retrieved.
        if hasattr(self, "_separated_contours"):
            return self._separated_contours
        # At first, contours just contains self's contours
        contours = [self.contour]
        fully_split_contours = []
        # Loop through and split each contour recursively
        for contour in contours:
            split_contours = CryptContour(contour).split()
            # If it can be split, extend contours with the split contours.
            if split_contours:
                contours.extend(split_contours)
            # Otherwise, add this contour to fully_split_contours if large enough.
            else:
                if CryptContour(contour).large_enough:
                    fully_split_contours.append(contour)
        # Set as attribute so it doesn't have to be retrieved again
        self._separated_contours = fully_split_contours
        return fully_split_contours

    @property
    def defects(self):
        """Returns defects above the depth threshold."""
        # Return attribute if already has been retrieved.
        if hasattr(self, "_defects"):
            return self._defects
        # Get defects -- if it fails (usually due to self-intersecting contour)
        #  return None
        try:
            defects = cv2.convexityDefects(self.contour, self.hull)
        except Exception as e:
            print(f"\nError finding defects on contour: {e}\n")
            return
        # Return if there are no defects
        if defects is None:
            return
        # Filter above depth threshold
        defects = defects[defects[:, :, 3] > 256 * self.defect_threshold]
        # Return if there are no defects
        if len(defects) == 0:
            return
        # Set as attribute so it doesn't have to be retrieved again
        self._defects = defects
        return defects

    def split(self):
        """Returns a list of the current contour split into 2. Returns None
         if unable to split.

        If there is only 1 defect, separates the contour by the line that
         connects that defect to the convex hull, but only if that line happens
         to be more parallel than perpendicular to the line through the mass of
         the blob. That way we avoid splitting a curved crypt in half.

        If there are 2 or more defects, separates along the pair of defects
        that has the most parallel hull-defect and defect-defect lines.
        """
        # If self is not large enough or there are no defects, return.
        if not self.large_enough or self.defects is None:
            return

        # If there is only 1 defect, separate by the hull line
        if len(self.defects) == 1:
            _, _, far = self.defect_Coords(self.defects[0])
            m = self.hull_Line_Slope(self.defects[0])
            # Break if the slope of the hull line is perp to the mass-fit line.
            m_fit, _ = self.linear_Fit()
            if inter_slope_angle(m, m_fit) >= 45:
                return
            # get y-intercept by knowing the line goes through far
            b = far[1] - m * far[0]
            # Get the coords at this line's intersection with the contour.
            sep_coords = self.intercepts_from_line_eqn(m, b)

        # If there are only 2 defects, separate by the connecting line.
        elif len(self.defects) == 2:
            sep_coords = tuple(self.defect_Coords(defect)[2] for defect in self.defects)
            # Unless the crypt has a waist and this is splitting it in half. To check,
            # See if the split line is perpendicular to the mass-fit line
            m_fit, b_fit = self.linear_Fit()
            m, b = line_eqn(*sep_coords)
            if inter_slope_angle(m, m_fit) >= 45:
                # If so, see if the crypt is very oblong
                # Find the minimum area rectangle that bounds the convex hull
                rect = cv2.minAreaRect(self.hull_points)
                length, width = rect[1][1], rect[1][0]
                # Do not split if it is indeed oblong
                if length > 2 * width:
                    return None

        # Separate if there are 3 or more
        elif len(self.defects) >= 3:
            # Start with no separation coords and a large (bad) best score
            sep_coords = None
            best_score = np.inf
            for defect in self.defects:
                # Get defect's hull line intersection coords and far coords
                hull_int = self.hull_Intersection(defect)
                far = self.defect_Coords(defect)[2]
                # Loop through every other defect
                for other_defect in self.defects:
                    # Except skip if other defect is the same defect
                    if np.array_equal(defect, other_defect):
                        continue
                    # Get other_defect's hull line intersection coords and far coords
                    other_hull_int = self.hull_Intersection(other_defect)
                    other_far = self.defect_Coords(other_defect)[2]
                    # Use parallelity measure to get score
                    score = score_parralelity(hull_int, far, other_hull_int, other_far)
                    # Quick check -- if the distance between both defects is
                    #  less than 3 (pinched connection), they belong together, use them
                    if dist(far, other_far) < 3:
                        score = 0
                    # Last check, if split line would intersect contour, don't use it
                    elif len(line_contour_intersects(far, other_far, self.contour)) > 2:
                        score = np.inf
                    # Replace if it's better than the last
                    if score < best_score:
                        best_score = score
                        sep_coords = (far, other_far)
            # If after all this no sep_coords were found, no split so return.
            if sep_coords is None:
                return

        # If there are not two sep_coords, don't split
        if not len(sep_coords) == 2:
            return
        # Split the contour at the found separation coords
        split_contours = split_contour(self.contour, sep_coords)
        # Only return if both split contours are large enough
        if all([CryptContour(c).large_enough for c in split_contours]):
            return split_contours
        else:
            return

    def plot(self, show_all=False, img_fp=None, pad=10):
        """Plots the contour with or without its defects, separated contours,
        and corresponding image (fp must be given).
        """
        # Have to work with a copy to avoid the original being modified
        contour = self.contour.copy()
        x, y, width, height = cv2.boundingRect(contour)
        # Translate contour so it starts at (0,0)
        contour[:, :, 0] -= x
        contour[:, :, 1] -= y
        # Make array of contour
        contour_arr = np.zeros(shape=(height, width))
        contour_arr = cv2.drawContours(contour_arr, [contour], -1, 1, 1)
        # Plot just the contour if desired
        if not show_all:
            plot_labelmap(np.pad(contour_arr, 10), title="Contour")
            return
        # Add the translated hull (val=2) to contour_arr
        hull = self.hull_points.copy()
        hull[:, :, 0] -= x
        hull[:, :, 1] -= y
        contour_arr = cv2.drawContours(contour_arr, [hull], -1, 2, 1)
        # Add the defects (val=3) to contour_arr
        defects = self.defects if self.defects is not None else []
        for defect in defects:
            def_x, def_y = self.defect_Coords(defect)[2]
            def_x, def_y = def_x - x, def_y - y  # translate
            contour_arr[def_y - 1 : def_y + 2, def_x - 1 : def_x + 2] = (
                3  # 3x3 box around defect
            )
        # Get the separated contours array
        sep_cont_arr = np.zeros(shape=(height, width))
        for i, cont in enumerate(self.separated_contours):
            cont = cont.copy()
            cont[:, :, 0] -= x
            cont[:, :, 1] -= y
            sep_cont_arr = cv2.drawContours(sep_cont_arr, [cont], -1, i + 1, 1)
        # Plot with or without img
        if img_fp:
            fig, axes = plt.subplots(ncols=3, dpi=200)
            ax1, ax2, ax3 = axes
        if not img_fp:
            fig, axes = plt.subplots(ncols=2, dpi=200)
            ax1, ax2 = axes
        title1 = f"{len(defects)} Defects"
        plot_labelmap(np.pad(contour_arr, 10), title=title1, ax=ax1)
        title2 = f"{len(self.separated_contours)} Contours"
        plot_labelmap(np.pad(sep_cont_arr, 10), title=title2, ax=ax2)
        if not img_fp:
            return
        # Crop img
        box = (x - pad, y - pad, x + width + pad, y + height + pad)
        blob_img = Image.open(img_fp).crop(box)
        title3 = "Image"
        plot_labelmap(blob_img, title=title3, ax=ax3)
        return fig


def score_parralelity(hull_int, far, other_hull_int, other_far):
    """Given the coordinates of two defects' hull intersections and points,
    returns a score of their parallelity, which is the sum of the deviations
    of the line angles from what they should ideally be.
    """
    # Get the angles between the hull-lines, and between each
    #  hull line and the defect-defect-line.
    hulls_angle = angle_between_vectors(hull_int, far, other_hull_int, other_far)
    hull_dd_angle = angle_between_vectors(hull_int, far, far, other_far)
    other_hull_dd_angle = angle_between_vectors(
        other_hull_int, other_far, far, other_far
    )
    # Get the deviations of these angles from what they should be
    #  (180 for the hulls_angle, either 0 or 180 for the other 2)
    hulls_dev = 180 - np.abs(hulls_angle)
    hull_dd_dev = min(180 - np.abs(hull_dd_angle), np.abs(hull_dd_angle))
    other_hull_dd_dev = min(
        180 - np.abs(other_hull_dd_angle), np.abs(other_hull_dd_angle)
    )
    # If any of these are too perpendicular, give them infinitely bad score
    if any(dev > 90 for dev in [hulls_dev, hull_dd_dev, other_hull_dd_dev]):
        return np.inf
    # Otherwise calculate the parallel score.
    score = sum([hulls_dev, hull_dd_dev, other_hull_dd_dev])
    return score


def closest_coord(coord, contour):
    """Given an (x,y) coord and a cv2 contour, returns the closest contour
    point to that coord.
    """
    x, y = coord
    # Calculate distances from the given point to each contour point
    distances = np.sqrt((contour[:, 0, 0] - x) ** 2 + (contour[:, 0, 1] - y) ** 2)
    # Find the index of the contour point with the minimum distance
    min_index = np.argmin(distances)
    # Extract the closest contour point
    closest_point = contour[min_index][0]
    return closest_point


def line_contour_intersects(p1, p2, contour):
    """Returns all the intersects of the line segment defined by p1 and p2 with contour."""
    # Collect unique (not neighbouring and not extreme line points) intersection points
    contour_coords = contour[:, 0, :]  # transform into simple array of coordinates
    intersection_coords = []
    for i in range(len(contour_coords) - 1):
        # Get each pair of contour points
        c1, c2 = contour_coords[i], contour_coords[i + 1]
        # If the line segment intersects the line segment between these contour points,
        if line_segments_intersect(p1, p2, c1, c2):
            # get the closest coordinate to the intersection
            if point_line_dist(*c1, p1, p2) <= point_line_dist(*c2, p1, p2):
                coord = c1
            else:
                coord = c2
            # Break if this intersection point is a neighbour of the last
            if intersection_coords and dist(intersection_coords[-1], coord) <= 2:
                continue
            # Otherwise, append coord to intersection_coords
            else:
                intersection_coords.append(coord)
    return intersection_coords


def split_contour(contour, separation_coords):
    """Given two coords on the contour, returns two contours split along the
    line between those two cooords.
    """
    coord1, coord2 = separation_coords
    x1, y1 = coord1
    x2, y2 = coord2
    idx1 = np.where((contour[:, 0, 0] == x1) & (contour[:, 0, 1] == y1))[0][0]
    idx2 = np.where((contour[:, 0, 0] == x2) & (contour[:, 0, 1] == y2))[0][0]
    # Determine the direction of traversal along the contour
    if idx1 < idx2:
        contour1 = contour[idx1 : idx2 + 1]
        contour2 = np.concatenate((contour[idx2:], contour[: idx1 + 1]))
    else:
        contour1 = contour[idx2 : idx1 + 1]
        contour2 = np.concatenate((contour[idx1:], contour[: idx2 + 1]))
    # Now that both separate contours have been attained, take the contour
    #  of the filled contour to ensure no self-intersection.
    contours = []
    for contour in [contour1, contour2]:
        x, y, width, height = cv2.boundingRect(contour)
        arr = np.zeros(shape=(y + height, x + width), dtype=np.uint8)
        arr = cv2.drawContours(arr, [contour], -1, 1, cv2.FILLED)
        contours.append(
            cv2.findContours(arr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0][0]
        )
    return contours


def get_all_separated_contours(
    seg_fp, img_fp=None, plot=True, plot_all=True, output_dir=None
):
    """Given a segmentation fp, returns a list of all separated contours. This function
    is not used by CryptContour but is useful for testing CryptContour on a seg."""
    # Get segmentation array
    seg_arr = np.array(Image.open(seg_fp).convert("L"), dtype=np.uint8)
    # Get contours (no chain approx because we need to have all the points stored to split contours)
    unseparated_contours, _ = cv2.findContours(
        seg_arr.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )
    # Get all separated contours
    contours = []
    for i, c in enumerate(unseparated_contours):
        crypt_contour = CryptContour(c)
        contours.extend(crypt_contour.separated_contours)
        # Plot if large enough to count
        if plot_all and crypt_contour.large_enough:
            fig = crypt_contour.plot(show_all=True, img_fp=img_fp)
            if output_dir:
                fig.savefig(
                    Path(output_dir, f"contour_{i + 1}.png"), dpi=100
                )  # Save with specified DPI
                plt.close(fig)  # Close the figure to avoid displaying it
    # Plot the entire seg_arr
    if plot:
        fig, axes = plt.subplots(ncols=2, dpi=200)
        ax1, ax2 = axes
        raw_arr = cv2.drawContours(
            np.zeros_like(seg_arr, dtype=np.uint8), unseparated_contours, -1, 1, 1
        )
        sep_arr = cv2.drawContours(
            np.zeros_like(seg_arr, dtype=np.uint8), contours, -1, 1, 1
        )
        plot_labelmap(raw_arr, title="Raw Contours", ax=ax1)
        plot_labelmap(sep_arr, title="Separated Contours", ax=ax2)
        if output_dir:
            fig.savefig(Path(output_dir, f"contours.png"), dpi=200)
            plt.close(fig)  # Close the figure to avoid displaying it
    return contours
