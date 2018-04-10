import numpy as np
import os
import scipy

from osgeo import gdal, ogr, osr
from skimage import exposure
from skimage.segmentation import slic
from sklearn import metrics
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

# run "classify_pipeline.py" first to get parameters.

# define a few functions (taken from https://github.com/machinalis/satimg/blob/master/object_based_image_analysis.ipynb)
def create_mask_from_vector(vector_data_path, cols, rows, geo_transform,
                            projection, target_value=1):
    """Rasterize the given vector (wrapper for gdal.RasterizeLayer)."""
    data_source = gdal.OpenEx(vector_data_path, gdal.OF_VECTOR)
    layer = data_source.GetLayer(0)
    driver = gdal.GetDriverByName('MEM')  # In memory dataset

    target_ds = driver.Create('', cols, rows, 1, gdal.GDT_UInt16)
    target_ds.SetGeoTransform(geo_transform)
    target_ds.SetProjection(projection)
    gdal.RasterizeLayer(target_ds, [1], layer, burn_values=[target_value])
    return target_ds

def vectors_to_raster(file_paths, rows, cols, geo_transform, projection):
    """Rasterize the vectors in the given directory in a single image."""
    labeled_pixels = np.zeros((rows, cols))
    for i, path in enumerate(file_paths):
        label = i + 1
        ds = create_mask_from_vector(path, cols, rows, geo_transform,
                                     projection, target_value=label)
        band = ds.GetRasterBand(1)
        labeled_pixels += band.ReadAsArray()
        ds = None
    return labeled_pixels

def write_geotiff(fname, data, geo_transform, projection, b_type):
    """Create a GeoTIFF file with the given data."""
    driver = gdal.GetDriverByName('GTiff')
    rows, cols = data.shape
    dataset = driver.Create(fname, cols, rows, 1, b_type)
    dataset.SetGeoTransform(geo_transform)
    dataset.SetProjection(projection)
    band = dataset.GetRasterBand(1)
    band.WriteArray(data)
    dataset = None  # Close the file

def segment_features(segment_pixels):
    """For each band, compute: min, max, mean, variance, skewness, kurtosis"""
    features = []
    n_pixels, n_bands = segment_pixels.shape
    for b in range(n_bands):
        stats = scipy.stats.describe(segment_pixels[:, b])
        band_stats = list(stats.minmax) + list(stats)[2:]
        if n_pixels == 1:
            # scipy.stats.describe raises a Warning and sets variance to nan
            band_stats[3] = 0.0  # Replace nan with something (zero)
        features += band_stats
    return features

def SLIC_object_creation(img, train_path, p_n_segments=50, p_compactness=1, p_sigma=0):
    """Creates objects based on a given segmentation algorithm"""
    segments = slic(img, n_segments=p_n_segments, compactness=p_compactness, sigma=p_sigma, max_size_factor=3)
    segment_ids = np.unique(segments)
    rows, cols, n_bands = img.shape
    files = [f for f in os.listdir(train_path) if f.endswith('.shp')]
    classes_labels = [f.split('.')[0] for f in files]
    shapefiles = [os.path.join(train_path, f) for f in files if f.endswith('.shp')]
    ground_truth = vectors_to_raster(shapefiles, rows, cols, geo_transform, proj)
    classes = np.unique(ground_truth)[1:]  # 0 doesn't count
    segments_per_klass = {}
    for klass in classes:
        segments_of_klass = segments[ground_truth == klass]
        segments_per_klass[klass] = set(segments_of_klass)
    # if there 1 segment contains more than 1 training class, then there are note enough segments! Stop.
    # when i convert this to an r function, should return a warning if this is the case.
    accum = set()
    intersection = set()
    for class_segments in segments_per_klass.values():
        intersection |= accum.intersection(class_segments)
        accum |= class_segments
    if len(intersection) > 0:
        return None
        # for a, b in segments_per_klass.items():
        #     segments_per_klass[a] = b.difference(intersection)
        #     # segments_per_klass[a] = mode(intersection)
    train_img = np.copy(segments)
    threshold = train_img.max() + 1
    for klass in classes:
        klass_label = threshold + klass
        for segment_id in segments_per_klass[klass]:
            train_img[train_img == segment_id] = klass_label
    train_img[train_img <= threshold] = 0
    train_img[train_img > threshold] -= threshold
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        objects = []
        objects_ids = []
        for segment_label in segment_ids:
            segment_pixels = img[segments == segment_label]
            segment_model = segment_features(segment_pixels)
            objects.append(segment_model)
            # Keep a reference to the segment label
            objects_ids.append(segment_label)
        # print("Created %i objects" % len(objects))
    training_labels = []
    training_objects = []
    for klass in classes:
        class_train_objects = [j for i, j in enumerate(objects) if objects_ids[i] in segments_per_klass[klass]]
        training_labels += [klass] * len(class_train_objects)
        # print("Training samples for class %i: %i" % (klass, len(class_train_objects)))
        training_objects += class_train_objects

    res = {
        'segments': segments,
        'segment_id': segment_id,
        'objects_ids':objects_ids,
        'objects': objects,
        'tr_objects': training_objects,
        'tr_labels': training_labels,
        'classes_labels': classes_labels,
        'rows': rows,
        'cols': cols
    }
    return res


scaler = StandardScaler()

# load image
image = "rgbz.tif"
raster = gdal.Open(image, gdal.GA_ReadOnly)
geo_transform = raster.GetGeoTransform()
proj = raster.GetProjectionRef()
n_bands = raster.RasterCount
bands_data = []
for b in range(1, n_bands + 1):
    band = raster.GetRasterBand(b)
    bands_data.append(band.ReadAsArray())
bands_data = np.dstack(b for b in bands_data)
img = exposure.rescale_intensity(bands_data)

# define the training and validation data
training_path = "train/"
validation_path = "train/"

classifier = RandomForestClassifier()

# classifier = MLPClassifier(activation="relu", alpha=0.1, hidden_layer_sizes=(14, 14),
#                            learning_rate_init=0.01, solver="adam")
# run the segmentation method

test = SLIC_object_creation(img, training_path, 1500, 1, 0.5)

# Fit only to the training data
scaler.fit(test["tr_objects"])
StandardScaler(copy=True, with_mean=True, with_std=True)

# Now apply the transformations to the data:
X_train = scaler.transform(test["tr_objects"])
X_test = scaler.transform(test["objects"])

classifier.fit(X_train, test['tr_labels'])
predicted = classifier.predict(X_test) # this takes the best estimator and parameters
clf = np.copy(test['segments'])
# prepare validation
for segment_id, klass in zip(test['objects_ids'], predicted):
    clf[clf == segment_id] = klass
# load validation data
shapefiles = [os.path.join(validation_path, "%s.shp" % c) for c in test['classes_labels']]
verification_pixels = vectors_to_raster(shapefiles, test['rows'], test['cols'], geo_transform, proj)
for_verification = np.nonzero(verification_pixels)
verification_labels = verification_pixels[for_verification]
predicted_labels = clf[for_verification]

# accuracy assessment
score = metrics.accuracy_score(verification_labels, predicted_labels)
print("Classification accuracy: %f" % score)

output_fname = "classified.tif"

# Just for the buildings to meet LAS specifications - pretty poor hack
clf_b = clf == 3
classified_b = clf_b * 6

write_geotiff(output_fname, classified_b, geo_transform, proj, gdal.GDT_Byte)

# this is stupid for now.
sourceRaster = gdal.Open('classified.tif')
band = sourceRaster.GetRasterBand(1)

target = osr.SpatialReference()
target.ImportFromEPSG(3095)

dst_layername = "buildings"
drv = ogr.GetDriverByName("GeoJSON")
dst_ds = drv.CreateDataSource( dst_layername + ".geojson")
dst_layer = dst_ds.CreateLayer(dst_layername, srs=target)
newField = ogr.FieldDefn('classification', ogr.OFTInteger)
dst_layer.CreateField(newField)

gdal.Polygonize(band, None, dst_layer, 0, [], callback=None)
