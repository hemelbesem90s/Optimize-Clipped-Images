# Inkscape Optimize Clipped Images Extension

This extension optimizes clipped images in an Inkscape SVG document by exporting them to PNG, re-importing them, and removing the original clipped image data.

## Functionality

The extension performs the following steps:

1.  **Identifies clipped images:** Finds all images in the SVG document that have a `clip-path` attribute.
2.  **Exports clipped images:** Exports each clipped image as a PNG file to a temporary location.
3.  **Re-imports images:** Imports the exported PNG images back into the SVG document.
4.  **Positions images:** Positions the re-imported images to match the original clipped images, taking into account any transformations applied.
5.  **Deletes original data:** Deletes the original clipped images and their associated clip paths, reducing the file size.

## Usage

1.  Install the extension by placing the `optimize_clipped_images.inx` and `optimize_clipped_images.py` files in your Inkscape extensions directory.
2.  Open your SVG document in Inkscape.
3.  Go to `Extensions > Image > Optimize Clipped Images`.

## Options

The extension provides the following options:

*   **Target resolution:** Allows the user to select the desired DPI for the exported images.

## Acknowledgements

This extension was developed with the help of [Gemini Advanced](https://sites.research.google/gemini), Google's next-generation AI model. 

Special thanks to the Inkscape community for their valuable contributions and support, particularly the following resources:

*   Inkscape Forum: [https://inkscape.org/forums/](https://inkscape.org/forums/)
*   Inkscape Wiki: [https://wiki.inkscape.org/wiki/](https://wiki.inkscape.org/wiki/)
*   Inkscape Extensions Documentation: [https://inkscape.gitlab.io/extensions/documentation/](https://inkscape.gitlab.io/extensions/documentation/)

## License

This extension is licensed under the GNU General Public License v2.0. See the LICENSE file for details.
