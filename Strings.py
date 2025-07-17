# Combining strings
Value = input("Enter a number: ") # This input is a string
print(Value)
print (Value + " is my lucky number.") # Concatination using '+' Operator
print (Value,"is my lucky number.")

# To perform arthmetic on the value, convert it to a a numerical value first 
num = int(Value)
print ("The product of the number with twelve is: ", num*12)


# Accessing the string 
note = "I am jethro Kimande"
first_ = note.find("am")
print(first_)
# Slicing 
my_name = note[5:11]
print(my_name)