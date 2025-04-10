import numpy as np  # dealing with arrays
import os  # dealing with directories
from random import shuffle  # mixing up or currently ordered data that might lead our network astray in training.
from tqdm import \
    tqdm  # a nice pretty percentage bar for tasks. Thanks to viewer Daniel BA1/4hler for this suggestion
import tflearn
from tflearn.layers.conv import conv_2d, max_pool_2d
from tflearn.layers.core import input_data, dropout, fully_connected
from tflearn.layers.estimator import regression
import tensorflow as tf
import matplotlib.pyplot as plt
from flask import Flask, render_template, url_for, request
import sqlite3
import cv2
import shutil




connection = sqlite3.connect('user_data.db')
cursor = connection.cursor()

command = """CREATE TABLE IF NOT EXISTS user(name TEXT, password TEXT, mobile TEXT, email TEXT)"""
cursor.execute(command)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/userlog', methods=['GET', 'POST'])
def userlog():
    if request.method == 'POST':

        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        name = request.form['name']
        password = request.form['password']

        query = "SELECT name, password FROM user WHERE name = '"+name+"' AND password= '"+password+"'"
        cursor.execute(query)

        result = cursor.fetchall()

        if len(result) == 0:
            return render_template('index.html', msg='Sorry, Incorrect Credentials Provided,  Try Again')
        else:
            return render_template('userlog.html')

    return render_template('index.html')


@app.route('/userreg', methods=['GET', 'POST'])
def userreg():
    if request.method == 'POST':

        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        name = request.form['name']
        password = request.form['password']
        mobile = request.form['phone']
        email = request.form['email']
        
        print(name, mobile, email, password)

        command = """CREATE TABLE IF NOT EXISTS user(name TEXT, password TEXT, mobile TEXT, email TEXT)"""
        cursor.execute(command)

        cursor.execute("INSERT INTO user VALUES ('"+name+"', '"+password+"', '"+mobile+"', '"+email+"')")
        connection.commit()

        return render_template('index.html', msg='Successfully Registered')
    
    return render_template('index.html')

@app.route('/image', methods=['GET', 'POST'])
def image():
    if request.method == 'POST':
 
        dirPath = "static/images"
        fileList = os.listdir(dirPath)
        for fileName in fileList:
            os.remove(dirPath + "/" + fileName)
        fileName=request.form['filename']
        dst = "static/images"
        

        shutil.copy("test/"+fileName, dst)
        image = cv2.imread("test/"+fileName)
        #color conversion
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        cv2.imwrite('static/gray.jpg', gray_image)
        #apply the Canny edge detection
        edges = cv2.Canny(image, 100, 200)
        cv2.imwrite('static/edges.jpg', edges)
        #apply thresholding to segment the image
        retval2,threshold2 = cv2.threshold(gray_image,128,255,cv2.THRESH_BINARY)
        cv2.imwrite('static/threshold.jpg', threshold2)
        # create the sharpening kernel
        kernel_sharpening = np.array([[-1,-1,-1],
                                    [-1, 9,-1],
                                    [-1,-1,-1]])

        # apply the sharpening kernel to the image
        sharpened = cv2.filter2D(image, -1, kernel_sharpening)

        # save the sharpened image
        cv2.imwrite('static/sharpened.jpg', sharpened)


        
        
        verify_dir = 'static/images'
        IMG_SIZE = 50
        LR = 1e-3
        MODEL_NAME = 'hyperspectral-{}-{}.model'.format(LR, '2conv-basic')
    ##    MODEL_NAME='keras_model.h5'
        def process_verify_data():
            verifying_data = []
            for img in os.listdir(verify_dir):
                path = os.path.join(verify_dir, img)
                img_num = img.split('.')[0]
                img = cv2.imread(path, cv2.IMREAD_COLOR)
                img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
                verifying_data.append([np.array(img), img_num])
                np.save('verify_data.npy', verifying_data)
            return verifying_data

        verify_data = process_verify_data()
        #verify_data = np.load('verify_data.npy')

        
        tf.compat.v1.reset_default_graph()
        #tf.reset_default_graph()

        convnet = input_data(shape=[None, IMG_SIZE, IMG_SIZE, 3], name='input')

        convnet = conv_2d(convnet, 32, 3, activation='relu')
        convnet = max_pool_2d(convnet, 3)

        convnet = conv_2d(convnet, 64, 3, activation='relu')
        convnet = max_pool_2d(convnet, 3)

        convnet = conv_2d(convnet, 128, 3, activation='relu')
        convnet = max_pool_2d(convnet, 3)

        convnet = conv_2d(convnet, 32, 3, activation='relu')
        convnet = max_pool_2d(convnet, 3)

        convnet = conv_2d(convnet, 64, 3, activation='relu')
        convnet = max_pool_2d(convnet, 3)

        convnet = fully_connected(convnet, 1024, activation='relu')
        convnet = dropout(convnet, 0.8)

        convnet = fully_connected(convnet, 5, activation='softmax')
        convnet = regression(convnet, optimizer='adam', learning_rate=LR, loss='categorical_crossentropy', name='targets')

        model = tflearn.DNN(convnet, tensorboard_dir='log')

        if os.path.exists('{}.meta'.format(MODEL_NAME)):
            model.load(MODEL_NAME)
            print('model loaded!')


        fig = plt.figure()
        
        str_label=" "
        accuracy=""
        pre=""
        pre1=""
        for num, data in enumerate(verify_data):

            img_num = data[1]
            img_data = data[0]

            y = fig.add_subplot(3, 4, num + 1)
            orig = img_data
            data = img_data.reshape(IMG_SIZE, IMG_SIZE, 3)
            # model_out = model.predict([data])[0]
            model_out = model.predict([data])[0]
            print(model_out)
            print('model {}'.format(np.argmax(model_out)))

            

            if np.argmax(model_out) == 0:
                str_label = "forest area"
                print("The predicted image of the hyperspectral image is forest areas with a accuracy  {} %".format(model_out[0]*100))
                accuracy="The predicted image of the hyperspectral image is forest areas with a accuracy  of {}%".format(model_out[0]*100)
                Pre = "The information about this analysis are:\n\n "
                Pre1 = ["A forest area is a region covered primarily by trees and vegetation, forming a natural habitat for diverse wildlife and contributing to the ecosystem's health",
                        "Forests play a crucial role in maintaining biodiversity, regulating climate, and supporting water cycles.",
                        "They also provide resources like timber, medicinal plants, and recreation, while serving as carbon sinks to mitigate climate change.",
                        "Forest areas can vary from tropical rainforests to temperate and boreal forests, each with distinct flora and fauna."]

                
            elif np.argmax(model_out) == 1:
                str_label  = "water resources"
                print("The predicted image of the hyperspectral image is water resources with a accuracy of {} %".format(model_out[1]*100))
                accuracy="The predicted image of the hyperspectral image is water resources with a accuracy  of {}%".format(model_out[1]*100)
                Pre = "The information about this analysis are:\n\n "
                Pre1 = ["Water resources refer to natural sources of water that are used for various purposes",
                        "including drinking, agriculture, industry, and energy production. These include surface water (rivers, lakes, reservoirs), groundwater (aquifers)",
                        "atmospheric water, and their sustainable management is crucial for meeting human and ecological needs."]
  
                
            elif np.argmax(model_out) == 2:
                str_label = "agricultural lands"
                print("The predicted image of the hyperspectral image is agricultral lands with a accuracy of {} %".format(model_out[2]*100))
                accuracy="The predicted image f the hyperspectral image is agricultral lands with a accuracy of {}%".format(model_out[2]*100)
                Pre = "The information about this analysis are:\n\n "
                Pre1 = ["Hyperspectral crop images capture detailed spectral information across a wide range of wavelengths, enabling precise analysis of crop health, stress",
                        "and nutrient content. This technology supports applications in precision agriculture, disease detection, and yield optimization.."]  
                

            elif np.argmax(model_out) == 3:
                str_label = "residental area"
                print("The predicted image of the hyperspectral image is residential area with a accuracy of {} %".format(model_out[3]*100))
                accuracy="The predicted image of the hyperspectral image is residential area with a accuracy of {}%".format(model_out[3]*100)
                Pre = "The information about this analysis are:\n\n "
                Pre1 = ["A residential area is a zone primarily designated for housing and living purposes, typically consisting of houses, apartments, or other dwelling types",
                        "These areas are designed to provide a safe and comfortable environment for people to live, with essential amenities like schools, parks, shops, and",
                        "public services nearby. Residential areas can vary in density, ranging from low-density suburban neighborhoods to high-density urban developments."]  
                                
            elif np.argmax(model_out) == 4:
                str_label = "desert"
                print("The predicted image of the hyperspectral image is desert with a accuracy of {} %".format(model_out[4]*100))
                accuracy="The predicted image of the hyperspectral image is desert with a accuracy of {}%".format(model_out[4]*100)
                Pre = "The information about this analysis are:\n\n "
                
                Pre1 = ["A desert is a barren landscape that receives very little precipitation (rain or snow)",
                        "typically less than 10 inches (25 cm) per year.Due to this extreme dryness, deserts have sparse vegetation and harsh living conditions.",
                        "Arid: Deserts are dry and have low humidity",
                        "Little rainfall: Deserts receive less than 10 inches of rain per year",
                        "Evaporation: Water evaporates faster than it can be replenished by rain.",
                        "Sparse vegetation: Deserts have little plant coverage.",
                        "Limited population: Deserts have a limited population of people and animals."]  
                
       
        return render_template('userlog.html', status=str_label,accuracy=accuracy,Precaution=Pre,Precaution1=Pre1,ImageDisplay="http://127.0.0.1:5000/static/images/"+fileName,ImageDisplay1="http://127.0.0.1:5000/static/gray.jpg",ImageDisplay2="http://127.0.0.1:5000/static/edges.jpg",ImageDisplay3="http://127.0.0.1:5000/static/threshold.jpg",ImageDisplay4="http://127.0.0.1:5000/static/sharpened.jpg")
        
    return render_template('index.html')

@app.route('/logout')
def logout():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
