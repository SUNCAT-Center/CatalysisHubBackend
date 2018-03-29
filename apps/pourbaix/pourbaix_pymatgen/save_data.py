import json


def save_data(data, file_name):
    """Store matrix data.

    Parameters:
    -----------
    data: (unknown)
        matrix data to save
    file_name: str
        path to save file
    """
    with open(file_name, 'w') as f:
        json.dump(data, f)
