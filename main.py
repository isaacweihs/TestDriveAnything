import sys
import os
import shutil
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QComboBox, 
QPushButton, QHBoxLayout, QStackedWidget, QSpinBox, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from package import parse as blk_parser

import time
import json

vehicle_type_dict = {"Tank": "tankModels", "Plane": "armada", "Boat": "ships"}

def set_game_directory(directory):
    with open(f"data//global//gamedir.txt", "w+") as gamedir:
        gamedir.write(directory)


def get_game_directory():
    with open(f"data//global//gamedir.txt", "r") as gamedir:
        try:
            return gamedir.readlines()[0]
        except:
            set_game_directory("")
            return None

def set_export_directories():
    global EXPORT_PATH_MISSION
    global EXPORT_PATH_VEHICLE

    gamedir = get_game_directory()

    if gamedir == None:
        EXPORT_PATH_MISSION = f"{os.curdir}//exports//"
        EXPORT_PATH_VEHICLE = f"{os.curdir}//exports//"
    else:
        gamedir = str(gamedir)
        EXPORT_PATH_MISSION = gamedir + "/UserMissions/Ask3lad/"
        EXPORT_PATH_VEHICLE = gamedir + "/content/pkg_local/gameData/units/tankModels/userVehicles/"

MANUAL_OVERRIDES = {
    ###TANKMODELS
    "cn_plz_05": "152mm"
}

NATIONS = {
    "cn": "CHINA",
    "fr": "FRANCE",
    "germ": "GERMANY",
    "il": "ISRAEL",
    "it": "ITALY",
    "jp": "JAPAN",
    "sw": "SWEDEN",
    "uk": "UNITED KINGDOM",
    "us": "USA",
    "ussr": "USSR_RUSSIA",
}

TYPE_CORR = {
    "Boat": "ships",
    "Plane": "armada",
    "Tank": "tankModels"
}

TEMP_PATH = os.path.abspath('./data/temp')

FILES_MARKED_FOR_DELETION = []

class ApplyWorker(QThread):
    """Worker thread to handle the apply function."""
    progress = pyqtSignal(str)  # Emit progress updates
    success = pyqtSignal(bool)  # Emit success status
    
    def __init__(self, apply_function, vehicle, parent=None):
        super().__init__(parent)
        self.apply_function = apply_function
        self.vehicle = vehicle

    def run(self):
        try:
            ################################################# -- 1
            self.progress.emit("Setting up prerequisites...")
            time.sleep(0.5)

            program_data = Program()
            operations = Operations()

            mission_file_txt = operations.clone_and_change_extension(program_data.mission_blk, '.txt', TEMP_PATH)
            vehicle_file_txt = operations.clone_and_change_extension(program_data.veh_blk, '.txt', TEMP_PATH)
            FILES_MARKED_FOR_DELETION.append(mission_file_txt)
            FILES_MARKED_FOR_DELETION.append(vehicle_file_txt)
            
            ################################################# -- 2
            self.progress.emit("Parsing mission data...")
            time.sleep(0.5)

            with open(mission_file_txt, "r") as mission:
                mission_file_parsed, mission_file_parsed_length = blk_parser.parse_blk_to_dict(''.join(mission))

            
            ################################################# -- 3
            self.progress.emit(f"Applying mission changes...\nLength: {mission_file_parsed_length}")
            time.sleep(0.5)

            parsed_mission = mission_file_parsed
            wing = blk_parser.find_value_by_path(parsed_mission, ["mission_settings", "player", "wing"])

            try:
                if blk_parser.find_element_by_value(parsed_mission, wing, self.vehicle.veh_type_id, path_is_index=True) != None:
                    player_unit_path = blk_parser.find_element_by_value(parsed_mission, wing, self.vehicle.veh_type_id, path_is_index=True)
                    player_unit_path_parent = blk_parser.closest_parent_by_path(parsed_mission, player_unit_path)
                else:
                    QMessageBox.critical(self, "Error", "Critical error - no player unit could be found. Fix the mission and try again.")
                    sys.exit()
            except:
                QMessageBox.critical(self, "Error", "Critical error - An unexpected error occured while applying changes.")
                sys.exit()
            
            if self.vehicle.ammo_types == None or self.vehicle.ammo_amount == None:
                QMessageBox.critical(self, "Error",f"Critical error - No ammunition selection could be found for the vehicle {self.vehicle.name}.")
                sys.exit()

            for i in range(0, 4):
                if self.vehicle.ammo_types[i] == "<default>" and self.vehicle.ammo_amount[i] == 0:
                    parsed_mission = blk_parser.modify_value_by_path(parsed_mission, player_unit_path_parent + [f"bullets{i}"], "")
                    parsed_mission = blk_parser.modify_value_by_path(parsed_mission, player_unit_path_parent + [f"bulletsCount{i}"], 0)
                else:
                    parsed_mission = blk_parser.modify_value_by_path(parsed_mission, player_unit_path_parent + [f"bullets{i}"], self.vehicle.ammo_types[i])
                    parsed_mission = blk_parser.modify_value_by_path(parsed_mission, player_unit_path_parent + [f"bulletsCount{i}"], self.vehicle.ammo_amount[i])
            
            parsed_mission = blk_parser.modify_value_by_path(parsed_mission, player_unit_path_parent + ["weapons"], self.vehicle.weapon)

            with open(EXPORT_PATH_MISSION + 'export_ask3lad_testdrive.txt', "w") as export_file:
                content = blk_parser.parse_dict_to_blk(parsed_mission)
                export_file.write(content)

            operations.clone_and_change_extension(EXPORT_PATH_MISSION + 'export_ask3lad_testdrive.txt', '.blk', EXPORT_PATH_MISSION)
            FILES_MARKED_FOR_DELETION.append(EXPORT_PATH_MISSION + 'export_ask3lad_testdrive.txt')


            ################################################# -- 4
            self.progress.emit("Changing vehicle...")
            time.sleep(0.5)
            
            with open(vehicle_file_txt, "r+") as veh_source:
                data = veh_source.readlines()[0].replace('\n', '')
                chars = []
                for char in data[-6::-1]:
                    if char != '/':
                        chars.append(char)
                    else:
                        break
                
                old_vehicle = ''.join(chars)[::-1]
                
                data = data.replace(old_vehicle, f"{self.vehicle.nation_id}_{self.vehicle.name}")

                veh_source.seek(0)
                veh_source.truncate(0)
                veh_source.write(data)

            operations.clone_and_change_extension(vehicle_file_txt, '.blk', EXPORT_PATH_VEHICLE)

            ################################################# -- 5 FINISH
            self.progress.emit("Finishing up...")
            time.sleep(0.5)

            operations.bulk_delete(FILES_MARKED_FOR_DELETION)

            
            # If everything succeeds, emit success
            self.success.emit(True)
        except Exception as e:
            print(f"Error during apply operation: {e}")
            self.success.emit(False)

class Program():
    def __init__(self):
        self.mission_blk = os.path.abspath('./data/blk/ask3lad_testdrive.blk')
        self.veh_blk = os.path.abspath('./data/blk/us_m2a4.blk')


class Operations():
    def clone_and_change_extension(self, source_file: str, new_extension: str, new_path: str) -> str:
        """
        Clones a file, changes its extension, and saves it to a new path.
        
        Args:
            source_file (str): The path to the source file.
            new_extension (str): The new file extension (e.g., '.txt', '.jpg').
            new_path (str): The directory where the new file will be saved.
            
        Returns:
            str: The path to the newly created file with the updated extension.
        
        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If the new extension is invalid.
            FileNotFoundError: If the specified new path does not exist.
        """
        # Ensure the source file exists
        if not os.path.isfile(source_file):
            raise FileNotFoundError(f"The source file '{source_file}' does not exist.")
        
        # Validate the new extension
        if not new_extension.startswith('.'):
            raise ValueError("The new extension must start with a dot (e.g., '.txt').")
        
        # Ensure the new path exists
        if not os.path.isdir(new_path):
            raise FileNotFoundError(f"The specified directory '{new_path}' does not exist.")
        
        # Construct the new file path with the updated extension in the specified directory
        base_name = os.path.splitext(os.path.basename(source_file))[0]  # Get the base name of the file
        new_file = os.path.abspath(os.path.join(new_path, base_name + new_extension))
        
        # Copy the source file to the new path with the updated name
        shutil.copy(source_file, new_file)
        
        return new_file
    
    def bulk_delete(self, files: list):
        for file in files:
            os.remove(os.path.abspath(file))


class Tank():
    def __init__(self, nation_id, veh_type_id, name):
        self.nation_id = nation_id
        self.name = name.lower()
        self.veh_type_id = veh_type_id 
        self.ammo_types = None
        self.ammo_amount = None
        
        data_file_path = os.path.abspath(f"./data/vehicles/{self.veh_type_id}/{self.nation_id}_{self.name}.json")
        with open(data_file_path) as data_file:
            self.data = json.load(data_file)

        try:
            self.weapon = self.data["weapon_presets"]["preset"]["name"]
        except KeyError:
            QMessageBox.warning("Warning", f"No weapon was found for <{self.name}>, weapons will be disabled for this vehicle.")
            self.weapon = ""

        self.gun_caliber = None
        if f"{self.nation_id}_{self.name}" in MANUAL_OVERRIDES:
            self.gun_caliber = MANUAL_OVERRIDES[f"{self.nation_id}_{self.name}"]
            self.caliber_source = "tda_OVERRIDE"
        else:
            try:
                self.caliber_source = self.data["commonWeapons"]["Weapon"][0]["blk"]
            except KeyError:
                try: 
                    self.caliber_source = self.data["commonWeapons"]["Weapon"]["blk"]
                except:
                    print(f"No weapon caliber found for {self.veh_type_id} - Patcher will not apply any ammunition for this vehicle.")
            
            if not any(char.isdigit() for char in self.caliber_source):
                print(f"No valid weapon caliber could be found for {self.veh_type_id} - Does the vehicle have a weapon?")
                self.caliber_source = None

            if self.caliber_source != None:
                self.caliber_source = self.caliber_source.split('/')[-1]

                self.gun_caliber = ""
                for char in self.caliber_source:
                    if char == "_" and not self.caliber_source[self.caliber_source.index(char) + 1].isnumeric():
                        break
                    elif char == "_" and self.caliber_source[self.caliber_source.index(char) - 1].isalpha():
                        break
                    elif len(self.gun_caliber) > 5:
                        break
                    else:
                        self.gun_caliber += char


    ############################# GET
    def get_vehicle_ammo_count(self):
        max_ammo = 0

        for stowages, attributes in self.data["ammoStowages"].items():
            for _t1, _t2 in attributes.items():
                if _t1 == "shells":
                    if type(_t2) == list:
                        for _t3 in _t2:
                            for _t4, value in _t3.items():
                                try:
                                    if type(value) == dict and value["count"] != None:
                                        max_ammo += value["count"]
                                except:
                                    print(f"Error finding ammo count in {_t4} - can be disregarded if program keeps running.")
                    elif type(_t2) == dict:
                        for _t3, value in _t2.items():
                            try:
                                if type(value) == dict and value["count"] != None:
                                    max_ammo += value["count"]
                            except:
                                print(f"Error finding ammo count in {_t3} - can be disregarded if program keeps running.")
                    else:
                        print("'shells' of type: " + type(_t2), + " please contact developer with the name of the vehicle on which this error occurred.")

        return max_ammo
    
    
    def get_vehicle_ammo_types(self):
        if self.caliber_source != None or self.caliber_source == "tda_OVERRIDE":
            ammo_types = []
            for modification, _v in self.data["modifications"].items():
                if self.gun_caliber in modification and "ammo_pack" not in modification:
                    ammo_types.append(modification)
                elif self.gun_caliber in ["12_7mm", "13_2mm"] and "ammo_pack" not in modification:
                    ammo_types.append(modification)
                elif self.gun_caliber in ["7_62", "7_92"] and "ammo_pack" not in modification:
                    ammo_types.append(modification)

        return ammo_types
    

    ################################# GET
    def set_vehicle_ammo_types(self, ammo_types, ammo_amount):
        self.ammo_types = ammo_types
        self.ammo_amount = ammo_amount


### APP
class TestDriveTool(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WT Test Drive Tool")
        self.setGeometry(100, 100, 1000, 600)

        # State variables
        self.total_ammo_selected = 0

        # Initialize the main layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Create a QStackedWidget to manage pages
        self.pages = QStackedWidget()
        self.main_layout.addWidget(self.pages)

        # Initialize pages
        self.vehicle_selection_page = self.create_vehicle_selection_page()
        self.ammunition_selection_page = self.create_ammunition_selection_page()
        self.loading_page = self.create_loading_page()

        # Add pages to QStackedWidget
        self.pages.addWidget(self.vehicle_selection_page)
        self.pages.addWidget(self.ammunition_selection_page)
        self.pages.addWidget(self.loading_page)

        # Set the main page as the default
        self.pages.setCurrentWidget(self.vehicle_selection_page)

        # Styling
        self.setStyleSheet("""
            QWidget {
                background-color: #101010;
                font-family: Arial;
                font-size: 16px;
            }
            QLabel {
                font-size: 16px; 
                font-weight: bold;
                color: #AAAAAA;
            }
            QComboBox {
                background-color: #303030;
                border: 1px solid #303030;
                padding: 5px;
            }
            QPushButton {
                background-color: #303030;
                color: #AAAAAA;
                font-size: 16px;
                padding: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #202020;
            }
        """)

        if get_game_directory() == None:
            self.ADD_TO_GAME_FILES = QMessageBox.question(
                self,
                "File Initialization",
                "Would you like the program to automatically replace the old missions so that you don't have to drag/drop them?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if self.ADD_TO_GAME_FILES == QMessageBox.StandardButton.Yes:
                self.GAME_DIRECTORY = QFileDialog.getExistingDirectory(
                    self, "Please select the Game Directory for War Thunder"
                )

                if self.GAME_DIRECTORY == "": 
                    set_game_directory(self.GAME_DIRECTORY)
                    sys.exit()

            set_game_directory(self.GAME_DIRECTORY)
            if os.path.isfile(get_game_directory() + '/aces.vromfs.bin') != True:
                set_game_directory("")
                print("Warning - aces.vromfs.bin could not be located in the directory. Please try again at next program launch.")
            
            self.activateWindow()
        
        set_export_directories()


    def create_vehicle_selection_page(self):
        """Creates the vehicle selection page."""
        page = QWidget()
        layout = QVBoxLayout(page)

        # Title label
        title_label = QLabel("WT Test Drive Tool")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Description label
        desc_label = QLabel("Test drive any vehicle using this program.")
        layout.addWidget(desc_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Nation selection
        nation_label = QLabel("Choose your desired vehicle's nation:")
        layout.addWidget(nation_label, alignment=Qt.AlignmentFlag.AlignLeft)

        self.nation_combo = QComboBox()
        self.nation_combo.addItems(["Select a nation"])
        self.nation_combo.currentIndexChanged.connect(self.on_selection_changed)

        for nation in NATIONS.values():
            self.nation_combo.addItems([nation])

        self.nation_combo.addItems(["MISC"])

        layout.addWidget(self.nation_combo)

        # Vehicle type selection
        type_label = QLabel("Choose your desired vehicle type:")
        layout.addWidget(type_label, alignment=Qt.AlignmentFlag.AlignLeft)

        self.type_combo = QComboBox()
        self.type_combo.setEnabled(False)
        self.type_combo.addItems(["Select a vehicle type", "Tank", "Plane", "Boat"])
        self.type_combo.currentIndexChanged.connect(self.on_selection_changed)
        layout.addWidget(self.type_combo)

        # Vehicle selection
        vehicle_label = QLabel("Choose your desired vehicle:")
        layout.addWidget(vehicle_label, alignment=Qt.AlignmentFlag.AlignLeft)

        self.vehicle_combo = QComboBox()
        self.vehicle_combo.setEnabled(False)
        self.vehicle_combo.currentIndexChanged.connect(self.on_selection_changed)
        layout.addWidget(self.vehicle_combo)

        # Next button
        self.next_button = QPushButton("Next")
        self.next_button.setEnabled(False)  # Initially disabled
        self.next_button.clicked.connect(self.on_next_clicked)
        layout.addWidget(self.next_button)

        return page


    def create_ammunition_selection_page(self):
        """Creates the ammunition selection page."""
        self.max_ammo = 0

        page = QWidget()
        layout = QVBoxLayout(page)

        # Title label for ammunition page
        self.ammo_title_label = QLabel("Choose Ammunition")
        self.ammo_title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(self.ammo_title_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Display Max Ammo
        self.ammo_desc_label = QLabel(f"Select up to {self.max_ammo} rounds of ammunition for your tank.")
        layout.addWidget(self.ammo_desc_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Create ammunition selection dropdowns
        self.ammo_combos = []
        self.amount_combos = []

        for i in range(4):
            ammo_layout = QHBoxLayout()
            
            self.ammo_combo = QComboBox()
            self.ammo_combo.addItems(["<default>"])
            self.ammo_combos.append(self.ammo_combo)
            ammo_layout.addWidget(self.ammo_combo)
            
            self.amount_combo = QComboBox()
            self.amount_combo.addItems([str(i) for i in range(0, self.max_ammo + 1)])
            self.amount_combo.currentIndexChanged.connect(self.on_amount_changed)
            self.amount_combos.append(self.amount_combo)
            ammo_layout.addWidget(self.amount_combo)
            
            layout.addLayout(ammo_layout)

        # Apply button
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.on_apply_clicked)
        layout.addWidget(apply_button)

        return page
        
    
    def create_loading_page(self):
        """Creates the loading page."""
        page = QWidget()
        layout = QVBoxLayout(page)

        loading_label = QLabel("Loading, please wait...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(loading_label)

        self.operation_label = QLabel("")
        self.operation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.operation_label)

        return page


    def on_selection_changed(self):
        """Manages dropdown enabling and ensures 'Next' button is activated only when valid selections are made."""
        try:
            nation_selected = self.nation_combo.currentIndex() > 0
            if nation_selected:
                self.type_combo.setEnabled(True)
            else:
                self.type_combo.setEnabled(False)
                self.type_combo.blockSignals(True)
                self.type_combo.setCurrentIndex(0)  # Reset type dropdown
                self.type_combo.blockSignals(False)

            type_selected = self.type_combo.currentIndex() > 0
            if nation_selected and type_selected:
                self.populate_vehicle_combo()
                self.vehicle_combo.setEnabled(True)
            else:
                self.vehicle_combo.blockSignals(True)
                self.vehicle_combo.clear()

                self.vehicle_combo.addItem("Select a vehicle")
                self.vehicle_combo.blockSignals(False)
                self.vehicle_combo.setEnabled(False)

            vehicle_selected = self.vehicle_combo.currentIndex() > 0
            self.next_button.setEnabled(nation_selected and type_selected and vehicle_selected)
        except Exception as e:
            print(f"Error in on_selection_changed: {e}")


    def populate_vehicle_combo(self):
        """Populates the vehicle dropdown based on selected nation and type."""
        try:
            nation = self.nation_combo.currentText()
            vehicle_type = self.type_combo.currentText()

            # Ensure valid nation and vehicle type
            if nation == "Select a nation" or vehicle_type == "Select a vehicle type":
                self.vehicle_combo.blockSignals(True)
                self.vehicle_combo.clear()
                self.vehicle_combo.addItem("Select a vehicle")
                self.vehicle_combo.blockSignals(False)
                return

            # Data for vehicle options
            self.nation_id = None
            self.veh_type_id = None
            for k, v in NATIONS.items():
                if v == nation:
                    self.nation_id = k
                    self.veh_type_id = TYPE_CORR[vehicle_type]
                    break
                
            vehicles = {}
            vehicles[(nation, vehicle_type)] = self.get_vehicles_from_nation()

            # Populate the vehicle dropdown
            current_items = [self.vehicle_combo.itemText(i) for i in range(self.vehicle_combo.count())]
            new_items = vehicles.get((nation, vehicle_type), [])

            # Only update if the contents differ
            if current_items[1:] != new_items:  # Ignore "Select a vehicle"
                self.vehicle_combo.blockSignals(True)
                self.vehicle_combo.clear()
                self.vehicle_combo.addItem("Select a vehicle")
                self.vehicle_combo.addItems(new_items)
                self.vehicle_combo.blockSignals(False)
        except Exception as e:
            print(f"Error in populate_vehicle_combo: {e}")


    def on_next_clicked(self):
        """Navigates to ammunition selection page if a tank was selected."""
        vehicle_type = self.type_combo.currentText()
        if vehicle_type == "Tank":
            self.VEHICLE = Tank(self.nation_id, self.veh_type_id, self.vehicle_combo.currentText())

            self.ammo_types = self.VEHICLE.get_vehicle_ammo_types()
            for item in self.ammo_combos:
                item.addItems(self.ammo_types)

            veh_max_ammo = self.VEHICLE.get_vehicle_ammo_count()
            self.update_max_ammo(veh_max_ammo)

            self.pages.setCurrentWidget(self.ammunition_selection_page)
        else:
            QMessageBox.information(self, "Information", f"You selected a {vehicle_type}!")
    

    def on_amount_changed(self):
        """Checks the total amount of ammo selected to ensure it doesn't exceed the max."""
        self.total_ammo_selected = sum(
            int(combo.currentText()) if combo.currentText().isdigit() else 0
            for combo in self.amount_combos
        )
        if self.total_ammo_selected > self.max_ammo:
            QMessageBox.warning(self, "Warning", "You have exceeded the maximum ammo limit!")


    def apply_function(self):
        """Parses final mission data
        """
        

    def on_apply_clicked(self, ammo_data):
        """Handles the apply button click."""
        # Switch to the loading page
        self.pages.setCurrentWidget(self.loading_page)

        # Set the ammunition for the vehicle
        ammo_types, ammo_amount = self.get_ammo_selection()
        self.VEHICLE.set_vehicle_ammo_types(ammo_types, ammo_amount)

        # Create and start the worker thread
        self.worker = ApplyWorker(self.apply_function, self.VEHICLE) ############################### PASS SOMETHING MORE THROUGH HERE --- WHAT AMMO USER HAS SELECTED TO APPLY!!!
        self.worker.progress.connect(self.update_loading_screen)
        self.worker.success.connect(self.on_apply_finished)
        self.worker.start()


    def update_loading_screen(self, message):
        """Updates the loading screen with the current operation."""
        self.operation_label.setText(message)


    def on_apply_finished(self, success):
        """Handles completion of the apply operation."""
        if success:
            QMessageBox.information(self, "Success", "Operation completed successfully!")
        else:
            QMessageBox.critical(self, "Error", "An error occurred during the operation.")

        # Exit program
        sys.exit()


    ################################# GET
    def get_vehicles_from_nation(self):
        directory = os.path.abspath(f"./data/vehicles/{self.veh_type_id}")

        vehicle_names = []
        for file in os.listdir(directory):
            if file[0:len(self.nation_id)] == self.nation_id:
                veh_name = file.replace(f"{self.nation_id}_", "").replace(".json", "").upper()
                vehicle_names.append(veh_name)

        return vehicle_names
    
    def get_ammo_selection(self):
        ammo_types = []
        ammo_amount = []

        for combo in self.ammo_combos:
            ammo_types.append(combo.currentText())
        
        for combo in self.amount_combos:
            ammo_amount.append(int(combo.currentText()))

        return ammo_types, ammo_amount
    

    ################################# SET
    def update_max_ammo(self, new_max_ammo):
        """Updates the max_ammo attribute and refreshes the ammo page."""
        self.max_ammo = new_max_ammo

        # Update ammunition selection page if it exists
        if hasattr(self, "ammo_combos") and hasattr(self, "amount_combos"):
            for amount_combo in self.amount_combos:
                amount_combo.clear()
                amount_combo.addItems([str(i) for i in range(0, self.max_ammo + 1)])

        # Update any UI labels reflecting max_ammo
        if hasattr(self, "ammo_desc_label"):
            self.ammo_desc_label.setText(f"Select up to {self.max_ammo} rounds of ammunition for your tank.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestDriveTool()
    window.show()
    sys.exit(app.exec())