import os

def create_folder(config):
    if not os.path.isdir("/mnt/" + f"nas{config['file_server_index']}/" + config['username'] ):
        os.mkdir("/mnt/" + f"nas{config['file_server_index']}/" + config['username'] )
    return