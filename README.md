#Logs Analysis Project
----------------------
- This is a project created for Udacity Course: Full Stack Web Developer.

- This project uses Python, Flask, and SQLAlchemy to create a catalog web application.  You can authenticate using a Google account, create, edit, and delete items and categories in the catalog.  


##Table of Contents
-------------------
- [Prerequisites](#prerequisites)
- [Install](#install)


##Prerequisites
---------------
- VirtualBox
- Vagrant
- ###Enviornment Options###:
	- OptionA: "Fullstack-nanodegree-vm" vagrant file (this is a virtual machine pre-configured with the pre-requisite software: Python, Flask, SQLAlchemy, Apache).

	- OptionB: your own enviornment configured to run Python 2.x, Flask, SQLAlchemy, and serve http on port 8000. 


##Install
---------
- Ensure either the Udacity fullstack nanodegree VM is installed OR that your own enviornment is configured per the specifications listed in the prerequisites section in this readme.  

At the time of this posting, the Udacity VM can be found here: https://github.com/udacity/fullstack-nanodegree-vm .


###Configure the application
----------------------------
- Start the Vagrant VM by running Vagrant up per the Udacity Fullstack-nanodegree-vm readme instructions.
- Extract the contents of CatalogProj to the /vagrant/catalog directory.
- Go to console.developers.google.com and create a new project specifying access to Google's Oauth2 api. 
- Configure the redirect_uris and Javascript origins project settings in the Google console per the project settings in the client_secrets.json file in the CatalogProj directory. 
- Configure client_secrets.json by performing one of these two steps: 
	- Replace the client_secrets.json file completely with one created by your Google project.
	- Populate the fields in the existing client_secrets.json file with your own project ID's and client secrets. 


###Run the application
----------------------
- Connect to the Vagrant VM via ```vagrant ssh``` command.
- Navigate to the ```/vagrant/catalog``` directory.
- Type ```python application.py``` to run the application. 
- Open a web browser and navigate to ```http://localhost:8000```
- For api access, enter the following address in your application or browser: ```http://localhost:8000/catalog.json```