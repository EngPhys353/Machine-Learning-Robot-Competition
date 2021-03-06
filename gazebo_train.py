import gym
import time
import numpy
from keras import models
from sklearn.preprocessing import LabelEncoder
from keras.utils import to_categorical


import cv2
import rospy
import roslaunch
import time
import numpy as np

import cv2
import math

import string
import robot


def get_plate(model, letters, invert_dict):
    plate = []
    for pic in letters:
        size = (32, 32)
        img = cv2.cvtColor(pic, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, size, interpolation=cv2.INTER_CUBIC)
        img = np.array(img)/255.0
        img_aug = np.expand_dims(img, axis=0)
        y_predict = conv_model.predict(img_aug)[0]
        result_int = np.argmax(y_predict)
        result = invert_dict[result_int]
        plate.append(result)
    seperator = ''
    license_plate = seperator.join(plate)
    #print(license_plate)
    return license_plate


def get_encoder(data):
    data = np.array(data)
    label_encoder = LabelEncoder()
    integer_encoded = label_encoder.fit_transform(data)
    encoded = to_categorical(integer_encoded)
    invert_dict = dict(zip(integer_encoded, data))
    return encoded, invert_dict


def filter_blue(original_img):
    hsv = cv2.cvtColor(original_img, cv2.COLOR_BGR2HSV)
    low = np.uint8([[[40, 0, 0]]])
    up = np.uint8([[[255, 96, 96]]])

    hsv_low = cv2.cvtColor(low, cv2.COLOR_BGR2HSV)
    hsv_high = cv2.cvtColor(up, cv2.COLOR_BGR2HSV)

    # Threshold of blue in HSV space
    lower_blue = np.array([hsv_low[0][0][0], hsv_high[0][0][1], hsv_low[0][0][2]])
    upper_blue = np.array([hsv_high[0][0][0], hsv_low[0][0][1], hsv_high[0][0][2]])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    return mask


def find_letters(binaryImg, drawOn):
    contours, _ = cv2.findContours(binaryImg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filtered_cnt = []
    dimensions = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if x > 3:
            x = x-3
        else: 
            x = 0
        if y > 3: 
            y = y-3
        else: 
            y = 0
        corners = (x, y, w+6, h+8)
        dimensions.append(corners)
    dimensions = sorted(dimensions, key=lambda l: l[0])

    if len(dimensions) == 4:
        for dim in dimensions:
            cropped_img = drawOn[dim[1]:dim[1]+dim[3], dim[0]:dim[0]+dim[2]]
            filtered_cnt.append(cropped_img)
        return True, filtered_cnt
    return False, filtered_cnt


def find_contours(binaryImg, quarter_drawOn):
    contours, _ = cv2.findContours(binaryImg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    plates_array = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area_ratio = float(cv2.contourArea(cnt)/(w*h))
        if area_ratio < 0.9 or h < 125 or w < 130: 
            continue
        plate = quarter_drawOn[y+h:y+h+35, x:x+w] #adjust this 
        plates_array.append(plate)
    if len(plates_array) != 0: 
        return True, plates_array
    return False, plates_array


def contains_white_line(cropped_original_img):
    hsv = cv2.cvtColor(cropped_original_img, cv2.COLOR_BGR2HSV)
    grey_line = np.uint8([[[95, 96, 95]]])
    green_line = np.uint8([[[118, 128, 111]]])
    hsv_low = cv2.cvtColor(grey_line, cv2.COLOR_BGR2HSV)
    hsv_high = cv2.cvtColor(green_line, cv2.COLOR_BGR2HSV)
    grey = np.array([hsv_low[0][0][0], hsv_low[0][0][1], hsv_low[0][0][2]])
    green = np.array([hsv_high[0][0][0], hsv_high[0][0][1], hsv_high[0][0][2]])
    mask = cv2.inRange(hsv, grey, green)
    return cv2.inRange(mask, 255, 255).any()


def contains_human(cropped_original_img):
    hsv = cv2.cvtColor(cropped_original_img, cv2.COLOR_BGR2HSV)
    lower = np.uint8([[[41, 20, 14]]])
    upper = np.uint8([[[158, 134, 107]]])
    hsv_low = cv2.cvtColor(lower, cv2.COLOR_BGR2HSV)
    hsv_high = cv2.cvtColor(upper, cv2.COLOR_BGR2HSV)
    #print("LOW: {}\nHIGH: {}".format(hsv_low, hsv_high))
    lower_limit = np.array([hsv_high[0][0][0], hsv_high[0][0][1], hsv_low[0][0][2]])
    upper_limit = np.array([hsv_low[0][0][0], hsv_low[0][0][1], hsv_high[0][0][2]])
    mask = cv2.inRange(hsv, lower_limit, upper_limit)
    return cv2.inRange(mask, 255, 255).any()


def ideal_car_position(cropped_original_img):
    hsv = cv2.cvtColor(cropped_original_img, cv2.COLOR_BGR2HSV)
    lower_limit = np.uint8([[[0, 0, 0]]])
    upper_limit = np.uint8([[[10, 10, 10]]])
    hsv_low = cv2.cvtColor(lower_limit, cv2.COLOR_BGR2HSV)
    hsv_high = cv2.cvtColor(upper_limit, cv2.COLOR_BGR2HSV)
    lower = np.array([hsv_low[0][0][0], hsv_low[0][0][1], hsv_low[0][0][2]])
    upper = np.array([hsv_high[0][0][0], hsv_high[0][0][1], hsv_high[0][0][2]])
    mask = cv2.inRange(hsv, lower, upper)
    # cv2.imshow("mask",mask)
    # cv2.waitKey(3)
    num_pixels = cv2.countNonZero(cv2.inRange(mask, 255, 255))
    #print(num_pixels)
    if(num_pixels > 10 and num_pixels < 140):
    # if(num_pixels > 1000):
        return True
    return False


def filter_plate(quarter_original_img):
    hsv = cv2.cvtColor(quarter_original_img, cv2.COLOR_BGR2HSV)
    lower_limit = np.uint8([[[99, 100, 99]]])
    upper_limit = np.uint8([[[203, 203, 203]]])
    hsv_low = cv2.cvtColor(lower_limit, cv2.COLOR_BGR2HSV)
    hsv_high = cv2.cvtColor(upper_limit, cv2.COLOR_BGR2HSV)
    lower = np.array([hsv_high[0][0][0], hsv_high[0][0][1], hsv_low[0][0][2]])
    upper = np.array([hsv_low[0][0][0], hsv_low[0][0][1], hsv_high[0][0][2]])
    mask = cv2.inRange(hsv, lower, upper)
    return mask


K = 3
D = 25
K_inner = 3
D_inner = 28
timer = 1
STRAIGHT = 1
BACK = -1
STOP = 0
LEFT = 1
RIGHT = -1
WHITE = 255
labels = ["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z"]
box_positions = {2: "2", 4: "3", 8: "4", 10: "5", 12: "6", 0: "1"}
inner_box_positions = {4: "8", 8: "7"}


if __name__ == '__main__':
    rospy.init_node("my_node")
    STATE = 0
    myrobot = robot.Robot()
    conv_model = models.load_model("/home/fizzer/enph353_gym-gazebo/examples/gazebo_train/text_cnn7.h5")
    _, invert_dict = get_encoder(labels)
    myrobot.publishLicensePlate(0, "XX00")
    #time.sleep(7)
    myrobot.linearChange(STRAIGHT)

    while True:
        while STATE == 0:
            img_slice = myrobot.imageSliceVer()
            for i in range(720):
                if img_slice[i] == WHITE and i > 600:
                    myrobot.angularChange(LEFT)
                    rospy.sleep(0.4)
                    STATE = 1
                    break
        while STATE == 3:
            img_slice = myrobot.imageSliceVertical()
            for i in range(720):
                if img_slice[i] == WHITE and i > 715:
                    myrobot.angularChange(STRAIGHT)
                    STATE = 1
                    break
        # img_slice = myrobot.imageSliceHor()
        # for i in reversed(range(500, 1280)):
        #     if img_slice[i] == WHITE:
        #         break
        previous_state = 1000
        #print(previous_state)
        got_letters = False
        black = 0
        pedestrian_passed = False

        while STATE == 1:
            img_slice = myrobot.imageSliceHor()
            cropped_original = myrobot.view[660:, :]
            if contains_white_line(cropped_original):
                if black > 150:
                    black = 0
                    myrobot.position = (myrobot.position+1) % 16
                    pedestrian_passed = False
            else:
                black += 1

            if(pedestrian_passed is False and myrobot.position == 5 or myrobot.position == 13):
                while(pedestrian_passed is False and not contains_human(myrobot.view[390:460, 540:740])):
                    myrobot.linearChange(STOP)
                while(contains_human(myrobot.view[390:460, 540:740])):
                    myrobot.linearChange(STOP)
                pedestrian_passed = True

            quarter_original_img = myrobot.view[360:, :600]
            plate_mask = filter_plate(quarter_original_img)
            success, plates = find_contours(plate_mask, quarter_original_img)
            if success:
                masked_plate = filter_blue(plates[len(plates) - 1])
                # cv2.imshow("plate", masked_plate)
                # cv2.waitKey(3)
                got_letters, letters = find_letters(masked_plate, plates[len(plates) - 1])
            if got_letters is True and myrobot.position in box_positions:
                plate = get_plate(conv_model, letters, invert_dict)
                myrobot.publishLicensePlate(box_positions[myrobot.position], plate)
                got_letters = False

            if myrobot.position == 8:
                myrobot.position = 9
                STATE = 2
                break

            for i in reversed(range(600, 1280)):
                if img_slice[i] == WHITE:
                    break
            error = i - previous_state
            d_error = 0
            if np.abs(error):
                d_error = error/timer
                timer = 0
            diff = K*error
            derivative = D*d_error
            total_error = diff + derivative
            if i < 1140 - total_error:
                myrobot.angularChange(LEFT)
            elif i > 1260 - total_error:
                myrobot.angularChange(RIGHT)
            else:
                myrobot.linearChange(STRAIGHT)
            previous_state = i
            timer += 1

        straight = [3, 5, 7]
        car_passed = False 
        previous_state = 170
        # for i in reversed(range(700)):
        #     if img_slice[i] == WHITE:
        #         break
        #     previous_state = i
        #     print("first" + str(previous_state))
            
        black = 0
        while STATE == 2:
            img_slice = myrobot.imageSliceHor()
            cropped_original = myrobot.view[660:, :]
            if contains_white_line(cropped_original):
                if black > 150:
                    myrobot.inner_position = (myrobot.inner_position+1)
                    black = 0
            else:
                black += 1

            if car_passed is False and myrobot.inner_position == 1: 
                while (not ideal_car_position(myrobot.view[250:400, 400:])):
                    myrobot.linearChange(STOP)
                car_passed = True 

            quarter_original_img = myrobot.view[360:, 600:]
            plate_mask = filter_plate(quarter_original_img)
            success, plates = find_contours(plate_mask, quarter_original_img)
            if success:
                masked_plate = filter_blue(plates[len(plates) - 1])
                got_letters, letters = find_letters(masked_plate, plates[len(plates) - 1])
            if got_letters is True and myrobot.inner_position in inner_box_positions:
                plate = get_plate(conv_model, letters, invert_dict)
                myrobot.publishLicensePlate(inner_box_positions[myrobot.inner_position], plate)
                got_letters = False

            if myrobot.inner_position in straight:
                myrobot.linearChange(STRAIGHT)
                continue
            if myrobot.inner_position == 11:
                myrobot.inner_position = 0
                #myrobot.position += 1
                STATE = 1
                break
            for i in reversed(range(700)):
                if img_slice[i] == WHITE:
                    break
            error = i - previous_state
            d_error = 0
            if np.abs(error):
                d_error = error/timer
                timer = 0
            diff = K_inner*error
            derivative = D_inner*d_error
            total_error = diff + derivative
            if i < 40 - total_error:
                myrobot.angularChange(LEFT)
            elif i > 150 - total_error:
                myrobot.angularChange(RIGHT)
            else:
                myrobot.linearChange(STRAIGHT)
            previous_state = i
            timer += 1

