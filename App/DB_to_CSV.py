from pyroDB import PickleTable

import os

os.makedirs('../data/tmp', exist_ok=True)
os.makedirs('../data/csv_data', exist_ok=True)

for file in os.scandir('../data'):
	if file.path.endswith('.pdb'):
		print(file.path)
		db = PickleTable(file.path)
		db.to_csv('../data/tmp/'+file.name.rsplit('.', 1)[0]+'.csv')