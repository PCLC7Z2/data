# Visualizing Point Clouds with Cesium and Entwine

[Cesium](https://cesiumjs.org) is a geospatial 3D mapping platform that can be used to create virtual globes and visualize point cloud data. This visualization is realized using the [3D Tiles](https://github.com/AnalyticalGraphicsInc/3d-tiles) specification for point clouds (more can be read [here]()).

Creating 3D tiles for visualization in Cesium is easiest done using docker. We will use [Entwine's cesium template](https://github.com/connormanning/entwine-cesium-pages) to accomplish this task. A local installation of Entwine requires local builds of both PDAL, LAZPERF, and Entwine and can easily be problematic. See the wiki for more on compiling these programs.

We will follow steps detailed by [Connor Manning](https://github.com/connormanning/entwine-cesium-pages) to create a set of static pages to view our point cloud data on Cesium.    

To start, let's clone the repo which has all the files necessary statically serve the Cesium viewer:

```bash
git clone https://github.com/connormanning/entwine-cesium-pages.git ~/repos/dotloom/
```

And pull the Entwine docker:

```bash
docker pull connormanning/entwine
```

Now, create the 3D tiles for cesium using Entwine's cesium configuration template:

***
Note:
  - Cesium 3D tiles requires 8 bit radiometric resolution. Luckily, Entwine's cesium configuration template will save us a little bit of work by recasting non-8 bit data to the required format.
  - The data in these examples have already gone through some degree of preprocessing. See [this example]().
***

```bash
docker run -v ~/repos/dotloom/data/:/out connormanning/entwine build /out/var/entwine/config/cesium-truncated.json -i /out/Example1/merged_clf.laz -o /out/entwine-cesium-pages/data/shizuoka

```

To view, statically serve the entwine-cesium-pages directory:

```bash
cd entwine-cesium-pages

python3 -m http.server 9000
```

And then navigate to [http://localhost:9000/?resource=shizuoka](http://localhost:9000/?resource=shizuoka) in a web browser and we're done!

![Cesium Screenshot](/Example1/screenshots/cesium.png)

***
(note that cesium is sensitive to altitude and "incorrect" z values can result in the model being either too far above or below the terrain surface.)
