import os
import sqlite3
import pickle
import ast
from random import Random
from IPython.display import clear_output


def menu(text: str, labels: list, max_inputs) -> tuple:
    """
    Get label input from user. First display text, then menu with label option and ask user to select labels.

    :param text: text to be labeled
    :param labels: list with tag selection
    :param max_inputs: int representing number of classes that can be linked to one text
    :return: tuple containing list with labels specified by user and string about action (e.g. continue, skip or exit)
    """
    label_list = []
    user_label = -3
    no_inputs = 0
    while no_inputs < max_inputs:
        clear_output()
        print("-" * 40)
        print(f"NUMBER OF LABELS GIVEN TO CURRENT TEXT: {no_inputs}/{max_inputs}.")
        print(f"Already given labels: {label_list}")
        print("-" * 40)
        print(f"TEXT FOR LABELLING: \n {text}")
        print("-" * 40)
        print("PLEASE SELECT ONE OF FOLLOWING OPTIONS:")
        print("-2.) Exit")
        print("-1.) Add new class")
        print("0.) Press 0 to finish labelling of current text")
        for index, label in enumerate(labels):
            if label not in label_list:
                print(f"{index + 1}.) {label}")
        try:
            user_label = int(input(">  "))
        except ValueError:
            print("Please type one of the valid options as a NUMBER. \n Let's try it again...")
            input("PRESS ANY KEY TO CONTINUE")
            continue
        if user_label in [0, -2]:
            # if special condition was triggered break the loop
            break
        elif user_label == -1:
            labels.append(input("Please type here new class label: "))
            label_list.append(len(labels))
            no_inputs += 1
        elif 1 <= user_label <= len(labels):
            if user_label not in label_list:
                label_list.append(user_label)
                no_inputs += 1
            else:
                print(f"Option {user_label} was already in list, please select one of other labels.")
                input("PRESS ANY KEY TO CONTINUE")
        else:
            print("Please type one of the valid options from displayed list. Let's try it again...")
            input("PRESS ANY KEY TO CONTINUE")

    label_list_str = []
    for label_number in label_list:
        label_list_str.append(labels[label_number - 1])

    if user_label == -2:
        status = "exit"
    elif user_label == 0 and not label_list_str:
        status = "skip"
    else:
        status = "continue"

    return label_list_str, status


def ask_user_for_label(record_id: str, text: str, database_path: str, labels: list, max_no_labels: int = 3) -> tuple:
    """
    Show text to user and ask for label input. Update database in case of valid input. If user type "skip" text will not
    be added into database.

    :param record_id: name of file from which text bullet was extracted
    :param text: text which is going to be tagged
    :param database_path: path to database
    :param labels: list with tags
    :param max_no_labels: int representing number of classes that can be linked to one text
    :return: tuple with labels given by user
    """
    user_labels, status = menu(text, labels, max_no_labels)

    if status not in ["exit", "skip"]:
        # write python list as string "[element1, element2, ...]"
        label_string = "['" + "','".join(user_labels) + "']"

        # add new record into database with tag provided by user
        db = sqlite3.connect(database_path)

        update_sql = "INSERT INTO label_table(id, text, labels) VALUES(?, ?, ?)"
        update_cursor = db.cursor()
        update_cursor.execute(update_sql, (record_id, text.strip("\n\r "), label_string))
        update_cursor.connection.commit()
        update_cursor.close()
        # update information about last processed file, once program will re-run it will start with next file
        update_sql = "UPDATE last_record SET id=?"
        update_cursor = db.cursor()
        update_cursor.execute(update_sql, (record_id,))
        update_cursor.connection.commit()
        update_cursor.close()

        db.close()

    return user_labels, status


def initiate_database(database_path: str) -> None:
    """
    This function create empty database ready to accept labels.

    :param database_path: path to sqlite database.
    :return: nothing.
    """
    database = sqlite3.connect(database_path)

    database.execute("""CREATE TABLE IF NOT EXISTS label_table
    (id TEXT, text TEXT, labels TEXT)""")
    database.execute("CREATE TABLE IF NOT EXISTS last_record(id TEXT)")
    database.execute("INSERT INTO last_record(id) VALUES('')")
    database.commit()
    database.close()
    print(f"Empty database was successfully created in {database_path}")


def start_labelling(database_path: str, data: list, record_id: list, labels: list,
                    shuffle_flag: bool = False, shuffle_seed: int = 123,
                    blank_database_flag: bool = False) -> None:
    """
    Loop through data. Ask user for input to specify tag for displayed text from data. Tag structure will be taken from
    tag dictionary. Program ask user for every level of tags. For every tag it will display menu. With Then update
    database with user input. User can close this function by typing "exit". Rerun of the function will automatically
    skip already filled records from data.

    :param database_path: path to sqlite database
    :param data: data extracted from xmls, format of data is ("file", {dict with xml tags}, {dict with content}
    :param record_id: filename or other type of study identification
    :param labels: list with all class labels
    :param shuffle_flag: True if it is desired to shuffle data (random sample)
    :param shuffle_seed: random seed for data shuffle
    :param blank_database_flag: True if it is desired to create blank database. If False database must already exist.
    :return: nothing just updates and close database
    """
    if blank_database_flag:
        # check if database already exists and delete it if so
        if os.path.exists(database_path):
            os.remove(database_path)
            print("Database file was successfully deleted and will be replaced with empty database.")
        # create empty database
        initiate_database(database_path)
        last_id = None
    else:
        db = sqlite3.connect(database_path)
        cursor_row_count = db.cursor()
        cursor_row_count.execute("SELECT * FROM last_record")
        last_id = cursor_row_count.fetchone()[0]
        cursor_row_count.close()
        cursor_labels = db.cursor()
        cursor_labels.execute("SELECT DISTINCT labels FROM label_table")
        database_labels = cursor_labels.fetchall()
        cursor_labels.close()
        db.close()

        # in case during previous labelling sessions we have added new label we will add this label into labels to be
        # able to display it in labelling menu
        for label_str in database_labels:
            for label in ast.literal_eval(label_str[0]):
                if label not in labels:
                    labels.append(label)

    if shuffle_flag:
        Random(shuffle_seed).shuffle(data)
        Random(shuffle_seed).shuffle(record_id)

    loop_through_data(record_id, last_id, data, database_path, labels)


def loop_through_data(record_id: list, last_id: str, data: list, database_path: str, labels: list):
    """
    Loop through given list with short text and ask tag from user.

    :param record_id: file from which text was extracted.
    :param last_id: last file present in the database.
    :param data: list with bullet points or short text.
    :param database_path: path to database.
    :param labels: list with tags.
    :return: nothing
    """
    if not last_id:
        start = True
    else:
        start = False

    user_label = []
    for index, text in enumerate(data):

        if not start and str(record_id[index]) == last_id:
            start = True
            continue
        elif not start:
            continue

        user_label, status = ask_user_for_label(record_id[index], text, database_path, labels)
        if status == "exit":
            break
        elif status == "skip":
            continue

        for label in user_label:
            if label not in labels:
                labels.append(label)

    print("All used labels:")
    print(labels)


# load inclusion and exclusion data extracted from xml files and loop through them and manually label them by own
# judgement. Function update_database loops through data and display labeling options menu in console. Labeled data
# will be saved in text_tag.sqlite database and could be retrieved for model validation analysis
if __name__ == "__main__":

    with open('data/text_data.pickle', 'rb') as saved_data:
        text_list = pickle.load(saved_data)

    id_list = [i+1 for i in range(len(text_list))]

    label_list = ['Culture', 'Science and Mathematics', 'Health', 'Education and Reference',
                  'Computers and Internet', 'Sports', 'Entertainment', "Business and Finance",
                  'Family and Relationships', 'Government and Politics']

    random_seed = 123
    # if we are starting with labeling, create database from scratch.
    # start_labelling('data/database.sqlite', text_list, id_list, label_list, True, random_seed, True)

    # if we already labeled part of data and want to continue. Keep the same random_seed!
    start_labelling('data/database.sqlite', text_list, id_list, label_list, True, random_seed, False)
