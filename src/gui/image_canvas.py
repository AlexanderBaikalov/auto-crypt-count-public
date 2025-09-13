import tkinter as tk
import numpy as np
import cv2
from PIL import Image, ImageTk, ImageDraw

import src.parameters

MAC_OS = src.parameters.MAC_OS
CANVAS_COLOR = src.parameters.CANVAS_COLOR
TOOLBAR_COLOR = src.parameters.TOOLBAR_COLOR
CRYPT_COLOR = src.parameters.CRYPT_COLOR
FIRST_CRYPT_COLOR = src.parameters.FIRST_CRYPT_COLOR
PROBLEM_CRYPT_COLOR = src.parameters.PROBLEM_CRYPT_COLOR
PROBLEM_COORD_RADIUS = src.parameters.PROBLEM_COORD_RADIUS


def seg_to_mask(seg):
    """Given a binary labelmap segmentation .png, returns a 2D uint8 mask
    (255 or 0) for pasting onto other images.
    """
    if type(seg) == str:
        seg_arr = np.array(Image.open(seg)).astype(np.uint8)
    elif type(seg) == Image.Image:
        seg_arr = np.array(seg).astype(np.uint8)
    elif type(seg) == np.ndarray:
        seg_arr = seg.astype(np.uint8)
    return Image.fromarray(255 * seg_arr).convert("L")


class ImageCanvas:

    def __init__(self, GUI):
        """Creates a canvas on the passed GUI object and offers a method to
        display a moveable and scrollable image on that canvas.
        Adapted from https://github.com/ImagingSolution/PythonImageViewer
        """
        # Bind buttons to actions
        GUI.master.bind("<Button-1>", self.mouse_down_left)  # click
        GUI.master.bind("<B1-Motion>", self.mouse_move_left)  # drag
        GUI.master.bind("<MouseWheel>", self.mouse_wheel)  # zoom
        # Create canvas
        self.canvas = tk.Canvas(GUI.master, background=CANVAS_COLOR)
        self.canvas.pack(expand=True, fill=tk.BOTH)
        # Bind double click, hover, and right click only to canvas.
        self.canvas.bind("<Double-Button-1>", self.mouse_double_click_left)
        self.canvas.bind("<Motion>", self.mouse_hover)  # hover
        right_button = "<Button-2>" if MAC_OS else "<Button-3>"
        self.canvas.bind(right_button, self.mouse_right_click)  # right click
        self.reset_transform()
        # Set initial attributes
        self.GUI = GUI
        self.outlines = []
        self.pil_image = None
        self.hover_coords_display = tk.StringVar()
        self.hover_crypt_display = tk.StringVar()

    def draw_outlines(self):
        """Draws crypt outlines of crypts larger than MIN_CRYPT_SIZE."""
        # Start by erasing existing outlines
        self.erase_outlines()
        # If outline_width is set to 0, or no crypts, return.
        if not (self.GUI.outline_width and self.GUI.crypt_data):
            return
        # Draw the borders (and the first crypt borders)
        width = self.GUI.outline_width
        contours = self.GUI.crypt_data["contours"]
        borders = np.zeros(self.GUI.crypt_data["shape"], dtype=np.uint8)
        first_borders = borders.copy()
        borders = cv2.drawContours(
            borders, contours, contourIdx=-1, color=1, thickness=width
        )
        first_borders = cv2.drawContours(
            first_borders, contours, contourIdx=0, color=1, thickness=width
        )
        # Paste the borders' masks onto the image
        self.pil_image.paste(CRYPT_COLOR, mask=seg_to_mask(borders))
        self.pil_image.paste(FIRST_CRYPT_COLOR, mask=seg_to_mask(first_borders))
        # If there are any problem crypts, highlight them
        self.draw_crypt(self.GUI.problem_crypts, color=PROBLEM_CRYPT_COLOR)
        # If there are any hover crypts, highlight them
        self.draw_crypt(self.GUI.hover_crypt_label, color=CRYPT_COLOR)
        # Reload image now with new outlines
        self.redraw_image()

    def erase_outlines(self):
        """Deletes all outlines (and crypt highlights) drawn on image."""
        # Reset image by replacing it with a copy of the original image.
        self.pil_image = self.og_image.copy()
        self.redraw_image()

    def draw_crypt(self, labels, color):
        """Draws the crypt(s) specified by the indices onto pil_image."""
        # If outline_width is set to 0, or no crypts, return.
        if not (self.GUI.outline_width and self.GUI.crypt_data):
            return
        # If no labels are given, return
        if not labels:
            return
        # Turn label(s) into a list if not already
        if not type(labels) == list:
            labels = [labels]
        # Separate the problem crypt indices from the problem coords
        coords = [x for x in labels if type(x) == tuple]
        labels = [x for x in labels if type(x) != tuple]
        # Highlight the crypt(s) specified by the indices
        contours_to_draw = [self.GUI.crypt_data["contours"][i - 1] for i in labels]
        crypt_to_draw = np.zeros(self.GUI.crypt_data["shape"], dtype=np.uint8)
        crypt_to_draw = cv2.drawContours(
            crypt_to_draw,
            contours_to_draw,
            contourIdx=-1,
            color=1,
            thickness=cv2.FILLED,
        )
        self.pil_image.paste(color, mask=seg_to_mask(crypt_to_draw))
        # Highlight circles on the coords specified by the coords
        if coords:
            draw = ImageDraw.Draw(self.pil_image)
            for coord in coords:
                x, y = coord
                r = PROBLEM_COORD_RADIUS
                draw.ellipse(
                    (x - r, y - r, x + r, y + r),
                    outline=PROBLEM_CRYPT_COLOR,
                    width=2 * self.GUI.outline_width,
                )
        self.redraw_image()

    def mouse_right_click(self, event):
        """Adds the clicked on labeled crypt or coordto problem_crypts."""
        # If outline_width is set to 0, or no crypts, return.
        if not (self.GUI.outline_width and self.GUI.crypt_data):
            return
        # Get coords of click
        coords = self.pil_image_coords(event)
        # If click was outside image, return
        if not coords:
            return
        # Add (or remove) the crypt label (or coords) to (or from) probem_crypts
        problem_label = self.get_crypt_label(coords)
        problem_label = problem_label if problem_label else coords
        if problem_label in self.GUI.problem_crypts:
            self.GUI.problem_crypts.remove(problem_label)
        else:
            self.GUI.problem_crypts.append(problem_label)
        # Redraw the outlines
        self.draw_outlines()

    def display_image(self, filepath):
        """画像ファイルを開く"""
        if not filepath:
            return
        self.pil_image = Image.open(filepath)
        self.og_image = self.pil_image.copy()  # create a copy
        self.zoom_fit(self.pil_image.width, self.pil_image.height)
        self.draw_image(self.pil_image)

    def mouse_down_left(self, event):
        """マウスの左ボタンを押した"""
        self.__old_event = event

    def mouse_move_left(self, event):
        """マウスの左ボタンをドラッグ"""
        if self.pil_image == None:
            return
        self.translate(event.x - self.__old_event.x, event.y - self.__old_event.y)
        self.redraw_image()
        self.__old_event = event

    def mouse_double_click_left(self, event):
        """Resets image in center of screen."""
        if self.pil_image == None:
            return
        self.zoom_fit(self.pil_image.width, self.pil_image.height)
        self.redraw_image()

    def mouse_wheel(self, event):
        """マウスホイールを回した"""
        if self.pil_image == None:
            return
        if event.state != 9:
            if event.delta < 0:
                self.scale_at(1.25, event.x, event.y)
            else:
                self.scale_at(0.8, event.x, event.y)
        else:
            if event.delta < 0:
                self.rotate_at(-5, event.x, event.y)
            else:
                self.rotate_at(5, event.x, event.y)
        self.redraw_image()

    def mouse_hover(self, event):
        """Displays the crypt label of the hovered pixel (if any) and
        highlights the crypt.
        """
        # Get the image coords
        coords = self.pil_image_coords(event)
        hover_coord_str = f"Coordinates: {coords}" if coords else ""
        self.hover_coords_display.set(hover_coord_str)
        # If no pil_image or coords outside of image, return
        if not coords:
            return
        # Retrieve the currently hovered label
        hover_label = self.get_crypt_label(coords)
        # If it's not different from the current display_label, return
        if hover_label == self.GUI.hover_crypt_label:
            return
        # Otherwise, change the display label and highlight as needed
        self.GUI.hover_crypt_label = hover_label
        hover_crypt_display_str = f"Crypt Label: {hover_label}" if hover_label else ""
        self.hover_crypt_display.set(hover_crypt_display_str)
        self.draw_outlines()

    def get_crypt_label(self, coords):
        """Returns the display label of the crypt at the given coords."""
        for i, contour in enumerate(self.GUI.crypt_data["contours"]):
            # For each contour, test if coords are within it.
            result = cv2.pointPolygonTest(contour, coords, False)
            # If so, return the corresponding label (index + 1)
            if result > 0:
                return i + 1
        # Otherwise, return nothing
        return

    def pil_image_coords(self, event):
        """Given (x,y) coords of an event on the canvas, returns the coords
        of the corresponding pixel of the original pil_image if and only if
        the coords are within that image.
        """
        if self.pil_image == None:
            return
        # Invert the affine transformation matrix
        mat_inv = np.linalg.inv(self.mat_affine)
        # Transform canvas coordinates to coordinates relative to pil_image
        x, y, _ = np.dot(mat_inv, [event.x, event.y, 1])
        width, height = self.pil_image.size
        # Return nothing if coords are not within the image.
        if not ((0 < x < width) & (0 < y < height)):
            return
        # Round to nearest integer
        return (round(x), round(y))

    def reset_transform(self):
        """アフィン変換を初期化（スケール１、移動なし）に戻す"""
        self.mat_affine = np.eye(3)

    def translate(self, offset_x, offset_y):
        """平行移動"""
        mat = np.eye(3)
        mat[0, 2] = float(offset_x)
        mat[1, 2] = float(offset_y)
        self.mat_affine = np.dot(mat, self.mat_affine)

    def scale(self, scale: float):
        """拡大縮小"""
        mat = np.eye(3)
        mat[0, 0] = scale
        mat[1, 1] = scale
        self.mat_affine = np.dot(mat, self.mat_affine)

    def scale_at(self, scale: float, cx: float, cy: float):
        """座標(cx, cy)を中心に拡大縮小"""
        self.translate(-cx, -cy)
        self.scale(scale)
        self.translate(cx, cy)

    def rotate(self, deg: float):
        """回転"""
        mat = np.eye(3)
        mat[0, 0] = np.cos(np.pi * deg / 180)
        mat[1, 0] = np.sin(np.pi * deg / 180)
        mat[0, 1] = -mat[1, 0]
        mat[1, 1] = mat[0, 0]
        self.mat_affine = np.dot(mat, self.mat_affine)

    def rotate_at(self, deg: float, cx: float, cy: float):
        """座標(cx, cy)を中心に回転"""
        self.translate(-cx, -cy)
        self.rotate(deg)
        self.translate(cx, cy)

    def zoom_fit(self, image_width, image_height):
        """画像をウィジェット全体に表示させる"""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if (image_width * image_height <= 0) or (canvas_width * canvas_height <= 0):
            return
        self.reset_transform()
        scale = 1.0
        offsetx = 0.0
        offsety = 0.0
        if (canvas_width * image_height) > (image_width * canvas_height):
            scale = canvas_height / image_height
            offsetx = (canvas_width - image_width * scale) / 2
        else:
            scale = canvas_width / image_width
            offsety = (canvas_height - image_height * scale) / 2
        self.scale(scale)
        self.translate(offsetx, offsety)

    def draw_image(self, pil_image):
        if pil_image == None:
            return
        self.pil_image = pil_image
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        mat_inv = np.linalg.inv(self.mat_affine)
        # numpy array
        affine_inv = (
            mat_inv[0, 0],
            mat_inv[0, 1],
            mat_inv[0, 2],
            mat_inv[1, 0],
            mat_inv[1, 1],
            mat_inv[1, 2],
        )
        # PIL
        dst = self.pil_image.transform(
            (canvas_width, canvas_height), Image.AFFINE, affine_inv, Image.NEAREST
        )
        im = ImageTk.PhotoImage(image=dst)
        self.canvas.create_image(0, 0, anchor="nw", image=im)
        self.image = im

    def redraw_image(self):
        """画像の再描画"""
        if self.pil_image == None:
            return
        self.draw_image(self.pil_image)
