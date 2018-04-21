# Visualizing Point Clouds with Potree

[Potree](potree.org) is a free open-source WebGL based point cloud renderer for large point clouds, developed at the Institute of Computer Graphics and Algorithms, TU Wien. We will use it to visualize a large point cloud dataset from Shizuoka.

To get started, download the potree repo and install all dependencies (as specified in package.json) and the gulp build tool:

```bash
git clone https://github.com/potree/potree.git
cd potree
npm install
npm install -g gulp

# To start a local web server to view examples and Potree pointclouds:
gulp watch
```

We can start a local web server and view an example by using the `gulp watch` command and going to [http://localhost:1234/examples/](http://localhost:1234/examples/).

Getting our own point cloud data into a Potree octree for visualization in Potree is done using [PotreeConverter](https://github.com/potree/PotreeConverter). This is easiest done in a docker. Local builds of the PotreeConverter is possible on Linux, Windows, and OSX, however it can be a pain to set this up.

We will pull the docker image from [jonazpiazu](https://hub.docker.com/r/jonazpiazu/potree/) to do the hard work of building the Potree octree and use data from Example2 in this repo.

```bash
docker pull jonazpiazu/potree
```
Let's create a directory to store the converted point clouds for Potree:

```bash
cd potree
mkdir potree_converted
```
And now, to run the potree converter:

```bash
docker run -v ~/repos/dotloom/:/ jonazpiazu/potree PotreeConverter /data/Example2/merged.laz -o /potree/potree_converted --output-format LAZ -p shizuoka
```

This also created the an html file called shizuoka for viewing the point cloud in Potree. Head to [http://localhost:1234/potree_converted/shizuoka_lg.html](http://localhost:1234/potree_converted/shizuoka.html).
