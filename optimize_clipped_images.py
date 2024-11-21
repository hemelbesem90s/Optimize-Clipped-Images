import inkex
import datetime
import subprocess
from lxml import etree
import copy
import os
import tkinter as tk  # Import tkinter
from tkinter import ttk, messagebox  # Import ttk and messagebox
from base64 import encodebytes
import urllib.parse as urlparse  # Import urlparse
import urllib.request as urllib  # Import urllib
from PIL import Image  # Import the Image module from Pillow
import numpy as np  # Import numpy for matrix operations

class OptimizeClippedImages(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)
        self.log_file = 'extension_log.txt'
        self.enable_logging = True

    def effect(self):
        if self.enable_logging:
            with open(self.log_file, 'a') as f:
                f.write(f"--- OptimizeClippedImages ---\n")
                f.write(f"{datetime.datetime.now()}\n")

        # Get target resolution from user input
        target_dpi = self.get_target_resolution()
        if target_dpi is None:
            return  # User canceled

        svg = self.document.getroot()
        images = svg.xpath('//svg:image[@clip-path]')
        total_images = len(images)
        processed_count = 0

        # Create a temporary layer
        temp_layer = etree.SubElement(svg, 'g')
        temp_layer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')
        temp_layer.set(inkex.addNS('label', 'inkscape'), 'Temporary Export Layer')
        
        # Get canvas bounding box width and height
        width, height = self.get_canvas_bounding_box()
        if width is None or height is None:
            self.print_to_log("Error: Could not get canvas bounding box dimensions.")
            return

        # Calculate safe x and y coordinates outside the canvas
        safe_x = 2*max(width, height) # Add margin
        safe_y = 2*max(width, height)  # Add margin


        for image in images:
            processed_count += 1
            self.print_to_log(f"Processing image {processed_count} of {total_images}", enable_logging=True)

            # Store original image data
            original_transform = image.get('transform')
            clip_path_id = image.get('clip-path').split('#')[1][:-1]  # Extract the ID
            clip_path = svg.find(f'.//*[@id="{clip_path_id}"]')
            
            # Find the shape within the clip path group
            clip_path_shape = clip_path.find('.//*')  # Find the first child element within the clip path
            
            #Log the values
            self.print_to_log(f"Old Transform: {original_transform}")


            # --- Export clipped image ---

            # Copy the image to the temporary layer
            image_copy = copy.copy(image)
            temp_layer.append(image_copy)

            # Get the original transform
            transform_str = image.get('transform')
            if transform_str:
                # Calculate and apply the new transform (using safe_x and safe_y)
                new_transform_str = self.calculate_transform(transform_str, safe_x, safe_y)
                image_copy.set('transform', new_transform_str)
                self.print_to_log(f"New Transform: {new_transform_str}")


            # Generate a new unique ID for the copied image
            new_image_id = self.svg.get_unique_id(image.get('id'))
            image_copy.set('id', new_image_id)

            # Apply changes to the SVG document before exporting
            self.document.write(self.options.input_file)

            # Calculate scaling factor
            bbox_image = image_copy.bounding_box()
            bbox_clip_path = clip_path_shape.bounding_box()
            scale_x = bbox_clip_path.width / bbox_image.width

            # Calculate export DPI
            export_dpi = target_dpi * scale_x  # Use target_dpi instead of fixed 96
            
            self.print_to_log(f"Calculated DPI: {export_dpi}")

            # Construct the command for subprocess (with calculated export DPI)
            temp_file_name = f"{new_image_id}.png"
            command = [
                "inkscape",
                "--export-type=png",
                f"--export-filename={temp_file_name}",
                f"--export-dpi={export_dpi}",  # Use calculated export DPI
                f"--export-id={new_image_id}",
                self.options.input_file
            ]
            
            
            try:
                subprocess.run(command, check=True)
                self.print_to_log(f"Exported image: {temp_file_name}")

                # Optimize the exported PNG using Pillow
                self.optimize_png(temp_file_name)

            except subprocess.CalledProcessError as e:
                self.print_to_log(f"Error exporting image {new_image_id}: {e}")  # Use new_image_id

            # Remove the copied image from the temporary layer
            temp_layer.remove(image_copy)

            

            # --- Re-import and position image ---
            try:
                # Get the parent layer of the original image
                parent_layer = image.getparent()

                # Create a new image element
                imported_image = etree.SubElement(parent_layer, 'image')  # Add to the parent layer
                
                # Get bounding box information of the original image
                bbox = image.bounding_box()

                # Set the x, y, width, and height attributes of the imported image
                # Set the x and y attributes of the imported image (corrected)
                imported_image.set('x', str(bbox.x.minimum))  # Extract the minimum value from BoundingInterval
                imported_image.set('y', str(bbox.y.minimum))  # Extract the minimum value from BoundingInterval
                imported_image.set('width', str(bbox.width))
                imported_image.set('height', str(bbox.height))
                
                # Set additional attributes
                imported_image.set('style', 'image-rendering:optimizeSpeed;')
                imported_image.set('preserveAspectRatio', 'none')

                # Construct the relative path to the image (using forward slashes)
                relative_path = os.path.relpath(temp_file_name, start=os.path.dirname(self.options.input_file)).replace('\\', '/')

                # Set the xlink:href attribute to the relative image path
                imported_image.set('xlink:href', relative_path)

                # Get image width and height
                #width, height = self.get_image_size(temp_file_name)

                # Get the width and height from the clip path shape
                #clip_path_width = clip_path_shape.get('width')
                #clip_path_height = clip_path_shape.get('height')

                # Set width and height attributes (from clip path shape)
                #imported_image.set('width', clip_path_width)
                #imported_image.set('height', clip_path_height)

                # Embed the image
                self.embed_image(imported_image)

                # Set the x and y attributes of the imported image
                #imported_image.set('x', clip_path_x)
                #imported_image.set('y', clip_path_y)       


                # Delete the original clipped image and its associated clip path
                parent_layer = image.getparent()
                parent_layer.remove(image)
                defs1_group = svg.find('.//*[@id="defs1"]')
                defs1_group.remove(clip_path)

                # Delete the temporary PNG file
                os.remove(temp_file_name)

                self.print_to_log(f"Imported and embedded image: {temp_file_name}")
            except Exception as e:
                self.print_to_log(f"Error importing image: {e}")
        
        # Remove the temporary layer
        svg.remove(temp_layer)
            
            
        # Update the SVG document
        self.document.write(self.options.input_file)

        if self.enable_logging:
            with open(self.log_file, 'a') as f:
                f.write('\n\n')

    def get_target_resolution(self):
        #"""Prompts the user to select the target resolution."""
        root = tk.Tk()
        root.withdraw()
        selected_dpi = tk.StringVar(value="96 dpi")  # Default value
        options = ["50 dpi", "72 dpi", "96 dpi"]
        ttk.Label(root, text="Select target resolution:\nInkscape standard is 96 dpi. ").pack(pady=5)
        dropdown = ttk.Combobox(root, textvariable=selected_dpi, values=options)
        dropdown.pack(pady=5)
        button = ttk.Button(root, text="OK", command=root.destroy)
        button.pack(pady=5)
        root.deiconify()
        root.mainloop()
        return int(selected_dpi.get().split()[0])  # Extract DPI value


    def optimize_png(self, image_path):
        """Optimizes a PNG image using Pillow."""
        try:
            with Image.open(image_path) as img:
                img.save(image_path, optimize=True)  # Optimize the image
            self.print_to_log(f"Optimized PNG: {image_path}")
        except Exception as e:
            self.print_to_log(f"Error optimizing PNG: {e}")
            
            
    def embed_image(self, node):
        """Embeds a linked image."""
        xlink = node.get("xlink:href")
        if xlink is not None and xlink[:5] == "data:":
            # No need, data already embedded
            return

        url = urlparse.urlparse(xlink)
        href = urllib.url2pathname(url.path)

        try:
            cwd = os.path.dirname(self.options.input_file)
        except TypeError:
            cwd = None

        path = self.absolute_href(href or "", cwd=cwd)

        if not os.path.isfile(path):
            path = node.get("sodipodi:absref", path)

        if not os.path.isfile(path):
            inkex.errormsg(_('File not found "{}". Unable to embed image.').format(path))
            return

        with open(path, "rb") as handle:
            file_type = self.get_type(path, handle.read(10))
            handle.seek(0)

            if file_type:
                node.set(
                    "xlink:href",
                    "data:{};base64,{}".format(
                        file_type, encodebytes(handle.read()).decode("ascii")
                    ),
                )
                node.pop("sodipodi:absref")
            else:
                inkex.errormsg(
                    _(
                        "%s is not of type image/png, image/jpeg, "
                        "image/bmp, image/gif, image/tiff, or image/x-icon"
                    )
                    % path
                )

    def get_type(self, path, header):
        """Basic magic header checker, returns mime type"""
        for head, mime in (
                (b"\x89PNG", "image/png"),
                (b"\xff\xd8", "image/jpeg"),
                (b"BM", "image/bmp"),
                (b"GIF87a", "image/gif"),
                (b"GIF89a", "image/gif"),
                (b"MM\x00\x2a", "image/tiff"),
                (b"II\x2a\x00", "image/tiff"),
        ):
            if header.startswith(head):
                return mime

        for ext, mime in (
                (".ico", "image/x-icon"),
                (".svg", "image/svg+xml"),
        ):
            if path.endswith(ext):
                return mime
        return None

    def print_to_log(self, message, enable_logging=True):
        """Prints a message to a log file."""
        if enable_logging:
            with open(self.log_file, 'a') as f:
                f.write(f"{message}\n")

    def get_image_size(self, image_path):
        """Returns the width and height of an image."""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
            return width, height
        except Exception as e:
            self.print_to_log(f"Error getting image size: {e}")
            return None, None
            
    def calculate_transform(self, transform_str, x_new, y_new):
        """Calculates the new transform matrix with the given translation."""
        try:
            # Parse the transform string and extract the matrix values
            if transform_str.startswith("matrix"):
                transform_parts = transform_str.replace("matrix(", "").replace(")", "").split()
                a, b, c, d, e, f = [float(value) for value in transform_parts]

                # Create the transformation matrix
                transform_matrix = np.array([
                    [a, c, e],
                    [b, d, f],
                    [0, 0, 1]
                ])
            else:
                # If not a matrix, assume it's a simple translate or rotate
                transform = inkex.transforms.Transform(transform_str)

                # Convert to 3x3 numpy array (corrected)
                transform_matrix = np.array([
                    [transform.a, transform.c, transform.e],
                    [transform.b, transform.d, transform.f],
                    [0, 0, 1]
                ])

            # Create the translation matrix
            translation_matrix = np.array([
                [1, 0, x_new],
                [0, 1, y_new],
                [0, 0, 1]
            ])

            # Multiply the matrices
            #new_transform_matrix = transform_matrix @ translation_matrix

            # Extract the new transform values
            #a, c, e, b, d, f = new_transform_matrix.flatten()[:6]

            # Construct the new transform string
            new_transform_str = f"matrix({a} {b} {c} {d} {e+x_new} {f+y_new})"

            return new_transform_str

        except Exception as e:
            self.print_to_log(f"Error calculating transform: {e}")
            return transform_str  # Return the original transform string on error
           

    def get_canvas_bounding_box(self):
        """
        Calculates the width and height of the bounding box of all layers on the canvas.

        Returns:
            tuple: A tuple containing the width and height of the bounding box, or None on error.
        """
        try:
            # Get all layers on the canvas
            all_layers = self.svg.xpath('//svg:g[@inkscape:groupmode="layer"]')

            # Initialize min and max values
            x_min = float('inf')
            y_min = float('inf')
            x_max = float('-inf')
            y_max = float('-inf')

            # Iterate through the layers and update min and max values
            for layer in all_layers:
                try:
                    layer_bbox = layer.bounding_box()
                    x_min = min(x_min, layer_bbox.x.minimum)
                    y_min = min(y_min, layer_bbox.y.minimum)
                    x_max = max(x_max, layer_bbox.x.maximum)
                    y_max = max(y_max, layer_bbox.y.maximum)
                except AttributeError:
                    # Handle the case where the layer doesn't have a bounding box
                    self.print_to_log(f"Warning: Layer {layer.get(inkex.addNS('label', 'inkscape'))} has no bounding box.")

            # Calculate width and height
            width = x_max - x_min
            height = y_max - y_min

            # Log the width and height
            self.print_to_log(f"Canvas bounding box width: {width}")
            self.print_to_log(f"Canvas bounding box height: {height}")

            return width, height

        except Exception as e:
            self.print_to_log(f"Error getting canvas bounding box: {e}")
            return None 
            
           
if __name__ == '__main__':
    OptimizeClippedImages().run()