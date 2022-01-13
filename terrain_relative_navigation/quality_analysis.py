import numpy as np
from numpy.lib import math

from osgeo import gdal
from affine import Affine

from qgis.core import QgsVectorLayer, QgsRasterLayer



def convertRasterToNumpyArray(lyr): #Input: QgsRasterLayer
    values=[]
    provider= lyr.dataProvider()
    block = provider.block(1,lyr.extent(),lyr.width(),lyr.height())
    for i in range(lyr.width()):
        for j in range(lyr.height()):
            values.append(block.value(i,j))
    return np.array(values)



def compute_fims(viewpoints_layer, viewshed_paths):
    """given a list of viewpoints and viewsheds, compute a list of FIM arrays of the same shapes"""
    reverse_transform = None
    viewshed_arrays = []
    for filename in viewshed_paths:
        ds = gdal.Open(filename)
        if reverse_transform is None:
            gt = ds.GetGeoTransform()
            reverse_transform = ~Affine.from_gdal(*gt)
            pixelSizeX = gt[1]
            pixelSizeY =-gt[5]
        array = ds.GetRasterBand(1).ReadAsArray().astype(np.uint8)
        viewshed_arrays.append(array)
    
    viewpoint_pixel_locs = []
    for feature in viewpoints_layer.getFeatures():
        point = feature.geometry().asPoint()
        x, y = point.x(), point.y()
        px, py = reverse_transform * (x, y)
        px, py = int(px + 0.5), int(py + 0.5)
        viewpoint_pixel_locs.append((px, py))


    h, w = viewshed_arrays[0].shape
    fims = [np.zeros((h, w, 3), dtype=np.float32) for _ in viewshed_arrays]

    for i, (viewshed, viewpoint) in enumerate(zip(viewshed_arrays, viewpoint_pixel_locs)):
        if np.isnan(viewshed).all():
            # raise ValueError("EMPTY VIEWSHED")
            continue

        eastsize = viewshed.shape[1]
        northsize = viewshed.shape[0]

        # Find pixel distances from that peak
        xarange = np.arange(eastsize) - viewpoint[0]
        yarange = np.arange(northsize) - viewpoint[1]

        # create matrices of distance components, dx, dy, for each pixel
        xmat = np.reshape(xarange,(eastsize,1))
        xmat = np.repeat(xmat,(northsize),axis=1).transpose()
        xmat = np.multiply(xmat,pixelSizeX)
        minval = np.min(xmat)
        maxval = np.max(xmat)
        print("X min:{}, X max:{}".format(minval,maxval))

        ymat = np.reshape(yarange,(northsize,1))
        ymat = np.repeat(ymat.transpose(),(eastsize),axis=0).transpose()
        ymat = np.multiply(ymat,pixelSizeY)
        minval = np.min(ymat)
        maxval = np.max(ymat)
        print("Y min:{}, Y max:{}".format(minval,maxval))

        x2mat = np.multiply(xmat,xmat)
        y2mat = np.multiply(ymat,ymat)
        r2mat = x2mat+y2mat+.01
        r1mat = np.sqrt(r2mat)
        minval = np.min(r1mat)
        maxval = np.max(r1mat)
        print("R min:{}, R max:{}".format(minval,maxval))

        cosmat = np.divide(xmat,r1mat)
        sinmat = np.divide(ymat,r1mat)
        cos2mat = np.divide(x2mat,r2mat)
        sin2mat = np.divide(y2mat,r2mat)

        fims[i][:,:,0] += viewshed * np.divide(sin2mat,r2mat)
        fims[i][:,:,1] -= viewshed * np.divide( np.multiply(sinmat,cosmat) , r2mat)
        fims[i][:,:,2] += viewshed * np.divide(cos2mat,r2mat)

        x2mat=None
        y2mat=None
        r2mat=None
        r1mat=None
        cosmat=None
        sinmat=None
        cos2mat=None
        sin2mat=None

    return fims
    

def compute_quality(fims, pointing, metric=0, nodata_value=1_000_000):
    """
    given a list of viewpoints and viewsheds, compute the quality metrix array of the same shape;
    0 = GDOP, 1 = Worst-Case
    """
    fim = np.sum(np.array(fims), axis=0)    # add up components
    fim /= math.pow(pointing, 2)

    # Compute largest eigenvalue of covariance matrix
    determ = fim[:,:,0]*fim[:,:,2] - fim[:,:,1]*fim[:,:,1]

    determ[determ<1e-9]=1e-9    # determ is zero some places

    covs = np.zeros(fim.shape)
    covs[:,:,0] = np.divide(fim[:,:,2], determ)
    covs[:,:,1] = -np.divide(fim[:,:,1], determ)
    covs[:,:,2] = np.divide(fim[:,:,0], determ)

    tracecovs = covs[:,:,0] + covs[:,:,2]
    detcovs = 1.0/determ

    # https://en.wikipedia.org/wiki/Eigenvalue_algorithm#2.C3.972_matrices
    max_eigen = (tracecovs + np.sqrt(np.square(tracecovs) - detcovs*4)) / 2

    if metric == 0:
        # GDOP
        quality = np.sqrt(tracecovs)    # same as `np.sqrt(min_eigen + max_eigen)`
    else:
        # Worst-Case
        quality = np.sqrt(max_eigen)

    # set all points with FIM 0 to nodata (corresponds to no observations)
    fim_zeros = np.logical_and(np.logical_and(fim[:,:,0] == 0, fim[:,:,1] == 0), fim[:,:,2] == 0)
    quality[fim_zeros] = nodata_value
    quality[np.isnan(quality)] = nodata_value

    return quality
