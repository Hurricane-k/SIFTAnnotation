# -*- coding: utf-8 -*-

# Just copy from GitHub, wanna know how to achieve SIFT

import warnings
warnings.filterwarnings("ignore")  #ignore warning
import numpy as np
import matplotlib.pyplot as plt
from sklearn.neighbors import KNeighborsClassifier
from PIL import Image

#%% function convolve

def convolve(filter_G,mat,padding,strides):
    #convolve(filter_G = GuassianKernel(sigma[i][j], dim),
    #         mat = samplePyramid[i],
    #         padding = [dim//2,dim//2,dim//2,dim//2],
    #         strides = [1,1])
    '''
    There is not explanation about inputs

    Parameters
    ----------
    filter_G : 2D - np.ndarray
        Gaussian Filter.
    mat : 2D - np.ndarray
        a binary image. or 3D np.ndarray (color image)
    padding : list
    strides : list

    Returns
    -------
    result : np.ndarray (2D or 3D depending the input mat (binary or color image))
        image after being processed by Gaussian Filter.

    '''

    result = None
    filter_size = filter_G.shape
    mat_size = mat.shape
    if len(filter_size) == 2: # the filter must be 2D?
        if len(mat_size) == 3: # for color image, e.g. RGB image
            channel = []
            for i in range(mat_size[-1]):
                pad_mat = np.pad(mat[:,:,i], ((padding[0], padding[1]), (padding[2], padding[3])), 'constant')
                temp = []
                for j in range(0,mat_size[0],strides[1]):
                    temp.append([])
                    for k in range(0,mat_size[1],strides[0]):
                        val = (filter_G*pad_mat[j:j+filter_size[0],k:k+filter_size[1]]).sum()
                        temp[-1].append(val)
                channel.append(np.array(temp))

            channel = tuple(channel)
            result = np.dstack(channel)
        elif len(mat_size) == 2: # for binary image grey-scale image
            channel = []
            pad_mat = np.pad(mat, ((padding[0], padding[1]), (padding[2], padding[3])), 'constant')
            for j in range(0, mat_size[0], strides[1]):
                channel.append([])
                for k in range(0, mat_size[1], strides[0]):
                    val = (filter_G * pad_mat[j:j + filter_size[0],k:k + filter_size[1]]).sum()
                    channel[-1].append(val)


            result = np.array(channel)


    return result

#%% function downsample

def downsample(img,step = 2):
    return img[::step,::step]

#%% function Gaussian Kernel

def GuassianKernel(sigma , dim):
    # GuassianKernel(sigma = sigma[i][j], dim = dim)
    '''
    :param sigma: scalar, Standard deviation
    :param dim: dimension(must be positive and also an odd number) 
                (an odd number is the key)
    :return result: np.ndarray, return the required Gaussian kernel.
    '''
    temp = [t - (dim//2) for t in range(dim)]
    assistant = []
    for i in range(dim):
        assistant.append(temp)
    assistant = np.array(assistant)
    temp = 2*sigma*sigma
    result = (1.0/(temp*np.pi))*np.exp(-(assistant**2+(assistant.T)**2)/temp)
    return result

#%% function get Difference of Gaussian Pyramid

def getDoG(img,n,sigma0,S = None,O = None):
    '''
    :param img: the original img.
    :param sigma0: sigma of the first stack of the first octave. default 1.52 for complicate reasons.
    :param n: how many stacks of feature that you wanna extract.
    :param S: how many stacks does every octave have. S must bigger than 3.
    :param k: the ratio of two adjacent stacks' scale.
    :param O: how many octaves do we have.
    :return: the DoG Pyramid
    '''
    if S == None:
        S = n + 3 # S is the number of images in octave in Gaussian Pyramid
    if O == None:
        O = int(np.log2(min(img.shape[0], img.shape[1]))) - 3
        # O is the number of octaves in Gaussian Pyramid

    k = 2 ** (1.0 / n) # k is the factor before sigma, like k*sigma for every image
    sigma = [[(k**s)*sigma0*(1<<o) for s in range(S)] for o in range(O)]
    samplePyramid = [downsample(img, 1 << o) for o in range(O)]
    
    # this loop is for creation of Gaussian Pyramid
    GuassianPyramid = []
    for i in range(O):
        GuassianPyramid.append([])
        for j in range(S):
            dim = int(6*sigma[i][j] + 1)
            if dim % 2 == 0: # the dimension of Gaussian Kernel has to be an odd number
                dim += 1
            GuassianPyramid[-1].append(convolve(GuassianKernel(sigma[i][j], dim),samplePyramid[i],[dim//2,dim//2,dim//2,dim//2],[1,1]))
    
    # this is for creating Pyramid of Difference of Gaussian
    # the former index of GaussianPyramid is No. of Octave
    # the latter index of GaussianPyramid is No. of scale
    DoG = [[GuassianPyramid[o][s+1] - GuassianPyramid[o][s] for s in range(S - 1)] for o in range(O)]


    return DoG,GuassianPyramid

#%% function find the true extrema location

def adjustLocalExtrema(DoG,o,s,x,y,contrastThreshold,edgeThreshold,sigma,n,SIFT_FIXPT_SCALE):
    '''

    Parameters
    ----------
    DoG : Pyramid of Difference of Gaussian
        list containing several np.ndarray.
    o : scalar
        the octave No. in DoG.
    s : scalar
        the image No. in one certain octave of DoG.
    x : scalar
        the intial x location of extrema candidate.
    y : scalar
        the intial y location of extrema candidate.
    contrastThreshold : scalar
        eliminate the extrema with low contrast.
    edgeThreshold : scalar
        eliminate the extrema located at edges.
    sigma : scalar
        another way representing image DoG.
    n : scalar (integer)
        the number of images where we wanna extract features in one certain octave.
    SIFT_FIXPT_SCALE : scalar (integer)
        solve for derivation.

    Returns
    -------
    Point: a list with 4 elements, but no idea of the last two elements
    x: the location x (integer) of the true extrema we want
    y: the location y (integer) of the true extrema we want
    s: the image where we wanna find keypoint in DoG Pyramid

    '''
    # adjustLocalExtrema(DoG,o,s,x=i,y=j,contrastThreshold,edgeThreshold,sigma,n,SIFT_FIXPT_SCALE)
    SIFT_MAX_INTERP_STEPS = 5
    SIFT_IMG_BORDER = 5

    point = []

    img_scale = 1.0 / (255 * SIFT_FIXPT_SCALE)
    deriv_scale = img_scale * 0.5 # 1-order derivation Dx Dy
    second_deriv_scale = img_scale # 2-order derivation Dxx Dyy
    cross_deriv_scale = img_scale * 0.25 # partial derivation Dxy

    img = DoG[o][s] # one image of Difference of Gaussian Pyramid
    i = 0
    # the limit about iteration about subpixel
    while i < SIFT_MAX_INTERP_STEPS:
        # s means the image (DoG Pyramid) needs to be middle image in octave
        # the keypoint cannot be near the boundary of image
        if s < 1 or s > n or y < SIFT_IMG_BORDER or y >= img.shape[1] - SIFT_IMG_BORDER or x < SIFT_IMG_BORDER or x >= img.shape[0] - SIFT_IMG_BORDER:
            return None,None,None,None

        img = DoG[o][s]
        prev = DoG[o][s - 1]
        foll = DoG[o][s + 1] 
        
        # next is about Taylor Expansion
        # dD is the matrix of 1-order derivation
        # dD = [d-y, d-x, d-sigma]
        dD = [ (img[x,y + 1] - img[x, y - 1]) * deriv_scale,
               (img[x + 1, y] - img[x - 1, y]) * deriv_scale,
               (foll[x, y] - prev[x, y]) * deriv_scale ] 
        
        # next is about 2-order derivation, Hessian Matrix
        # s is abbr of sigma
        # [[dxx, dxy, dxs]]
        # [[dxy, dyy, dys]]
        # [[dxs, dys, dss]]
        v2 = img[x, y] * 2
        dxx = (img[x, y + 1] + img[x, y - 1] - v2) * second_deriv_scale
        dyy = (img[x + 1, y] + img[x - 1, y] - v2) * second_deriv_scale
        dss = (foll[x, y] + prev[x, y] - v2) * second_deriv_scale
        dxy = (img[x + 1, y + 1] - img[x + 1, y - 1] - img[x - 1, y + 1] + img[x - 1, y - 1]) * cross_deriv_scale
        dxs = (foll[x, y + 1] - foll[x, y - 1] - prev[x, y + 1] + prev[x, y - 1]) * cross_deriv_scale
        dys = (foll[x + 1, y] - foll[x - 1, y] - prev[x + 1, y] + prev[x - 1, y]) * cross_deriv_scale
        
        # 3x3 Hessian Matrix
        H=[ [dxx, dxy, dxs],
            [dxy, dyy, dys],
            [dxs, dys, dss]]
        
        # X is the offset of the real extrema (maybe subpixel) from taking derivation of Taylor Expansion
        X = np.matmul(np.linalg.pinv(np.array(H)),np.array(dD))

        xi = -X[2] # xi is the offset of sigma
        xr = -X[1] # xr is the offset of x
        xc = -X[0] # xc is the offset of y
        
        # if the offset is too much small, just negligible
        if np.abs(xi) < 0.5 and np.abs(xr) < 0.5 and np.abs(xc) < 0.5:
            break

        y += int(np.round(xc))
        x += int(np.round(xr))
        s += int(np.round(xi))

        i+=1
    
    # can't find the true extrema in the limited iteration
    # I think this if-judgement is not necessary, 
    # coz i cannot be greater than equal to SIFT_MAX_INTERP_STEPS
    if i >= SIFT_MAX_INTERP_STEPS:        
        return None,x,y,s
    
    # in case that the subpixel extrema is not what we want, 
    # even if we find it within the limited iteration
    # the next if-judgement is the same as the first one in while-loop
    if s < 1 or s > n or y < SIFT_IMG_BORDER or y >= img.shape[1] - SIFT_IMG_BORDER or x < SIFT_IMG_BORDER or x >= \
            img.shape[0] - SIFT_IMG_BORDER:
        return None, None, None, None

    # if the contrast of extrema is pretty low, should be out
    # the next two steps is first-order taylor expansion
    # you can combine two steps into one line
    t = (np.array(dD)).dot(np.array([xc, xr, xi]))
    contr = img[x,y] * img_scale + t * 0.5
    
    if np.abs(contr) * n < contrastThreshold:
        return None,x,y,s
    
    # the next step is to elimate some extrema located at edges
    # solve for the principal curvatures of x-axis and y-axis using Hessian Matrix
    # here is second-order Hessian Matrix
    # [[dxx, dxy]]
    # [[dxy, dyy]]
    tr = dxx + dyy # trace of Hessian Matrix
    det = dxx * dyy - dxy * dxy # det of Hessian Matrix
    # the value 10 of edgeThreshold is recommended by intial article
    if det <= 0 or tr * tr * edgeThreshold >= (edgeThreshold + 1) * (edgeThreshold + 1) * det:
        return None,x,y,s
    
    # coz these extrema maybe at different octave in Gaussian Pyramid
    # if some image is after downsample, the location of extrema should be done with inverse of downsample;
    # which means upsample
    point.append((x + xr) * (1 << o))
    point.append((y + xc) * (1 << o))
    # actually, don't get it, the next two lines
    point.append(o + (s << 8) + (int(np.round((xi + 0.5)) * 255) << 16))
    point.append(sigma * np.power(2.0, (s + xi) / n) * (1 << o) * 2)

    return point,x,y,s

#%% function get the main direction of each keypoint

def GetMainDirection(img,r,c,radius,sigma,BinNum):
    # GetMainDirection(img = GuassianPyramid[o][layer],
    #                  r = x, c = y,
    #                  radius = int(np.round(SIFT_ORI_RADIUS * scl_octv)),
    #                  sigma = SIFT_ORI_SIG_FCTR * scl_octv,BinNum)
    '''
    INPUT
    img: one image in Gaussian Pyramid
    r: x location of true extrema
    c: y location of true extrema
    radius: the range of surroundings
    sigma: the parameter of Gaussian
    BinNum: the number of histogram 
    
    OUTPUT
    maxval: the maximun of histogram
    hist: the smooth histogram
    '''
    
    # weighted by Gaussian
    expf_scale = -1.0 / (2.0 * sigma * sigma)

    X = []
    Y = []
    W = []
    temphist = []

    for i in range(BinNum):
        temphist.append(0.0)

    # pixel range for image gradient histogram statistic
    k = 0
    for i in range(-radius,radius+1):
        y = r + i
        if y <= 0 or y >= img.shape[0] - 1:
            continue
        for j in range(-radius,radius+1):
            x = c + j
            if x <= 0 or x >= img.shape[1] - 1:
                continue

            dx = (img[y, x + 1] - img[y, x - 1])
            dy = (img[y - 1, x] - img[y + 1, x])

            X.append(dx)
            Y.append(dy)
            W.append((i * i + j * j) * expf_scale)
            k += 1


    length = k

    W = np.exp(np.array(W)) # this is Gaussian Weight
    Y = np.array(Y) 
    X = np.array(X)
    # cal the degree, ranging from -180 to 180
    Ori = np.arctan2(Y,X)*180/np.pi 
    Mag = (X**2+Y**2)**0.5 # this is magnitude, the 2-L norm of gradient

    # calculate each bion of the histogram
    for k in range(length):
        bin_each = int(np.round((BinNum / 360.0) * Ori[k]))
        if bin_each >= BinNum:
            bin_each -= BinNum
        if bin_each < 0:
            bin_each += BinNum
        temphist[bin_each] += W[k] * Mag[k] # the Gaussian-based weighted gradient

    # smooth the histogram (Gaussian Smoothing)
    # temp [350-360, 340-350, 0-10, 10-20]
    temp = [temphist[BinNum - 1], temphist[BinNum - 2], temphist[0], temphist[1]]
    temphist.insert(0, temp[0])
    temphist.insert(0, temp[1])
    temphist.insert(len(temphist), temp[2])
    temphist.insert(len(temphist), temp[3])      # padding
    # there are 40 elements in temphist
    # temphist [340-350, 350-360, 0-10, 10-20, 20-30, ..., 340-350, 350-360, 0-10, 10-20]
    
    # cannot get it
    hist = []
    for i in range(BinNum):
        hist.append((temphist[i] + temphist[i+4]) * (1.0 / 16.0) + (temphist[i+1] + temphist[i+3]) * (4.0 / 16.0) + temphist[i+2] * (6.0 / 16.0))

    # 得到主方向
    maxval = max(hist)

    return maxval,hist

#%% function to find the potential keypoints

def LocateKeyPoint(DoG,sigma,GuassianPyramid,n,BinNum = 36,contrastThreshold = 0.04,edgeThreshold = 10.0):
    # LocateKeyPoint(DoG, sigma = SIFT_SIGMA, GuassianPyramid, n)
    '''
    DoG: the Pyramid of Difference of Gaussian
    sigma: a scalar, the inital sigma value from the paper (SIFT)
    Guassian Pyramid: Gaussian Pyramid
    n: the number of images we wanna extract features
    BinNum: every bin contains 10 degrees (0-10, 10-20, 20-30, ...)
    '''
    
    SIFT_ORI_SIG_FCTR = 1.52 # sqrt(1.6**2 - 0.5**2)
    SIFT_ORI_RADIUS = 3 * SIFT_ORI_SIG_FCTR # the radius
    SIFT_ORI_PEAK_RATIO = 0.8

    SIFT_INT_DESCR_FCTR = 512.0
    # SIFT_FIXPT_SCALE = 48
    SIFT_FIXPT_SCALE = 1

    KeyPoints = []
    O = len(DoG) # the layer of Pyramid, the number of octaves
    S = len(DoG[0]) # the number of image in each octave in Gaussian Pyramid
   
    for o in range(O):
        # o = 0
        for s in range(1,S-1): # only extract features in the middle images in each octave
            # s = 1
            # remove some unstable or noisy point    
            # but no idea why there are two factors following "n"
            threshold = 0.5*contrastThreshold/(n*255*SIFT_FIXPT_SCALE)
            # need to compare in 3D x-axis, y-axis, sigma-axis
            img_prev = DoG[o][s-1]
            img = DoG[o][s]
            img_next = DoG[o][s+1]
            for i in range(img.shape[0]):
                for j in range(img.shape[1]):
                    val = img[i,j] 
                    eight_neiborhood_prev = img_prev[max(0, i - 1):min(i + 2, img_prev.shape[0]), max(0, j - 1):min(j + 2, img_prev.shape[1])]
                    eight_neiborhood = img[max(0, i - 1):min(i + 2, img.shape[0]), max(0, j - 1):min(j + 2, img.shape[1])]
                    eight_neiborhood_next = img_next[max(0, i - 1):min(i + 2, img_next.shape[0]), max(0, j - 1):min(j + 2, img_next.shape[1])]
                    # extrema minimum or extrema maximum
                    if np.abs(val) > threshold and \
                        ((val > 0 and (val >= eight_neiborhood_prev).all() and (val >= eight_neiborhood).all() and (val >= eight_neiborhood_next).all())
                         or (val < 0 and (val <= eight_neiborhood_prev).all() and (val <= eight_neiborhood).all() and (val <= eight_neiborhood_next).all())):
                        
                        # find the true extrema (subpixel)
                        # the 1st element of point is the float version of x
                        # the 2nd element of point os the float version of y
                        # layer is the number of image in one octave in octave
                        # but no idea of the meaning the last two elements in point
                        point,x,y,layer = adjustLocalExtrema(DoG,o,s,i,j,contrastThreshold,edgeThreshold,sigma,n,SIFT_FIXPT_SCALE)
                        if point == None:
                            continue
                        
                        # solve radius for getting main direction
                        scl_octv = point[-1]*0.5/(1 << o)
                        
                        # noticably, main direction is done in Gaussian Pyramid instead of Difference of Gaussian
                        # one question here, layer is applied to Gaussian Pyramid, but layer is from s, s is applied in DoG, here I cannot get it
                        # I think there are some problems about the chosen layer
                        omax,hist = GetMainDirection(GuassianPyramid[o][layer],x,y,int(np.round(SIFT_ORI_RADIUS * scl_octv)),SIFT_ORI_SIG_FCTR * scl_octv,BinNum)
                        mag_thr = omax * SIFT_ORI_PEAK_RATIO
                        # magnitude threshold, in case there is vice-direction
                        # if there is the second main direction
                        for k in range(BinNum):
                            if k > 0:
                                l = k - 1
                            else:
                                l = BinNum - 1
                            if k < BinNum - 1:
                                r2 = k + 1
                            else:
                                r2 = 0
                            if hist[k] > hist[l] and hist[k] > hist[r2] and hist[k] >= mag_thr:
                                bin_each = k + 0.5 * (hist[l]-hist[r2]) /(hist[l] - 2 * hist[k] + hist[r2])
                                if bin_each < 0:
                                    bin_each = BinNum + bin_each
                                else:
                                    if bin_each >= BinNum:
                                        bin_each = bin_each - BinNum
                                temp = point[:]
                                temp.append((360.0/BinNum) * bin_each)
                                KeyPoints.append(temp)

    return KeyPoints

#%% function get the descriptor of each keypoint shape (128,)

def calcSIFTDescriptor(img,ptf,ori,scl,d,n,SIFT_DESCR_SCL_FCTR = 3.0,
                       SIFT_DESCR_MAG_THR = 0.2,SIFT_INT_DESCR_FCTR = 512.0,
                       FLT_EPSILON = 1.19209290E-07):
    # calcSIFTDescriptor(img, ptf, 
    #                    ori = kpt[-1], 
    #                    scl = size * 0.5, d, n)
    # this function I haven't understand fully yet,
    # I know this is for extract the gradient magnitude of 8 direction surrounding keypoint
    # totally contain 128 gradient magnitude (4*4*8)
    '''
    INPUT
    img: np.ndarray (the targeted image in Gaussian Pyramid)
    ptf: list (showing the location of the keypoint)
    ori: np.float64 (the main direction of the keypoint)
    d: SIFT_DESCR_WIDTH
    n: SIFT_DESCR_HIST_BINS (8 directions)
    '''
    
    dst = [] # this is output
    pt = [int(np.round(ptf[0])), int(np.round(ptf[1]))] # coordinate point rounding
    cos_t = np.cos(ori * (np.pi / 180)) # cal cosine
    sin_t = np.sin(ori * (np.pi / 180)) # cal sine
    
    # actually, no idea about what they are doing (the next lines)
    bins_per_rad = n / 360.0
    exp_scale = -1.0 / (d * d * 0.5)
    hist_width = SIFT_DESCR_SCL_FCTR * scl
    radius = int(np.round(hist_width * 1.4142135623730951 * (d + 1) * 0.5))
    cos_t /= hist_width
    sin_t /= hist_width

    rows = img.shape[0]
    cols = img.shape[1]


    hist = [0.0]*((d+2)*(d+2)*(n+2)) # this is a list
    X = []
    Y = []
    RBin = []
    CBin = []
    W = []

    k = 0
    for i in range(-radius,radius+1):
        # i = -24
        for j in range(-radius,radius+1):
            # j = -24
            # need to find the location of surrounding pixel after rotation based on main direction
            c_rot = j * cos_t - i * sin_t # no idea, i, and j is radius
            r_rot = j * sin_t + i * cos_t # no idea
            rbin = r_rot + d // 2 - 0.5
            cbin = c_rot + d // 2 - 0.5
            r = pt[1] + i # the index 1 is x-axis
            c = pt[0] + j # the index 0 is y-axis

            if rbin > -1 and rbin < d and cbin > -1 and cbin < d and r > 0 and r < rows - 1 and c > 0 and c < cols - 1:
                dx = (img[r, c+1] - img[r, c-1])
                dy = (img[r-1, c] - img[r+1, c])
                X.append(dx)
                Y.append(dy)
                RBin.append(rbin)
                CBin.append(cbin)
                W.append((c_rot * c_rot + r_rot * r_rot) * exp_scale)
                k+=1

    length = k
    Y = np.array(Y)
    X = np.array(X)
    Ori = np.arctan2(Y,X)*180/np.pi
    Mag = (X ** 2 + Y ** 2) ** 0.5
    W = np.exp(np.array(W))

    for k in range(length):
        rbin = RBin[k]
        cbin = CBin[k]
        obin = (Ori[k] - ori) * bins_per_rad
        mag = Mag[k] * W[k]

        r0 = int(rbin)
        c0 = int(cbin)
        o0 = int(obin)
        rbin -= r0
        cbin -= c0
        obin -= o0

        if o0 < 0:
            o0 += n
        if o0 >= n:
            o0 -= n

        # histogram update using tri-linear interpolation
        v_r1 = mag * rbin
        v_r0 = mag - v_r1

        v_rc11 = v_r1 * cbin
        v_rc10 = v_r1 - v_rc11

        v_rc01 = v_r0 * cbin
        v_rc00 = v_r0 - v_rc01

        v_rco111 = v_rc11 * obin
        v_rco110 = v_rc11 - v_rco111

        v_rco101 = v_rc10 * obin
        v_rco100 = v_rc10 - v_rco101

        v_rco011 = v_rc01 * obin
        v_rco010 = v_rc01 - v_rco011

        v_rco001 = v_rc00 * obin
        v_rco000 = v_rc00 - v_rco001

        idx = ((r0 + 1) * (d + 2) + c0 + 1) * (n + 2) + o0
        hist[idx] += v_rco000
        hist[idx+1] += v_rco001
        hist[idx + (n+2)] += v_rco010
        hist[idx + (n+3)] += v_rco011
        hist[idx+(d+2) * (n+2)] += v_rco100
        hist[idx+(d+2) * (n+2)+1] += v_rco101
        hist[idx+(d+3) * (n+2)] += v_rco110
        hist[idx+(d+3) * (n+2)+1] += v_rco111

    # finalize histogram, since the orientation histograms are circular
    for i in range(d):
        for j in range(d):
            idx = ((i+1) * (d+2) + (j+1)) * (n+2)
            hist[idx] += hist[idx+n]
            hist[idx+1] += hist[idx+n+1]
            for k in range(n):
                dst.append(hist[idx+k])

    # copy histogram to the descriptor,
    # apply hysteresis thresholding
    # and scale the result, so that it can be easily converted
    # to byte array
    nrm2 = 0
    length = d * d * n
    for k in range(length):
        nrm2 += dst[k] * dst[k]
    thr = np.sqrt(nrm2) * SIFT_DESCR_MAG_THR # abbr of threshold?

    nrm2 = 0
    for i in range(length):
        val = min(dst[i], thr)
        dst[i] = val
        nrm2 += val * val
    nrm2 = SIFT_INT_DESCR_FCTR / max(np.sqrt(nrm2), FLT_EPSILON)
    for k in range(length):
        dst[k] = min(max(dst[k] * nrm2,0),255)

    return dst

#%% function regarded it as the main function of calcSIFTDescriptor

def calcDescriptors(gpyr,keypoints,SIFT_DESCR_WIDTH = 4,SIFT_DESCR_HIST_BINS = 8):
    # calcDescriptors(gpyr = GuassianPyramid, keypoints = KeyPoints)
    # SIFT_DESCR_WIDTH = 4 # Describe the width of the histogram
    # SIFT_DESCR_HIST_BINS = 8
    '''
    INPUT
    gpyr: Gaussian Pyramid
    keypoints: a series of keypoints
    OUTPUT
    descriptors: 128 features for one keypoint 
    '''
    
    d = SIFT_DESCR_WIDTH
    n = SIFT_DESCR_HIST_BINS
    descriptors = []

    for i in range(len(keypoints)):
        kpt = keypoints[i]
        # the next lines show the meanings of the 3rd, 4th elements of the every keypoint (np.ndarray)
        # the No. of Octave
        o = kpt[2] & 255 
        # the No. of image in one certain Octave
        s = (kpt[2] >> 8) & 255 # 该特征点所在的组序号和层序号
        # scaling factor for what
        scale = 1.0 / (1 << o)  # 缩放倍数
        # size, what is size, whose size, size applied to x,y locations
        size = kpt[3] * scale # 该特征点所在组的图像尺寸
        # ptf is the keypoint location
        ptf = [kpt[1] * scale, kpt[0] * scale] # 该特征点在金字塔组中的坐标
        # one targeted image in Gaussian Pyramid
        img = gpyr[o][s] # 该点所在的金字塔图像

        descriptors.append(calcSIFTDescriptor(img, ptf, kpt[-1], size * 0.5, d, n))
    return descriptors

#%% the main function of the above functions

def SIFT(img,showDoGimgs = False):
    '''

    Parameters
    ----------
    img : a image (binary often)
    showDoGimgs : bool, optional
        True to show / visualize Gaussian Pyramid, otherwise False.

    Returns
    -------
    KeyPoints : 2D list
        a list consisting of np.ndarray shape (5,).
        x (x-axis location), y (y-axis location), one encoder, no idea #2, main direction
        one encoder is used to represent Octave No., Image No. of one certain octave
    discriptors : 2D list (corresponding to KeyPoints)
        a list consisting of np.ndarray shape (128,)
        every np.ndarray has 128 features.

    '''
    SIFT_SIGMA = 1.6
    SIFT_INIT_SIGMA = 0.5 # 假设的摄像头的尺度
    sigma0 = np.sqrt(SIFT_SIGMA**2-SIFT_INIT_SIGMA**2)

    n = 3 # the middle images in every octave in GoD pyramid

    DoG,GuassianPyramid = getDoG(img, n, sigma0)
    if showDoGimgs:
        for i in DoG:
            for j in i:
                plt.imshow(j.astype(np.uint8), cmap='gray')
                plt.axis('off')
                plt.show()

    KeyPoints = LocateKeyPoint(DoG, SIFT_SIGMA, GuassianPyramid, n)
    # KeyPoints is 2D list consisting of np.ndarray (5,)
    # x, y, no idea #1, no idea #2, main direction
    discriptors = calcDescriptors(GuassianPyramid,KeyPoints)

    return KeyPoints,discriptors

#%% post-process #1

def Lines(img,info,color = (255,0,0),err = 700):

    if len(img.shape) == 2:
        result = np.dstack((img,img,img))
    else:
        result = img
    k = 0
    for i in range(result.shape[0]):
        for j in range(result.shape[1]):
            temp = (info[:,1]-info[:,0])
            A = (j - info[:,0])*(info[:,3]-info[:,2])
            B = (i - info[:,2])*(info[:,1]-info[:,0])
            temp[temp == 0] = 1e-9
            t = (j-info[:,0])/temp
            e = np.abs(A-B)
            temp = e < err
            if (temp*(t >= 0)*(t <= 1)).any():
                result[i,j] = color
                k+=1
    print(k)

    return result

#%% post-process #2

def drawLines(X1,X2,Y1,Y2,dis,img,num = 10):
    
    # dis is abbr of distance

    info = list(np.dstack((X1,X2,Y1,Y2,dis))[0])
    info = sorted(info,key=lambda x:x[-1])
    info = np.array(info)
    info = info[:min(num,info.shape[0]),:]
    img = Lines(img,info)
    #plt.imsave('./sift/3.jpg', img)

    if len(img.shape) == 2:
        plt.imshow(img.astype(np.uint8),cmap='gray')
    else:
        plt.imshow(img.astype(np.uint8))
    plt.axis('off')
    #plt.plot([info[:,0], info[:,1]], [info[:,2], info[:,3]], 'c')
    # fig = plt.gcf()
    # fig.set_size_inches(int(img.shape[0]/100.0),int(img.shape[1]/100.0))
    #plt.savefig('./sift/2.jpg')
    plt.show()

#%% connect all functions to achieve SIFT (Scale-Invariant Feature Transform)

if __name__ == '__main__':
    origimg = plt.imread(r'SIFTimage2.jpeg')
    if len(origimg.shape) ==  3:
        img = origimg.mean(axis=-1)
    else:
        img = origimg
    keyPoints,discriptors = SIFT(img)


    origimg2 = plt.imread(r'SIFTimage1.jpeg')
    if len(origimg.shape) == 3:
        img2 = origimg2.mean(axis=-1)
    else:
        img2 = origimg2
    # no idea why to change the size of image 2
    ScaleRatio = img.shape[0]*1.0/img2.shape[0]

    img2 = np.array(Image.fromarray(img2).resize((int(round(ScaleRatio * img2.shape[1])),img.shape[0]), Image.BICUBIC))
    keyPoints2, discriptors2 = SIFT(img2,True)

    knn = KNeighborsClassifier(n_neighbors=1)
    knn.fit(discriptors,[0]*len(discriptors))
    match = knn.kneighbors(discriptors2,n_neighbors=1,return_distance=True)

    keyPoints = np.array(keyPoints)[:,:2] # the keypoint location in image 1
    keyPoints2 = np.array(keyPoints2)[:,:2] # the keypoint location in image 2

    keyPoints2[:, 1] = img.shape[1] + keyPoints2[:, 1]

    origimg2 = np.array(Image.fromarray(origimg2).resize((img2.shape[1],img2.shape[0]), Image.BICUBIC))
    result = np.hstack((origimg,origimg2))


    keyPoints = keyPoints[match[1][:,0]] # change the order based on KNN

    X1 = keyPoints[:, 1]
    X2 = keyPoints2[:, 1]
    Y1 = keyPoints[:, 0]
    Y2 = keyPoints2[:, 0]

    drawLines(X1,X2,Y1,Y2,match[0][:,0],result)
    
    
