# Write a Python program to
# concatenate all elements in a list into a string and return it
from unittest import result


def concatenate_list_data(list):
    result = ''
    for elemeant in list :
        result += str(elemeant)
    return result
print(concatenate_list_data([1,5,3,4,44,56]))