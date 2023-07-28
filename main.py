import boto3
import cv2
import time
import json
import random
import datetime
import mysql.connector
import os
import numpy as np
from colorama import Fore, init, Style
from colorama.initialise import deinit
from botocore.exceptions import ClientError
# def hasher(st): 
#     n=len(st) 
#     st+=st; 
#     for i in range(n): 
#         s1=ord(st[i])^ord(st[n-i-1]) 
#     s1=s1^ord("X") 
#     return s1
from cryptography.fernet import Fernet

# Generate a key to use for encryption and decryption
key = Fernet.generate_key()
#cipher_suite = Fernet(key)
key_str = key.decode('utf-8')


# Function to encrypt a string
def encrypt_string(s,key):
    return Fernet(key).encrypt(s.encode('utf-8')).decode('utf-8')

# Function to decrypt an encrypted string
def decrypt_string(s,key):
    return Fernet(key).decrypt(s.encode('utf-8')).decode('utf-8')


# For new user registration
def register_face(target_capture):
    s3 = boto3.client("s3")  # S3 client (S3 is an object storage service)
    bucket = "project3007"  # Bucket name (Folder to store images in S3)
    print("[INFO]: Uploading image to S3")
    name = input("Enter the name of passenger: ")  # Name of user
    age = input("Enter the age of passenger: ")  # Age of user
    start_date = str(datetime.date.today())  # Start date of user
    end_date = input("Enter the end date of the pass: ")  # End date of user
    end_date= encrypt_string(end_date,key)
    image = name + age + start_date + end_date + ".png"  # Name of image
    ra = random.randint(1, 999)  # Random number
    lic_num = end_date + start_date + age + str(ra)  # License number of user
    face_id= key_str
    try:
        # Upload target_capture image to project3006 bucket with name someuser1.jpg
        s3.upload_file(target_capture, bucket, image)
        print("[INFO]: Image uploaded to S3")
        insert_rds(
            name, age, start_date, end_date, image, lic_num,face_id
        )  # Insert user details into RDS
    except ClientError as e:  # If error, print error
        print(e)


# For comparing faces
def compare_face(target):
    # Rekognition client (Rekognition is a service that recognizes faces in images)
    rekognition = boto3.client("rekognition")
    s3 = boto3.client("s3")  # S3 client (S3 is an object storage service)
    print("[INFO]: Connected to Rekognition")
    print("[INFO]: Connected to S3")
    print("[INFO]: Comparing faces")
    similarity = 0.00
    # loop through all the images in the bucket and compare them to the target image
    for image in s3.list_objects(Bucket="project3007")["Contents"]:
        image_source = {"S3Object": {"Bucket": "project3007", "Name": image["Key"]}}
        image_target = open( target, "rb")  # Image of user taken when comparing

        try:
            response = rekognition.compare_faces(
                SimilarityThreshold=98,
                SourceImage=image_source,
                TargetImage={"Bytes": image_target.read()},
            )  # Compare faces

            # print("[INFO]: Faces compared")
            for face_match in response["FaceMatches"]:
                position = face_match['Face']['BoundingBox']
                similarity = float(face_match["Similarity"])
                print(similarity, "s")

            if similarity > 98.5:
                image_target.close()  # Close image_target
                print("[INFO]: Face matched")
                print("The face is " + str(similarity) + "%"+"similar")
                fetch_rds(image["Key"])
                up_ip=input("Update if Expired :[Y/N] ")
                if(up_ip=='Y'or up_ip=='y'):
                    update_rds(image["Key"])
                    break
                else:
                    break
            elif image == s3.list_objects(Bucket="project3007")["Contents"][-1]:
                print(Fore.RED + "[INFO]: Face not matched")
                print("The face is " + str(similarity) + "%"+"similar")
                image_target.close()
                break
            else:
                continue

        except ClientError as e:  # On recieving an error, print error
            if e.response["Error"]["Code"] == "InvalidParameterException":
                print(Fore.RED + "Face not found")
                break


# Capture image from webcam
def capture():
    camera = cv2.VideoCapture(0)  # Open webcam
    print("[INFO]: Capturing image")
    print("[INFO]: Press SPACE to capture image or ESC to exit")
    time.sleep(1)  # Wait for 2 seconds
    while True:
        ret, frame = camera.read()  # Read image from webcam
        if not ret:
            print("[INFO]: Failed to capture image.")
        cv2.namedWindow("Capturing", cv2.WINDOW_NORMAL)  # Create window
        cv2.imshow("Capturing", frame)  # Show image
        key = cv2.waitKey(1)  # Wait for key press
        if key % 256 == 27:  # If esc key is pressed, exit
            camera.release()
            cv2.destroyAllWindows()
            print("[INFO]: Esc key pressed, Exiting")
            exit()

        elif key % 256 == 32:  # if space key is pressed, save image
            cv2.imwrite("C:/Users/harsh/OneDrive/Desktop/tmp/img.png", frame)
            print("[INFO]: Image captured")
            camera.release()
            cv2.destroyAllWindows()
            break


# Insert user details into RDS
def insert_rds(name, age, start_date, end_date, image, lic_num,face_id):
    # MySQL Config
    with open("config.json") as config_file:
        config = json.load(config_file)
        host = config["mysql"]["host"]
        user = config["mysql"]["user"]
        password = config["mysql"]["passwd"]
        database = config["mysql"]["db"]
    mysql_connection = mysql.connector.connect(
        host=host, user=user, password=password, database=database
    )
    print("[INFO]: Connected to RDS")
    cursor = mysql_connection.cursor()
    sql = "INSERT INTO users (name, age, start_date, end_date, image, lic_num,face_id) VALUES (%s, %s, %s, %s, %s, %s,%s)"
    val = (name, age, start_date, end_date, image, lic_num,face_id)
    cursor.execute(sql, val)
    mysql_connection.commit()
    print("[INFO]: Data uploaded to RDS")
    cursor.close()
    mysql_connection.close()


def fetch_rds(name):
    # MySQL Config
    with open("config.json") as config_file:
        config = json.load(config_file)
        host = config["mysql"]["host"]
        user = config["mysql"]["user"]
        password = config["mysql"]["passwd"]
        database = config["mysql"]["db"]
    mysql_connection = mysql.connector.connect(
        host=host, user=user, password=password, database=database
    )
    print("[INFO]: Connected to RDS")
    cursor = mysql_connection.cursor(buffered=True)
    sql = "SELECT * FROM users where image = %s"
    val = (name,)
    cursor.execute(sql, val)
    row = cursor.fetchone()
    init()
    print(Fore.YELLOW + "Biometric Authentication SUCCESS!!")
    print(Style.RESET_ALL + "[INFO]: Printing data from RDS")
    print(Fore.CYAN + "Name: " + row[0])
    print(Fore.CYAN + "Age: " + str(row[1]))
    print(Fore.CYAN + "Start Date: " + str(row[2]))
    print(Fore.GREEN + "End Date: " + decrypt_string(row[3],row[6].encode('utf-8')))
    print(Style.RESET_ALL + "[INFO]: Data fetched from RDS, Closing connections")
    deinit()
    cursor.close()
    mysql_connection.close()

def update_rds(name):
    key = Fernet.generate_key()
    #cipher_suite = Fernet(key)
    key_str = key.decode('utf-8')
    # MySQL Config
    with open("config.json") as config_file:
        config = json.load(config_file)
        host = config["mysql"]["host"]
        user = config["mysql"]["user"]
        password = config["mysql"]["passwd"]
        database = config["mysql"]["db"]
    mysql_connection = mysql.connector.connect(
        host=host, user=user, password=password, database=database
    )
    print("[INFO]: Connected to RDS")
    cursor = mysql_connection.cursor(buffered=True)
    end_date = input("Enter the end date of the pass: ")  # End date of user
    end_date= encrypt_string(end_date, key)
    #row = cursor.fetchone()
    #end_date= encrypt_string(end_date,row[0].encode('utf-8'))
    sql = "UPDATE users SET face_id = %s, end_date = %s WHERE image = %s"
    val = (key_str, end_date, name)
    cursor.execute(sql, val)
    mysql_connection.commit()
    cursor.close()
    mysql_connection.close()

def load_data(bucket, key):
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket, key)
    body = obj.get()['Body'].read()
    data = np.frombuffer(body, dtype=np.uint8)
    data = np.reshape(data, (-1, 28, 28, 1))
    data = data.astype('float32') / 255.0
    return data


def main():
    print("Welcome to public transport service\n")
    print("What do you want to do?\n 1. Register\n 2. Compare\n 3.Exit")
    #decrypt_string("gAAAAABkLlw-EjYqj__9bhD-nyaxJzNUHk7NK6zfbwi7l3oAoAANz46g-X0BTaG8fQ7epeEp1HPq1Of7g6T3c-tw3S0eQ_HpMA==")
    choice = input()
    if choice == "1":
        capture()  # Capture image from webcam
        target_capture = "C:/Users/harsh/OneDrive/Desktop/tmp/img.png"  # Target image
        register_face(target_capture)  # Register image
    elif choice == "2":
        capture()  # Capture image from webcam
        target_capture = "C:/Users/harsh/OneDrive/Desktop/tmp/img.png"  # Target image
        compare_face(target_capture)  # Compare image
    elif choice == "3":
        exit()
    else:
        print("Invalid choice")
        main()


if __name__ == "__main__":
    main()