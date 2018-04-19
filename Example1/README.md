# PDAL classify and clip to buildings example

A processing example with PDAL. For more a more detailed look at PDAL, please see the [wiki](https://github.com/dotloom/data/wiki/PDAL).

***
To do this example, we will need:
  - [GDAL](http://www.gdal.org/)
  - [jq](https://stedolan.github.io/jq/)
  - [Python 3.6](https://www.python.org/)
  (and a bunch of packages for Python...)
And to run the [pcdc-downloader](https://github.com/dotloom/pcdb-downloader), we will need [npm](https://www.npmjs.com/)
***

In this example, we will:
  * Merge multiple point clouds that are saved in the [LAS file format](https://www.asprs.org/divisions-committees/lidar-division/laser-las-file-format-exchange-activities).
  * Assign a coordinate reference system to the point cloud data (where it was before non-existent).
  * Identify buildings (using GDAL and various machine learning and computer vision packages in Python).
  * Update the [ASPRS classification](https://www.asprs.org/wp-content/uploads/2010/12/LAS_1_4_r13.pdf) dimension of the LAS data so that it specifies buildings.
  * Clip the point cloud data to only show buildings.
  * Visualize some results in Cesium.

We will do this using pipelines with a general processing flow that follows:
  1. Download the LAS data we want to work with.
  2. Apply some preprocessing steps using a JSON pipeline.
  3. Apply the processing steps (classification) using a second JSON pipeline.
  4. Visualize the data in Cesium.

## Downloading data:

We will download some example data using the [pcdc-downloader](https://github.com/dotloom/pcdb-downloader). Make sure that the "info.json" file is in the working directory. Make sure that you have all the dependencies for the downloader installed (see the [ReadMe](https://github.com/dotloom/pcdb-downloader/blob/master/README.md)).

```bash
/Users/iosefa/GitHub/pcdb-downloader/download.js /Users/iosefa/GitHub/data/Example1/input/
```  

To see what we are working with, we can observe the metadata as well as statistics of each of the data dimensions:

```bash
docker run -v /Users/iosefa/GitHub/data/Example1/input/:/data pdal/pdal:1.7 pdal info data/28K2460011102-1.las --metadata

docker run -v /Users/iosefa/GitHub/data/Example1/input/:/data pdal/pdal:1.7 pdal info data/28K2460011102-1.las --stats
```

There are several important things to note. The first is that the data is not classified (see [LAS documentation]((https://www.asprs.org/wp-content/uploads/2010/12/LAS_1_4_r13.pdf) for more on ASPRS classification), which makes this exercise worth it ;). We can also see that the SRS is not defined and so the first thing to do will be to fix this. "Finding" the SRS is somewhat of a painful exercise that requires educated guess-work and brute-force validation. After going through a few likely possibilities and checking them with the [Shizuoka maps](https://pointcloud.pref.shizuoka.jp/lasmap/ankenmap?ankenno=28K2460011102), it is clear that the SRS is EPSG:6676. We can also notice that the radiometric resolution of the data is not 8 bit. If we want to be able to visualize with this data in Cesium (as we will), we will need to cast the spectral data to 8 bit. We can re-write the SRS and re-cast the spectral data as 8-bit integers, as well as merge the different LAS files into a single file all using a pipeline. This is done in the preprocessing step below.

## Preprocessing step

The "preprocessing.json" pipeline will load and merge all downloaded data, "clean up" the data by removing any statistical outliers, and then apply the correct radiometric resolution and SRS before compressing the point cloud as a [LAZ](https://www.laszip.org/) file. In docker:

```bash
docker run -v /Users/iosefa/GitHub/data/Example1/:/data pdal/pdal:1.7 pdal pipeline data/preprocessing.json
```

This pipeline reads all .las files as inputs and outputs a single compressed LAZ file.

![Merged LAZ Screenshot](/Example1/screenshots/merged.png)

## Processing step

The main processing step of this example is to classify buildings. There are several approaches towards solving this classification problem; one simple method is to re-write the LAZ data as a raster and perform an image classification algorithm to the data. Our approach will be to create polygons for each class and then re-assign the class of the points that fall within each of the polygons. To do this, we will rely on the GDAL bindings for python and the scikit-learn and scikit-image python packages.

For now, this will be done using several pipelines. The first four will take the LAZ file created earlier and will convert the data into a raster (not very elegant, but it gets the job done). To create the raster, we call upon the different pipelines to make rasters for each spectral value (RGB):
  * "MakeRaster_R.json"
  * "MakeRaster_G.json"
  * "MakeRaster_B.json"

However, just RGB spectral and XY data may not be enough to distinguish rooftops from cars, roads, and pavement. In this example, a simple method to aid the classifier is to include height data as well, and we can write this to a raster with "MakeRaster_Z.json"

```bash
docker run -v /Users/iosefa/GitHub/data/Example1/:/data pdal/pdal:1.7 pdal pipeline data/MakeRaster_R.json

docker run -v /Users/iosefa/GitHub/data/Example1/:/data pdal/pdal:1.7 pdal pipeline data/MakeRaster_G.json

docker run -v /Users/iosefa/GitHub/data/Example1/:/data pdal/pdal:1.7 pdal pipeline data/MakeRaster_B.json

docker run -v /Users/iosefa/GitHub/data/Example1/:/data pdal/pdal:1.7 pdal pipeline data/MakeRaster_Z.json
```

Once this is complete, we can use GDAL to merge them into a single multi-band raster.

```bash
gdal_merge.py -seperate -o /Users/iosefa/GitHub/data/Example1/rgbz.tif -co PHOTOMETRIC=MINISBLACK /Users/iosefa/GitHub/data/Example1/R.tif /Users/iosefa/GitHub/data/Example1/G.tif /Users/iosefa/GitHub/data/Example1/B.tif /Users/iosefa/GitHub/data/Example1/Z.tif
```

Now, we can apply an object-based image classifier (one that utilizes SLIC segmentation and a random forests classifier) on the raster.

```bash
python3 Example1/classify.py
```

Now that we have our vector geometries. We can update the classification dimension of the LAZ point cloud file.

```bash
docker run -v /Users/iosefa/GitHub/data/Example1/:/data pdal/pdal:1.7 pdal pipeline data/apply_classifier.json
```

![Classified Screenshot](/Example1/screenshots/classified.png)

And then finally, we can clip to show buildings only.

```bash
docker run -v /Users/iosefa/GitHub/data/Example1/:/data pdal/pdal:1.7 pdal pipeline data/clip.json
```

## Visualize in Cesium
(This should be changed... taken from [https://github.com/connormanning/entwine-cesium-pages](https://github.com/connormanning/entwine-cesium-pages)).

Finally, we can load this classified point cloud data product in [Cesium](https://cesium.com/). This step is a little involved, and it requires pulling the Entwine docker. Please check the wiki for more detailed information on Entwine and Cesium. We will follow steps detailed by [Connor Manning](https://github.com/connormanning/entwine-cesium-pages) to create a set of static pages to view our point cloud data on Cesium.    

To start, let's clone the repo, which has all the files necessary statically serve the Cesium viewer:

```bash
git clone https://github.com/connormanning/entwine-cesium-pages.git /Users/iosefa/GitHub/data/entwine-cesium-pages
```

And pull the Entwine docker:

```bash
docker pull connormanning/entwine
```

Now, create the 3D tiles for cesium using Entwine's cesium configuration template:

```bash
docker run -v /Users/iosefa/GitHub/data/:/data connormanning/entwine build /var/entwine/config/cesium.json -i /data/Example1/merged_clf.laz -o /data/entwine-cesium-pages/data/shizuoka

docker run -v /Users/iosefa/GitHub/data/:/data connormanning/entwine build /var/entwine/config/cesium-truncated.json -i /data/Example2/merged.laz -o /data/entwine-cesium-pages/data/shizuoka_lg

```

To view, statically serve the entwine-cesium-pages directory:

```bash
cd Example1/entwine-cesium-pages

python3 -m http.server 9000
```

And then navigate to [http://localhost:9000/?resource=shizuoka](http://localhost:9000/?resource=shizuoka) in a web browser and we're done!

![Cesium Screenshot](/Example1/screenshots/cesium.png)

(note that the terrain might have to be set to "WGS84 Ellipsoid" in the web browser.)

***
