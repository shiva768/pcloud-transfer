import sys, os, datetime
from pathlib import Path

from requests import put, post, Session
from requests_toolbelt.multipart import encoder

MIN_SIZE = 524288000
BASE_FOLDER_ID = 1855971723


class FileLimiter(object):
    def __init__(self, file_obj, read_limit):
        self.read_limit = read_limit
        self.amount_seen = 0
        self.file_obj = file_obj

        # So that requests doesn't try to chunk the upload but will instead stream it:
        self.len = read_limit

    def read(self, amount=-1):
        if self.amount_seen >= self.read_limit:
            return b''
        remaining_amount = self.read_limit - self.amount_seen
        data = self.file_obj.read(min(amount, remaining_amount))
        self.amount_seen += len(data)
        return data

def send(_token, _folder_id, _path):
    session = Session()
    try:
        filename = os.path.basename(_path)
        with open(_path, 'rb') as f:
            params = encoder.MultipartEncoder({
                "filename": (filename, f, "application/octet-stream"),
                'auth': _token, 'folderid': str(_folder_id)
            })
            headers = {"Prefer": "respond-async", "Content-Type": params.content_type}
            response = session.post('https://api.pcloud.com/uploadfile', headers=headers, data=params)
            response.raise_for_status()
    finally:
        session.close()
    print("upload success {}".format(filename))


def create_folder(_name, _token):
    params = {'auth': _token, 'folderid': BASE_FOLDER_ID, 'name': _name}
    response = post('https://api.pcloud.com/createfolderifnotexists', params)
    response.raise_for_status()
    parsed = response.json()
    if parsed['created']:
        print('directory create')
    return parsed['metadata']['folderid']


def token():
    with open('.token', 'r') as f:
        return f.readline()


def search_files(_path, _token):
    p = Path(_path)

    for path in p.iterdir():
        if path.is_dir():
            search_files(path, _token)
        elif path.is_file():
            size = path.stat().st_size
            if size >= MIN_SIZE:
                transfer_file(path.resolve(), _token)


def validate(_args):
    if len(_args) <= 1:
        print('invalid parameter')
        sys.exit(1)

    if not os.path.exists(_args[1]):
        print('file path invalid')
        sys.exit(1)


def transfer_file(_path, _token):
    folder_name = datetime.date.today().strftime("%Y%m%d")
    folder_id = create_folder(folder_name, _token)
    send(_token, folder_id, _path)


def main(_path, _token):
    if os.path.isfile(_path):
        if os.path.getsize(_path) >= MIN_SIZE:
            transfer_file(_path, _token)
            print('success')
    else:
        search_files(_path, _token)
        print('success')


if __name__ == '__main__':
    args = sys.argv
    validate(args)
    path = args[1]
    main(path, token())
