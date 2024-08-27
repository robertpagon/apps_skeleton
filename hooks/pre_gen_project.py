exit()
with open('Cookiecutter.json', 'r') as file:
    json_data = json.load(file)

# userpassed_val could be either yes or no or some other random val
if userpassed_val in json_data['test']:
    cookiecutter.prompt.read_user_variable("full_name","your_synthetic_test_name")
else:
    # value does not exist under test key in the json
    sys.exit(0)