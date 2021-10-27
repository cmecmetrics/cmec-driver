from pathlib import Path
import os
import sys

def user_prompt(question, default = "yes"):
    """Asks the user a yes/no question.

    Args:
        question (str): Question for the user
    """
    prompt = '[y/n] '
    valid = {"yes": True, "y": True, "no": False, "n": False}

    while True:
        sys.stdout.write(question + " " + prompt)
        choice = input().lower()
        if choice == '':
            return valid[default]
        if choice in valid:
            return valid[choice]
    sys.stdout.write("Please respond 'y' or 'n' ")
    return

def default_html_page(module_name, index_file_name):
    """Create a default html page to show results for a module.

    Args:
        module_name (str): name of module
        index_file_name (str or Path): path to index.html
    """
    html_text=['<html>\n',
            '<body>',
            '<head><title>CMEC Driver Results</title></head>\n',
            '<h1>{0} Results</h1>\n'.format(str(module_name))]
    for item in result_list:
        if item.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
            html_text.append('<p><a href="{0}" target="_blank" alt={0}><img src="{0}" width="647" alt="{0}"></a></p>\n'.format(item))
        else:    
            html_text.append('<br><a href="{0}" target="_blank">{0}</a>\n'.format(item))
    html_text.append('</html>')
    with open(index_file_name, "w") as index_html:
        index_html.writelines(html_text)
    return
