import os


def call():
    return_list = []
    for curdir, subfolders, files in os.walk(".logs"):
        for file in files:
            return_list.append(f"{os.path.join(curdir, file)}")
    return return_list