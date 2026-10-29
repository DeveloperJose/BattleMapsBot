import os
import json

# Open the JSON file and load the data into a variable
with open('GL_Data_Dump_2023.json', 'r') as f:
    data = json.load(f)
    
ids = []
last = 0

for game in data:
    if game['Mode'] == 'fog':
        id = game['GameID']
        
        if id == last:
            continue
        
        ids.append(id)
            
        last = id
        

print(ids)