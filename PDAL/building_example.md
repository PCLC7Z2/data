# PDAL clip to buildings example

This is just an example of some of PDAL's functionality. For more detailed descriptions, please see the [wiki](https://github.com/dotloom/data/wiki/PDAL). In it, we will:
  * Merge multiple point clouds that are saved in the [LAS file format](https://www.asprs.org/divisions-committees/lidar-division/laser-las-file-format-exchange-activities).
  * Assign a coordinate reference system to the point cloud data (where it was before non-existent).
  * Identify buildings (using GDAL and Python).
  * Update the [ASPRS classification](https://www.asprs.org/wp-content/uploads/2010/12/LAS_1_4_r13.pdf) dimension of the LAS data so that it specifies buildings.
  * Clip the point cloud data to only show buildings.

***
### Dependencies
To do this example, we will need:
  - [GDAL](http://www.gdal.org/)
  - [jq](https://stedolan.github.io/jq/)
  - [Python 3.6.5](https://www.python.org/)
And to run the [pcdc-downloader](https://github.com/dotloom/pcdb-downloader), we will need [npm](https://www.npmjs.com/)
***

Let's first download some data using the [pcdc-downloader](https://github.com/dotloom/pcdb-downloader). Make sure that the "info.json" file is in the working directory. Make sure that you have all the dependencies for the downloader installed (see the [ReadMe](https://github.com/dotloom/pcdb-downloader/blob/master/README.md)).

```bash
/Users/iosefa/GitHub/pcdb-downloader/download.js /Users/iosefa/GitHub/data/PDAL/
```  

To see what we are working with, it is important to observe the metadata:

```bash
docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal info data/28K2460011102-1.las --metadata
```

We can see that the SRS is not defined and so the first thing to do will be to fix this. "Finding" the SRS is somewhat of a painful exercise that requires educated guess-work and brute-force validation. After going through a few likely possibilities and checking them with the [Shizuoka maps](https://pointcloud.pref.shizuoka.jp/lasmap/ankenmap?ankenno=28K2460011102), it is clear that the SRS is EPSG:6676. While re-writing the SRS, we can also merge the two point-cloud datasets into one. The "merge.json" file has a pipeline to do such tasks.

```bash
docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal pipeline data/merge.json
```

It is also apparent that all data is classified as "0", and none of the points have been classified. We can verify this, in a way, by filtering by classification value (see [LAS documentation]((https://www.asprs.org/wp-content/uploads/2010/12/LAS_1_4_r13.pdf))). "filter_classifier.json" will filter by classification value and only show unclassified points. (For fun, it also shows how to write as a compressed file using [LAZ](https://www.laszip.org/)). The output laz file can be viewed in [plas.io](plas.io).

```bash
docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal pipeline data/filter_classifier.json
```

The fact that the LAS data is not classified obviously makes clipping to buildings a little challenging. However, there are several ways we can solve this problem. One is to just create vector polygons at each building and clip to the these polygons. A "simple" way of creating these polygons is to save the point cloud data in raster format and then use an image classifier on the raster data.

To start, we will write the point cloud as a raster and we will need the bounding box of the area of interest.

```bash
docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal info data/merged.las --all | jq .stats.bbox.native.bbox
```

This will give us the min and max XYZ values. Then, to create the raster, we call upon the different pipelines to make rasters for each spectral value (RGB):
  * "make_raster_R.json"
  * "make_raster_G.json"
  * "make_raster_B.json"

Just RGB spectral and XY data may not be enough to distinguish rooftops from cars, roads, and pavement. In this example, a simple method to aid the classifier is to include height data as well, and we can write this to a raster with "make_raster_Z.json"

```bash
docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal pipeline data/make_raster_R.json

docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal pipeline data/make_raster_G.json

docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal pipeline data/make_raster_B.json

docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal pipeline data/make_raster_Z.json
```

Once this is complete, we can use GDAL to merge them into a single multi-band raster.

```bash
gdal_merge.py -seperate -o /Users/iosefa/GitHub/data/PDAL/rgbz.tif -co PHOTOMETRIC=MINISBLACK /Users/iosefa/GitHub/data/PDAL/raster_R.tif /Users/iosefa/GitHub/data/PDAL/raster_G.tif /Users/iosefa/GitHub/data/PDAL/raster_B.tif /Users/iosefa/GitHub/data/PDAL/raster_Z.tif
```

Now, we need to classify the raster to create the vector polygons. As a first pass we will segment the image into "super-pixels" using the SLIC segmentation algorithm and create objects based on this segmentation. These objects will be classified using the Random Forest classifier as either building or not building. This is done using Python, and because it is a little out of scope of this example, I will skip this part for now, but the python scripts are there.

... classifier does its work and creates "buildings.geojson"...

Now that we have our vector geometries. We can update the classification dimension of the LAS point cloud file.

```bash
docker run -v /Users/iosefa/GitHub/data/PDAL/:/data pdal/pdal:1.7 pdal pipeline data/apply_classifier.json
```

And then finally, we can clip to show buildings only.

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
