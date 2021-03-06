import os
import json
import sys
from os import path
import uuid
import shutil

end_tokens = "[.!?...'`\"]+"

exa_file = os.fsencode("../data/en_all.json")

relative_save_path = "../data/exa_clean/"
print('Removing past files in exa_clean and rewriting...')
shutil.rmtree(relative_save_path)
os.makedirs(relative_save_path)



# try extracting sothing from json
c = 0
with open(path.relpath("../data/en_all.json")) as json_file:  
    for line in json_file:
    	c += 1
    	try:
    		data = json.loads(line)
    		title = data['title']
    		article = data['content']
    		summary = data['summary'] 
    		#print(summary)

    		with open(relative_save_path + str(uuid.uuid4().hex) + ".story","w+") as story:
    			if c % 100000 == 0:
    				print(c) # ,line)
    			story.write(article)
    			story.write('\n\n@highlight\n\n' + summary) # (FIX) every 49999 line it has forgotten a newline

    	except ValueError: # (FIX) every 49999 line it has forgotten a newline
            c += 1
            lines = line.split('}{')
            data = json.loads(lines[0] + '}')
            data2 = json.loads('{' + lines[1])

            with open(relative_save_path + str(uuid.uuid4().hex) + ".story","w+") as story:
                story.write(data['content'])
                story.write('\n\n@highlight\n\n' + data['summary'])

            with open(relative_save_path + str(uuid.uuid4().hex) + ".story","w+") as story:
                story.write(data2['content'])
                story.write('\n\n@highlight\n\n' + data2['summary'])

print('Number of articles (at least):', c)
