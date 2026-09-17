import cv2
import os
import numpy as np
import pandas as pd
import mediapipe as mp
#from mediapipe import solutions
#from mediapipe.framework.formats import landmark_pb2

""" 
Así se fuerza el recargo de la librería después de modificarla, para que los cambios se reflejen en el notebook sin necesidad de reiniciar el kernel.
import importlib
import landmarksLib  # La librería que ya tenías cargada
import evaluation

# Después de modificar el código de la librería:
importlib.reload(landmarksLib)
importlib.reload(evaluation)
 """
mp_hands = mp.tasks.vision.HandLandmarksConnections
mp_drawing = mp.tasks.vision.drawing_utils
mp_drawing_styles = mp.tasks.vision.drawing_styles

MARGIN = 10  # pixels
FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (88, 205, 54) # vibrant green

def get_XYZ(results, image_rgb):

    landmark_values = [[0, 0] for _ in range(21)]
    
    # esto para dibujar
    mp_drawing = mp.solutions.drawing_utils
    
    image_height, image_width, _ = image_rgb.shape
        
    for hand_landmarks in results.multi_hand_landmarks:
        # Draw hand landmarks on the frame
        mp.solutions.drawing_utils.draw_landmarks(image_rgb, 
                                                  hand_landmarks, 
                                                  mp.solutions.hands.HAND_CONNECTIONS,
                                                  mp.solutions.drawing_utils.DrawingSpec(color=(255, 255, 0), thickness=4, circle_radius=5),
                                                  mp.solutions.drawing_utils.DrawingSpec(color=(255, 0, 255), thickness=4))
        
        for i in range(len(hand_landmarks.landmark)):
            x = hand_landmarks.landmark[i].x  # * image_width
            y = 1 - hand_landmarks.landmark[i].y  # * image_height (1-y for providing same shape as in image)
            landmark_values[i] = [x, y]
                
    return image_rgb, landmark_values

def draw_landmarks_on_image(rgb_image, detection_result):
    hand_landmarks_list = detection_result.hand_landmarks
    handedness_list = detection_result.handedness
    annotated_image = np.copy(rgb_image)
    
    landmark_values = []
    
    # Loop through the detected hands to visualize.
    for idx in range(len(hand_landmarks_list)):
      hand_landmarks = hand_landmarks_list[idx]
      handedness = handedness_list[idx]

      # Draw the hand landmarks.
      mp_drawing.draw_landmarks(
          annotated_image,
          hand_landmarks,
          mp_hands.HAND_CONNECTIONS,
          mp_drawing_styles.get_default_hand_landmarks_style(),
          mp_drawing_styles.get_default_hand_connections_style())

      # Get the top left corner of the detected hand's bounding box.
      height, width, _ = annotated_image.shape
      x_coordinates = [landmark.x for landmark in hand_landmarks]
      y_coordinates = [landmark.y for landmark in hand_landmarks]
      text_x = int(min(x_coordinates) * width)
      text_y = int(min(y_coordinates) * height) - MARGIN

      # Draw handedness (left or right hand) on the image.
      cv2.putText(annotated_image, f"{handedness[0].category_name}",
                  (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX,
                  FONT_SIZE, HANDEDNESS_TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA)

      # Arrange the landmarkks as an array landmark_values[i] = [x, y]
      for landmark in hand_landmarks:
        landmark_values.append([landmark.x, landmark.y])

    return annotated_image, landmark_values

def GetLandmarksListFromDetectionResult(detection_result):
    landmark_values = []
    
    if detection_result.hand_landmarks is not None:
        for hand_landmarks in detection_result.hand_landmarks:
            for landmark in hand_landmarks:
                landmark_values.append([landmark.x, landmark.y])
    else:
        # If no hand landmarks are detected, we return a list of 21 pairs of zeros
        landmark_values = [[0, 0] for _ in range(21)]
    
    return landmark_values

# GetLandmarksFromImages function
# The function takes a list of image file names,
# processes each image to detect hand landmarks using MediaPipe Hands,
# extracts the X and Y coordinates of the landmarks,
# and creates a DataFrame containing this information along with additional metadata.
# The DataFrame is then saved to a CSV file, and the function handles exceptions and logs errors encountered during the process.
def GetLandmarksFromImages(detector, IMAGE_FILES, images_path, images_subfolder, images_class, landmarks_path, annotations_path, config):
  
    columns = [["x" + str(i), "y" + str(i)] for i in range(config.num_landmarks)]  # [x0, y0],[x1,y1],[x2,y2]...
    columns = [item for sublist in columns for item in sublist]  # ['x0', 'y0', 'x1', 'y1' ....
    df_columns = columns + ["label", "frame", "path"]

    if not os.path.exists(images_path):
        # If the folder where the images are stored does not exist, we abort and log the event
        # This is an error because we cannot process the images if the folder does not exist
        print('\t[ERROR!!!][%s][FOLDER DOES NOT EXIST!!! ABORTING...]' % images_path)
        with open('HAR_mediapipe/logs.txt', 'a') as f:
            print('GetLandmarksFromImages()', images_path, file=f)
        return None     

    out_landmarks_path = landmarks_path + '/' + images_subfolder + '/'
    
    if not os.path.exists(out_landmarks_path):
        print('\t[%s][Folder does not exist!!! We create it!]' % out_landmarks_path)
        os.makedirs(out_landmarks_path)
        
    if config.save_images:
        out_path_imgs = annotations_path + '/' + images_subfolder + '/' 
     
        if not os.path.exists(out_path_imgs):
            print('\t[%s][Folder does not exist!!! We create it!]' % out_path_imgs)
            os.makedirs(out_path_imgs)
        
        out_path_imgs = out_path_imgs + images_class + '/'
        
        if not os.path.exists(out_path_imgs):
            print('\t[%s][Folder does not exist!!! We create it!]' % out_path_imgs)
            os.makedirs(out_path_imgs)

    out_path_df = os.path.join(out_landmarks_path + '/' + images_subfolder + '_' + images_class + '_poses_landmarks.csv')
    print('\t[New .csv file with landmarks][%s]' % out_path_df)

    print('\n[GetLandmarksFromImages]')
    print('\t[files][%s]' % str(IMAGE_FILES))
    print('\t[input images in path][%s]' % images_path)
    print('\t[landmarks out in path][%s]' % landmarks_path)
    print('\t[annotations out in path][%s]' % annotations_path)
    print('\t[columns][%s]' % str(df_columns))
    print('\n')

    successful_detections_df = pd.DataFrame([], columns=df_columns)

    num_successful_detections = 0
    num_failed_detections = 0

    for idx, file in enumerate(IMAGE_FILES):
        path_img = images_path + '/' + images_class + '/' + file
        
        if not os.path.exists(path_img):
          print(f"File does not exist: {path_img}")
          return None

        # Load the input image.
        image = cv2.imread(path_img)
        
        if image is None:
          print(f"Error: image could not be loaded: {path_img}")
          with open('logs.txt', 'a') as f:
            print('extract_XYZ()', images_path, idx + 1, file, file=f)
          return None
        
        #image_height, image_width, _ = image.shape

        # Convert the BGR image to RGB and processes each image to detect hand landmarks using MediaPipe Hands
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Process the image and get hand landmarks
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        detection_result = detector.detect(mp_image)

        landmark_values = []
        
        # Test if we have successfully detected a hand in the image, if not we add a row of zeros to the DataFrame and log the error
        if detection_result is None or detection_result.hand_landmarks is None:
            # We have NOT successfully detected a hand in the image
            num_failed_detections = num_failed_detections + 1

            print(f'\t[ERROR!!!][{num_failed_detections}][{path_img}][FAILED TO DETECT HAND!!]')
            with open('HAR_mediapipe/logs.txt', 'a') as f:
                print('GetLandmarksFromImages()', images_path, idx + 1, file, file=f)
        else:            
            landmark_values = GetLandmarksListFromDetectionResult(detection_result)
            
            # If landmark_values is empty we iterate and ignore current sample
            if not landmark_values:
                # We have NOT successfully detected a hand in the image
                num_failed_detections = num_failed_detections + 1

                print(f'\t[ERROR!!!][{num_failed_detections}][{path_img}][FAILED TO DETECT HAND!!]')
                with open('HAR_mediapipe/logs.txt', 'a') as f:
                    print('GetLandmarksFromImages()', images_path, idx + 1, file, file=f)
                continue
            
            # We have successfully detected a hand in the image
            num_successful_detections = num_successful_detections + 1
            print(f'\t[{num_successful_detections}][{path_img}][SUCCESS!!]')

            if config.save_images:
                image, landmark_values = draw_landmarks_on_image(image, detection_result)
                out_annotated_image_path = out_path_imgs + file.split(".")[0] + '.jpg'
                # We save the annotated images to a specified output directory
                cv2.imwrite(out_annotated_image_path, image)
                print(f'\t[{out_annotated_image_path}][ANNOTATED IMAGE SAVED!!]')
            
            # Only samples with a successful detection result are stored
            # We first unwrap landmark_values to a arrange them in a single row before passing them to the DataFrame
            df_landmark_values = [item for sublist in landmark_values for item in sublist]
            
            frame_number = file.split(".")[0]
            frame_number = frame_number.split("_")[1]

            # We add the image label, the frame number, and the image path to the DataFrame
            print(f"\timages_class = {images_class}, frame_number = {frame_number}, path_img = {path_img}")
            new_row = pd.DataFrame([df_landmark_values + [images_class, frame_number, path_img]], columns=df_columns)

            if successful_detections_df.empty:
                successful_detections_df = new_row
            else:
                successful_detections_df = pd.concat([successful_detections_df, new_row], ignore_index=True)

    # Finally we create a .csv file with the results of the landmarks detection
    successful_detections_df.to_csv(out_path_df, sep=",", header=True, index=False)

    return (successful_detections_df, num_successful_detections, num_failed_detections)
    # End of the GetLandmarksFromImages function

def remove_last_subfolder(path):
    head, tail = os.path.split(path)
    if tail:
        return head, tail
    elif head:
        new_head, new_tail = os.path.split(head)
        return new_head, new_tail
    else:
        return '', ''

def sorted_lists_match(list1, list2):
    sorted_list1 = sorted(list1)
    sorted_list2 = sorted(list2)

    return sorted_list1 == sorted_list2

def extract_classes_list_from_folders(folders_path, new_dataset_path):
  classes = []

  # Creation of a .txt file with different classes
  # First, we check the train folder substructure
  for root, dirs, files in os.walk(folders_path):
      for dir in dirs:
          classes.append(dir)

  classes = sorted(classes)

  root_path, processed_subfolder = remove_last_subfolder(folders_path)

  new_txt_filename = new_dataset_path + '/' + processed_subfolder + '_classes_list.txt'
  print('\n[extract_classes_list_from_folders][NEW .txt file]\n\t[%s]' % new_txt_filename)

  with open(new_txt_filename, 'w') as f:
    for c in classes:
      if c !='Landmarks' and c !='to_use'and c !='models':
        f.write(c + "\n")
    f.close()

  return classes

def load_individual_class_features_and_create_labeled_csv_dataset(input_mode, new_dataset_path, landmarks_path):
  classes_list_filename = new_dataset_path + '/' + input_mode + '_classes_list.txt'

  # Load file with classes
  print('\n[load_individual_class_features_and_create_labeled_csv_dataset][%s]\n\t[LOAD .txt file with the list of classes][%s]' % (input_mode, classes_list_filename))
  classes_list = pd.read_csv(classes_list_filename, header=None)
  classes_list = classes_list.rename(columns={0: "symbol"})
  classes_list["label"] = range(1, len(classes_list) + 1)

  # Load the first
  j = 0
  common_landmarks_folder = landmarks_path
  csv_filename = common_landmarks_folder + input_mode + '/' + input_mode + '_' + classes_list.loc[j]['symbol'] + '_poses_landmarks.csv'
  print('\t[LOAD .csv file with landmarks][%s]' % csv_filename)
  df = pd.read_csv(csv_filename)
  df['label'] = np.ones(len(df)) * classes_list.loc[j]["label"]

  # Load the rest
  for j in range(1, len(classes_list)):
    csv_filename = common_landmarks_folder + input_mode + '/' + input_mode + '_' + classes_list.loc[j]['symbol'] + '_poses_landmarks.csv'
    print('\t[LOAD .csv file with landmarks][%s]' % csv_filename)
    current_df = pd.read_csv(csv_filename)
    current_df['label'] = np.ones(len(current_df)) * classes_list.loc[j]['label']
    df = pd.concat([df, current_df])

  if not os.path.exists(new_dataset_path):
      # If the folder where the new dataset will be saved does not exist, this is an major error because we cannot save the new dataset, so we abort and log the event
      print('\t[ERROR!!!][%s][FOLDER DOES NOT EXIST!!! ABORTING...]' % new_dataset_path)
      with open('HAR_mediapipe/logs.txt', 'a') as f:
          print('load_individual_class_features_and_create_labeled_csv_dataset()', new_dataset_path, file=f)
      return None
  
  new_csv_filename = new_dataset_path + '/' + input_mode + '_dataset_with_labels.csv'
  print('\t[CREATING NEW .csv file][%s]' % new_csv_filename)
  df.to_csv(new_csv_filename, index=False)

# Create file CSV and Numpy
def create_numpy_with_feats_and_csv_with_just_labels(input_mode, new_dataset_path, NO_GESTURE=False):
  if NO_GESTURE:
    aux = '_plus_NO_GESTURE'
  else:
    aux = ''

  print('\n[create_numpy_with_feats_and_csv_with_just_labels][%s]' % input_mode)
  input_file = new_dataset_path + '/' + input_mode + '_dataset_with_labels' + aux + '.csv'
  print('\t[input_file][%s]' % input_file)
  df = pd.read_csv(input_file)
  num_points = 42

  new_df = pd.DataFrame([], columns=["frame", "label"])
  data = np.zeros((len(df), num_points))
  fea_list = [["x" + str(j), "y" + str(j)] for j in range(int(num_points / 2))]
  flat_fea_list = [item for sublist in fea_list for item in sublist]

  for i in range(len(df)):
      data[i] = df.loc[i][flat_fea_list]
      new_df.loc[i] = [df["frame"][i], df["label"][i]]

  # Save NEW .csv which includes just the labels information
  new_csv_filename = new_dataset_path + '/' + input_mode + '_labels' + aux + '.csv'
  print('\t[NEW .csv][%s]' % new_csv_filename)
  new_df.to_csv(new_csv_filename, index=False)

  # Save NEW .npy which includes only the features
  new_npy_filename = new_dataset_path + '/' + input_mode + '_dataset' + aux + '.npy'
  print('\t[NEW .npy][%s]' % new_npy_filename)
  np.save(new_npy_filename, data)
  
  # This function takes a NumPy array data as input and returns a new array new_data with normalized landmarks.
# In summary, this function takes hand landmark data, assumes that the first two coordinates represent
# the center of the hand, and shifts the remaining landmarks' coordinates so that the center becomes the new origin.
# This can be useful for normalizing hand landmark data for further analysis or processing.
def normalize_from_0_landmark(data):
  # We create a copy of the input data array to ensure that the original data is not modified,
  # and the modifications are made to the copy
  new_data = np.copy(data)
  # This loop iterates through each row of the data array.
  # Each row represents a different hand instance or sample.
  for i in range(data.shape[0]):
    # This condition helps to skip rows where the sum of X and Y coordinates is zero,
    # which may represent a case where there are no landmarks.
    if ((data[i, 0] + data[i, 1]) != 0):
      # These lines extract the X and Y coordinates of the center of the hand landmarks (typically, the palm).
      x_center = data[i, 0]
      y_center = data[i, 1]
      # This inner loop iterates through the remaining elements of the row,
      # starting from the third element (index 2).
      # In hand landmark data, these are typically the landmarks' X and Y coordinates, alternating.
      for k in range(2, data.shape[1], 2):
        # These lines calculate the new coordinates of each landmark relative to the center.
        # They subtract the center's X and Y coordinates from the corresponding landmark's X and Y coordinates.
        # This effectively shifts the coordinates so that the center becomes the new origin (0, 0).
        new_data[i, k] = data[i, k] - x_center
        new_data[i, k + 1] = data[i, k + 1] - y_center
  return new_data

def ArrangeInputDataForNetwork (x_data, debug = False):
  # x_data is expected as (num_samples, num_features_flat), where features are interleaved as x0,y0,x1,y1,...
  if debug:
    print('x_data')
    print(x_data.shape)
    print(x_data)

  # Allocate (num_samples, num_landmarks, 2) to separate x/y coordinates per landmark.
  x_data_reshaped = np.zeros((x_data.shape[0],
                              int(x_data.shape[1] / 2),
                              2))
  if debug:
    print('x_data_reshaped')
    print(x_data_reshaped.shape)
    print(x_data_reshaped)

  # Split even columns into x channel and odd columns into y channel.
  for i in range(len(x_data)):
    x_data_reshaped[i, :, 0] = x_data[i, 0::2]
    x_data_reshaped[i, :, 1] = x_data[i, 1::2]

  # Add a final singleton channel dimension for CNN-style input: (N, landmarks, 2, 1).
  x_data_out = np.reshape(x_data_reshaped, (x_data_reshaped.shape[0], x_data_reshaped.shape[1], x_data_reshaped.shape[2], 1))

  if debug:
    print('x_data_out')
    print(x_data_out.shape)
    print(x_data_out)

  # Return tensor ready for network input.
  return x_data_out