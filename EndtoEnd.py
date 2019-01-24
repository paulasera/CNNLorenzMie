import numpy as np
import json, keras
import re,os,sys
import warnings
from matplotlib import pyplot as plt
from PIL import Image
from keras import backend as K
sys.path.append('/home/group/lauren_yolo/')
from pylorenzmie.theory.Instrument import Instrument, coordinates
from Estimator import Estimator
from YOLocalizer import Localizer
from crop import crop
from pylorenzmie.theory.Feature import Feature
from lmfit import report_fit

class EndtoEnd(object):

    '''
    Attributes
    __________
    localizer: Localizer
        Object resprenting the trained YOLO model
    estimator: Estimator
        Object representing the trained Keras model
    instrument: Instrument
        Object resprenting the light-scattering instrument
        
    Methods
    _______
    predict(img_names_path=None, img_list=[], save_predictions=False, predictions_path='predictions.json', save_crops=False, crop_dir='./cropped_img')
        loads img_names.txt from str 'img_names_path', imports images
        img_names.txt contains absolute paths of images, separated by line break
        or, just input images as a list
        predicts on list of images using self.model
        saves output to predictions_path if save_predictions = True
        saves cropped images to crop_dir if save_crops = True
    '''
    
    def __init__(self,
                 localizer=None,
                 estimator=None):

        '''
        Parameters
        ----------
        pixels: tuple                    #coordinates instead?                                           
            (img_rows, img_cols)
        instrument: Instrument  
            Object resprenting the light-scattering instrument
        model_path: str
            path to model.h5 file
        '''
        if estimator is None:
            self.estimator = Estimator()
        else:
            self.estimator = estimator
        if localizer is None:
            self.localizer = Localizer()
        else:
            self.localizer = localizer
        self.coordinates = localizer.coordinates
        if estimator.instrument != localizer.instrument:
            warnings.warn("Warning: estimator and localizer have different instruments")
        self.instrument = estimator.instrument

    @property
    def coordinates(self):
        return self._coordinates

    @coordinates.setter
    def coordinates(self, coordinates):
        self._coordinates = coordinates
    
    @property
    def instrument(self):
        return self._instrument

    @instrument.setter
    def instrument(self, instrument):
        self._instrument = instrument

    @property
    def estimator(self):
        return self._estimator

    @estimator.setter
    def estimator(self, estimator):
        self._estimator = estimator
        
    @property
    def localizer(self):
        return self._localizer

    @localizer.setter
    def localizer(self, localizer):
        self._localizer = localizer

    def predict(self, img_names_path=None,
                save_predictions=False, predictions_path='predictions.json',
                save_crops=False, crop_dir='./cropped_img'):
        '''
        output:
        predictions: list of features
        n images => n lists of dicts
        per holo prediction:
            {img_path: 'image0001.png', 'x': x_centroid, 'y': y_centroid, 'z': z_p, 'a': a_p, 'n': n_p}
            if save_crops=True, cropped image is saved to img_path (can be ignored otherwise)
        '''
        (a,b,c,d) = self.estimator.model.input_shape
        crop_px = (b,c)
        yolo_predictions = self.localizer.predict(img_names_path = img_names_path, save_to_json=False)
        crop_img = crop(img_names_path = img_names_path, xy_preds = yolo_predictions, new_pixels = crop_px, save_to_folder = save_crops, crop_dir = crop_dir)
        char_predictions = self.estimator.predict(img_list = crop_img, save_to_json=False)
        out_features = []
        for num in range(len(crop_img)):
            f = Feature()
            shape = crop_px
            f.model.coordinates = coordinates(shape)
            f.model.instrument = self.instrument
            data = np.array(crop_img[num])/100
            data = np.array([item for sublist in data for item in sublist])
            f.data = data
            p = f.model.particle
            z = char_predictions['z_p'][num]
            a = char_predictions['a_p'][num]
            n = char_predictions['n_p'][num]
            p.r_p = [100, 100, z]
            p.a_p = a
            p.n_p = n
            out_features.append(f)
        return out_features
            


if __name__ == '__main__':
    from pylorenzmie.theory.Instrument import coordinates
    
    #keras_model_path = '/home/group/lauren_yolo/Holographic-Characterization/models/predict_lab_stamp_final_800.h5'
    keras_model_path = '/home/group/lauren_yolo/Holographic-Characterization/models/predict_lab_stamp_pylm_800.h5'
    #cropdir = '/home/group/endtoend/cropped_img/'
    #predictions_json = '/home/group/endtoend/ML_predictions.json'       
    estimator = Estimator(model_path=keras_model_path)

    
    darknet_filehead = '/home/group/lauren_yolo/darknet'
    config_path = darknet_filehead + '/cfg/holo.cfg'
    weight_path = darknet_filehead + '/backup/holo_55000.weights'
    meta_path = darknet_filehead + '/cfg/holo.data'
    shape = (1024,1280)
    coords = coordinates(shape)
    localizer = Localizer(coordinates = coords, config_path = config_path, weight_path = weight_path, meta_path = meta_path)


    e2e = EndtoEnd(estimator=estimator, localizer=localizer)
    img_files = '/home/group/example_data/movie_img/filenames.txt'
    features = e2e.predict(img_names_path = img_files)
    example = features[3]
    example.model.instrument.wavelength = 0.447
    example.model.instrument.magnification = 0.048
    example.model.instrument.n_m = 1.340

    '''
    h = example.model.hologram()
    fig, (ax1, ax2) = plt.subplots(1,2)
    ax1.imshow(example.data.reshape(pix), cmap='gray')
    ax2.imshow(h.reshape(pix), cmap='gray')
    fig.suptitle('Data, Predicted Hologram')
    plt.show()
    '''
    pix = (200,200)
    result = example.optimize()
    report_fit(result)
    h = example.model.hologram()
    fig, (ax1, ax2, ax3) = plt.subplots(1,3)
    ax1.imshow(example.data.reshape(pix), cmap='gray')
    ax2.imshow(h.reshape(pix), cmap='gray')
    ax3.imshow(example.residuals().reshape(pix), cmap='gray')
    fig.suptitle('Data, optimized hologram, residual')
    plt.show()