import util
from configparser import ConfigParser
import webbrowser


config_object = ConfigParser()
config_object.read("config/config.ini")

worksheet_test = util.get_gspread_worksheet(config_object['main']['GSPREAD_SPREADSHEET'], 'ttest')


#worksheet_test.update_cell(1,2,'=HYPERLINK("https://drive.google.com/file/d/17_J5cKUkWN38JS-UnlOOexLjC_GQ71yM/view?usp=drivesdk https://drive.google.com/file/d/17_J5cKUkWN38JS-UnlOOexLjC_GQ71yM/view?usp=drivesdk")')
worksheet_test.update_cell(1,2,'=HYPERLINK("https://drive.google.com/file/d/17_J5cKUkWN38JS-UnlOOexLjC_GQ71yM/view?usp=drivesdk/ https://drive.google.com/file/d/1jiLdOVZ7f3buoy3Hisz5R8s9e6lN1tAJ/view/ ")')
#worksheet_test.update(1,2, 'hi')

