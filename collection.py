import numpy as np 
# List collections
# Assigned a consective number based on its position 0,1,2,3 ...
cities = [
    "Tokyo",
    "Dakar",
    "Nairobi",
    "Kampala",
]
# Dictionaries
# Each item in the dictionary has a lable, and they are used to identify the coresponding items 
jethro_details = {
    "name":"jethro",
    "Id": "29393",
    "Email": "jethro.kimande@gmail.com",
    "Profession": "engineer",

}
# How to access values in a list 
print ("Peint values from a list in python")
print (cities[0]) # print the first entry in the list 
print (cities[0:2]) # print the the firt twoo enetries in the list 
print(cities[-1])# print the last entry in the list 

# How to access values in adictioinary 
print("Print values from a dictionary in python ")
print (jethro_details["Id"])
print (jethro_details["Profession"])

# printing the list using a for loop
print("Print the values in a list usinng a for loop in python")
for city in cities:
    print(city)


# while loop 
# count to 100 in steps of 5 
i = 5
print ("Count to 100 by fives: ")
while i <= 100:
    print (i)
    i += 5

print("List complete")

# Exercise 
fruits = [
    "Apples",
    "Bananas",
    "Guavas",
    "Oranges",
    "Pawpaws",
]
print ("Our fruit selection:")
for fruit in fruits:
    print(fruit)