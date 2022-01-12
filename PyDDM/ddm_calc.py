###########################################################################
# File moved from other DDM repository on 5/21/2021                   #####
# Renamed ddm_calc.py from ddm.py from ddm_clean.py                   #####
# Authors:                                                            #####
#   Ryan McGorty (rmcgorty@sandiego.edu)                              #####
###########################################################################

import sys
import copy
import numpy as np
import xarray as xr
from scipy.optimize import least_squares, curve_fit
from scipy.special import gamma
from scipy.signal import blackmanharris #for Blackman-Harris windowing
import socket
import skimage
import fit_parameters_dictionaries as fpd
import logging
from IPython.core.display import clear_output

class IPythonStreamHandler(logging.StreamHandler):
    "A StreamHandler for logging that clears output between entries."
    def emit(self, s):
        clear_output(wait=True)
        print(s.getMessage())
    def flush(self):
        sys.stdout.flush()

logger = logging.getLogger("DDM Calculations")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
#ch = IPythonStreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

logger2 = logging.getLogger("DDM Analysis")
logger2.setLevel(logging.DEBUG)
ch2 = logging.StreamHandler()
#ch = IPythonStreamHandler()
ch2.setLevel(logging.DEBUG)
formatter2 = logging.Formatter('%(name)s - %(message)s')
ch2.setFormatter(formatter2)
logger2.addHandler(ch2)

comp_name = socket.gethostname()

#This function is used to determine a new time when a distribution
# of decay times are present
newt = lambda t,s: (1./s)*gamma(1./s)*t

#Sometimes it is helpful to apply a window function to the images (deals with beads/molecules leaving the field of view)
def window_function(im):
    '''
    Use of windowing function described in paper here: (https://arxiv.org/abs/1707.07501)

    :param im: Images series
    :type im: numpy array

    More information: `link_to_article <https://link.springer.com/article/10.1140%2Fepje%2Fi2017-11587-3>`_

    '''
    if im.ndim==3:
        numPixels = im.shape[1]
    elif im.ndim==2:
        numPixels = im.shape[0]
    elif isinstance(im, int):
        numPixels = im
    x,y = np.meshgrid(blackmanharris(numPixels),blackmanharris(numPixels))
    filter_func = x*y
    return filter_func

def determining_A_and_B(im, use_BH_filter=False,
                        centralAngle=None, angRange=None):
    '''
    Calculates the 2D Fourier transform of each frame in the image series and takes the radial averages.
    This in order to find the amplitude and background.

    :param im: Images series
    :type im: numpy array
    :param use_BH_filter: Apply window filter
    :type use_BH_filter: bool

    :return:
            * radial_averages (*numpy array*)- radial average of all frames in provided image series


    '''
    av_fftsq_of_each_frame = np.zeros_like(im[0]*1.0) #initialize array
    nFrames,ndx,ndy = im.shape
    if use_BH_filter:
        filterfunction = window_function(im)
    else:
        filterfunction = np.ones_like(im[0])
    for i in range(nFrames):
        fft_of_image = np.fft.fft2(im[i]*filterfunction)
        sqr_of_fft = np.fft.fftshift(fft_of_image*np.conj(fft_of_image))
        av_fftsq_of_each_frame = av_fftsq_of_each_frame + abs(sqr_of_fft)
    av_fftsq_of_each_frame = av_fftsq_of_each_frame/(1.0*nFrames*ndx*ndy)
    rad_av_av_fftsq = radial_avg_ddm_matrix(av_fftsq_of_each_frame.reshape(1,ndx,ndy),
                                      centralAngle=centralAngle,
                                      angRange=angRange)
    return rad_av_av_fftsq

def generateLogDistributionOfTimeLags(start,stop,numPoints):
    '''
    This function will generate a logarithmically spaced set of numbers.
    This is for generating the lag times over which to calculate the intermediate scattering function.

    :param start: First time delay (usually 1)
    :type start: int
    :param stop: Last time delay (often 600 or 100 but can be ~20-50 for quick calculations)
    :type stop: int
    :param numPoints: number of time delays (can be 60 for quick calculations)


    :return:
        * listOfLagTimes (*List[int]*)- list of numbers from start to stop, logarithmically spaced

    '''
    newpts = [] #empty list

    #first, will make list of numbers log-spaced longer than intended list.
    #This is due to fact that after converting list to integers, we will have
    # multiple duplicates. So to generate enough *unique* numbers we need to
    # first make a longer-than-desired list.
    listOfLagTimes = np.geomspace(start, stop, num=numPoints, dtype=int)
    numberOfPoints = len(np.unique(listOfLagTimes))
    if numberOfPoints == numPoints:
        return np.unique(listOfLagTimes)
    else:
        newStartingNumberOfPoints = numPoints
        while numberOfPoints < numPoints:
            newStartingNumberOfPoints += 1
            listOfLagTimes = np.geomspace(start, stop, num=newStartingNumberOfPoints, dtype=int)
            numberOfPoints = len(np.unique(listOfLagTimes))
        return np.unique(listOfLagTimes)

def new_ddm_matrix(imageArray):
    '''

    '''

    #First, generate Fourier transforms of all images
    fft_ims = np.zeros(imageArray.shape,dtype='complex128')
    ndx,ndy = imageArray[0].shape
    num_images = imageArray.shape[0]
    for i,im in enumerate(imageArray):
        fft_ims[i] = np.fft.fftshift(np.fft.fft2(im))/(ndx*ndy)

    #Getting the "d_c" term from the paper:
    #   Norouzisadeh, M., Chraga, M., Cerchiari, G. & Croccolo, F. The modern structurator:
    #    increased performance for calculating the structure function. Eur. Phys. J. E 44, 146 (2021).
    fft_in_times = np.fft.fftn(fft_ims, axes=(0,))
    new_matrix = np.conj(fft_in_times)*fft_in_times
    inverse_fft_in_times = np.fft.ifftn(new_matrix, axes=(0,))
    return np.real(inverse_fft_in_times)


def computeDDMMatrix(imageArray, dts, use_BH_windowing=False, fast_mode=False, quiet=False):
    '''
    This code calculates the image structure function for the series of images
    in imageArray at the lag times specified in dts.
    :param imageArray: image data
    :param dts: 1D array of delay times
    :param shiftAtEnd: defaults to False
    :param noshift: defaults to False
    :param submean: defaults to true
    :return: two numpy arrays: the fft'd data and the list of times
    '''

    ### TO-DO: check that imageArray is in fact a 3D array
    #
    #

    if use_BH_windowing:
        filterfunction = window_function(imageArray)
    else:
        filterfunction = np.ones_like(imageArray[0])

    #Determines the dimensions of the data set (number of frames, x- and y-resolution in pixels
    ntimes, ndx, ndy = imageArray.shape

    #Initializes array for Fourier transforms of differences
    fft_diffs = np.zeros((len(dts), ndx, ndy),dtype=np.float)

    steps_in_diffs = np.ceil(dts/3.0).astype(np.int)
    if fast_mode:
        w = np.where(steps_in_diffs < 20)
        steps_in_diffs[w] = 20


    j=0

    num_pairs_per_dt = []


    #Loops over each delay time
    for k,dt in enumerate(dts):

        if not quiet:
            if k%4 == 0:
                #print("Running dt=%i...\n" % dt)
                logger.info("Running dt = %i..." % dt)

        #Calculates all differences of images with a delay time dt
        all_diffs = filterfunction*(imageArray[dt:].astype(np.float) - imageArray[0:(-1*dt)].astype(np.float))

        #Rather than FT all image differences of a given lag time, only select a subset
        all_diffs_new = all_diffs[0::steps_in_diffs[k],:,:]

        #Loop through each image difference and take the fourier transform
        for i in range(0,all_diffs_new.shape[0]):
            temp = np.fft.fft2(all_diffs_new[i]) # - all_diffs_new[i].mean())
            fft_diffs[j] = fft_diffs[j] + abs(temp*np.conj(temp))/(ndx*ndy)

        num_pairs_per_dt.append(all_diffs_new.shape[0])

        #Divide the running sum of FTs to get the average FT of the image differences of that lag time
        fft_diffs[j] = fft_diffs[j] / (all_diffs_new.shape[0])
        fft_diffs[j] = np.fft.fftshift(fft_diffs[j])

        #fft_diffs[j] = np.fft.fftshift(np.fft.fft2(all_diffs.mean(axis=0)-all_diffs.mean()))
        j = j+1

    return fft_diffs, np.array(num_pairs_per_dt)


def get_FF_DDM_matrix(imageFile, dts, submean=True,
                       useBH_windowing=False):
    '''
    This code calculates the far-field DDM matrix for the series of images
    in imageFile at the lag times specified in dts.
    :param imageFile: Either a string specifying the location of the data or the data itself as a numpy array
    :param dts: 1D array of delay times
    :param limitImsTo: defaults to None
    :param every: defaults to None
    :param shiftAtEnd: defaults to False
    :param noshift: defaults to False
    :param submean: defaults to true
    :return: two numpy arrays: the fft'd data and the list of times

    For more on this far-field DDM method see:

    Buzzaccaro, S., Alaimo, M. D., Secchi, E. & Piazza, R. Spatially: resolved heterogeneous dynamics in a strong colloidal gel. J. Phys.: Condens. Matter 27, 194120 (2015).

    Philippe, A. et al. An efficient scheme for sampling fast dynamics at a low average data acquisition rate. J. Phys.: Condens. Matter 28, 075201 (2016).


    '''
    if isinstance(imageFile, np.ndarray):
        ims = imageFile
    elif isinstance(imageFile, basestring):
        ims = skimage.io.imread(imageFile)
    else:
        print("Not sure what you gave for imageFile")
        return 0

    if useBH_windowing:
        filterfunction = window_function(ims)
    else:
        filterfunction = np.ones_like(ims[0]*1.0)

    #Determines the dimensions of the data set (number of frames, x- and y-resolution in pixels
    ntimes, ndx, ndy = ims.shape

    #Initializes array for Fourier transforms of images
    fft_images = np.zeros((ntimes, ndx, ndy),dtype=np.complex128)

    ddm_matrix = np.zeros((len(dts),ndx,ndy),dtype=np.float)

    for i in range(ntimes):
        new_image = filterfunction*ims[i]
        if submean:
            new_image = new_image - new_image.mean()
        fft_images[i] = np.fft.fftshift(np.fft.fft2(new_image))/(ndx*ndy)

    for k,dt in enumerate(dts):
        all_pairs_1 = fft_images[dt:] * fft_images[0:(-1*dt)]
        norm_1 = np.mean(abs(fft_images[dt:] * np.conj(fft_images[dt:])),axis=0)
        norm_2 = np.mean(abs(fft_images[0:(-1*dt)] * np.conj(fft_images[0:(-1*dt)])),axis=0)
        all_pairs_2 = abs(all_pairs_1 * np.conj(all_pairs_1))
        all_pairs_3 = all_pairs_2.mean(axis=0) / (norm_1 * norm_2)
        ddm_matrix[k] = all_pairs_3

    return ddm_matrix, dts



def fit_ddm_all_qs(dData, times, param_dictionary,
                   amplitude_from_ims,
                   first_use_leastsq=True,
                   use_curvefit_method=False,
                   sigma=None,
                   update_tau_based_on_estimated_diffcoeff=False,
                   estimated_diffcoeff=None,
                   update_tau_based_on_estimated_velocity=False,
                   estimated_velocity=None,
                   update_tau2_based_on_estimated_diffcoeff=False,
                   estimated_diffcoeff2=None,
                   update_tau2_based_on_estimated_velocity=False,
                   estimated_velocity2=None,
                   update_limits_on_tau=False,
                   updated_lims_on_tau_fraction=0.1,
                   use_A_from_images_as_guess=False,
                   update_limits_on_A=False,
                   updated_lims_on_A_fraction=0.1,
                   err=None, logfit=False,maxiter=600,
                   factor=1e-3, quiet=False, quiet_on_method=True,
                   last_times = None, given_fit_method = None,
                   update_initial_guess_each_q = False,
                   debug=False):

    '''


    '''

    num_times, num_qs = dData.shape

    best_fit_params = {}

    number_of_parameters = len(param_dictionary['parameter_info'])

    for param in param_dictionary['parameter_info']:
        best_fit_params[param['parname']] = np.zeros((num_qs))

    theory = np.empty((num_times, num_qs)) #Empyt array to store theoretical models calculated with best fits
    theory.fill(np.nan)

    for i in range(num_qs):
        if debug:
            print("Fitting for q index of %i..." % i)
        if last_times is not None:
            if np.isscalar(last_times):
                data_to_fit = dData[:last_times,i]
                times_to_fit = times[:last_times]
            else:
                data_to_fit = dData[:int(last_times[i]),i]
                times_to_fit = times[:int(last_times[i])]
        else:
            data_to_fit = dData[:,i]
            times_to_fit = times

        #For basing initial guess for 'Tau' on expected diffusion coefficient or velocity
        qvalue = dData.q[i].values
        if update_tau_based_on_estimated_diffcoeff and (estimated_diffcoeff is not None):
            for element in param_dictionary['parameter_info']:
                if (element['parname']=='Tau') and (i>0):
                    new_tau = 1./(qvalue*qvalue*estimated_diffcoeff)
                    if update_limits_on_tau:
                        element['limits'][0] = new_tau * (1-updated_lims_on_tau_fraction)
                        element['limits'][1] = new_tau * (1+updated_lims_on_tau_fraction)
                        element['value'] = new_tau
                    if (new_tau>=element['limits'][0]) and (new_tau<=element['limits'][1]):
                        element['value'] = new_tau
        elif update_tau_based_on_estimated_velocity and (estimated_velocity is not None):
            for element in param_dictionary['parameter_info']:
                if (element['parname']=='Tau') and (i>0):
                    new_tau = 1./(qvalue*estimated_velocity)
                    if update_limits_on_tau:
                        element['limits'][0] = new_tau * (1-updated_lims_on_tau_fraction)
                        element['limits'][1] = new_tau * (1+updated_lims_on_tau_fraction)
                        element['value'] = new_tau
                    elif (new_tau>=element['limits'][0]) and (new_tau<=element['limits'][1]):
                        element['value'] = new_tau
        if update_tau2_based_on_estimated_diffcoeff and (estimated_diffcoeff2 is not None):
            for element in param_dictionary['parameter_info']:
                if (element['parname']=='Tau2') and (i>0):
                    new_tau2 = 1./(qvalue*qvalue*estimated_diffcoeff2)
                    if update_limits_on_tau:
                        element['limits'][0] = new_tau2 * (1-updated_lims_on_tau_fraction)
                        element['limits'][1] = new_tau2 * (1+updated_lims_on_tau_fraction)
                        element['value'] = new_tau2
                    elif (new_tau2>=element['limits'][0]) and (new_tau2<=element['limits'][1]):
                        element['value'] = new_tau2
        elif update_tau2_based_on_estimated_velocity and (estimated_velocity2 is not None):
            for element in param_dictionary['parameter_info']:
                if (element['parname']=='Tau2') and (i>0):
                    new_tau2 = 1./(qvalue*estimated_velocity2)
                    if update_limits_on_tau:
                        element['limits'][0] = new_tau2 * (1-updated_lims_on_tau_fraction)
                        element['limits'][1] = new_tau2 * (1+updated_lims_on_tau_fraction)
                        element['value'] = new_tau2
                    elif (new_tau2>=element['limits'][0]) and (new_tau2<=element['limits'][1]):
                        element['value'] = new_tau2
        if use_A_from_images_as_guess:
            for element in param_dictionary['parameter_info']:
                if (element['parname']=='Amplitude') and (i>0):
                    new_A = amplitude_from_ims[i]
                    if new_A<0:
                        new_A=1
                    if update_limits_on_A:
                        element['limits'][0] = new_A * (1-updated_lims_on_A_fraction)
                        element['limits'][1] = new_A * (1+updated_lims_on_A_fraction)
                        element['value'] = new_A
                    elif (new_A>=element['limits'][0]) and (new_A<=element['limits'][1]):
                        element['value'] = new_A


        ret_params, theory[:len(times_to_fit),i], error, chi2 = fit_ddm(data_to_fit, times_to_fit, param_dictionary,
                                                                        first_use_leastsq=first_use_leastsq,
                                                                        use_curvefit_method=use_curvefit_method,
                                                                        sigma=sigma,
                                                                        err=err, logfit=logfit,maxiter=maxiter,
                                                                        factor=factor, quiet=quiet,
                                                                        quiet_on_method=quiet_on_method)

        for j, bf_param in enumerate(best_fit_params):
            best_fit_params[bf_param][i] = ret_params[j]

    return best_fit_params, theory



def fit_ddm(dData, times, param_dictionary,
            first_use_leastsq=True,
            use_curvefit_method=False,
            sigma=None,
            err=None, logfit=False,maxiter=600,
            factor=1e-3, quiet=False, quiet_on_method=True):


    parameter_values = fpd.extract_array_of_parameter_values(param_dictionary)
    param_mins, param_maxs = fpd.extract_array_of_param_mins_maxes(param_dictionary)
    #print(param_mins)

    #If 'first_use_leastsq' is true, we will use the scipy.optimize leastsquares fitting method
    #  first (just to get initial parameters).
    if first_use_leastsq:
        lsqr_params, lsqr_theory, lsqr_error = execute_LSQ_fit(dData, times, param_dictionary, debug=False)
        which_params_should_be_fixed = fpd.extract_array_of_fixed_or_not(param_dictionary)
        for i,tofix in enumerate(which_params_should_be_fixed):
            if not tofix:
                parameter_values[i] = lsqr_params[i]

    #print(parameter_values)
    if use_curvefit_method:
        if first_use_leastsq:
            updated_param_dict = copy.deepcopy(param_dictionary)
            fpd.populate_intial_guesses(updated_param_dict, parameter_values)
            res = execute_ScipyCurveFit_fit(dData, times, updated_param_dict, sigma=sigma, debug=False)
        else:
            res = execute_ScipyCurveFit_fit(dData, times, param_dictionary, sigma=sigma, debug=False)
        return res[0], res[1], res[2], None


    else:
        return lsqr_params, lsqr_theory, lsqr_error, None




def execute_LSQ_fit(dData, times, param_dict, debug=True):

    theory_function = param_dict['model_function']

    params_to_pass_to_lsqr = fpd.extract_array_of_parameter_values(param_dict)
    minimum_of_parameters, maximum_of_parameters = fpd.extract_array_of_param_mins_maxes(param_dict)

    #define the error function (difference between data and the model)
    error_function = lambda parameters: dData-theory_function(times,*parameters)

    if debug:
        print("Parameters going to lsqr fitting: ", params_to_pass_to_lsqr)
        print("Min parameters going to lsqr fitting: ", minimum_of_parameters)
        print("Max parameters going to lsqr fitting: ", maximum_of_parameters)
        print("Size of data going to lsqr fitting: %i" % len(dData))
        print("Number of lag times going to lsqr fitting: %i" % len(times))
    lsqr_results = least_squares(error_function, params_to_pass_to_lsqr, bounds=(minimum_of_parameters, maximum_of_parameters))
    lsqr_params = lsqr_results['x']

    return lsqr_params, theory_function(times,*lsqr_params), lsqr_results['fun']


def execute_ScipyCurveFit_fit(dData, times, param_dict, sigma=None, debug=True, method=None):

    theory_function = param_dict['model_function']

    params_to_pass_to_cf = fpd.extract_array_of_parameter_values(param_dict)
    minimum_of_parameters, maximum_of_parameters = fpd.extract_array_of_param_mins_maxes(param_dict)

    if debug:
        print("Parameters going to CurveFit fitting: ", params_to_pass_to_cf)
        print("Min parameters going to CurveFit fitting: ", minimum_of_parameters)
        print("Max parameters going to CurveFit fitting: ", maximum_of_parameters)
        print("Size of data going to CurveFit fitting: %i" % len(dData))
        print("Number of lag times going to CurveFit fitting: %i" % len(times))
    try:
        if method == 'lm':
            #With 'lm' method, must be unconstrained problem. So no bounds
            cf_results = curve_fit(theory_function, times, dData, p0=params_to_pass_to_cf,
                                   sigma=sigma, absolute_sigma=False, method='lm')
        elif method == None:
            cf_results = curve_fit(theory_function, times, dData, p0=params_to_pass_to_cf,
                                   bounds=(minimum_of_parameters, maximum_of_parameters),
                                   sigma=sigma, absolute_sigma=False)
        else:
            cf_results = curve_fit(theory_function, times, dData, p0=params_to_pass_to_cf,
                                   bounds=(minimum_of_parameters, maximum_of_parameters),
                                   sigma=sigma, absolute_sigma=False, method=method)
        cf_params = cf_results[0]
        errors_1stddev = np.sqrt(np.diag(cf_results[1]))
    except:
        cf_params = params_to_pass_to_cf
        errors_1stddev = np.zeros_like(cf_params)

    return cf_params, theory_function(times,*cf_params), errors_1stddev


def generate_mask(im, centralAngle, angRange):
    '''
    Generates a mask of the same size as 'im'.
    If the DDM matrix is not to be radially averaged, we can use a mask
      to average values of the matrix only in some angular range around
      a central angle.

    Parameters
    ----------
    im : ndarray
        DESCRIPTION.
    centralAngle : float
        DESCRIPTION.
    angRange : float
        DESCRIPTION.

    Returns
    -------
    mask : ndarray
        DESCRIPTION.

    '''
    nx,ny = im.shape
    xx = np.arange(-(nx-1)/2., nx/2.)
    yy = np.arange(-(ny-1)/2., ny/2.)
    x,y = np.meshgrid(yy,xx)
    q = np.sqrt(x**2 + y**2)
    angles = np.arctan2(x,y)

    mask = np.ones_like(angles)
    if (angRange is not None) and (centralAngle is not None):
        mask = np.empty_like(q)
        mask.fill(np.nan)
        centralAngleRadians = centralAngle * np.pi/180
        angRangeRadians = angRange * np.pi/180
        w = np.where(abs(angles-centralAngleRadians)<angRangeRadians)
        mask[w] = 1
        maskCopy = np.fliplr(np.flipud(mask))
        mask[maskCopy==1] = 1
    return mask


def find_radial_average(im, mask=None, centralAngle=None, angRange=None):
    '''
    For a single 2D matrix, finds radial average

    '''
    #From https://github.com/MathieuLeocmach/DDM/blob/master/python/DDM.ipynb
    nx,ny = im.shape

    if (centralAngle!=None) and (angRange!=None) and (mask==None):
        mask = generate_mask(im, centralAngle, angRange)
    elif mask==None:
        mask = np.ones_like(im)

    #dists = np.sqrt(np.fft.fftfreq(shape[0])[:,None]**2 +  np.fft.fftfreq(shape[1])[None,:]**2)

    dists = np.sqrt(np.arange(-1*nx/2, nx/2)[:,None]**2 + np.arange(-1*ny/2, ny/2)[None,:]**2)

    #because sometimes there is a "cross" shape in Fourier transform:
    #dists[0] = 0
    #dists[:,0] = 0

    bins = np.arange(max(nx,ny)/2+1)
    histo_of_bins = np.histogram(dists, bins)[0]
    h = np.histogram(dists, bins, weights=im*mask)[0]
    return h/histo_of_bins


def radial_avg_ddm_matrix(ddm_matrix, mask=None,
                          centralAngle=None, angRange=None,
                          remove_vert_line=True):
    #From https://github.com/MathieuLeocmach/DDM/blob/master/python/DDM.ipynb
    nx,ny = ddm_matrix[0].shape
    dists = np.sqrt(np.arange(-1*nx/2, nx/2)[:,None]**2 + np.arange(-1*ny/2, ny/2)[None,:]**2)

    bins = np.arange(max(nx,ny)/2+1) - 0.5
    histo_of_bins = np.histogram(dists, bins)[0]

    if (centralAngle!=None) and (angRange!=None) and (mask==None):
        mask = generate_mask(ddm_matrix[0], centralAngle, angRange)
    elif mask==None:
        mask = np.ones_like(ddm_matrix[0])

    array_to_radial_avg = ddm_matrix[0]
    if remove_vert_line:
        array_to_radial_avg[:,int(ny/2)]=0
    h = np.histogram(dists, bins, weights=mask*array_to_radial_avg)[0]

    ravs = np.zeros((ddm_matrix.shape[0], len(h)))
    ravs[0] = h/histo_of_bins

    for i in range(1,ddm_matrix.shape[0]):
        array_to_radial_avg = ddm_matrix[i]
        if remove_vert_line:
            array_to_radial_avg[:,int(ny/2)]=0
        h = np.histogram(dists, bins, weights=mask*array_to_radial_avg)[0]
        ravs[i] = h/histo_of_bins
    return ravs


def get_MSD_from_DDM_data(q, A, D, B, qrange_to_avg):
    '''
    From Eq. 6 of Bayles, A. V., Squires, T. M. & Helgeson, M. E. Probe microrheology
         without particle tracking by differential dynamic microscopy.
         Rheol Acta 56, 863–869 (2017).

    '''
    msd = (4./(q*q)) * np.log(A / (A-D+B))
    msd_mean = msd[qrange_to_avg[0]:qrange_to_avg[1],:].mean(axis=0)
    msd_stddev = msd[qrange_to_avg[0]:qrange_to_avg[1],:].std(axis=0)
    return msd_mean, msd_stddev



