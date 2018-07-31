# Entwine Point Tile (EPT) Format

Converting to the [new EPT format](https://github.com/connormanning/ept) is very simple and straight-forward using docker.

To get started, pull the latest entwine docker container:

```bash
docker pull connormanning/entwine
```
And then, using the same point cloud data used in Example 1, it is as simple as:
```bash
docker run -it -v /Users/iosefa/repos/dotloom/data:/data connormanning/entwine build -i data/merged.laz -o /data/EPT_Format/shizuoka01
```
The basic entwine command used here is `build`. The `build` command simply generates an EPT dataset from point cloud data. The `-i` flag sets the input and the `-o` flag sets the output EPT dataset.

This EPT data set is now ready to be viewed in your favorite point cloud viewer (or P-Next!). 
