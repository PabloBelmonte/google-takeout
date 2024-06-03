import os
import subprocess
import json
from pathlib import Path
from pprint import pprint
import shutil


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
    print(os.getcwd())

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
            if not os.path.exists(f"{base_out_path}\{file.name}"):
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
    
if __name__ == "__main__":
    main()