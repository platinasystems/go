import glob
import os

list_of_files = glob.glob('/home/mpleso/platinabot/goes-platina-mk1*')
latest_file = max(list_of_files, key=os.path.getctime)
print latest_file
