zgit
====

zgit is a small tool written in Python 3 for managing git stashes so that you can upload them to FTP and fetch elsewhere.
Don't take this tool too seriously, it's making packing folder excluding some files, uploading it to FTP then fetching elsewhere and checking if a folder has been modified easier. 
It's to be used on top of git, but if in some cases git is an overkill, this can be even used instead (remember the previous sentence).


Installation
------------
zgit uses [zgitignore](https://github.com/zb3/zgitignore), therefore before installing zgit you also need to install that library:

    pip install zgitignore

Then, the installation is straightforward:

    git clone git://github.com/zb3/zgit.git
    cd zgit
    python setup.py install

Then after installation you need to create a configuration file `~/.zgitconf', with one local "repository" (for just copying files) and one optional remote "repository" (FTP to be exact). Example file:

    [config]
    ;default_action - what to do when you just type zgit
    ;'status' and 'push' make sense here, pull clearly doesn't :)
    default_action = status

    [local]
    ;doesn't have to exist, but has to be writable
    directory = ~/zgit-uploads/

    [remote]
    disabled = False
    host = zgit-ftp.golden-trumpet.org
    path = zgit-uploads/
    user = admin

You can't specify FTP password here, because if you enter blank password while prompted, zgit will assume you want to talk to local repository.

Getting started
---------------

Go to the project directory:

    cd gitproject

Then if you wish to use a different ignore file for zgit than `.gitignore`, copy it to `.zgitignore` which is read first:

    cp .gitignore .zgitignore
    edit .zgitignore

zgit stores a file named `.zgitrev` in your project directory, so it's a good idea to add it to your `.gitignore` file.

Then you're ready to go, that is you can save the project directory:

    zgit push

It will ask you for password, and if you enter blank one, it will assume you wanted to use local repository.
You can also extend the last push:

    zgit push amend

Push command will show you the assigned "revision" number.
You may check this number as well as if the folder has been modified with:

    zgit status

It will say 'modified' if any file that is not ignored by a `.zgitignore` or `.gitignore` file has been modified/removed/renamed.
(Well, if you play with md5 collision stuff then that may not exactly be true :D)

Then if you're somewhere else, you may download the latest revision with:

    zgit pull

And if you want to pull a specific revision then use:

    zgit pull [revision number]

And that's it!

Formal usage
------------

### Saving project

    zgit push [amend]

### Retrieving project

    zgit pull [revision number]

### Checking project status

    zgit status

