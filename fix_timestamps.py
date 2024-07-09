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
import numpy as np
import time

from numbers import Real
from timeit import default_timer as timer
from dataclasses import dataclass

from multiprocessing import Process
import concurrent.futures

@dataclass
class WatchTimer:
    """Data class for watch timer."""
    id: str = ""
    start_time: Real = None
    end_time: Real = None
    elapsed_time: Real = None

    def start(self) -> None:
        self.start_time = timer()
    
    def stop(self) -> None:
        self.end_time = timer()
        self.elapsed_time = self.end_time - self.start_time
    
    def get_time(self) -> Real:
        return self.elapsed_time
    
    def log(self, file_name: str, append: bool = True) -> None:
        """Log results into a file"""

        open_letter = "a" if append else "w"
        with open(file_name, open_letter) as results:
            results.write(
                f"""
<Watch timer>: {self.id}
<Start time>: {self.start_time:.3f} s
<End time>: {self.end_time:.3f} s
<Elapsed time>: {self.elapsed_time:.3f} s
"""
            )
    
    def __repr__(self) -> str:
        """To replace the print() method return for this object."""
        return f"""
<Watch timer>: {self.id}
<Start time>: {self.start_time:.3f} s
<End time>: {self.end_time:.3f} s
<Elapsed time>: {self.elapsed_time:.3f} s
"""
    
    def __post_init__(self) -> None:
        """Start timer"""
        self.start()

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

def hash_difference(hash0: imagehash.ImageHash, hash1: imagehash.ImageHash, cutoff: int):
    difference = hash0 - hash1
    similar = abs(hash0 - hash1) <= cutoff
    if similar:
        logging.debug(f'Images are similar, with diff = <{difference}>')
    else:
        logging.debug(f'Images are not similar, with diff = <{difference}>')
    return similar, difference

def check_hash_similarity(file_path:Path):
    # hash = imagehash.average_hash(Image.open(file_path))
    # hash = imagehash.phash(Image.open(file_path))
    hash = imagehash.dhash(Image.open(file_path))
    logging.debug(f"Hash for file {file_path} is: <{hash}>")
    return {str(file_path): str(hash)}


def build_image_hash_dict(
    base_path:Path,
    go_to_subfolders:bool=True,
    ignore_folders:list=[],
    arg_list:list=[],
    ) -> dict:
    hash_img_dict = {}
    ignore_extensions = [
        ".lrv",
        ".mp4",
        ".dng",
    ]
    
    for file_path in base_path.iterdir():
        if file_path.is_dir() and file_path.name not in ignore_folders:
            logging.debug(file_path)
            if go_to_subfolders:
                go_to_path(file_path)
                build_image_hash_dict(
                    base_path=file_path,
                    go_to_subfolders=go_to_subfolders,
                    arg_list=arg_list,
                )
        else:
            if file_path.is_file():
                extension = file_path.suffix
                if extension.lower() in ignore_extensions:
                    continue
                logging.debug(f"Extension: {extension} for file {file_path}")
                arg_list.append(file_path)
    n_threads = None
    n_threads = min(32, (os.cpu_count() or 1) + 4)
    my_timer = WatchTimer(id=f"Check similarity with n_threads = {n_threads}.")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as executor:
        return_values = executor.map(check_hash_similarity, arg_list)
    for item in return_values:
        hash_img_dict.update(item)
    time.sleep(0.01)
    my_timer.stop()
    time.sleep(0.01)
    my_timer.log(file_name='timer.log', append = True)
    
    return hash_img_dict

def find_duplicate_images(similarity_dict:dict, cutoff:int=5):
    already_checked = []
    for nxt_img in similarity_dict:
        if str(nxt_img) not in already_checked:
            most_similar, min_hash = find_most_similar_image(
                file_path=Path(str(nxt_img)),
                hash_img_dict=similarity_dict,
                cutoff=cutoff,
            )
            if most_similar is None:
                already_checked.append(str(nxt_img))
                continue
            img_name = Path(nxt_img).name
            img_base_path = Path(nxt_img).parent
            similar_name = Path(most_similar).name
            similar_base_path = Path(most_similar).parent
            msg = f"Image <{img_name}> is similar with <{similar_name}> [hash diff = <{min_hash}>]"
            if img_base_path == similar_base_path:
                msg += f"\n\tBoth images are in the same folder : <{img_base_path}>"
            else:
                msg += f"\n\tImages are in different folders: <{img_base_path}> and <{similar_base_path}>"
            logging.info(msg)
            if str(most_similar) not in already_checked:
                already_checked.append(str(most_similar))

def find_most_similar_image(file_path:Path, hash_img_dict:dict, cutoff:int) -> Path:
    if str(file_path) in hash_img_dict:
        hash0 = imagehash.hex_to_hash(hash_img_dict[str(file_path)])
    else:
        temp = check_hash_similarity(file_path=Path(file_path))
        hash0 = imagehash.hex_to_hash(temp[str(file_path)])
    all_similar = {}
    for fpath in hash_img_dict:
        next_hash = imagehash.hex_to_hash(hash_img_dict[fpath])
        if str(fpath) == str(file_path):
            continue
        logging.debug(f"Next file path: {fpath}")
        similar, difference = hash_difference(
            hash0=hash0,
            hash1=next_hash,
            cutoff=cutoff,
            )
        if similar:
            all_similar.update({difference: fpath})
        
    if all_similar == {}:
        return None, None
    min_hash = min(all_similar.keys())
    return all_similar.get(min_hash), min_hash

def save_json(hash_img_dict:dict, out_file:Path):
    with open(out_file, "w") as f:
        json.dump(hash_img_dict, f, indent=4)

def load_json(in_file:Path):
    with open(in_file, "r") as f:
        return json.load(f)

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
    level = logging.INFO
    logging.basicConfig(filename='timestamps.log', filemode='w', format='[%(levelname)s] - %(message)s', level=level)
    # logging.basicConfig(filename='timestamps.log', filemode='w', format='%(message)s', level=level)
    
    # main()
    
    current_path = Path(__file__).parent.absolute()
    
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    
    similarity_dict = build_image_hash_dict(
        # base_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\DRONE"),
        # base_path=Path(r"C:\BACKUP FOTOS ONEDRIVE\DRONE"),
        base_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\Fotos Casamento"),
        # base_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\Lapinha"),
        go_to_subfolders=True,
        # ignore_folders=["teste"],
    )
    save_json(similarity_dict, current_path / "fotos_casamento_timestamps.json")
    # save_json(similarity_dict, current_path / "drone_timestamps.json")
    
    # similarity_dict = load_json(current_path / "drone_timestamps.json")
    # similarity_dict = load_json(current_path / "timestamps.json")
    similarity_dict = load_json(current_path / "fotos_casamento_timestamps.json")
    logging.info(pformat(similarity_dict))
    
    find_duplicate_images(
        similarity_dict=similarity_dict.copy(),
        cutoff=0
    )
    pprint(similarity_dict)
    
    _STOP_
    loop_over_files(
        # base_path=Path(r"C:\BACKUP FOTOS ONEDRIVE\Pictures"),
        # base_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\Download"),
        # base_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\takeout"),
        # base_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\Camera Roll"),
        # base_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\DRONE"),
        base_path=Path(r"C:\Users\Pablo\OneDrive\Pictures\Fotos Casamento"),
        go_to_subfolders=1,
        # ignore_folders=["teste"],
        modfify=0
    )
    
    # modify_timestamps(file_path=file_path, modfify=False)
    # # modify_timestamps(file_path=file_path)