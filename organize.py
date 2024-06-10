import os
import re
import shutil
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class Config:
    def __init__(self, json_config):
        self.inbox_path = json_config['inbox_path']
        self.notebooks_path = json_config['notebooks_path']
        self.boxes_path = json_config['boxes_path']
        self.boxes_file = json_config['boxes_file']
        self.last_modified_notes_file = json_config['last_modified_notes_file']
    
    @staticmethod
    def get_config_from_file(config_path):
        with open(config_path, 'r', encoding="utf-8") as config_file:
            return Config(json.load(config_file))

config = Config.get_config_from_file('config.json')

class HeaderLines:
    def __init__(self):
        self.header_lines = []

    @staticmethod
    def read_file(file_path):
        with open(file_path, 'r') as file:
            if not file.readline().startswith("---\n"):
                return None
            
            header_lines = []
            for line in file:
                if line.startswith("---"):
                    header_instance = HeaderLines()
                    header_instance.header_lines = header_lines
                    return header_instance

                header_lines.append(line.rstrip())
            
            return None

class ItemReference:
    def __init__(self):
        self.notebooks: Dict[str, 'Notebook'] = {}
        self.boxes: Dict[str, 'Box'] = {}
        self.notes: Dict[str, 'Note'] = {}
    
    @staticmethod
    def get_all_notes_from_notebooks_path(notebooks_path):
        notebook_folders = [os.path.join(notebooks_path, item) for item in os.listdir(notebooks_path) if os.path.isdir(os.path.join(notebooks_path, item))]
        item_ref = ItemReference()
        for notebook_folder_path in notebook_folders:
            note_files = [os.path.join(notebook_folder_path, item) for item in os.listdir(notebook_folder_path) if os.path.isfile(os.path.join(notebook_folder_path, item))]
            notebook_name, _ = os.path.splitext(os.path.basename(notebook_folder_path))
            for note_file in note_files:
                note_name, _ = os.path.splitext(os.path.basename(note_file))
                item_ref.notes[note_name] = Note(notebook_name, note_file)

        return item_ref

class Inbox(ItemReference):
    def __init__(self):
        super().__init__()
    
    def _move_boxes(self):
        for box in self.boxes.values():
            file_name = os.path.basename(box.file_path)
            new_path = os.path.join(config.boxes_path, file_name)
            shutil.move(box.file_path, new_path)

    def _move_notebooks(self):
        for notebook in self.notebooks.values():
            file_name = os.path.basename(notebook.file_path)
            new_path = os.path.join(config.notebooks_path, file_name)
            shutil.move(notebook.file_path, new_path)

    def _move_notes(self):
        for note in self.notes.values():
            file_name = os.path.basename(note.file_path)
            notebook_file_path = os.path.join(config.notebooks_path, note.notebook_name)

            if not os.path.exists(notebook_file_path):
                os.makedirs(notebook_file_path)

            new_note_path = os.path.join(notebook_file_path, file_name)

            if os.path.exists(new_note_path):
                raise Exception(f"Note {new_note_path} already exists!")

            shutil.move(note.file_path, new_note_path)
    
    def move_according_to_reference(self):
        self._move_boxes()
        self._move_notebooks()
        self._move_notes()
    
    def _write_on_boxes_file(self):
        with open(config.boxes_file, 'a', encoding="utf-8") as f:
            for box in self.boxes.values():
                box_name, _ = os.path.splitext(os.path.basename(box.file_path))
                f.write(f"[[{box_name}]]\n")
    
    def _write_on_box_file(self):
        for notebook in self.notebooks.values():
            notebook_name, _ = os.path.splitext(os.path.basename(notebook.file_path))
            box_file_path = os.path.join(config.boxes_path, f"{notebook.box_name}.md")
            open(box_file_path, 'a', encoding="utf-8").write(f"[[{notebook_name}]]\n")
    
    def _write_on_notebook_file(self):
        for note in self.notes.values():
            note_name, _ = os.path.splitext(os.path.basename(note.file_path))
            notebook_file_path = os.path.join(config.notebooks_path, f"{note.notebook_name}.md")
            open(notebook_file_path, 'a', encoding="utf-8").write(f"[[{note_name}]]\n")

    def write_refs(self):
        self._write_on_boxes_file()
        self._write_on_notebook_file()

    @staticmethod
    def _is_template_or_not_valid_ref(item_name):
        return item_name == None

    @staticmethod
    def process_inbox(inbox_path: str):
        inbox = Inbox()
        
        if not os.path.exists(inbox_path):
            raise Exception(f"The directory {inbox_path} does not exist.")

        inbox_files = [os.path.join(inbox_path, item) for item in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, item))]
        
        print("Processing Inbox:")
        for file_path in inbox_files:
            item_name, _ = os.path.splitext(os.path.basename(file_path))
            header_lines = HeaderLines.read_file(file_path)
            
            print(f"{file_path} ", end="")
            if header_lines == None:
                if item_name.startswith("Box"):
                    box = Box(file_path)
                    inbox.boxes[item_name] = box
                    print("added to Boxes")
            else:
                reference_line = header_lines.header_lines[0]
                reference_name = extract_reference_from_line(reference_line)
                
                if Inbox._is_template_or_not_valid_ref(reference_name):
                    print("ignored")
                    continue

                if reference_line.startswith("box"):
                    box_name = reference_name

                    notebook = Notebook(box_name, file_path)
                    inbox.notebooks[item_name] = notebook
                    print("added to Notebooks")
                elif reference_line.startswith("notebook"):
                    notebook_name = reference_name

                    note = Note(notebook_name, file_path)
                    inbox.notes[item_name] = note
                    print("added to Notes")
        return inbox

class Box:
    def __init__(self, file_path: str):
        self.notebooks: List['Notebook'] = []
        self.file_path: str = file_path

class Notebook:
    def __init__(self, box_name: str, file_path: str):
        self.box_name: str = box_name
        self.notes: List['Note'] = []
        self.file_path: str = file_path

class Note:
    def __init__(self, notebook_name: str, file_path: str):
        self.notebook_name: str = notebook_name
        self.file_path: str = file_path

class WeekNotes:
    def __init__(self, start_of_week: str, end_of_week: str):
        self.start_of_week = start_of_week
        self.end_of_week = end_of_week
        self.notes = []

class LastModifiedNotes:
    def __init__(self, all_notes: List['Note']):
        self.notes: List['Note'] = sorted(all_notes, key=lambda note: os.path.getmtime(note.file_path), reverse=True)
    
    def write_last_modified_notes_by_week(self, first_day_of_week=6):
        week_notes: Dict[str, 'WeekNotes'] = {}

        for note in self.notes:
            note_mtime = datetime.fromtimestamp(os.path.getmtime(note.file_path))

            start_of_week = self._get_start_of_week(note_mtime, first_day_of_week)
            end_of_week = start_of_week + timedelta(days=6)

            start_of_week_str = start_of_week.strftime("%Y-%m-%d")
            end_of_week_str = end_of_week.strftime("%Y-%m-%d")
            
            if start_of_week_str not in week_notes:
                week_notes[start_of_week_str] = WeekNotes(start_of_week_str, end_of_week_str)

            current_week = week_notes[start_of_week_str]
            current_week.notes.append(note)
        
        with open(config.last_modified_notes_file, "w", encoding="utf-8") as f:
            week_number = len(week_notes.values())

            for week_note in week_notes.values():
                f.write(f"# Week {week_number}: {week_note.start_of_week} - {week_note.end_of_week}\n")
                week_number -= 1
                for note in week_note.notes:
                    note_name = os.path.splitext(os.path.basename(note.file_path))[0]
                    f.write(f"[[{note_name}]]\n")
                f.write("\n")

    def _get_start_of_week(self, date: datetime, first_day_of_week: int) -> datetime:
        day_diff = (date.weekday() - first_day_of_week) % 7
        return date - timedelta(days=day_diff)

def extract_text(text: str, pattern: str) -> Optional[str]:
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None

def extract_reference_from_line(destin_line):
    return extract_text(destin_line, r"\[\[(.+)\]\]")

# If you want the destination line not to be the first one
def get_destination(header_lines_instance: HeaderLines, destination_type: str):
    for line in header_lines_instance.header_lines:
        if line.startswith(destination_type):
            return extract_text(line, r"(\[\[.+\]\])")
    
    return None

inbox = Inbox.process_inbox(config.inbox_path)
inbox.move_according_to_reference()
inbox.write_refs()

item_ref = ItemReference.get_all_notes_from_notebooks_path(config.notebooks_path)
last_modified_notes = LastModifiedNotes(list(item_ref.notes.values()))
last_modified_notes.write_last_modified_notes_by_week()