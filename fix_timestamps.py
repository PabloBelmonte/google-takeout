import os
import subprocess
import json
from pathlib import Path
from pprint import pprint, pformat
import shutil
import datetime
import re
# pip install win32-setctime
from win32_setctime import setctime
import logging
from PIL import Image, ImageFile
import imagehash

# Run the exiftool command to fix timestamps
def call_exiftool(exiftool_path:Path, target_path:Path):
    # exiftool -r -d %s -tagsfromfile "%d/%F.json" "-FileCreateDate<PhotoTakenTimeTimestamp" -ext "*" -overwrite_original -progress --ext json "."
    subprocess.call([
        str(exiftool_path),
        "-r",
        "-d",
        "%s",
        "-tagsfromfile",
        "%d/%F.json",
        "-FileCreateDate<PhotoTakenTimeTimestamp",
        "-ext",
        "*",
        "-overwrite_original",
        "-progress",
        "--ext",
        "json",
        str(target_path)
        ])

def go_to_path(target_path:Path):
    os.chdir(str(target_path))
    logging.debug(os.getcwd())

def verify_json_files(target_path:Path):
    # Get all the json files within the target path and subfolders
    # json_files = target_path.glob('**/*.json')
    json_files = target_path.glob('**/*/*.json')
    for json_file in json_files:
        json_file_name = json_file.name
        print(json_file_name)
        # Check if theare are 2 extensions or more, like *.jpg.json
        if len(json_file_name.split('.')) < 3:
            # Get the original file with no json extension
            original_file_name = json_file_name.split('.')[0]
            original_file = target_path.glob(f'**/{original_file_name}.*')
            # Remove json extension from list
            original_file = [f for f in original_file if f.suffix != '.json']
            if len(original_file) > 1:
                raise Exception(f"Error: More than one file for list > {original_file}")
            elif len(original_file) == 0:
                print(f"[WARNING]: No file associated with json > '{json_file_name}'")
                continue
            
            file_extenstion = original_file[0].suffix
            new_json = original_file_name + file_extenstion + '.json'
            json_file.rename(new_json)
            print(f"[WARNING]: Renamed '{json_file_name}' to '{new_json}'")

def copy_files(target_path:Path, output_path:Path, album_names:list):
    non_json_files = target_path.glob('**/*/*.*')
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    for file in non_json_files:
        if file.suffix != '.json':
            # Google Fotos
            parent_folder = file.parent.name
            if parent_folder in album_names:
                base_out_path = f"{output_path}\{parent_folder}"
                if not os.path.exists(base_out_path):
                    os.makedirs(base_out_path)
            else:
                base_out_path = f"{output_path}"
            print(f"Copying '{file}' to '{base_out_path}\{file.name}'")
            # shutil.copy(file, f"{base_out_path}\{file.name}")
            # Check if file exists
            if os.path.exists(f"{base_out_path}\{file.name}"):
                os.remove(f"{base_out_path}\{file.name}")
            file.rename(f"{base_out_path}\{file.name}")

def main():
    current_path = Path(__file__).parent.absolute()
    # Got from "https://exiftool.org"
    exiftool_path = current_path / 'exiftool.exe'
    # target_path = Path(r"D:\Pablo\Downloads\takeout-20240602T024945Z\Takeout\Google Fotos")
    # target_path = Path(r"D:\Pablo\Downloads\takeout-20240602T021041Z\Takeout\Google Fotos")
    out_name = 'takeout-20240602T024945Z'; album_names = ["Lapinha", "Lixeira"]
    # out_name = 'takeout-20240602T021041Z'; album_names = []
    target_path = Path(rf"D:\Pablo\Downloads\{out_name}\Takeout\Google Fotos")
    
    # target_path = Path(r"D:\Pablo\Downloads\takeout-20240602T024945Z\Takeout - TEST\Google Fotos")
    
    output_path = Path(r"D:\Pablo\Downloads\takeout-20240602T021041Z\Takeout\Google Fotos\output")
    output_path = current_path / out_name
    go_to_path(target_path=target_path)
    verify_json_files(target_path=target_path)
    call_exiftool(exiftool_path=exiftool_path, target_path=target_path)
    copy_files(target_path=target_path, output_path=output_path, album_names=album_names)


def get_file_timestamps(file_path:Path):
    stinfo = os.stat(file_path)
    creation_time = datetime.datetime.fromtimestamp(stinfo.st_ctime)
    modification_time = datetime.datetime.fromtimestamp(stinfo.st_mtime)
    access_time = datetime.datetime.fromtimestamp(stinfo.st_atime)
    logging.info(f"Creation time: {creation_time.year}/{creation_time.month}/{creation_time.day}")
    logging.info(f"Modification time: {modification_time.year}/{modification_time.month}/{modification_time.day}")
    logging.info(f"Access time: {access_time.year}/{access_time.month}/{access_time.day}")
    return creation_time, modification_time, access_time

def regex_compile_list_and_search(list_phrase : list, text : str):
    valid = re.compile("|".join(list_phrase))
    for m in valid.finditer(text):
        yield m

def identity_file_date_from_name(file_path:Path):
    date_time = None
    date_time_stamp = None
    # No suffix
    file_name = file_path.stem
    # file_name = "2015-02-09(1)"
    # file_name = "2015-02-09(2)"
    # file_name = ""
    # file_name = "Screenshot_2024-03-06-10-01-49-163_com.google.a"
    # file_name = "VID_20220816_165640"
    # file_name = "2013-10-08 - Copia"
    logging.info(f"File name: {file_name}")
    
    search_list = [
        # "2015-02-09(1)",
        "\d\d\d\d(-)?\d\d(-)?\d\d",
        # "(Pupil grid size)\s*:\s+\d+\s+by\s+\d+",
        # "(Image grid size)\s*:\s+\d+\s+by\s+\d+",
        # "(Center point is):\s*(row)?\s*\d+[.,]\s*(column)?\s*\d+",
        ##### "Data area is .* µm wide."
        # f"(Values are){SPACE_WORD}(\.)?(\s+\=)?(\s+{FLOAT_NUM})?\n",
        # "(Values are){SPACE_WORD}",
    ]
    for m in regex_compile_list_and_search(search_list, file_name):
        logging.info(f"[{m.start()}:{m.end()}] : <{m.group()}>")
        if "-" in m.group():
            date = m.group().strip()
            date_time = datetime.datetime.strptime(date, "%Y-%m-%d")
            break
        else:
            date = m.group().strip()
            try:
                date_time = datetime.datetime.strptime(date, "%Y%m%d")
            except ValueError:
                date_time = None
            break
    if date_time is None:
        err_ms = f"File name: {file_name} not found in regex:"
        logging.error(err_ms)
        logging.debug(f"Regex pattern = {search_list}")
        # raise Exception(err_ms)
    else:
        date_time_stamp = date_time.timestamp()
        logging.debug(f"Name date time: {date_time.year}/{date_time.month}/{date_time.day}")
    return date_time_stamp, date_time

def equal(date1:datetime.datetime, date2:datetime.datetime):
    return date1.year == date2.year\
        and date1.month == date2.month\
            and date1.day == date2.day

def modify_timestamps(file_path:Path, modfify:bool=True):
    logging.info("----------------------------------------")
    creation_datetime, modification_datetime, _ = get_file_timestamps(file_path)
    _, name_date_time = identity_file_date_from_name(file_path)
    
    needs_modification = False
    if name_date_time is None:
        if not equal(creation_datetime, modification_datetime):
            needs_modification = True
        min_date = min(creation_datetime, modification_datetime)
        logging.info(f"[min_date (3)]: {min_date.year}/{min_date.month}/{min_date.day}")
    else:
        if not equal(creation_datetime, modification_datetime) \
            or not equal(creation_datetime, name_date_time) \
                or not equal(name_date_time, modification_datetime):
            needs_modification = True
        min_date = min(creation_datetime, modification_datetime, name_date_time)
        logging.info(f"[min_date (2)]: {min_date.year}/{min_date.month}/{min_date.day}")
    
    min_date = min_date.timestamp()
    if modfify and needs_modification:
        # Set modified timestamp
        os.utime(file_path, (min_date, min_date))
        # Set creation timestamp
        setctime(file_path, min_date)
        logging.critical("[REAL] Modified timestamps!")
    elif needs_modification:
        logging.critical("[MOCK] Would be modified!")
    
    asdsda

def hash_difference(hash0: imagehash.ImageHash, hash1: imagehash.ImageHash, cutoff: int=5):
    difference = hash0 - hash1
    if abs(hash0 - hash1) < cutoff:
        logging.debug(f'Images are similar, with diff = <{difference}>')
    else:
        logging.debug(f'Images are not similar, with diff = <{difference}>')

import time
from dataclasses import dataclass
@dataclass
class HashDict:
    data:dict

def check_hash_similarity(file_path:Path, hash_img_dict:HashDict=HashDict(data={})):
    hash = imagehash.average_hash(Image.open(file_path))
    # time.sleep(0.01)
    logging.debug(f"Hash for file {file_path} is: <{hash}>")
    hash_img_dict.data.setdefault(str(file_path), str(hash))

def build_image_hash_dict(
    base_path:Path,
    go_to_subfolders:bool=True,
    ignore_folders:list=[],
    ) -> dict:
    # hash_img_dict = {}
    hash_img_dict = HashDict(data={})
    ignore_extensions = [
        ".lrv",
        ".mp4",
        ".dng",
    ]
    
    from multiprocessing import Process
    ######## CHECK WITH QUEUE????
    
    processes = []
    
    for file_path in base_path.iterdir():
        if file_path.is_dir() and file_path.name not in ignore_folders:
            logging.debug(file_path)
            if go_to_subfolders:
                go_to_path(file_path)
                build_image_hash_dict(
                    base_path=file_path,
                    go_to_subfolders=go_to_subfolders,
                )
        else:
            if file_path.is_file():
                extension = file_path.suffix
                if extension.lower() in ignore_extensions:
                    continue
                logging.debug(f"Extension: {extension} for file {file_path}")
                # check_hash_similarity(file_path=file_path, hash_img_dict=hash_img_dict)
                p = Process(target=check_hash_similarity, args=(file_path, hash_img_dict))
                processes.append(p)
    
    for p in processes:
        p.start()
    
    for p in processes:
        p.join()
    
    return hash_img_dict

def find_most_similar_image(file_path:Path, hash_img_dict:HashDict) -> Path:
    if file_path in hash_img_dict.data:
        hash0 = imagehash.hex_to_hash(hash_img_dict.data[file_path])
    else:
        temp = HashDict(data={})
        check_hash_similarity(file_path=Path(file_path), hash_img_dict=temp)
        hash0 = imagehash.hex_to_hash(temp[str(file_path)])
        
    for fpath in hash_img_dict.data:
        next_hash = imagehash.hex_to_hash(hash_img_dict.data[fpath])
        if fpath == file_path:
            continue
        logging.debug(f"Next file path: {fpath}")
        hash_difference(
            hash0=hash0,
            hash1=next_hash,
            cutoff=5,
            )

def save_json(hash_img_dict:dict, out_file:Path):
    # Check if file exists
    # if os.path.exists(out_file):
    #     asdasd
    with open(out_file, "w") as f:
        json.dump(hash_img_dict, f, indent=4)

def loop_over_files(
    base_path:Path,
    go_to_subfolders:bool=True,
    ignore_folders:list=[],
    modfify:bool=True
    ):
    for file_path in base_path.iterdir():
        if file_path.is_dir() and file_path.name not in ignore_folders:
            logging.debug(file_path)
            if go_to_subfolders:
                go_to_path(file_path)
                loop_over_files(
                    base_path=file_path,
                    go_to_subfolders=go_to_subfolders,
                    modfify=modfify
                )
        else:
            if file_path.is_file():
                modify_timestamps(file_path=file_path, modfify=modfify)

if __name__ == "__main__":
    # Set logging to file and console
    level = logging.DEBUG
    logging.basicConfig(filename='timestamps.log', filemode='w', format='[%(levelname)s] - %(message)s', level=level)
    # logging.basicConfig(filename='timestamps.log', filemode='w', format='%(message)s', level=level)
    
    # main()
    
    current_path = Path(__file__).parent.absolute()
    
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    
    
    # file_path = Path(r"D:\Pablo\Downloads\test - Copia.jpg")
    # file_path = Path(r"D:\Pablo\Downloads\2023-12-18 - Copia.jpg")
    # # file_path = Path(r"C:\Users\Pablo\OneDrive\Pictures\takeout\2015-02-09 - Copia.jpg")
    # # file_path = Path(r"C:\Users\Pablo\OneDrive\Pictures\takeout\2015-02-09.jpg")
    # # file_path = Path(r"C:\Users\Pablo\OneDrive\Pictures\takeout\2015-02-09(1).jpg")
    # # file_path = Path(r"C:\Users\Pablo\OneDrive\Pictures\takeout\2013-10-08 - Copia.jpg")
    # # file_path = Path(r"C:\Users\Pablo\OneDrive\Pictures\takeout\2013-10-08.jpg")
    # file_path = Path(r"C:\Users\Pablo\OneDrive\Pictures\takeout\Screenshot_2021-12-18-13-57-12-973_com.google.a.jpg")
    
    # check_similarity()
    
    similarity_dict = build_image_hash_dict(
        base_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\DRONE"),
        # base_path=Path(r"C:\BACKUP FOTOS ONEDRIVE\DRONE"),
        go_to_subfolders=1,
        # ignore_folders=["teste"],
    )
    logging.info(pformat(similarity_dict))
    asd
    save_json(similarity_dict, current_path / "timestamps.json")
    
    find_most_similar_image(
        file_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\DRONE\Recovered_jpg_file(35).jpg"),
        hash_img_dict=similarity_dict
    )
    
    _STOP_
    loop_over_files(
        # base_path=Path(r"C:\BACKUP FOTOS ONEDRIVE\Pictures"),
        # base_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\Download"),
        # base_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\takeout"),
        # base_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\Camera Roll"),
        base_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\DRONE"),
        go_to_subfolders=1,
        # ignore_folders=["teste"],
        modfify=0
    )
    
    # modify_timestamps(file_path=file_path, modfify=False)
    # # modify_timestamps(file_path=file_path)