# PDAL clip to buildings example

This is just an example of some of PDAL's functionality. For more detailed descriptions, please see the wiki.

***
### Dependencies
GDAL
jq
***

In this example, we will clean up some of the metadata for the Shizuoka point-cloud data and attempt to classify buildings following the ASPRS classification scheme.

Let's first download some data using the pcdc-downloader script. Make sure that the "info.json" file is in the working directory. Make sure that you have all the dependencies for the downloader installed (see setup.md).

```bash
/Users/iosefa/GitHub/pcdb-downloader/download.js /Users/iosefa/GitHub/data/PDAL/
```  

To see what we are working with, it is important to observe the metadata:

```bash
docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal info data/28K2460011102-1.las --metadata
```

We can see that the SRS is not defined and so the first thing to do will be to fix this. We can also merge the two point-cloud datasets into one. The "merge.json" file has a pipeline to do such tasks.

```bash
docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal pipeline data/merge.json
```

It is also apparent that all data is classified as "0", and none of the points have been classified. We can verify this, in a way, by filtering by classification value (see LAS documentation). "filter_classifier.json" will filter by classification value and only show unclassified points. (for fun, it also shows how to write as a compressed file using laz). The output laz file can be viewed in plas.io.

```bash
docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal pipeline data/filter_classifier.json
```

This obviously makes clipping to buildings a little challenging. However, there are several simple ways we can solve this problem. One is to just create vector polygons at each building and clip to the these polygons. We can do this, but to do it "right" requires that we perform some sort of classification task to create the vector polygons. We can do this by taking a quick detour using GDAL and Python's Scikit-Learn and Scikit-Image packages.

But, before that, we need an image to classify. We can create one by writing the 3D point cloud to a 2D raster and taking the mean spectral value of each XY location.

To start, we will need the bounding box of the area of interest.

```bash
docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal info data/merged.las --all | jq .stats.bbox.native.bbox
```

This will give us the min and max XYZ values. Then, to create the raster, we call upon the different pipelines to make rasters for each spectral value (RGB):
  * "make_raster_R.json"
  * "make_raster_G.json"
  * "make_raster_B.json"

```bash
docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal pipeline data/make_raster_R.json

docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal pipeline data/make_raster_G.json

docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal pipeline data/make_raster_B.json
```

Once this is complete, we can use GDAL to merge them into a single multi-band raster.

```bash
gdal_merge.py -seperate -o /Users/iosefa/GitHub/data/PDAL/rgb.tif -co PHOTOMETRIC=MINISBLACK /Users/iosefa/GitHub/data/PDAL/raster_R.tif /Users/iosefa/GitHub/data/PDAL/raster_G.tif /Users/iosefa/GitHub/data/PDAL/raster_B.tif
```

Now, we need to classify the raster to create the vector polygons. We will use object-based image analysis using SLIC segmentation and an artificial neural network - at some point I will update my own repos to share... This is done using Python, and because it is a little out of scope of this example, I will skip this part for now.

... (actually, this failed - poor accuracy - made by hand for now)

Now that we have our vector geometries. We can clip our point-cloud to the polygons.

```bash
docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal pipeline data/clip.json
```

Finally, we can view this in plas.io.









In summary, we could:

  * check the metadata of the point-cloud datasets
  * merge the .las files into one .las (view in plas.io)
  * write the 3D point cloud to a 2D RGB raster taking the mean spectral value of each [X, Y] point.
  * classify the raster using GDAL, scikit-image, and scikit-learn in Python (out of scope of PDAL)
  * classify features of the point-cloud using vector data created in the previous step
  * crop to show buildings only
