import hashlib

def name_to_color(name):
    hash_object = hashlib.md5(name.encode())
    hex_color = "#" + hash_object.hexdigest()[:6]
    return hex_color